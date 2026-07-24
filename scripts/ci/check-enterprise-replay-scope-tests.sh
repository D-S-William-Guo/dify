#!/usr/bin/env bash

set -euo pipefail

readonly OFFICIAL_BASE_COMMIT="5c6372d2f76d240265b92fd27c16bc772ffcb107"

repo_root=$(git rev-parse --show-toplevel)
checker="$repo_root/scripts/ci/check-enterprise-replay-scope.sh"
tmp_root=$(mktemp -d)
trap 'rm -rf "$tmp_root"' EXIT

pass_count=0

fallback_bin="$tmp_root/fallback-bin"
mkdir -p "$fallback_bin"
for command_name in bash git awk grep; do
  ln -s "$(command -v "$command_name")" "$fallback_bin/$command_name"
done

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

expect_pass_without_ast() {
  local name=$1
  local fixture=$2
  shift 2

  if (cd "$fixture" && PATH="$fallback_bin" "$checker" "$@") >"$tmp_root/$name.out" 2>&1; then
    printf 'ok - %s\n' "$name"
    pass_count=$((pass_count + 1))
    return
  fi

  printf 'not ok - %s (expected dependency-free fallback success)\n' "$name" >&2
  sed -n '1,20p' "$tmp_root/$name.out" >&2
  exit 1
}

expect_fail_without_ast() {
  local name=$1
  local expected=$2
  local fixture=$3
  shift 3

  if (cd "$fixture" && PATH="$fallback_bin" "$checker" "$@") >"$tmp_root/$name.out" 2>&1; then
    printf 'not ok - %s (expected dependency-free fallback failure)\n' "$name" >&2
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
printf '%s\n' 'A filename containing venv is not a virtual-environment directory.' \
  >"$fixture/docs/enterprise/venv-migration-notes.md"
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

fixture=$(new_fixture virtual-environment)
mkdir -p "$fixture/tools/runtime/.venv/bin"
printf '%s\n' 'fixture' >"$fixture/tools/runtime/.venv/bin/python"
commit_fixture "$fixture"
expect_fail ".venv dependency artifact" "virtual environment content is a dependency/runtime artifact" \
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

fixture=$(new_fixture controller-db-session-add-all)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'db.session.add_all([account])' \
  >"$fixture/api/controllers/console/db_session_add_all_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller db.session.add_all fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-session-begin)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'session.begin()' >"$fixture/api/controllers/console/session_begin_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller session.begin fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-session-constructor)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'controller_session = Session(bind=engine)' \
  >"$fixture/api/controllers/console/session_constructor_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller Session fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-sessionmaker)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'factory = sessionmaker(bind=engine)' \
  >"$fixture/api/controllers/console/sessionmaker_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller sessionmaker fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-session-get)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'account = session.get(Account, account_id)' \
  >"$fixture/api/controllers/console/session_get_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller SQLAlchemy session.get fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-bare-select)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'statement = select(Account)' \
  >"$fixture/api/controllers/console/bare_select_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller bare select fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-db-select)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'statement = db.select(Account)' \
  >"$fixture/api/controllers/console/db_select_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller db.select fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-sa-update)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'statement = sa.update(Account)' \
  >"$fixture/api/controllers/console/sa_update_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller sa.update fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-sqlalchemy-insert)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'statement = sqlalchemy.insert(account_table)' \
  >"$fixture/api/controllers/console/sqlalchemy_insert_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller sqlalchemy.insert fallback" "adds direct controller SQLAlchemy" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-flask-session-single-quote)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' "tenant_id = session.get('tenant-id')" \
  >"$fixture/api/controllers/console/flask_session_single_quote_fixture.py"
commit_fixture "$fixture"
expect_pass_without_ast "Flask session.get single-quoted key fallback" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-flask-session-double-quote)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'tenant_id = session.get("tenant-id")' \
  >"$fixture/api/controllers/console/flask_session_double_quote_fixture.py"
commit_fixture "$fixture"
expect_pass_without_ast "Flask session.get double-quoted key fallback" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-flask-session-multiline-single-quote)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' \
  'tenant_id = session.get(' \
  "    'tenant-id'" \
  ')' \
  >"$fixture/api/controllers/console/flask_session_multiline_single_quote_fixture.py"
commit_fixture "$fixture"
expect_pass_without_ast "Flask session.get multiline single-quoted key fallback" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-flask-session-multiline-double-quote)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' \
  'tenant_id = session.get(' \
  '    "tenant-id"' \
  ')' \
  >"$fixture/api/controllers/console/flask_session_multiline_double_quote_fixture.py"
commit_fixture "$fixture"
expect_pass_without_ast "Flask session.get multiline double-quoted key fallback" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-sqlalchemy-session-get-multiline)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' \
  'account = session.get(' \
  '    Account,' \
  '    account_id,' \
  ')' \
  >"$fixture/api/controllers/console/sqlalchemy_session_get_multiline_fixture.py"
commit_fixture "$fixture"
expect_fail_without_ast "controller multiline SQLAlchemy session.get fallback" \
  "adds direct controller SQLAlchemy" "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-request-session-get)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' 'account = request.session.get(Account, account_id)' \
  >"$fixture/api/controllers/console/request_session_get_fixture.py"
commit_fixture "$fixture"
expect_pass_without_ast "request.session.get is not bare session fallback" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-allowed-session-boundaries)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' \
  'db.session.commit()' \
  'db.session.flush()' \
  'session.commit()' \
  'session.flush()' \
  >"$fixture/api/controllers/console/session_boundaries_fixture.py"
commit_fixture "$fixture"
expect_pass_without_ast "controller commit and flush boundaries fallback" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture controller-similar-identifiers)
mkdir -p "$fixture/api/controllers/console"
printf '%s\n' \
  'selected_account = selection_helper(account_id)' \
  'updated_account = update_cache_value(account_id)' \
  >"$fixture/api/controllers/console/similar_identifiers_fixture.py"
commit_fixture "$fixture"
expect_pass_without_ast "controller similar identifiers fallback" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

if ! grep -Fq "AST guard did not run" "$tmp_root/controller similar identifiers fallback.out"; then
  printf 'not ok - dependency-free fallback diagnostic (AST status missing)\n' >&2
  exit 1
fi
if ! grep -Fq "dependency-free fallback ran" "$tmp_root/controller similar identifiers fallback.out"; then
  printf 'not ok - dependency-free fallback diagnostic (fallback status missing)\n' >&2
  exit 1
fi
printf 'ok - dependency-free fallback diagnostic\n'
pass_count=$((pass_count + 1))

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

fixture=$(new_fixture handwritten-console-fetch)
mkdir -p "$fixture/web/app/components"
printf '%s\n' "export const loadLegacy = () => fetch('/console/api/apps')" \
  >"$fixture/web/app/components/legacy-fetch.ts"
commit_fixture "$fixture"
expect_fail "handwritten Console fetch" "adds a handwritten Console fetch" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture legacy-app-context-hook)
mkdir -p "$fixture/web/app/components/platform-admin"
printf '%s\n' 'const appContext = useAppContext()' \
  >"$fixture/web/app/components/platform-admin/legacy-context.tsx"
commit_fixture "$fixture"
expect_fail "legacy app context hook" "legacy app context" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture legacy-app-context-import)
mkdir -p "$fixture/web/app/components/enterprise-marketplace"
printf '%s\n' "import { useAppContext } from '@/context/app-context'" \
  >"$fixture/web/app/components/enterprise-marketplace/legacy-context.tsx"
commit_fixture "$fixture"
expect_fail "legacy app context import" "legacy app context" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" HEAD

fixture=$(new_fixture invalid-ref)
expect_fail "invalid ref" "head ref is not a valid commit" \
  "$fixture" "$OFFICIAL_BASE_COMMIT" refs/heads/does-not-exist

fixture=$(new_fixture wrong-base)
wrong_base=$(git -C "$fixture" rev-parse "${OFFICIAL_BASE_COMMIT}^")
expect_fail "wrong baseline" "base ref does not resolve to the approved Dify 1.16.0 commit" \
  "$fixture" "$wrong_base" HEAD

printf 'all %d enterprise replay scope tests passed\n' "$pass_count"
