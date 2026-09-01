#!/usr/bin/env bash

set -euo pipefail

VERSION="1.16.0-enterprise"
OUTPUT_DIR="dist/offline"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -Version|--Version)
      VERSION="${2:?missing value for $1}"
      shift 2
      ;;
    -OutputDir|--OutputDir)
      OUTPUT_DIR="${2:?missing value for $1}"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: ./scripts/build-enterprise-config-package.sh [-Version <version>] [-OutputDir <dir>]" >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${OFFLINE_GATE_REPO_ROOT:-$SCRIPT_DIR/..}" && pwd)"
OUTPUT_PATH="$REPO_ROOT/$OUTPUT_DIR"
MANIFEST_PATH="$OUTPUT_PATH/manifest-$VERSION.json"
IMAGES_PATH="$OUTPUT_PATH/images-$VERSION.txt"
ARCHIVE_PATH="$OUTPUT_PATH/dify-enterprise-config-$VERSION.tar.gz"

if [[ ! "$VERSION" =~ ^[A-Za-z0-9._-]+$ || "$OUTPUT_DIR" == /* || "/$OUTPUT_DIR/" == */../* ]]; then
  echo "Unsafe version or output directory." >&2
  exit 1
fi

if [[ ! -f "$MANIFEST_PATH" || ! -f "$IMAGES_PATH" ]]; then
  echo "Missing offline manifest or image list for version $VERSION." >&2
  echo "Run build-enterprise-offline with explicit -Mode rebuild first." >&2
  exit 1
fi

if ! python3 - "$MANIFEST_PATH" "$VERSION" <<'PY'
import json
import sys

path, version = sys.argv[1:]
try:
    manifest = json.load(open(path, encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Invalid release manifest: {exc}")
if manifest.get("version") != version or manifest.get("mode") != "rebuild" or manifest.get("release_gate") is not True:
    raise SystemExit("Config package requires version-matched rebuild release provenance.")
PY
then
  exit 1
fi

source_files=(
  "docker/docker-compose.yaml"
  "docker/docker-compose.enterprise.yaml"
  "docker/.env.example"
  "docker/nginx/conf.d/default.conf.template"
  "docker/nginx/docker-entrypoint.sh"
  "docker/nginx/https.conf.template"
  "docker/nginx/nginx.conf.template"
  "docker/nginx/proxy.conf.template"
  "docker/nginx/ssl/.gitkeep"
  "docker/ssrf_proxy/docker-entrypoint.sh"
  "docker/ssrf_proxy/squid.conf.template"
  "docker/ssrf_proxy/test_ssrf_proxy_config.sh"
)

mapfile -t env_example_files < <(git -C "$REPO_ROOT" ls-tree -r --name-only HEAD -- docker/envs | awk '/\.env\.example$/ { print }' | sort)
if [[ ${#env_example_files[@]} -ne 37 ]]; then
  echo "Candidate must contain exactly 37 tracked docker/envs/*.env.example files (found ${#env_example_files[@]})." >&2
  exit 1
fi
source_files+=("${env_example_files[@]}")

generated_files=(
  "$OUTPUT_DIR/manifest-$VERSION.json"
  "$OUTPUT_DIR/images-$VERSION.txt"
)

for path in "${source_files[@]}"; do
  if [[ ! -f "$REPO_ROOT/$path" || -L "$REPO_ROOT/$path" ]] ||
    [[ "$(git -C "$REPO_ROOT" ls-tree HEAD -- "$path" | awk '{print $1}')" != 100* ]]; then
    echo "Missing required file: $path" >&2
    exit 1
  fi
done

if ! git -C "$REPO_ROOT" diff --quiet HEAD -- "${source_files[@]}"; then
  echo "Configuration inputs must match the exact candidate tree." >&2
  exit 1
fi

candidate_context_files=$(printf '%s\n' "${source_files[@]:3}" | sort)
working_context_files=$(find "$REPO_ROOT/docker/envs" "$REPO_ROOT/docker/nginx" "$REPO_ROOT/docker/ssrf_proxy" \
  ! -type d -printf '%p\n' | sed -e "s#^$REPO_ROOT/##" | sort)
if [[ "$working_context_files" != "$candidate_context_files" ]]; then
  echo "Configuration input roots contain non-candidate, missing, or wrong-type members." >&2
  exit 1
fi

for path in "${generated_files[@]}"; do
  if [[ ! -f "$REPO_ROOT/$path" || -L "$REPO_ROOT/$path" ]]; then
    echo "Missing required generated file: $path" >&2
    exit 1
  fi
done

mkdir -p "$OUTPUT_PATH"

tmp_archive=$(mktemp "$OUTPUT_PATH/.config-package.XXXXXX")
trap 'rm -f "$tmp_archive"' EXIT
tar \
  --create \
  --gzip \
  --file "$tmp_archive" \
  --directory "$REPO_ROOT" \
  -- \
  "${source_files[@]}" \
  "${generated_files[@]}"
mv "$tmp_archive" "$ARCHIVE_PATH"
trap - EXIT

echo "Enterprise configuration bundle ready."
echo "Archive: $ARCHIVE_PATH"
