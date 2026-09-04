#!/usr/bin/env bash

set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
offline_script="$repo_root/scripts/build-enterprise-offline.sh"
config_script="$repo_root/scripts/build-enterprise-config-package.sh"
check_script="$repo_root/scripts/ci/check-enterprise-offline.sh"
fake_docker="$repo_root/scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker"
tmp_root=$(mktemp -d)
trap 'rm -rf "$tmp_root"' EXIT
pass_count=0

real_git=$(command -v git)
real_python3=$(command -v python3)
fake_bin="$tmp_root/bin"
mkdir -p "$fake_bin"
cp "$fake_docker" "$fake_bin/docker"
ln -s "$real_git" "$fake_bin/git"
ln -s "$real_python3" "$fake_bin/python3"
for command_name in bash grep awk sed sort find tar mktemp mkdir rm cp printf sha256sum basename dirname tr chmod mv cut; do
  ln -s "$(command -v "$command_name")" "$fake_bin/$command_name"
done

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

new_fixture() {
  local fixture="$tmp_root/$1"
  git clone --quiet --shared --no-tags "$repo_root" "$fixture"
  git -C "$fixture" switch --quiet --detach HEAD
  cp "$fixture/docker/.env.example" "$fixture/docker/.env"
  printf '%s\n' "$fixture"
}

fake_defaults() {
  local fixture=$1
  export FAKE_DOCKER_IMAGES="$ALL_IMAGES"
  export FAKE_DOCKER_COMPOSE_IMAGES="$COMPOSE_IMAGES"
  export FAKE_DOCKER_COMMIT_SHA
  FAKE_DOCKER_COMMIT_SHA=$(git -C "$fixture" rev-parse HEAD)
  export FAKE_DOCKER_LOG="$fixture/fake-docker.log"
  unset FAKE_DOCKER_NO_DIGEST FAKE_DOCKER_BAD_ID FAKE_DOCKER_MISMATCH_DIGEST
  unset FAKE_DOCKER_MULTIPLE_DIGEST FAKE_DOCKER_WEB_CONTEXT_LISTING
  unset FAKE_DOCKER_SAVE_STYLE FAKE_DOCKER_SAVE_CASE
  unset HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy
}

expect_pass() {
  local name=$1 fixture=$2
  shift 2
  if (cd "$fixture" && PATH="$fake_bin:$PATH" OFFLINE_GATE_REPO_ROOT="$fixture" "$@") >"$tmp_root/$name.out" 2>&1; then
    printf 'ok - %s\n' "$name"
    pass_count=$((pass_count + 1))
    return
  fi
  printf 'not ok - %s (expected success)\n' "$name" >&2
  sed -n '1,80p' "$tmp_root/$name.out" >&2
  exit 1
}

expect_fail() {
  local name=$1 expected=$2 fixture=$3
  shift 3
  if (cd "$fixture" && PATH="$fake_bin:$PATH" OFFLINE_GATE_REPO_ROOT="$fixture" "$@") >"$tmp_root/$name.out" 2>&1; then
    printf 'not ok - %s (expected failure)\n' "$name" >&2
    sed -n '1,80p' "$tmp_root/$name.out" >&2
    exit 1
  fi
  if ! grep -Fq "$expected" "$tmp_root/$name.out"; then
    printf 'not ok - %s (missing diagnostic: %s)\n' "$name" "$expected" >&2
    sed -n '1,80p' "$tmp_root/$name.out" >&2
    exit 1
  fi
  printf 'ok - %s\n' "$name"
  pass_count=$((pass_count + 1))
}

build_release() {
  local name=$1 fixture=$2
  expect_pass "$name" "$fixture" "$offline_script" -Version 1.16.0-enterprise -Mode rebuild
}

build_config() {
  local name=$1 fixture=$2
  expect_pass "$name" "$fixture" "$config_script" -Version 1.16.0-enterprise
}

check_args() {
  printf '%s\n' \
    -Archive dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar \
    -ConfigArchive dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz \
    -Manifest dist/offline/manifest-1.16.0-enterprise.json \
    -Images dist/offline/images-1.16.0-enterprise.txt
}

mutate_config() {
  local source=$1 output=$2 mutation=$3
  python3 - "$source" "$output" "$mutation" <<'PY'
import copy
import io
import sys
import tarfile

source, output, mutation = sys.argv[1:]
with tarfile.open(source, "r:gz") as archive:
    entries = []
    for member in archive.getmembers():
        data = archive.extractfile(member).read() if member.isreg() else b""
        entries.append((copy.copy(member), data))

def regular(name, data=b"synthetic\n"):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    return info, data

if mutation == "env": entries.append(regular("docker/.env"))
elif mutation == "volume": entries.append(regular("docker/volumes/runtime/data"))
elif mutation == "keycert": entries.extend((regular("docker/nginx/server.key"), regular("docker/nginx/server.crt")))
elif mutation == "credential": entries.append(regular("docker/nginx/credentials/token"))
elif mutation == "duplicate": entries.append((copy.copy(entries[0][0]), entries[0][1]))
elif mutation == "absolute": entries.append(regular("/absolute"))
elif mutation == "traversal": entries.append(regular("../outside"))
elif mutation in {"symlink", "hardlink", "device", "fifo", "wrongtype"}:
    name = "docker/.env.example" if mutation == "wrongtype" else f"docker/nginx/{mutation}"
    info = tarfile.TarInfo(name)
    info.type = {"symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE, "device": tarfile.CHRTYPE, "fifo": tarfile.FIFOTYPE, "wrongtype": tarfile.SYMTYPE}[mutation]
    info.linkname = "docker/docker-compose.yaml"
    if mutation == "wrongtype": entries = [(info, b"") if item.name == name else (item, data) for item, data in entries]
    else: entries.append((info, b""))
elif mutation == "missing": entries = entries[1:]
elif mutation == "extra": entries.append(regular("docker/nginx/extra.conf"))
elif mutation in {"devbad", "devwarn"}:
    secret = b"DIFY_AGENT_SERVER_SECRET_KEY=MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY\n"
    if mutation == "devwarn": secret += b"# WARNING: Replace this development default in production\n"
    for index, (item, data) in enumerate(entries):
        if item.name == "docker/.env.example":
            item.size = len(secret)
            entries[index] = (item, secret)
else: raise SystemExit(f"unknown mutation: {mutation}")

with tarfile.open(output, "w:gz") as archive:
    for member, data in entries:
        archive.addfile(member, io.BytesIO(data) if member.isreg() else None)
PY
}

mutate_manifest() {
  local source=$1 output=$2 mutation=$3
  python3 - "$source" "$output" "$mutation" <<'PY'
import json
import sys

source, output, mutation = sys.argv[1:]
data = json.load(open(source, encoding="utf-8"))
if mutation == "duplicate": data["images"].append(dict(data["images"][0]))
elif mutation == "omit": data["images"].pop()
elif mutation == "reorder": data["images"][0], data["images"][1] = data["images"][1], data["images"][0]
elif mutation == "rename": data["images"][0]["name"] = "renamed.invalid:1"
elif mutation == "candidate": data["enterprise_commit"] = "2" * 40
elif mutation == "badid": data["images"][0]["id"] = "not-an-id"
elif mutation == "emptyid": data["images"][0]["id"] = ""
elif mutation == "baddigest": data["images"][0]["digest"] = "other.example/repo@sha256:" + "3" * 64
else: raise SystemExit(f"unknown mutation: {mutation}")
json.dump(data, open(output, "w", encoding="utf-8"), indent=2)
PY
}

# P02: convenience modes cannot emit a normal release package.
fixture=$(new_fixture p02-modes)
fake_defaults "$fixture"
expect_fail "P02 reuse cannot emit release provenance" "requires explicit -Mode rebuild" "$fixture" \
  "$offline_script" -Version 1.16.0-enterprise -Mode reuse
expect_fail "P02 smart cannot emit release provenance" "requires explicit -Mode rebuild" "$fixture" \
  "$offline_script" -Version 1.16.0-enterprise -Mode smart

# R01/P02: check-only reuse remains side-effect-free and explicitly non-release.
expect_pass "R01 check-only reuse remains available" "$fixture" \
  "$offline_script" -CheckOnly -Version 1.16.0-enterprise -Mode reuse
if grep -Eq '^docker (build|pull|save|run) ' "$fixture/fake-docker.log" ||
  ! grep -Fq '"release_gate": false' "$fixture/dist/offline/manifest-1.16.0-enterprise.json"; then
  printf 'not ok - R01 check-only must be side-effect-free and non-release\n' >&2
  exit 1
fi
printf 'ok - R01 check-only emits no release provenance or build/pull/save/run call\n'
pass_count=$((pass_count + 1))

fixture=$(new_fixture p02-dirty)
fake_defaults "$fixture"
printf '\n# synthetic dirty candidate\n' >> "$fixture/api/Dockerfile"
expect_fail "P02 dirty candidate rebuild fails closed" "must match the exact candidate" "$fixture" \
  "$offline_script" -Version 1.16.0-enterprise -Mode rebuild

fixture=$(new_fixture m03-build-label)
fake_defaults "$fixture"
export FAKE_DOCKER_COMMIT_SHA="2222222222222222222222222222222222222222"
expect_fail "M03 first-party build commit mismatch fails" "is not bound to candidate" "$fixture" \
  "$offline_script" -Version 1.16.0-enterprise -Mode rebuild

# P01/A01/W01/M04: one clean synthetic rebuild exercises both audited contexts.
fixture=$(new_fixture release-base)
mkdir -p "$fixture/web/nested/.env.local" "$fixture/e2e/nested"
printf 'SYNTHETIC_WEB_ENV=1\n' > "$fixture/web/nested/.env"
printf 'SYNTHETIC_WEB_ENV_DIR=1\n' > "$fixture/web/nested/.env.local/value"
printf 'SYNTHETIC_E2E_ENV=1\n' > "$fixture/e2e/nested/.env.local"
ln -s .env.local "$fixture/e2e/nested/.env"
fake_defaults "$fixture"
export FAKE_DOCKER_WEB_CONTEXT_LISTING="$fixture/web-context.txt"
export FAKE_DOCKER_MULTIPLE_DIGEST="postgres:15-alpine"
export FAKE_DOCKER_MISMATCH_DIGEST="redis:6-alpine"
build_release "P01 explicit rebuild creates candidate-bound release artifacts" "$fixture"

candidate=$(git -C "$fixture" rev-parse HEAD)
if ! grep -Fq -- "--build-arg COMMIT_SHA=$candidate -f $fixture/api/Dockerfile -t dify-api-enterprise:1.16.0-enterprise $fixture" "$fixture/fake-docker.log"; then
  printf 'not ok - A01 API build must use api/Dockerfile and repository-root context\n' >&2
  sed -n '1,30p' "$fixture/fake-docker.log" >&2
  exit 1
fi
printf 'ok - A01 API build uses repository-root context and candidate SHA\n'
pass_count=$((pass_count + 1))

# H01-H05: host proxy is explicit, passes names only, and never reaches outputs.
fixture_proxy=$(new_fixture host-proxy)
fake_defaults "$fixture_proxy"
proxy_canary=$(mktemp "$tmp_root/proxy-canary.XXXXXX")
expect_pass "H01 default build omits host proxy options" "$fixture_proxy" \
  "$offline_script" -Version 1.16.0-enterprise -Mode rebuild
if grep -Eq -- '--network=host|--build-arg (HTTP_PROXY|HTTPS_PROXY|ALL_PROXY|NO_PROXY|http_proxy|https_proxy|all_proxy|no_proxy)' "$fixture_proxy/fake-docker.log"; then
  printf 'not ok - H01 default build must not enable host proxy options\n' >&2
  exit 1
fi
printf 'ok - H01 default build omits host proxy options\n'
pass_count=$((pass_count + 1))

fixture_proxy=$(new_fixture host-proxy-opt-in)
fake_defaults "$fixture_proxy"
expect_pass "H02 opt-in forwards all proxy variable names to API and Web" "$fixture_proxy" \
  env HTTP_PROXY="$proxy_canary" HTTPS_PROXY="$proxy_canary" ALL_PROXY="$proxy_canary" NO_PROXY="$proxy_canary" \
  http_proxy="$proxy_canary" https_proxy="$proxy_canary" all_proxy="$proxy_canary" no_proxy="$proxy_canary" \
  "$offline_script" -Version 1.16.0-enterprise -Mode rebuild -UseHostProxy
if [[ "$(grep -Ec '^docker build ' "$fixture_proxy/fake-docker.log")" -ne 2 ]] ||
  [[ "$(grep -Fc -- '--network=host' "$fixture_proxy/fake-docker.log")" -ne 2 ]]; then
  printf 'not ok - H02 API and Web builds must both use host networking\n' >&2
  exit 1
fi
for proxy_variable in HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy; do
  if [[ "$(grep -Fc -- "--build-arg $proxy_variable" "$fixture_proxy/fake-docker.log")" -ne 2 ]]; then
    printf 'not ok - H02 missing name-only build argument for %s\n' "$proxy_variable" >&2
    exit 1
  fi
done
if grep -Fq -- "$proxy_canary" "$fixture_proxy/fake-docker.log" ||
  grep -R -Fq -- "$proxy_canary" "$fixture_proxy/dist"; then
  printf 'not ok - H02 synthetic proxy value reached an argv capture or generated artifact\n' >&2
  exit 1
fi
printf 'ok - H02 opt-in uses host networking and name-only proxy arguments without values\n'
pass_count=$((pass_count + 1))

fixture_proxy=$(new_fixture host-proxy-unset)
fake_defaults "$fixture_proxy"
expect_pass "H03 unset proxy variables are omitted" "$fixture_proxy" \
  env HTTP_PROXY="$proxy_canary" "$offline_script" -Version 1.16.0-enterprise -Mode rebuild -UseHostProxy
if grep -Eq -- '--build-arg (HTTPS_PROXY|ALL_PROXY|NO_PROXY|http_proxy|https_proxy|all_proxy|no_proxy)' "$fixture_proxy/fake-docker.log"; then
  printf 'not ok - H03 unset proxy variables must not be forwarded\n' >&2
  exit 1
fi
printf 'ok - H03 unset proxy variables are omitted\n'
pass_count=$((pass_count + 1))

fixture_proxy=$(new_fixture host-proxy-missing)
fake_defaults "$fixture_proxy"
expect_fail "H04 host proxy without a usable proxy fails before build" "requires a configured" "$fixture_proxy" \
  env NO_PROXY="$proxy_canary" no_proxy="$proxy_canary" \
  "$offline_script" -Version 1.16.0-enterprise -Mode rebuild -UseHostProxy
if [[ -f "$fixture_proxy/fake-docker.log" ]] && grep -Eq '^docker build ' "$fixture_proxy/fake-docker.log"; then
  printf 'not ok - H04 host proxy failure must occur before fake Docker build\n' >&2
  exit 1
fi
printf 'ok - H04 host proxy without a usable proxy fails before fake Docker build\n'
pass_count=$((pass_count + 1))

fixture_proxy=$(new_fixture host-proxy-empty)
fake_defaults "$fixture_proxy"
expect_fail "H05 host proxy with empty primary proxy fails before build" "requires a configured" "$fixture_proxy" \
  env HTTP_PROXY= "$offline_script" -Version 1.16.0-enterprise -Mode rebuild -UseHostProxy
if [[ -f "$fixture_proxy/fake-docker.log" ]] && grep -Eq '^docker build ' "$fixture_proxy/fake-docker.log"; then
  printf 'not ok - H05 empty primary proxy failure must occur before fake Docker build\n' >&2
  exit 1
fi
printf 'ok - H05 host proxy with empty primary proxy fails before fake Docker build\n'
pass_count=$((pass_count + 1))

if grep -Eq '(^|/)\.env($|\.)' "$fixture/web-context.txt" ||
  ! grep -Fxq 'web/package.json' "$fixture/web-context.txt" ||
  ! grep -Fxq 'e2e/package.json' "$fixture/web-context.txt" ||
  ! grep -Fxq 'packages/dify-ui/package.json' "$fixture/web-context.txt" ||
  ! grep -Fxq 'sdks/nodejs-client/package.json' "$fixture/web-context.txt"; then
  printf 'not ok - W01 temporary Web context prune failed\n' >&2
  exit 1
fi
printf 'ok - W01 nested .env/.env.* canaries are absent from the Web build context\n'
pass_count=$((pass_count + 1))

if ! grep -Fxq '*' "$fixture/api/Dockerfile.dockerignore" ||
  ! grep -Fxq '!api/**' "$fixture/api/Dockerfile.dockerignore" ||
  ! grep -Fxq '!dify-agent/src/**' "$fixture/api/Dockerfile.dockerignore" ||
  ! grep -Fxq '*.env.*' "$fixture/api/Dockerfile.dockerignore" ||
  ! grep -Fxq 'api/storage/**' "$fixture/api/Dockerfile.dockerignore"; then
  printf 'not ok - A02 API Dockerfile-specific ignore contract changed\n' >&2
  exit 1
fi
printf 'ok - A02 API ignore remains deny-by-default with env/runtime exclusions\n'
pass_count=$((pass_count + 1))

if ! python3 - "$fixture/dist/offline/manifest-1.16.0-enterprise.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
by_name = {entry["name"]: entry for entry in data["images"]}
assert data["release_gate"] is True and data["mode"] == "rebuild"
assert by_name["postgres:15-alpine"]["digest"].startswith("postgres@sha256:")
assert by_name["redis:6-alpine"]["digest"] == ""
PY
then
  printf 'not ok - M04 repository-matched RepoDigest selection failed\n' >&2
  exit 1
fi
printf 'ok - M04 matching RepoDigest is selected and mismatched-only provenance is omitted\n'
pass_count=$((pass_count + 1))

build_config "C01 config package builds from exact candidate members" "$fixture"
config_archive="$fixture/dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz"
if [[ "$(tar tzf "$config_archive" | wc -l)" -ne 51 ]] || tar tvzf "$config_archive" | grep -q '^d'; then
  printf 'not ok - C01 config archive must contain exactly 51 regular members\n' >&2
  exit 1
fi
printf 'ok - C01 config archive has exactly 49 source plus 2 generated regular members\n'
pass_count=$((pass_count + 1))

mapfile -t base_check_args < <(check_args)
expect_pass "M01 exact metadata graph passes" "$fixture" "$check_script" "${base_check_args[@]}"

# C02: producer never expands its candidate member set.
fixture_c02=$(new_fixture c02-inputs)
fake_defaults "$fixture_c02"
build_release "C02 prerequisite release build" "$fixture_c02"
mkdir -p "$fixture_c02/docker/envs/rogue" "$fixture_c02/docker/nginx/credentials" "$fixture_c02/docker/ssrf_proxy/volumes"
printf 'x\n' > "$fixture_c02/docker/envs/rogue/rogue.env.example"
printf 'x\n' > "$fixture_c02/docker/nginx/.env"
printf 'x\n' > "$fixture_c02/docker/nginx/private.key"
printf 'x\n' > "$fixture_c02/docker/nginx/server.crt"
printf 'x\n' > "$fixture_c02/docker/nginx/credentials/token"
printf 'x\n' > "$fixture_c02/docker/ssrf_proxy/volumes/runtime"
expect_fail "C02 producer rejects working-tree expansion canaries" "non-candidate" "$fixture_c02" \
  "$config_script" -Version 1.16.0-enterprise

# C03-C08/R01: mutate only synthetic config metadata/content; never extract it.
declare -a config_cases=(
  "C03 real .env|env|real environment file"
  "C04 runtime volume|volume|docker/volumes runtime data"
  "C05 key and certificate|keycert|credential, key, or certificate"
  "C06 credential directory|credential|credential-path member"
  "C07 duplicate member|duplicate|duplicate config member"
  "C07 absolute member|absolute|unsafe archive member"
  "C07 traversal member|traversal|unsafe archive member"
  "C07 symlink member|symlink|non-regular config member"
  "C07 hardlink member|hardlink|non-regular config member"
  "C07 device member|device|non-regular config member"
  "C07 FIFO member|fifo|non-regular config member"
  "C08 missing member|missing|missing config member"
  "C08 unexpected member|extra|unexpected config member"
  "C08 allowed name wrong type|wrongtype|non-regular config member"
  "R01 dev default without warning|devbad|without required WARNING"
)
for row in "${config_cases[@]}"; do
  IFS='|' read -r label mutation diagnostic <<< "$row"
  output="$fixture/dist/offline/config-$mutation.tar.gz"
  mutate_config "$config_archive" "$output" "$mutation"
  expect_fail "$label fails closed" "$diagnostic" "$fixture" "$check_script" \
    -Archive dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar \
    -ConfigArchive "dist/offline/config-$mutation.tar.gz" \
    -Manifest dist/offline/manifest-1.16.0-enterprise.json \
    -Images dist/offline/images-1.16.0-enterprise.txt
done
warned_archive="$fixture/dist/offline/config-devwarn.tar.gz"
mutate_config "$config_archive" "$warned_archive" devwarn
expect_pass "R01 dev default with warning passes bounded member read" "$fixture" "$check_script" \
  -Archive dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar \
  -ConfigArchive dist/offline/config-devwarn.tar.gz \
  -Manifest dist/offline/manifest-1.16.0-enterprise.json \
  -Images dist/offline/images-1.16.0-enterprise.txt

# M02-M05: image-list and release-manifest mutations fail identity validation.
manifest_source="$fixture/dist/offline/manifest-1.16.0-enterprise.json"
for mutation in duplicate omit reorder rename; do
  bad_manifest="$fixture/dist/offline/manifest-$mutation.json"
  mutate_manifest "$manifest_source" "$bad_manifest" "$mutation"
  expect_fail "M02 $mutation manifest image fails" "manifest image names" "$fixture" "$check_script" \
    -Archive dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar \
    -ConfigArchive dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz \
    -Manifest "dist/offline/manifest-$mutation.json" \
    -Images dist/offline/images-1.16.0-enterprise.txt
done
for mutation in candidate badid emptyid baddigest; do
  bad_manifest="$fixture/dist/offline/manifest-$mutation.json"
  mutate_manifest "$manifest_source" "$bad_manifest" "$mutation"
  case "$mutation" in
    candidate) label=M03; diagnostic="candidate does not match" ;;
    badid|emptyid) label=M05; diagnostic="immutable image ID" ;;
    baddigest) label=M04; diagnostic="repository-mismatched" ;;
  esac
  expect_fail "$label $mutation evidence fails" "$diagnostic" "$fixture" "$check_script" \
    -Archive dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar \
    -ConfigArchive dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz \
    -Manifest "dist/offline/manifest-$mutation.json" \
    -Images dist/offline/images-1.16.0-enterprise.txt
done

# M06: Docker 29 Config paths bind without opening layers.
fixture_m06=$(new_fixture m06-docker29)
fake_defaults "$fixture_m06"
export FAKE_DOCKER_SAVE_STYLE=docker29
build_release "M06 Docker 29 synthetic bundle builds" "$fixture_m06"
build_config "M06 Docker 29 config package builds" "$fixture_m06"
mapfile -t m06_args < <(check_args)
expect_pass "M06 Docker 29 Config metadata binds" "$fixture_m06" "$check_script" "${m06_args[@]}"

# M07: every observed required-metadata defect is FAIL, never NOT_RUN.
for mutation in missing duplicate nonregular malformed oversized inconsistent; do
  bad_bundle="$fixture/dist/offline/bundle-$mutation.tar"
  (cd "$fixture" && PATH="$fake_bin:$PATH" FAKE_DOCKER_SAVE_CASE="$mutation" docker save -o "$bad_bundle" $ALL_IMAGES)
  expect_fail "M07 $mutation Docker-save metadata fails" "image bundle metadata validation failed" "$fixture" \
    "$check_script" \
    -Archive "dist/offline/bundle-$mutation.tar" \
    -ConfigArchive dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz \
    -Manifest dist/offline/manifest-1.16.0-enterprise.json \
    -Images dist/offline/images-1.16.0-enterprise.txt
  if grep -Fq 'NOT_RUN:' "$tmp_root/M07 $mutation Docker-save metadata fails.out"; then
    printf 'not ok - M07 observed metadata failure must not be NOT_RUN\n' >&2
    exit 1
  fi
done

# M05 producer-side malformed ID also fails before save.
fixture_m05=$(new_fixture m05-producer)
fake_defaults "$fixture_m05"
export FAKE_DOCKER_BAD_ID="redis:6-alpine"
expect_fail "M05 producer rejects malformed immutable ID" "malformed immutable image ID" "$fixture_m05" \
  "$offline_script" -Version 1.16.0-enterprise -Mode rebuild

# D01: the suite used only the shim and the checker contains no retired scan path.
if find "$tmp_root" -name fake-docker.log -type f -exec grep -EH '^docker (run|load|export) ' {} + | grep -q . ||
  grep -Eq 'SecretsPattern|layer\.tar|tar x|extractall' "$check_script"; then
  printf 'not ok - D01 retired daemon/layer/protected scan path observed\n' >&2
  exit 1
fi
printf 'ok - D01 fake Docker only; no run/load/export/layer/protected scan path\n'
pass_count=$((pass_count + 1))

printf 'all %d enterprise offline tests passed\n' "$pass_count"
