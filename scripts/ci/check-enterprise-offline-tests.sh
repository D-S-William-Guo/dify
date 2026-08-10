#!/usr/bin/env bash

set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
offline_script="$repo_root/scripts/build-enterprise-offline.sh"
config_script="$repo_root/scripts/build-enterprise-config-package.sh"
check_script="$repo_root/scripts/ci/check-enterprise-offline.sh"
fixtures_dir="$repo_root/scripts/ci/check-enterprise-offline-fixtures"

tmp_root=$(mktemp -d)
trap 'rm -rf "$tmp_root"' EXIT

pass_count=0

new_fixture() {
  local name=$1
  local fixture="$tmp_root/$name"

  git clone --quiet --shared --no-tags "$repo_root" "$fixture"
  git -C "$fixture" config user.name "Enterprise Offline Guard Test"
  git -C "$fixture" config user.email "offline-guard@example.invalid"
  git -C "$fixture" switch --quiet --detach HEAD
  cp "$offline_script" "$fixture/scripts/build-enterprise-offline.sh"
  cp "$config_script" "$fixture/scripts/build-enterprise-config-package.sh"
  cp "$check_script" "$fixture/scripts/ci/check-enterprise-offline.sh"
  cp "$fixture/docker/.env.example" "$fixture/docker/.env"
  printf '%s\n' "$fixture"
}

real_git=$(command -v git)
real_python3=$(command -v python3)

fake_bin="$tmp_root/bin"
mkdir -p "$fake_bin"
cp "$fixtures_dir/bin/fake-docker" "$fake_bin/docker"
cp "$fixtures_dir/bin/fake-git" "$fake_bin/git"
for command_name in bash grep awk sed sort find tar mktemp mkdir rm cp printf sha256sum basename dirname tr chmod; do
  ln -s "$(command -v "$command_name")" "$fake_bin/$command_name"
done
ln -s "$real_python3" "$fake_bin/python3"

COMPOSE_IMAGES="postgres:15-alpine
dify-api-enterprise:1.16.0-enterprise
semitechnologies/weaviate:1.27.0
dify-web-enterprise:1.16.0-enterprise
ubuntu/squid:latest
langgenius/dify-agent-backend:1.16.0
busybox:latest
langgenius/dify-plugin-daemon:0.6.3-local
nginx:latest
dify-api-enterprise:1.16.0-enterprise
redis:6-alpine
dify-api-enterprise:1.16.0-enterprise
langgenius/dify-agent-local-sandbox:1.16.0
dify-api-enterprise:1.16.0-enterprise
langgenius/dify-sandbox:0.2.15"

ALL_IMAGES=$(printf '%s\n' "$COMPOSE_IMAGES" | sort -u)
EXPECTED_IMAGES_FILE=$(printf '%s\n' "$COMPOSE_IMAGES" | sort -u)

expect_pass() {
  local name=$1
  local fixture=$2
  shift 2

  if (cd "$fixture" && PATH="$fake_bin:$PATH" "$@") >"$tmp_root/$name.out" 2>&1; then
    printf 'ok - %s\n' "$name"
    pass_count=$((pass_count + 1))
    return
  fi

  printf 'not ok - %s (expected success)\n' "$name" >&2
  sed -n '1,40p' "$tmp_root/$name.out" >&2
  exit 1
}

expect_fail() {
  local name=$1
  local expected=$2
  local fixture=$3
  shift 3

  if (cd "$fixture" && PATH="$fake_bin:$PATH" "$@") >"$tmp_root/$name.out" 2>&1; then
    printf 'not ok - %s (expected failure)\n' "$name" >&2
    sed -n '1,40p' "$tmp_root/$name.out" >&2
    exit 1
  fi
  if ! grep -Fq "$expected" "$tmp_root/$name.out"; then
    printf 'not ok - %s (missing safe diagnostic: %s)\n' "$name" "$expected" >&2
    sed -n '1,40p' "$tmp_root/$name.out" >&2
    exit 1
  fi

  printf 'ok - %s\n' "$name"
  pass_count=$((pass_count + 1))
}

# --- reuse gate: enterprise image missing -----------------------------------
fixture=$(new_fixture reuse-missing)
expect_fail "reuse gate rejects missing enterprise image" "is not reusable" \
  "$fixture" ./scripts/build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse

# --- reuse gate: COMMIT_SHA mismatch -----------------------------------------
fixture=$(new_fixture reuse-mismatch)
export FAKE_DOCKER_IMAGES="dify-api-enterprise:1.16.0-enterprise dify-web-enterprise:1.16.0-enterprise"
export FAKE_DOCKER_COMMIT_SHA="1.15.0-enterprise"
export FAKE_DOCKER_COMPOSE_IMAGES="$COMPOSE_IMAGES"
expect_fail "reuse gate rejects COMMIT_SHA mismatch" "Expected COMMIT_SHA=1.16.0-enterprise" \
  "$fixture" ./scripts/build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse
unset FAKE_DOCKER_IMAGES FAKE_DOCKER_COMMIT_SHA FAKE_DOCKER_COMPOSE_IMAGES

# --- reuse gate: COMMIT_SHA match, full reuse run -----------------------------
fixture=$(new_fixture reuse-match)
export FAKE_DOCKER_IMAGES="$ALL_IMAGES"
export FAKE_DOCKER_COMMIT_SHA="1.16.0-enterprise"
export FAKE_DOCKER_COMPOSE_IMAGES="$COMPOSE_IMAGES"
export FAKE_DOCKER_LOG="$fixture/fake-docker.log"
export FAKE_DOCKER_OUT="$fixture/dist/offline"
expect_pass "reuse gate accepts matching enterprise image" \
  "$fixture" ./scripts/build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse
unset FAKE_DOCKER_LOG FAKE_DOCKER_OUT

if grep -Eq '^docker (build|pull) ' "$fixture/fake-docker.log"; then
  printf 'not ok - reuse run must not build or pull enterprise images\n' >&2
  sed -n '1,40p' "$fixture/fake-docker.log" >&2
  exit 1
fi
if ! grep -Eq '^docker save ' "$fixture/fake-docker.log"; then
  printf 'not ok - reuse run must produce the image bundle via docker save\n' >&2
  sed -n '1,40p' "$fixture/fake-docker.log" >&2
  exit 1
fi
if [[ ! -f "$fixture/dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar" ]]; then
  printf 'not ok - reuse run must write the offline image bundle archive\n' >&2
  exit 1
fi
printf 'ok - reuse run saves the image bundle without building or pulling\n'
pass_count=$((pass_count + 1))
unset FAKE_DOCKER_IMAGES FAKE_DOCKER_COMMIT_SHA FAKE_DOCKER_COMPOSE_IMAGES

# --- image list parsing -------------------------------------------------------
if [[ "$(tr -d '\n' < "$fixture/dist/offline/images-1.16.0-enterprise.txt")" != "$(printf '%s' "$EXPECTED_IMAGES_FILE" | tr -d '\n')" ]]; then
  printf 'not ok - images-*.txt must equal compose config --images | sort -u\n' >&2
  diff <(cat "$fixture/dist/offline/images-1.16.0-enterprise.txt") <(printf '%s\n' "$EXPECTED_IMAGES_FILE") >&2 || true
  exit 1
fi
for required in \
  "langgenius/dify-agent-backend:1.16.0" \
  "langgenius/dify-agent-local-sandbox:1.16.0" \
  "dify-api-enterprise:1.16.0-enterprise" \
  "dify-web-enterprise:1.16.0-enterprise"; do
  if ! grep -Fxq "$required" "$fixture/dist/offline/images-1.16.0-enterprise.txt"; then
    printf 'not ok - images-*.txt missing required image: %s\n' "$required" >&2
    exit 1
  fi
done
printf 'ok - images-*.txt matches compose image list and required images\n'
pass_count=$((pass_count + 1))

# --- manifest schema ----------------------------------------------------------
if python3 - "$fixture/dist/offline/manifest-1.16.0-enterprise.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
for field in ("version", "baseline", "enterprise_commit", "image_tag", "generated_at", "images"):
    assert field in manifest, f"missing manifest field: {field}"
assert manifest["baseline"] == {"tag": "1.16.0", "commit": "5c6372d2f76d240265b92fd27c16bc772ffcb107"}, "baseline mismatch"
assert manifest["version"] == manifest["image_tag"] == "1.16.0-enterprise", "version/image_tag mismatch"
assert manifest["enterprise_commit"] == "1111111111111111111111111111111111111111", "enterprise_commit not from git shim"
assert isinstance(manifest["images"], list) and manifest["images"], "images[] empty"
for entry in manifest["images"]:
    assert set(entry) >= {"name", "id", "digest"}, f"images[] entry missing fields: {entry}"
    assert entry["name"], "image name empty"
    assert entry["id"], f"image id empty: {entry['name']}"
    assert entry["digest"], f"image digest empty: {entry['name']}"
PY
then
  printf 'ok - manifest schema complete (version/baseline/enterprise_commit/image_tag/generated_at/images[]name,id,digest)\n'
  pass_count=$((pass_count + 1))
else
  printf 'not ok - manifest schema validation failed\n' >&2
  exit 1
fi

# --- -CheckOnly dry-run: no build/pull/save ------------------------------------
fixture=$(new_fixture checkonly)
export FAKE_DOCKER_IMAGES="$ALL_IMAGES"
export FAKE_DOCKER_COMMIT_SHA="1.16.0-enterprise"
export FAKE_DOCKER_COMPOSE_IMAGES="$COMPOSE_IMAGES"
export FAKE_DOCKER_LOG="$fixture/fake-docker.log"
export FAKE_DOCKER_OUT="$fixture/dist/offline"
expect_pass "-CheckOnly dry-run passes reuse gate" \
  "$fixture" ./scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse
unset FAKE_DOCKER_LOG FAKE_DOCKER_OUT

if grep -Eq '^docker (build|pull|save) ' "$fixture/fake-docker.log"; then
  printf 'not ok - -CheckOnly must never build, pull, or save\n' >&2
  sed -n '1,40p' "$fixture/fake-docker.log" >&2
  exit 1
fi
if [[ ! -f "$fixture/dist/offline/images-1.16.0-enterprise.txt" || ! -f "$fixture/dist/offline/manifest-1.16.0-enterprise.json" ]]; then
  printf 'not ok - -CheckOnly must write images-*.txt and manifest\n' >&2
  exit 1
fi
if [[ -e "$fixture/dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar" ]]; then
  printf 'not ok - -CheckOnly must not write the image bundle\n' >&2
  exit 1
fi
printf 'ok - -CheckOnly dry-run forbids build/pull/save and writes images+manifest\n'
pass_count=$((pass_count + 1))
unset FAKE_DOCKER_IMAGES FAKE_DOCKER_COMMIT_SHA FAKE_DOCKER_COMPOSE_IMAGES

# --- config package dependency: missing manifest/images ------------------------
fixture=$(new_fixture config-no-deps)
expect_fail "config package fails without manifest or images" "Missing offline manifest" \
  "$fixture" ./scripts/build-enterprise-config-package.sh -Version 1.16.0-enterprise

# --- config package content -----------------------------------------------------
fixture=$(new_fixture config-content)
export FAKE_DOCKER_IMAGES="$ALL_IMAGES"
export FAKE_DOCKER_COMMIT_SHA="1.16.0-enterprise"
export FAKE_DOCKER_COMPOSE_IMAGES="$COMPOSE_IMAGES"
expect_pass "config package prerequisite offline artifacts" \
  "$fixture" ./scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse
unset FAKE_DOCKER_IMAGES FAKE_DOCKER_COMMIT_SHA FAKE_DOCKER_COMPOSE_IMAGES
expect_pass "config package builds tar.gz" \
  "$fixture" ./scripts/build-enterprise-config-package.sh -Version 1.16.0-enterprise

config_archive="$fixture/dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz"
config_listing="$tmp_root/config-content-listing.txt"
tar tzf "$config_archive" | sed 's#^./##' | sort > "$config_listing"

for entry in \
  "docker/docker-compose.yaml" \
  "docker/docker-compose.enterprise.yaml" \
  "docker/.env.example" \
  "dist/offline/manifest-1.16.0-enterprise.json" \
  "dist/offline/images-1.16.0-enterprise.txt" \
  "docker/nginx/" \
  "docker/ssrf_proxy/"; do
  if ! grep -Fxq "$entry" "$config_listing"; then
    printf 'not ok - config archive missing required entry: %s\n' "$entry" >&2
    exit 1
  fi
done
env_count=$(grep -c '^docker/envs/.*\.env\.example$' "$config_listing")
if [[ "$env_count" -ne 37 ]]; then
  printf 'not ok - config archive must include all 37 env examples (found %s)\n' "$env_count" >&2
  exit 1
fi
if grep -Eq '^docker/volumes/|^docker/.*/\.env$|(^|/)\.git($|/)|node_modules|/\.venv/|/\.next/|\.env\.production$' "$config_listing"; then
  printf 'not ok - config archive contains a forbidden entry\n' >&2
  grep -E '^docker/volumes/|^docker/.*/\.env$|(^|/)\.git($|/)|node_modules|/\.venv/|/\.next/|\.env\.production$' "$config_listing" >&2
  exit 1
fi
for forbidden in \
  "docker/ENTERPRISE_DEPLOY_STARTUP.md" \
  "docker/dify-env-sync.py" \
  "docker/dify-env-sync.sh" \
  "docker/README.enterprise.md" \
  "scripts/check-enterprise-vector-indexes.sh"; do
  if grep -Fxq "$forbidden" "$config_listing"; then
    printf 'not ok - config archive must not contain 1.15-only file: %s\n' "$forbidden" >&2
    exit 1
  fi
done
printf 'ok - config package contains compose + 37 env examples + nginx/ssrf_proxy + manifest/images, no forbidden entries\n'
pass_count=$((pass_count + 1))

# --- check script: clean artifacts PASS -----------------------------------------
export FAKE_DOCKER_IMAGES="$ALL_IMAGES"
export FAKE_DOCKER_COMMIT_SHA="1.16.0-enterprise"
export FAKE_DOCKER_COMPOSE_IMAGES="$COMPOSE_IMAGES"
export FAKE_DOCKER_OUT="$fixture/dist/offline"
expect_pass "check-enterprise-offline passes on clean artifacts" \
  "$fixture" ./scripts/ci/check-enterprise-offline.sh \
  -Archive "dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar" \
  -ConfigArchive "dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz" \
  -Manifest "dist/offline/manifest-1.16.0-enterprise.json" \
  -Images "dist/offline/images-1.16.0-enterprise.txt"
unset FAKE_DOCKER_IMAGES FAKE_DOCKER_COMMIT_SHA FAKE_DOCKER_COMPOSE_IMAGES FAKE_DOCKER_OUT

# --- check script: canary real .env rejected ------------------------------------
fixture=$(new_fixture check-canary-env)
mkdir -p "$fixture/canary/docker/envs/core-services" "$fixture/canary/docker/volumes"
printf '%s\n' 'DB_PASSWORD=super-secret' > "$fixture/canary/docker/.env"
printf '%s\n' 'x' > "$fixture/canary/docker/envs/core-services/api.env.example"
printf '%s\n' 'x' > "$fixture/canary/docker/volumes/runtime"
(
  cd "$fixture/canary"
  tar czf "$fixture/canary-bad.tar.gz" docker/.env docker/envs/core-services/api.env.example docker/volumes/runtime
)
expect_fail "check rejects real .env in config archive" "real environment file" \
  "$fixture" ./scripts/ci/check-enterprise-offline.sh \
  -Archive "dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar" \
  -ConfigArchive "canary-bad.tar.gz" \
  -Manifest "dist/offline/manifest-1.16.0-enterprise.json" \
  -Images "dist/offline/images-1.16.0-enterprise.txt"

# --- check script: canary dev default key without WARNING rejected ---------------
fixture=$(new_fixture check-canary-secret)
mkdir -p "$fixture/canary/docker/envs/core-services"
printf '%s\n' 'DIFY_AGENT_SERVER_SECRET_KEY=MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY' \
  > "$fixture/canary/docker/envs/core-services/api.env.example"
(
  cd "$fixture/canary"
  tar czf "$fixture/canary-bad.tar.gz" docker/envs/core-services/api.env.example
)
expect_fail "check rejects dev default secret without WARNING" "without an adjacent WARNING marker" \
  "$fixture" ./scripts/ci/check-enterprise-offline.sh \
  -Archive "dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar" \
  -ConfigArchive "canary-bad.tar.gz" \
  -Manifest "dist/offline/manifest-1.16.0-enterprise.json" \
  -Images "dist/offline/images-1.16.0-enterprise.txt"

# --- check script: canary docker/volumes entry rejected --------------------------
fixture=$(new_fixture check-canary-volume)
mkdir -p "$fixture/canary/docker/volumes/sandbox"
printf '%s\n' 'x' > "$fixture/canary/docker/volumes/sandbox/data"
(
  cd "$fixture/canary"
  tar czf "$fixture/canary-bad.tar.gz" docker/volumes/sandbox/data
)
expect_fail "check rejects docker volume entries" "docker/volumes runtime data" \
  "$fixture" ./scripts/ci/check-enterprise-offline.sh \
  -Archive "dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar" \
  -ConfigArchive "canary-bad.tar.gz" \
  -Manifest "dist/offline/manifest-1.16.0-enterprise.json" \
  -Images "dist/offline/images-1.16.0-enterprise.txt"

# --- check script: manifest/images/missing required args fail --------------------
fixture=$(new_fixture check-canary-missing-images)
: > "$fixture/empty-images.txt"
: > "$fixture/empty-manifest.json"
expect_fail "check rejects empty images file" "required image missing" \
  "$fixture" ./scripts/ci/check-enterprise-offline.sh \
  -Archive "missing.tar" \
  -ConfigArchive "missing.tar.gz" \
  -Manifest "empty-manifest.json" \
  -Images "empty-images.txt"

printf 'all %d enterprise offline tests passed\n' "$pass_count"
