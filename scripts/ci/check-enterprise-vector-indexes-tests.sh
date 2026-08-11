#!/usr/bin/env bash
#
# Fixture/dry-run test suite for scripts/check-enterprise-vector-indexes.sh.
#
# Runs the read-only vector consistency checker against fake psql/curl shims and
# canned fixture inventory data (see docs/enterprise/replay-1.16.0/
# B8_IMPLEMENTATION_PLAN.md §7.2 for the required case list).  Every case
# asserts PASS/FAIL/NOT_RUN output, the fixed `summary:` line, and the expected
# exit code; the negative read-only case also proves no writes reached psql,
# weaviate, or the filesystem.

set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
checker="$repo_root/scripts/check-enterprise-vector-indexes.sh"
fixtures_dir="$repo_root/scripts/ci/check-enterprise-vector-indexes-fixtures"

tmp_root=$(mktemp -d)
trap 'rm -rf "$tmp_root"' EXIT
mkdir -p "$tmp_root/run"

pass_count=0

DATASET_ID="11111111-2222-3333-4444-555555555555"
CLASS_PREFIX="FixtureVectorClassAbc123"
EXTRA_CLASS="FixtureExtraClassDef456"
ENDPOINT="http://weaviate.invalid:8080"
API_KEY="sk-fixture-weaviate-key-0001"
PGOPTIONS_VALUE="-c default_transaction_read_only=on"
FALLBACK_CLASS="Vector_index_11111111_2222_3333_4444_555555555555_Node"

fixture_row="$(printf '%s|%s|%s|%s' "$DATASET_ID" "$CLASS_PREFIX" 2 63)"
fallback_row="$(printf '%s|%s|%s|%s' "$DATASET_ID" "" 2 63)"

fake_bin="$tmp_root/bin"
mkdir -p "$fake_bin"
cp "$fixtures_dir/bin/fake-psql" "$fake_bin/psql"
cp "$fixtures_dir/bin/fake-curl" "$fake_bin/curl"
for command_name in bash grep awk sed sort find mktemp mkdir rm cp printf sha256sum basename dirname tr chmod cut python3; do
  ln -s "$(command -v "$command_name")" "$fake_bin/$command_name"
done

clean_env() {
  unset PGOPTIONS VECTOR_STORE WEAVIATE_ENDPOINT WEAVIATE_API_KEY \
    FAKE_PSQL_ROWS FAKE_PSQL_FAIL FAKE_PSQL_LOG \
    FAKE_WEAVIATE_SCHEMA FAKE_WEAVIATE_STATUS FAKE_WEAVIATE_CLASSES FAKE_WEAVIATE_LOG \
    DIFY_ENTERPRISE_VERSION COMPOSE_PROFILES 2>/dev/null || true
}

set_defaults() {
  export PGOPTIONS="$PGOPTIONS_VALUE"
  export VECTOR_STORE="weaviate"
  export WEAVIATE_ENDPOINT="$ENDPOINT"
  export WEAVIATE_API_KEY="$API_KEY"
  export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-present.json"
  export FAKE_WEAVIATE_STATUS="200"
  export FAKE_WEAVIATE_CLASSES="$CLASS_PREFIX"
}

expect() {
  local out=$1
  local name=$2
  local expected_exit=$3
  shift 3
  local actual_exit=0
  (cd "$tmp_root/run" && PATH="$fake_bin:$PATH" "$@") >"$out" 2>&1 || actual_exit=$?
  if [[ "$actual_exit" != "$expected_exit" ]]; then
    printf 'not ok - %s (expected exit %s, got %s)\n' "$name" "$expected_exit" "$actual_exit" >&2
    sed -n '1,40p' "$out" >&2
    exit 1
  fi
  printf 'ok - %s\n' "$name"
  pass_count=$((pass_count + 1))
}

expect_grep() {
  local name=$1
  local fixed=$2
  local out=$3
  if grep -Fq -- "$fixed" "$out"; then
    printf 'ok - %s\n' "$name"
    pass_count=$((pass_count + 1))
  else
    printf 'not ok - %s (missing output: %s)\n' "$name" "$fixed" >&2
    sed -n '1,40p' "$out" >&2
    exit 1
  fi
}

expect_grep_fixed() {
  local name=$1
  local fixed=$2
  local out=$3
  if grep -Fxq -- "$fixed" "$out"; then
    printf 'ok - %s\n' "$name"
    pass_count=$((pass_count + 1))
  else
    printf 'not ok - %s (missing exact line: %s)\n' "$name" "$fixed" >&2
    sed -n '1,40p' "$out" >&2
    exit 1
  fi
}

expect_no_grep() {
  local name=$1
  local pattern=$2
  local out=$3
  if ! grep -Eq -- "$pattern" "$out"; then
    printf 'ok - %s\n' "$name"
    pass_count=$((pass_count + 1))
  else
    printf 'not ok - %s (unexpected output: %s)\n' "$name" "$pattern" >&2
    grep -E -- "$pattern" "$out" >&2 || true
    exit 1
  fi
}

# --- 1. no high_quality dataset -> all PASS ----------------------------------
clean_env
set_defaults
export FAKE_PSQL_ROWS=""
export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-empty.json"
export FAKE_WEAVIATE_CLASSES=""
out="$tmp_root/case-01.out"
expect "$out" "no high_quality dataset exits 0" 0 "$checker"
expect_grep "no high_quality dataset reports PASS" "no high_quality dataset with completed documents and segments" "$out"
expect_grep_fixed "no high_quality dataset summary" "summary: 1 PASS / 0 FAIL / 0 NOT_RUN" "$out"
clean_env

# --- 2. high_quality dataset with class present -> PASS -----------------------
clean_env
set_defaults
export FAKE_PSQL_ROWS="$fixture_row"
export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-present.json"
export FAKE_WEAVIATE_CLASSES="$CLASS_PREFIX"
out="$tmp_root/case-02.out"
expect "$out" "class present exits 0" 0 "$checker"
expect_grep "class present line" "weaviate_schema_class=present" "$out"
expect_grep_fixed "class present summary" "summary: 1 PASS / 0 FAIL / 0 NOT_RUN" "$out"
clean_env

# --- 3. high_quality dataset with class missing -> FAIL, exit 1 ---------------
clean_env
set_defaults
export FAKE_PSQL_ROWS="$fixture_row"
export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-empty.json"
export FAKE_WEAVIATE_CLASSES=""
out="$tmp_root/case-03.out"
expect "$out" "class missing exits 1" 1 "$checker"
expect_grep "class missing line" "weaviate_schema_class=missing" "$out"
expect_grep "missing class reports separately authorized repair" "repair is a separately authorized task; not performed by this read-only check" "$out"
expect_grep_fixed "class missing summary" "summary: 0 PASS / 1 FAIL / 0 NOT_RUN" "$out"
clean_env

# --- 4. VECTOR_STORE=qdrant (outside release blocker set) -> all NOT_RUN -------
clean_env
set_defaults
unset WEAVIATE_ENDPOINT
export VECTOR_STORE="qdrant"
export FAKE_PSQL_ROWS="$fixture_row"
out="$tmp_root/case-04.out"
expect "$out" "qdrant provider exits 0" 0 "$checker"
expect_grep "qdrant provider NOT_RUN" "unsupported vector provider: VECTOR_STORE=qdrant" "$out"
expect_grep_fixed "qdrant provider summary" "summary: 0 PASS / 0 FAIL / 1 NOT_RUN" "$out"
clean_env

# --- 5. weaviate without WEAVIATE_ENDPOINT -> NOT_RUN --------------------------
clean_env
set_defaults
unset WEAVIATE_ENDPOINT
export FAKE_PSQL_ROWS="$fixture_row"
out="$tmp_root/case-05.out"
expect "$out" "missing endpoint exits 0" 0 "$checker"
expect_grep "missing endpoint NOT_RUN" "WEAVIATE_ENDPOINT not configured" "$out"
expect_grep_fixed "missing endpoint summary" "summary: 0 PASS / 0 FAIL / 1 NOT_RUN" "$out"
clean_env

# --- 6. GET /v1/schema 403 -> NOT_RUN, never PASS ------------------------------
clean_env
set_defaults
export FAKE_PSQL_ROWS="$fixture_row"
export FAKE_WEAVIATE_STATUS="403"
export FAKE_WEAVIATE_CLASSES="$CLASS_PREFIX"
out="$tmp_root/case-06.out"
expect "$out" "schema 403 exits 0" 0 "$checker"
expect_grep "schema 403 NOT_RUN" "weaviate schema unavailable (GET /v1/schema returned 403)" "$out"
expect_grep_fixed "schema 403 summary" "summary: 0 PASS / 0 FAIL / 1 NOT_RUN" "$out"
clean_env

# --- 7. PG session not read-only (PGOPTIONS unset) -> FAIL, exit 1 -------------
clean_env
set_defaults
unset PGOPTIONS
export FAKE_PSQL_ROWS="$fixture_row"
out="$tmp_root/case-07.out"
expect "$out" "PGOPTIONS unset exits 1" 1 "$checker"
expect_grep "PGOPTIONS unset FAIL" "PostgreSQL session is not read-only: PGOPTIONS must set" "$out"
expect_grep_fixed "PGOPTIONS unset summary" "summary: 0 PASS / 1 FAIL / 0 NOT_RUN" "$out"
clean_env

# --- 8. read-only negative: no writes to psql/weaviate/files -------------------
clean_env
set_defaults
export FAKE_PSQL_ROWS="$fixture_row"
export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-present.json"
export FAKE_WEAVIATE_CLASSES="$CLASS_PREFIX"
export FAKE_PSQL_LOG="$tmp_root/psql.log"
export FAKE_WEAVIATE_LOG="$tmp_root/weaviate.log"
out="$tmp_root/case-08.out"
expect "$out" "read-only run exits 0" 0 "$checker"
expect_no_grep "no psql write commands in shim log" '\b(INSERT|UPDATE|DELETE|ALTER|DROP|CREATE|VACUUM|TRUNCATE)\b' "$FAKE_PSQL_LOG"
expect_no_grep "no non-GET weaviate requests in shim log" 'curl (POST|PUT|DELETE) ' "$FAKE_WEAVIATE_LOG"
expect_grep "weaviate shim saw only GET" 'curl GET /v1/' "$FAKE_WEAVIATE_LOG"
if [[ -n "$(find "$tmp_root/run" -type f 2>/dev/null)" ]]; then
  printf 'not ok - read-only run wrote files into the run directory\n' >&2
  find "$tmp_root/run" -type f >&2 || true
  exit 1
fi
printf 'ok - read-only run wrote no files into the run directory\n'
pass_count=$((pass_count + 1))
clean_env

# --- 9. extra class (EXTRA) reported, does not block ---------------------------
clean_env
set_defaults
export FAKE_PSQL_ROWS="$fixture_row"
export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-extra.json"
export FAKE_WEAVIATE_CLASSES="$CLASS_PREFIX $EXTRA_CLASS"
out="$tmp_root/case-09.out"
expect "$out" "extra class exits 0" 0 "$checker"
expect_grep "extra class present class still PASS" "weaviate_schema_class=present" "$out"
expect_grep "extra class NOT_RUN reported" "extra class (not expected from PostgreSQL): class=sha256:" "$out"
expect_grep_fixed "extra class summary" "summary: 1 PASS / 0 FAIL / 1 NOT_RUN" "$out"
clean_env

# --- 10. output redaction: no plaintext dataset/class/endpoint/key -------------
clean_env
set_defaults
export FAKE_PSQL_ROWS="$fixture_row"
export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-present.json"
export FAKE_WEAVIATE_CLASSES="$CLASS_PREFIX"
out="$tmp_root/case-10.out"
expect "$out" "redaction run exits 0" 0 "$checker"
expect_no_grep "no plaintext dataset id in output" "$DATASET_ID" "$out"
expect_no_grep "no plaintext class in output" "$CLASS_PREFIX" "$out"
expect_no_grep "no plaintext endpoint in output" "$ENDPOINT" "$out"
expect_no_grep "no plaintext api key in output" "$API_KEY" "$out"
expect_grep "dataset targets are sha256-redacted" "dataset=sha256:" "$out"
expect_grep "class targets are sha256-redacted" "class=sha256:" "$out"
clean_env

# --- 11. PostgreSQL connection failure -> NOT_RUN, exit 0 ----------------------
clean_env
set_defaults
export FAKE_PSQL_ROWS="$fixture_row"
export FAKE_PSQL_FAIL="1"
out="$tmp_root/case-11.out"
expect "$out" "PostgreSQL connection failure exits 0" 0 "$checker"
expect_grep "PostgreSQL failure NOT_RUN" "PostgreSQL read-only session unavailable" "$out"
expect_grep_fixed "PostgreSQL failure summary" "summary: 0 PASS / 0 FAIL / 1 NOT_RUN" "$out"
clean_env

# --- 12. explicit -WeaviateEndpoint argument -----------------------------------
clean_env
set_defaults
unset WEAVIATE_ENDPOINT
export FAKE_PSQL_ROWS="$fixture_row"
export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-present.json"
export FAKE_WEAVIATE_CLASSES="$CLASS_PREFIX"
out="$tmp_root/case-12.out"
expect "$out" "explicit -WeaviateEndpoint exits 0" 0 "$checker" -WeaviateEndpoint "$ENDPOINT"
expect_grep "explicit endpoint line PASS" "weaviate_schema_class=present" "$out"
expect_grep_fixed "explicit endpoint summary" "summary: 1 PASS / 0 FAIL / 0 NOT_RUN" "$out"
clean_env

# --- 13. class_prefix fallback to official collection name ---------------------
clean_env
set_defaults
export FAKE_PSQL_ROWS="$fallback_row"
export FAKE_WEAVIATE_SCHEMA="$fixtures_dir/data/schema-fallback.json"
export FAKE_WEAVIATE_CLASSES="$FALLBACK_CLASS"
out="$tmp_root/case-13.out"
expect "$out" "class_prefix fallback exits 0" 0 "$checker"
expect_grep "class_prefix fallback line PASS" "weaviate_schema_class=present" "$out"
expect_grep_fixed "class_prefix fallback summary" "summary: 1 PASS / 0 FAIL / 0 NOT_RUN" "$out"
clean_env

printf 'all %d enterprise vector index checker tests passed\n' "$pass_count"
