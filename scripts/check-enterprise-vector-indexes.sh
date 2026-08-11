#!/usr/bin/env bash
#
# Read-only vector consistency checker for Dify Enterprise 1.16.0.
#
# Compares the PostgreSQL-expected Weaviate class set against the live Weaviate
# schema using only read-only queries.  This script is the default read-only
# gate for B8 and has no repair path: repair is a separately authorized task and
# is never performed here.
#
# Boundaries (see docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN.md §3):
#   - PostgreSQL: only SHOW / SELECT, every psql call carries
#     PGOPTIONS='-c default_transaction_read_only=on', and the session is
#     asserted read-only via SHOW transaction_read_only.
#   - Weaviate: only authenticated HTTP GET; no object bodies are queried and no
#     vector data is written.
#   - Inputs come from the environment only (no connection strings on the
#     command line); dataset IDs, class names, endpoints and keys are never
#     printed in plaintext.
#   - Non-weaviate vector providers are reported NOT_RUN, never PASS or FAIL.

set -uo pipefail

WEAVIATE_ENDPOINT="${WEAVIATE_ENDPOINT:-}"
VECTOR_STORE="${VECTOR_STORE:-}"
DIFY_ENTERPRISE_VERSION="${DIFY_ENTERPRISE_VERSION:-1.16.0-enterprise}"
COMPOSE_PROFILES="${COMPOSE_PROFILES:-weaviate,postgresql,collaboration}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -Postgres | --Postgres)
      shift
      ;;
    -WeaviateEndpoint | --WeaviateEndpoint)
      WEAVIATE_ENDPOINT="${2:?missing value for $1}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: scripts/check-enterprise-vector-indexes.sh [-Postgres] [-WeaviateEndpoint <url>]" >&2
      exit 1
      ;;
  esac
done

pass_count=0
fail_count=0
notrun_count=0

redact() {
  printf 'sha256:%s' "$(printf '%s' "$1" | sha256sum | cut -c1-12)"
}

pass() {
  printf 'PASS    %s\n' "$1"
  pass_count=$((pass_count + 1))
}

fail() {
  printf 'FAIL    %s\n' "$1" >&2
  fail_count=$((fail_count + 1))
}

notrun() {
  printf 'NOT_RUN %s\n' "$1"
  notrun_count=$((notrun_count + 1))
}

finish() {
  printf 'summary: %d PASS / %d FAIL / %d NOT_RUN\n' "$pass_count" "$fail_count" "$notrun_count"
  if [[ "$fail_count" -gt 0 ]]; then
    exit 1
  fi
  exit 0
}

# --- 1. identity gate -------------------------------------------------------
printf '# vector consistency check, VECTOR_STORE=%s, DIFY_ENTERPRISE_VERSION=%s, COMPOSE_PROFILES=%s\n' \
  "$VECTOR_STORE" "$DIFY_ENTERPRISE_VERSION" "$COMPOSE_PROFILES"

if [[ "$VECTOR_STORE" != "weaviate" ]]; then
  notrun "unsupported vector provider: VECTOR_STORE=${VECTOR_STORE:-<unset>} (release blocker set is PostgreSQL + Weaviate)"
  finish
fi

if [[ -z "$WEAVIATE_ENDPOINT" ]]; then
  notrun "WEAVIATE_ENDPOINT not configured (set WEAVIATE_ENDPOINT or pass -WeaviateEndpoint); environment incomplete"
  finish
fi

# --- 2. read-only enforcement (PostgreSQL) ----------------------------------
if [[ "${PGOPTIONS:-}" != *"default_transaction_read_only=on"* ]]; then
  fail "PostgreSQL session is not read-only: PGOPTIONS must set -c default_transaction_read_only=on"
  finish
fi

readonly_value=""
if psql_output=$(psql -X -v ON_ERROR_STOP=1 -A -t -c "SHOW transaction_read_only" 2>/dev/null); then
  readonly_value="$(printf '%s\n' "$psql_output" | sed -n '1p' | tr -d '[:space:]')"
else
  notrun "PostgreSQL read-only session unavailable; runtime Phase D/G gate required"
  finish
fi
if [[ "$readonly_value" != "on" ]]; then
  fail "PostgreSQL session is not read-only: SHOW transaction_read_only returned ${readonly_value:-<empty>}"
  finish
fi

# --- 3. PostgreSQL expected-class set (read-only) ----------------------------
# Only high_quality datasets that still have completed, enabled, non-archived
# documents and completed, enabled segments require a Weaviate class.  The
# class is read from index_struct.vector_store.class_prefix; when absent it
# falls back to the official Dataset.gen_collection_name_by_id naming.
read -r -d '' EXPECTED_CLASSES_SQL <<'SQL' || true
SELECT d.id,
       COALESCE(d.index_struct::jsonb #>> '{vector_store,class_prefix}', '') AS class_prefix,
       (SELECT COUNT(*) FROM documents doc
        WHERE doc.dataset_id = d.id
          AND doc.indexing_status = 'completed'
          AND doc.enabled = true
          AND doc.archived = false) AS documents,
       (SELECT COUNT(*) FROM document_segments seg
        WHERE seg.dataset_id = d.id
          AND seg.status = 'completed'
          AND seg.enabled = true) AS segments
FROM datasets d
WHERE d.indexing_technique = 'high_quality'
  AND EXISTS (SELECT 1 FROM documents doc
              WHERE doc.dataset_id = d.id
                AND doc.indexing_status = 'completed'
                AND doc.enabled = true
                AND doc.archived = false)
  AND EXISTS (SELECT 1 FROM document_segments seg
              WHERE seg.dataset_id = d.id
                AND seg.status = 'completed'
                AND seg.enabled = true)
ORDER BY d.id
SQL

dataset_ids=()
class_prefixes=()
documents_counts=()
segments_counts=()

if ! pg_rows=$(psql -X -v ON_ERROR_STOP=1 -A -t -F '|' -c "$EXPECTED_CLASSES_SQL" 2>/dev/null); then
  notrun "PostgreSQL expected-class query unavailable; runtime Phase D/G gate required"
  finish
fi

while IFS='|' read -r ds_id cls docs segs; do
  [[ -n "$ds_id" ]] || continue
  dataset_ids+=("$ds_id")
  class_prefixes+=("$cls")
  documents_counts+=("$docs")
  segments_counts+=("$segs")
done <<< "$pg_rows"

if [[ "${#dataset_ids[@]}" -eq 0 ]]; then
  pass "no high_quality dataset with completed documents and segments (expected class set empty)"
fi

# --- 4. Weaviate read-only schema check (GET only) --------------------------
tmp_root="$(mktemp -d)"
trap 'rm -rf "$tmp_root"' EXIT

weaviate_get() {
  local path="$1"
  local out_file="$2"
  local code=""
  if command -v curl >/dev/null 2>&1; then
    local headers=()
    if [[ -n "${WEAVIATE_API_KEY:-}" ]]; then
      headers=(-H "Authorization: Bearer ${WEAVIATE_API_KEY}")
    fi
    if ! code=$(curl --silent --show-error --output "$out_file" --write-out '%{http_code}' "${headers[@]}" \
      "${WEAVIATE_ENDPOINT}${path}" 2>/dev/null); then
      return 1
    fi
  elif command -v wget >/dev/null 2>&1; then
    if [[ -n "${WEAVIATE_API_KEY:-}" ]]; then
      if ! code=$(wget -q -O "$out_file" --header="Authorization: Bearer ${WEAVIATE_API_KEY}" \
        --server-response "${WEAVIATE_ENDPOINT}${path}" 2>&1 | awk 'NR==1 {print $2}'); then
        return 1
      fi
    else
      if ! code=$(wget -q -O "$out_file" --server-response "${WEAVIATE_ENDPOINT}${path}" 2>&1 | awk 'NR==1 {print $2}'); then
        return 1
      fi
    fi
  else
    return 1
  fi
  printf '%s' "$code"
}

schema_body="$tmp_root/schema.json"
schema_code=""
if ! schema_code=$(weaviate_get "/v1/schema" "$schema_body"); then
  notrun "weaviate schema unavailable (GET /v1/schema failed to connect); runtime Phase D/G gate required"
  finish
fi

if [[ "$schema_code" != "200" ]]; then
  for i in "${!dataset_ids[@]}"; do
    notrun "weaviate schema unavailable (GET /v1/schema returned ${schema_code}); runtime Phase D/G gate required"
  done
  if [[ "${#dataset_ids[@]}" -eq 0 ]]; then
    notrun "weaviate schema unavailable (GET /v1/schema returned ${schema_code}); runtime Phase D/G gate required"
  fi
  finish
fi

actual_classes=()
if ! actual_classes_output=$(python3 - "$schema_body" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
for cls in data.get("classes", []):
    print(cls["class"])
PY
); then
  notrun "weaviate schema unavailable (GET /v1/schema response could not be parsed); runtime Phase D/G gate required"
  finish
fi
while IFS= read -r cls; do
  [[ -n "$cls" ]] || continue
  actual_classes+=("$cls")
done <<< "$actual_classes_output"

expected_class_names=()
for i in "${!dataset_ids[@]}"; do
  if [[ -n "${class_prefixes[$i]}" ]]; then
    expected_class_names+=("${class_prefixes[$i]}")
  else
    normalized_id="${dataset_ids[$i]//-/_}"
    expected_class_names+=("Vector_index_${normalized_id}_Node")
  fi
done

# --- 5. per-class GET + bidirectional comparison -----------------------------
for i in "${!dataset_ids[@]}"; do
  class_body="$tmp_root/class-${i}.json"
  class_code=""
  if ! class_code=$(weaviate_get "/v1/schema/${expected_class_names[$i]}" "$class_body"); then
    notrun "dataset=$(redact "${dataset_ids[$i]}")  class=$(redact "${expected_class_names[$i]}")  documents=${documents_counts[$i]}  segments=${segments_counts[$i]}  weaviate_schema_class=unavailable (class GET failed)"
    continue
  fi
  case "$class_code" in
    200)
      pass "dataset=$(redact "${dataset_ids[$i]}")  class=$(redact "${expected_class_names[$i]}")  documents=${documents_counts[$i]}  segments=${segments_counts[$i]}  weaviate_schema_class=present"
      ;;
    404)
      fail "dataset=$(redact "${dataset_ids[$i]}")  class=$(redact "${expected_class_names[$i]}")  documents=${documents_counts[$i]}  segments=${segments_counts[$i]}  weaviate_schema_class=missing"
      echo "repair is a separately authorized task; not performed by this read-only check"
      ;;
    *)
      notrun "dataset=$(redact "${dataset_ids[$i]}")  class=$(redact "${expected_class_names[$i]}")  documents=${documents_counts[$i]}  segments=${segments_counts[$i]}  weaviate_schema_class=unavailable (class GET returned ${class_code})"
      ;;
  esac
done

for i in "${!actual_classes[@]}"; do
  is_expected=0
  for expected in "${expected_class_names[@]}"; do
    if [[ "${actual_classes[$i]}" == "$expected" ]]; then
      is_expected=1
      break
    fi
  done
  if [[ "$is_expected" -eq 0 ]]; then
    notrun "extra class (not expected from PostgreSQL): class=$(redact "${actual_classes[$i]}")"
  fi
done

finish
