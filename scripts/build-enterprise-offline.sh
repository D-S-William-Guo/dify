#!/usr/bin/env bash

set -euo pipefail

VERSION="enterprise-local"
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
      echo "Usage: ./scripts/build-enterprise-offline.sh [-Version <version>] [-OutputDir <dir>]" >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"
ENV_FILE="$DOCKER_DIR/.env"
OUTPUT_PATH="$REPO_ROOT/$OUTPUT_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing docker/.env. Copy docker/.env.example to docker/.env and fill in deployment settings first." >&2
  exit 1
fi

API_IMAGE="dify-api-enterprise:$VERSION"
WEB_IMAGE="dify-web-enterprise:$VERSION"

mkdir -p "$OUTPUT_PATH"

echo "Building enterprise API image: $API_IMAGE"
docker build \
  --build-arg "COMMIT_SHA=$VERSION" \
  -f "$REPO_ROOT/api/Dockerfile" \
  -t "$API_IMAGE" \
  "$REPO_ROOT/api"

echo "Building enterprise Web image: $WEB_IMAGE"
docker build \
  --build-arg "COMMIT_SHA=$VERSION" \
  -f "$REPO_ROOT/web/Dockerfile" \
  -t "$WEB_IMAGE" \
  "$REPO_ROOT"

echo "Resolving compose image list"
mapfile -t IMAGES < <(
  docker compose --env-file "$ENV_FILE" \
    -f "$DOCKER_DIR/docker-compose.yaml" \
    -f "$DOCKER_DIR/docker-compose.enterprise.yaml" \
    config --images | sed '/^[[:space:]]*$/d' | sort -u
)

if [[ ${#IMAGES[@]} -eq 0 ]]; then
  echo "Unable to resolve images from docker compose configuration." >&2
  exit 1
fi

for image in "${IMAGES[@]}"; do
  if [[ "$image" != "$API_IMAGE" && "$image" != "$WEB_IMAGE" ]]; then
    echo "Pulling dependency image: $image"
    docker pull "$image"
  fi
done

MANIFEST_PATH="$OUTPUT_PATH/manifest-$VERSION.json"
IMAGES_PATH="$OUTPUT_PATH/images-$VERSION.txt"
ARCHIVE_PATH="$OUTPUT_PATH/dify-enterprise-offline-$VERSION.tar"

printf '%s\n' "${IMAGES[@]}" > "$IMAGES_PATH"

python3 - <<PY
from datetime import datetime, timezone
from pathlib import Path
import json

manifest_path = Path(r"$MANIFEST_PATH")
images = Path(r"$IMAGES_PATH").read_text(encoding="utf-8").splitlines()
manifest = {
    "version": r"$VERSION",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "images": images,
}
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

echo "Saving offline image bundle to $ARCHIVE_PATH"
docker save -o "$ARCHIVE_PATH" "${IMAGES[@]}"

echo "Offline bundle ready."
echo "Manifest: $MANIFEST_PATH"
echo "Images : $IMAGES_PATH"
echo "Archive: $ARCHIVE_PATH"
