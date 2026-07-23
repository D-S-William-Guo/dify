#!/usr/bin/env bash

set -euo pipefail

readonly OFFICIAL_BASE_COMMIT="5c6372d2f76d240265b92fd27c16bc772ffcb107"

repo_root=$(git rev-parse --show-toplevel)
checker="$repo_root/scripts/ci/check-enterprise-replay-scope.sh"
tmp_root=$(mktemp -d)
trap 'rm -rf "$tmp_root"' EXIT

pass_count=0

new_fixture() {
  local name=$1
  local fixture="$tmp_root/$name"

  git clone --quiet --shared --no-tags "$repo_root" "$fixture"
  git -C "$fixture" config user.name "Enterprise Replay Guard Test"
  git -C "$fixture" config user.email "replay-guard@example.invalid"
  git -C "$fixture" switch --quiet --detach "$OFFICIAL_BASE_COMMIT"
  printf '%s\n' "$fixture"
}

commit_fixture() {
  local fixture=$1
  git -C "$fixture" add -A --force
  git -C "$fixture" commit --quiet -m "fixture change"
}

expect_pass() {
  local name=$1
  local fixture=$2
  shift 2

  if (cd "$fixture" && "$checker" "$@") >"$tmp_root/$name.out" 2>&1; then
    printf 'ok - %s\n' "$name"
    pass_count=$((pass_count + 1))
    return
  fi

  printf 'not ok - %s (expected success)\n' "$name" >&2
  sed -n '1,20p' "$tmp_root/$name.out" >&2
  exit 1
}

expect_fail() {
  local name=$1
  local expected=$2
  local fixture=$3
  shift 3

  if (cd "$fixture" && "$checker" "$@") >"$tmp_root/$name.out" 2>&1; then
    printf 'not ok - %s (expected failure)\n' "$name" >&2
    exit 1
  fi
  if ! grep -Fq "$expected" "$tmp_root/$name.out"; then
    printf 'not ok - %s (missing safe diagnostic: %s)\n' "$name" "$expected" >&2
    sed -n '1,20p' "$tmp_root/$name.out" >&2
    exit 1
  fi

  printf 'ok - %s\n' "$name"
  pass_count=$((pass_count + 1))
}

expect_pass "current legal candidate diff" "$repo_root" 1.16.0 HEAD

fixture=$(new_fixture legal-ci-docs)
mkdir -p "$fixture/.github/workflows" "$fixture/docs/enterprise"
printf '%s\n' 'name: fixture' >"$fixture/.github/workflows/fixture.yml"
printf '%s\n' 'Historical db.session and console_ns.schema_model references are documentation.' \
  >"$fixture/docs/enterprise/replay-notes.md"
commit_fixture "$fixture"
expect_pass "legal CI and documentation changes" "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture docker-volume)
mkdir -p "$fixture/safe"
printf '%s\n' 'fixture' >"$fixture/safe/original name.txt"
commit_fixture "$fixture"
git -C "$fixture" mv "safe/original name.txt" "docker/volumes/runtime data.txt"
commit_fixture "$fixture"
expect_fail "docker volumes rename with spaces" "docker/volumes is runtime data" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture docker-volume-delete)
git -C "$fixture" rm --quiet docker/volumes/sandbox/conf/config.yaml
commit_fixture "$fixture"
expect_fail "docker volumes deletion" "docker/volumes is runtime data" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture env-secret)
mkdir -p "$fixture/config"
printf '%s\n' 'placeholder-only' >"$fixture/config/.env.production"
commit_fixture "$fixture"
expect_fail "real env path" "real environment files are not allowed" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture secret-key)
mkdir -p "$fixture/config"
printf '%s\n' 'placeholder-only' >"$fixture/config/service-account-test.json"
commit_fixture "$fixture"
expect_fail "secret-like path" "credential, key, or compiled artifact paths are not allowed" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture cache)
mkdir -p "$fixture/web/node_modules/example"
printf '%s\n' 'fixture' >"$fixture/web/node_modules/example/index.js"
commit_fixture "$fixture"
expect_fail "node_modules path" "node_modules is a dependency artifact" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture cache-artifact)
mkdir -p "$fixture/api/.pytest_cache"
printf '%s\n' 'fixture' >"$fixture/api/.pytest_cache/state"
commit_fixture "$fixture"
expect_fail "cache artifact path" "cache content is not allowed" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture build-artifact)
mkdir -p "$fixture/web/.next/cache"
printf '%s\n' 'fixture' >"$fixture/web/.next/cache/output"
commit_fixture "$fixture"
expect_fail "build artifact path" "generated build or coverage output is not allowed" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-sqlalchemy)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'def legacy_controller():' '    return db.session.query(Account).all()' \
  >"$fixture/api/controllers/console/legacy_fixture.py"
commit_fixture "$fixture"
expect_fail "controller SQLAlchemy" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture legacy-contract)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'legacy = console_ns.schema_model("Legacy", {})' \
  >"$fixture/api/controllers/console/legacy_contract_fixture.py"
commit_fixture "$fixture"
expect_fail "legacy Console contract" "legacy Console schema_model contract" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture implicit-service-session)
mkdir -p "$fixture/api/services"
printf '%s\n' 'def legacy_service():' '    return db.session.scalar(statement)' \
  >"$fixture/api/services/legacy_fixture.py"
commit_fixture "$fixture"
expect_fail "implicit service session" "adds implicit db.session usage" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture handwritten-web-service)
mkdir -p "$fixture/web/service"
printf '%s\n' 'export const legacy = true' >"$fixture/web/service/use-platform-admin.ts"
commit_fixture "$fixture"
expect_fail "legacy handwritten Web service" "legacy handwritten Console model/service" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture invalid-ref)
expect_fail "invalid ref" "head ref is not a valid commit" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" refs/heads/does-not-exist

fixture=$(new_fixture wrong-base)
wrong_base=$(git -C "$fixture" rev-parse "${OFFICIAL_BASE_COMMIT}^")
expect_fail "wrong baseline" "base ref does not resolve to the approved Dify 1.16.0 commit" \
  "$fixture" "$wrong_base" HEAD

printf 'all %d enterprise replay scope tests passed\n' "$pass_count"
