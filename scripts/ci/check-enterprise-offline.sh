#!/usr/bin/env bash

set -euo pipefail

ARCHIVE=""
CONFIG_ARCHIVE=""
MANIFEST=""
IMAGES=""
SECRETS_PATTERN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -Archive|--Archive)
      ARCHIVE="${2:?missing value for $1}"
      shift 2
      ;;
    -ConfigArchive|--ConfigArchive)
      CONFIG_ARCHIVE="${2:?missing value for $1}"
      shift 2
      ;;
    -Manifest|--Manifest)
      MANIFEST="${2:?missing value for $1}"
      shift 2
      ;;
    -Images|--Images)
      IMAGES="${2:?missing value for $1}"
      shift 2
      ;;
    -SecretsPattern|--SecretsPattern)
      SECRETS_PATTERN="${2:?missing value for $1}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: ./scripts/ci/check-enterprise-offline.sh -Archive <tar> -ConfigArchive <tar.gz> -Manifest <json> -Images <txt> [-SecretsPattern <file>]" >&2
      exit 1
      ;;
  esac
done

for required in ARCHIVE CONFIG_ARCHIVE MANIFEST IMAGES; do
  if [[ -z "${!required}" ]]; then
    echo "Missing required argument: -${required#ARCHIVE}" >&2
    exit 1
  fi
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

readonly DEV_AGENT_SECRET="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY"
readonly WARNING_MARKERS=(
  "WARNING"
  "Replace this development default in production"
)
readonly REQUIRED_IMAGES=(
  "dify-api-enterprise:1.16.0-enterprise"
  "dify-web-enterprise:1.16.0-enterprise"
  "langgenius/dify-agent-backend:1.16.0"
  "langgenius/dify-agent-local-sandbox:1.16.0"
)
readonly FORBIDDEN_1_15_FILES=(
  "docker/ENTERPRISE_DEPLOY_STARTUP.md"
  "docker/dify-env-sync.py"
  "docker/dify-env-sync.sh"
  "docker/README.enterprise.md"
  "scripts/check-enterprise-vector-indexes.sh"
)

pass_count=0
fail_count=0
notrun_count=0

pass() {
  printf 'PASS: %s\n' "$1"
  pass_count=$((pass_count + 1))
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  fail_count=$((fail_count + 1))
}

notrun() {
  printf 'NOT_RUN: %s\n' "$1"
  notrun_count=$((notrun_count + 1))
}

forbidden_path() {
  local entry="$1"
  local normalized="${entry#./}"
  case "/$normalized/" in
    */docker/volumes/*)
      echo "docker/volumes runtime data"
      return 0
      ;;
    */node_modules/*)
      echo "node_modules dependency artifact"
      return 0
      ;;
    */.venv/*|*/venv/*)
      echo "virtual environment content"
      return 0
      ;;
    */.cache/*|*/.pytest_cache/*|*/.mypy_cache/*|*/.ruff_cache/*|*/.uv-cache/*|*/__pycache__/*|*/.pnpm-store/*)
      echo "cache content"
      return 0
      ;;
    */.git/*|*/.git)
      echo ".git metadata"
      return 0
      ;;
    */.secrets/*|*/secrets/*)
      echo "secret-bearing directory"
      return 0
      ;;
  esac

  # Only the gitignored offline artifacts (dist/offline/*) are allowed; other
  # generated business build output is forbidden.
  case "/$normalized/" in
    */dist/offline/*|*/dist/offline)
      ;;
    */dist/*|*/build/*|*/.next/*|*/coverage/*|*/htmlcov/*)
      echo "generated build or coverage output"
      return 0
      ;;
  esac

  local basename="${normalized##*/}"
  if [[ "$basename" == ".env" || "$basename" == *.env.production || "$basename" == .env.local || "$basename" == *.env.local ]]; then
    echo "real environment file"
    return 0
  fi
  if [[ "$basename" == *.env && "$normalized" != *.env.example && "$normalized" != *.env.sample && "$normalized" != *.env.template ]]; then
    echo "real environment file"
    return 0
  fi

  case "$basename" in
    credentials.json|service-account*.json|id_rsa|id_ed25519|*.pem|*.key|*.p12|*.pfx)
      echo "credential or key file"
      return 0
      ;;
  esac

  return 1
}

scan_content_secrets() {
  local label="$1"
  local file="$2"
  local hit=0

  if [[ "$DEV_AGENT_SECRET" != "" && -n "$SECRETS_PATTERN" ]]; then
    while IFS= read -r pattern; do
      [[ -z "$pattern" || "$pattern" == \#* ]] && continue
      if grep -Fq -- "$pattern" "$file"; then
        printf 'FAIL: %s contains a real secret pattern (target hit, content redacted)\n' "$label" >&2
        fail_count=$((fail_count + 1))
        hit=1
      fi
    done < "$SECRETS_PATTERN"
  fi

  if grep -Fq -- "$DEV_AGENT_SECRET" "$file"; then
    printf 'FAIL: %s contains the development agent default secret (dev default must stay out of runnable artifacts)\n' "$label" >&2
    fail_count=$((fail_count + 1))
    hit=1
  fi

  if [[ "$hit" -eq 0 ]]; then
    return 1
  fi
  return 0
}

tmp_root=$(mktemp -d)
chmod 700 "$tmp_root"
trap 'rm -rf "$tmp_root"' EXIT

# --- 1. images file -----------------------------------------------------
if [[ ! -f "$IMAGES" ]]; then
  fail "images file not found: $IMAGES"
else
  if [[ ! -s "$IMAGES" ]]; then
    fail "images file is empty: $IMAGES"
  else
    pass "images file exists and is non-empty: $IMAGES"
  fi

  missing=0
  while IFS= read -r required; do
    if ! grep -Fxq -- "$required" "$IMAGES"; then
      printf 'FAIL: required image missing from %s: %s\n' "$IMAGES" "$required" >&2
      fail_count=$((fail_count + 1))
      missing=1
    fi
  done < <(printf '%s\n' "${REQUIRED_IMAGES[@]}")
  if [[ "$missing" -eq 0 ]]; then
    pass "required-image assertions satisfied for $IMAGES"
  fi

  if scan_content_secrets "images file $IMAGES" "$IMAGES"; then
    :
  else
    pass "images file contains no dev default or secret patterns"
  fi
fi

# --- 2. manifest --------------------------------------------------------
if [[ ! -f "$MANIFEST" ]]; then
  fail "manifest not found: $MANIFEST"
else
  if python3 - "$MANIFEST" "$IMAGES" <<'PY'
import json
import sys

manifest_path, images_path = sys.argv[1:]
with open(manifest_path, encoding="utf-8") as f:
    manifest = json.load(f)

errors = []
for field in ("version", "baseline", "enterprise_commit", "image_tag", "generated_at", "images"):
    if field not in manifest:
        errors.append(f"missing manifest field: {field}")
if not errors:
    if manifest.get("baseline") != {"tag": "1.16.0", "commit": "5c6372d2f76d240265b92fd27c16bc772ffcb107"}:
        errors.append("baseline must be 1.16.0 / 5c6372d2f76d240265b92fd27c16bc772ffcb107")
    if manifest.get("version") != manifest.get("image_tag"):
        errors.append("version and image_tag must match")
    if not isinstance(manifest["images"], list) or not manifest["images"]:
        errors.append("images[] must be a non-empty list")
    else:
        for entry in manifest["images"]:
            for field in ("name", "id", "digest"):
                if field not in entry:
                    errors.append(f"images[] entry missing field: {field}")
        with open(images_path, encoding="utf-8") as f:
            image_lines = [line.strip() for line in f if line.strip()]
        manifest_names = [entry.get("name") for entry in manifest["images"]]
        if sorted(manifest_names) != sorted(image_lines):
            errors.append("manifest images[] names must match the images file")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
PY
  then
    pass "manifest schema is complete and consistent with the images file"
  else
    fail "manifest schema validation failed: $MANIFEST"
  fi

  if scan_content_secrets "manifest $MANIFEST" "$MANIFEST"; then
    :
  else
    pass "manifest contains no dev default or secret patterns"
  fi
fi

# --- 3. config archive ---------------------------------------------------
if [[ ! -f "$CONFIG_ARCHIVE" ]]; then
  fail "config archive not found: $CONFIG_ARCHIVE"
else
  config_listing="$tmp_root/config-listing.txt"
  if ! tar tzf "$CONFIG_ARCHIVE" > "$config_listing" 2>/dev/null; then
    fail "config archive cannot be listed: $CONFIG_ARCHIVE"
  else
    pass "config archive is listable: $CONFIG_ARCHIVE"

    forbidden=0
    while IFS= read -r entry; do
      if reason=$(forbidden_path "$entry"); then
        printf 'FAIL: forbidden entry in config archive: %s — %s\n' "$entry" "$reason" >&2
        fail_count=$((fail_count + 1))
        forbidden=1
      fi
    done < "$config_listing"
    if [[ "$forbidden" -eq 0 ]]; then
      pass "config archive contains no forbidden paths"
    fi

    for forbidden_file in "${FORBIDDEN_1_15_FILES[@]}"; do
      if grep -Fxq -- "$forbidden_file" "$config_listing"; then
        printf 'FAIL: 1.15-only file must not be in the config package: %s\n' "$forbidden_file" >&2
        fail_count=$((fail_count + 1))
      fi
    done

    manifest_basename="$(basename "$MANIFEST")"
    images_basename="$(basename "$IMAGES")"
    required_entries=(
      "docker/docker-compose.yaml"
      "docker/docker-compose.enterprise.yaml"
      "docker/.env.example"
      "dist/offline/$manifest_basename"
      "dist/offline/$images_basename"
      "docker/nginx/"
      "docker/ssrf_proxy/"
    )
    missing=0
    for entry in "${required_entries[@]}"; do
      if ! grep -Fxq -- "$entry" "$config_listing"; then
        printf 'FAIL: config archive missing required entry: %s\n' "$entry" >&2
        fail_count=$((fail_count + 1))
        missing=1
      fi
    done
    if [[ "$missing" -eq 0 ]]; then
      pass "config archive contains the required 1.16 entry set"
    fi

    repo_env_examples=$(cd "$REPO_ROOT" && find docker/envs -type f -name "*.env.example" -printf "docker/envs/%P\n" | sort)
    missing_env=0
    while IFS= read -r example; do
      if ! grep -Fxq -- "$example" "$config_listing"; then
        printf 'FAIL: config archive missing env example: %s\n' "$example" >&2
        fail_count=$((fail_count + 1))
        missing_env=1
      fi
    done <<< "$repo_env_examples"
    if [[ "$missing_env" -eq 0 ]]; then
      pass "config archive includes the full docker/envs env-example set"
    fi

    # Extract and content-scan every archive member.
    extract_dir="$tmp_root/config-extract"
    mkdir -p "$extract_dir"
    tar xzf "$CONFIG_ARCHIVE" -C "$extract_dir" 2>/dev/null || fail "config archive cannot be extracted for content scan"

    dev_default_violations=0
    while IFS= read -r entry; do
      [[ -n "$entry" ]] || continue
      extracted="$extract_dir/${entry#./}"
      [[ -f "$extracted" ]] || continue
      if grep -Fq -- "$DEV_AGENT_SECRET" "$extracted"; then
        has_warning=0
        for marker in "${WARNING_MARKERS[@]}"; do
          if grep -Fq -- "$marker" "$extracted"; then
            has_warning=1
            break
          fi
        done
        if [[ "$has_warning" -ne 1 ]]; then
          printf 'FAIL: dev agent default secret present without an adjacent WARNING marker: %s\n' "${entry#./}" >&2
          fail_count=$((fail_count + 1))
          dev_default_violations=1
        fi
      fi
    done < "$config_listing"
    if [[ "$dev_default_violations" -eq 0 ]]; then
      pass "dev agent default secret only appears where the WARNING marker is present"
    fi
  fi
fi

# --- 4. image bundle archive ---------------------------------------------
if [[ ! -f "$ARCHIVE" ]]; then
  notrun "image bundle archive missing ($ARCHIVE); offline target docker save is Phase F/G/H, not authorized"
else
  bundle_listing="$tmp_root/bundle-listing.txt"
  if ! tar tf "$ARCHIVE" > "$bundle_listing" 2>/dev/null; then
    fail "image bundle archive cannot be listed: $ARCHIVE"
  else
    pass "image bundle archive is listable: $ARCHIVE"

    if grep -Fq "manifest.json" "$bundle_listing" && grep -Fq "repositories" "$bundle_listing"; then
      pass "image bundle has a docker-save top-level layout (manifest.json + repositories)"
    else
      fail "image bundle does not have a docker-save layout (manifest.json + repositories)"
    fi

    forbidden=0
    while IFS= read -r entry; do
      if reason=$(forbidden_path "$entry"); then
        printf 'FAIL: forbidden entry in image bundle: %s — %s\n' "$entry" "$reason" >&2
        fail_count=$((fail_count + 1))
        forbidden=1
      fi
    done < "$bundle_listing"
    if [[ "$forbidden" -eq 0 ]]; then
      pass "image bundle contains no forbidden paths"
    fi

    layer_scan_passes=0
    layer_scan_notrun=0
    while IFS= read -r layer_tar; do
      [[ "$layer_tar" == */layer.tar ]] || continue
      layer_dir="$tmp_root/layer-$(printf '%s' "$layer_tar" | tr '/' '_')"
      mkdir -p "$layer_dir"
      tar xf "$ARCHIVE" -C "$layer_dir" "$layer_tar" 2>/dev/null || {
        printf 'NOT_RUN: image bundle layer could not be extracted: %s\n' "$layer_tar"
        notrun_count=$((notrun_count + 1))
        layer_scan_notrun=1
        continue
      }
      if tar tzf "$layer_dir/$layer_tar" > "$layer_dir/layer-contents.txt" 2>/dev/null; then
        layer_forbidden=0
        while IFS= read -r entry; do
          if reason=$(forbidden_path "$entry"); then
            printf 'FAIL: forbidden entry inside image bundle layer %s: %s — %s\n' "$layer_tar" "$entry" "$reason" >&2
            fail_count=$((fail_count + 1))
            layer_forbidden=1
          fi
        done < "$layer_dir/layer-contents.txt"
        if [[ "$layer_forbidden" -eq 0 ]]; then
          layer_scan_passes=$((layer_scan_passes + 1))
        fi
      else
        printf 'NOT_RUN: image bundle layer cannot be listed (gzip tar scan): %s\n' "$layer_tar"
        notrun_count=$((notrun_count + 1))
        layer_scan_notrun=1
      fi
    done < <(grep '/layer.tar$' "$bundle_listing")

    if [[ "$layer_scan_passes" -gt 0 ]]; then
      pass "image bundle layer scans clean ($layer_scan_passes layers, $layer_scan_notrun NOT_RUN)"
    elif [[ "$layer_scan_notrun" -gt 0 ]]; then
      notrun "no image bundle layer was listable; runtime layer scan remains Phase G"
    fi
  fi
fi

# --- 5. real-secret scan (S-8) --------------------------------------------
if [[ -n "$SECRETS_PATTERN" ]]; then
  if [[ ! -f "$SECRETS_PATTERN" ]]; then
    fail "secrets pattern file not found: $SECRETS_PATTERN"
  else
    pass "real-secret pattern scan configured from protected environment"
  fi
else
  notrun "real-secret pattern scan (S-8) needs a protected-environment pattern file; not available in this B7 run"
fi

echo
echo "check-enterprise-offline summary: $pass_count PASS / $fail_count FAIL / $notrun_count NOT_RUN"

if [[ "$fail_count" -gt 0 ]]; then
  exit 1
fi
exit 0
