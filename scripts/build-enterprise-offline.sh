#!/usr/bin/env bash

set -euo pipefail

VERSION="1.16.0-enterprise"
OUTPUT_DIR="dist/offline"
MODE="reuse"
CHECK_ONLY=false
BASELINE_TAG="1.16.0"
BASELINE_COMMIT="5c6372d2f76d240265b92fd27c16bc772ffcb107"

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
    -Mode|--Mode)
      MODE="${2:?missing value for $1}"
      shift 2
      ;;
    -CheckOnly|--CheckOnly)
      CHECK_ONLY=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: ./scripts/build-enterprise-offline.sh [-Version <version>] [-OutputDir <dir>] [-Mode <smart|rebuild|reuse>] [-CheckOnly]" >&2
      exit 1
      ;;
  esac
done

case "$MODE" in
  smart|rebuild|reuse)
    ;;
  *)
    echo "Unsupported mode: $MODE" >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOCKER_DIR="$REPO_ROOT/docker"
ENV_FILE="$DOCKER_DIR/.env"
OUTPUT_PATH="$REPO_ROOT/$OUTPUT_DIR"
WEB_BUILD_CONTEXT=""

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing docker/.env. Copy docker/.env.example to docker/.env and fill in deployment settings first." >&2
  exit 1
fi

API_IMAGE="dify-api-enterprise:$VERSION"
WEB_IMAGE="dify-web-enterprise:$VERSION"
PREVIOUS_DIFY_ENTERPRISE_VERSION="${DIFY_ENTERPRISE_VERSION-__UNSET__}"
PREVIOUS_DEBUG="${DEBUG-__UNSET__}"
PREVIOUS_ENTERPRISE_ENABLED="${ENTERPRISE_ENABLED-__UNSET__}"
PREVIOUS_COMPOSE_PROFILES="${COMPOSE_PROFILES-__UNSET__}"
export DIFY_ENTERPRISE_VERSION="$VERSION"
export DEBUG="${DEBUG:-false}"
export ENTERPRISE_ENABLED="${ENTERPRISE_ENABLED:-false}"
if [[ -z "${COMPOSE_PROFILES:-}" ]]; then
  ENV_VECTOR_STORE="$(awk -F= '/^VECTOR_STORE=/{print $2; exit}' "$ENV_FILE")"
  ENV_DB_TYPE="$(awk -F= '/^DB_TYPE=/{print $2; exit}' "$ENV_FILE")"
  export COMPOSE_PROFILES="${ENV_VECTOR_STORE:-weaviate},${ENV_DB_TYPE:-postgresql},collaboration"
fi

mkdir -p "$OUTPUT_PATH"

cleanup() {
  if [[ -n "$WEB_BUILD_CONTEXT" ]]; then
    rm -rf "$WEB_BUILD_CONTEXT"
  fi

  if [[ "$PREVIOUS_DIFY_ENTERPRISE_VERSION" == "__UNSET__" ]]; then
    unset DIFY_ENTERPRISE_VERSION
  else
    export DIFY_ENTERPRISE_VERSION="$PREVIOUS_DIFY_ENTERPRISE_VERSION"
  fi
  if [[ "$PREVIOUS_DEBUG" == "__UNSET__" ]]; then
    unset DEBUG
  else
    export DEBUG="$PREVIOUS_DEBUG"
  fi
  if [[ "$PREVIOUS_ENTERPRISE_ENABLED" == "__UNSET__" ]]; then
    unset ENTERPRISE_ENABLED
  else
    export ENTERPRISE_ENABLED="$PREVIOUS_ENTERPRISE_ENABLED"
  fi
  if [[ "$PREVIOUS_COMPOSE_PROFILES" == "__UNSET__" ]]; then
    unset COMPOSE_PROFILES
  else
    export COMPOSE_PROFILES="$PREVIOUS_COMPOSE_PROFILES"
  fi
}

trap cleanup EXIT

get_image_commit_sha() {
  local image="$1"
  docker image inspect "$image" --format '{{range .Config.Env}}{{println .}}{{end}}' 2>/dev/null \
    | awk -F= '/^COMMIT_SHA=/{print $2; exit}'
}

is_reusable_image() {
  local image="$1"
  local expected="$2"
  local actual
  actual="$(get_image_commit_sha "$image" || true)"
  [[ -n "$actual" && "$actual" == "$expected" ]]
}

# Read-only content gate: verifies a same-tag enterprise API image actually
# matches the current candidate HEAD before it is accepted as reusable.
# All docker operations below (run) never modify the image.
verify_enterprise_image_content() {
  local image="$1"
  local repo_migrations image_migrations

  repo_migrations="$(find "$REPO_ROOT/api/migrations/versions" -maxdepth 1 -type f -name '*.py' -printf '%f\n' | sort)"
  image_migrations="$(docker run --rm --entrypoint sh "$image" -c 'ls -1 /app/api/migrations/versions/*.py 2>/dev/null | sed "s#.*/##"' 2>/dev/null | sort || true)"

  if [[ "$image_migrations" != "$repo_migrations" ]]; then
    echo "Image $image is not reusable: image migration file set differs from the repository api/migrations/versions at current HEAD." >&2
    diff <(printf '%s\n' "$repo_migrations") <(printf '%s\n' "$image_migrations") >&2 || true
    return 1
  fi

  if ! docker run --rm --entrypoint sh "$image" -c 'grep -Fq _align_snapshot_to_composition /app/api/clients/agent_backend/request_builder.py' >/dev/null 2>&1; then
    echo "Image $image is not reusable: /app/api/clients/agent_backend/request_builder.py does not contain _align_snapshot_to_composition." >&2
    return 1
  fi

  return 0
}

ensure_enterprise_image() {
  local image="$1"
  local dockerfile="$2"
  local context_path="$3"
  local expected="$4"
  local verify_content="${5:-false}"

  if [[ "$CHECK_ONLY" == true || "$MODE" == "reuse" ]]; then
    if ! is_reusable_image "$image" "$expected"; then
      echo "Image $image is not reusable. Expected COMMIT_SHA=$expected." >&2
      exit 1
    fi
    if [[ "$verify_content" == true ]] && ! verify_enterprise_image_content "$image"; then
      exit 1
    fi
    echo "Reusing enterprise image: $image"
    return
  fi

  if [[ "$MODE" == "smart" ]] && is_reusable_image "$image" "$expected"; then
    if [[ "$verify_content" == true ]] && ! verify_enterprise_image_content "$image"; then
      exit 1
    fi
    echo "Reusing enterprise image: $image"
    return
  fi

  echo "Building enterprise image: $image"
  docker build \
    --build-arg "COMMIT_SHA=$expected" \
    -f "$dockerfile" \
    -t "$image" \
    "$context_path"
}

build_enterprise_web_image() {
  local image="$1"
  local expected="$2"

  if [[ "$CHECK_ONLY" == true || "$MODE" == "reuse" ]]; then
    if ! is_reusable_image "$image" "$expected"; then
      echo "Image $image is not reusable. Expected COMMIT_SHA=$expected." >&2
      exit 1
    fi
    echo "Reusing enterprise image: $image"
    return
  fi

  if [[ "$MODE" == "smart" ]] && is_reusable_image "$image" "$expected"; then
    echo "Reusing enterprise image: $image"
    return
  fi

  local temp_context
  temp_context="$(mktemp -d)"
  WEB_BUILD_CONTEXT="$temp_context"

  echo "Building enterprise image: $image"
  cp "$REPO_ROOT/package.json" "$REPO_ROOT/pnpm-lock.yaml" "$REPO_ROOT/pnpm-workspace.yaml" "$temp_context/"
  [[ -f "$REPO_ROOT/.nvmrc" ]] && cp "$REPO_ROOT/.nvmrc" "$temp_context/"
  cp -R "$REPO_ROOT/web" "$REPO_ROOT/e2e" "$REPO_ROOT/packages" "$REPO_ROOT/sdks" "$temp_context/"
  find "$temp_context" \
    \( -path '*/node_modules' -o -path '*/.next' -o -path '*/dist' -o -path '*/build' -o -path '*/coverage' -o -path '*/.pnpm-store' \) \
    -prune -exec rm -rf {} +

  docker build \
    --build-arg "COMMIT_SHA=$expected" \
    -f "$temp_context/web/Dockerfile" \
    -t "$image" \
    "$temp_context"
}

ensure_enterprise_image "$API_IMAGE" "$REPO_ROOT/api/Dockerfile" "$REPO_ROOT/api" "$VERSION" true
build_enterprise_web_image "$WEB_IMAGE" "$VERSION"

echo "Resolving compose image list"
mapfile -t RAW_IMAGES < <(
  docker compose --env-file "$ENV_FILE" \
    -f "$DOCKER_DIR/docker-compose.yaml" \
    -f "$DOCKER_DIR/docker-compose.enterprise.yaml" \
    config --images | sed '/^[[:space:]]*$/d'
)
mapfile -t IMAGES < <(printf '%s\n' "${RAW_IMAGES[@]}" | sort -u)

if [[ ${#IMAGES[@]} -eq 0 ]]; then
  echo "Unable to resolve images from docker compose configuration." >&2
  exit 1
fi

api_count=$(printf '%s\n' "${RAW_IMAGES[@]}" | grep -Fx -c "$API_IMAGE" || true)
web_count=$(printf '%s\n' "${RAW_IMAGES[@]}" | grep -Fx -c "$WEB_IMAGE" || true)
api_tag_entries=$(printf '%s\n' "${IMAGES[@]}" | grep -E -c '^dify-api-enterprise:' || true)
web_tag_entries=$(printf '%s\n' "${IMAGES[@]}" | grep -E -c '^dify-web-enterprise:' || true)
if [[ "$api_count" -ne 4 ]]; then
  echo "Required-image assertion failed: enterprise API image $API_IMAGE must resolve for api, worker, worker_beat and api_websocket (found $api_count)." >&2
  exit 1
fi
if [[ "$web_count" -ne 1 ]]; then
  echo "Required-image assertion failed: enterprise Web image $WEB_IMAGE must resolve exactly once (found $web_count)." >&2
  exit 1
fi
if [[ "$api_tag_entries" -ne 1 ]]; then
  echo "Required-image assertion failed: exactly one enterprise API tag expected (found $api_tag_entries)." >&2
  exit 1
fi
if [[ "$web_tag_entries" -ne 1 ]]; then
  echo "Required-image assertion failed: exactly one enterprise Web tag expected (found $web_tag_entries)." >&2
  exit 1
fi
for required in \
  "langgenius/dify-agent-backend:1.16.0" \
  "langgenius/dify-agent-local-sandbox:1.16.0"; do
  if ! printf '%s\n' "${IMAGES[@]}" | grep -Fxq "$required"; then
    echo "Required-image assertion failed: missing required image $required." >&2
    exit 1
  fi
done

for image in "${IMAGES[@]}"; do
  if [[ "$image" != "$API_IMAGE" && "$image" != "$WEB_IMAGE" ]]; then
    if docker image inspect "$image" >/dev/null 2>&1; then
      echo "Reusing local dependency image: $image"
    elif [[ "$CHECK_ONLY" == true ]]; then
      echo "Dry-run: dependency image $image is not local; pull would run on the build machine."
    else
      echo "Pulling dependency image: $image"
      docker pull "$image"
    fi
  fi
done

MANIFEST_PATH="$OUTPUT_PATH/manifest-$VERSION.json"
IMAGES_PATH="$OUTPUT_PATH/images-$VERSION.txt"
ARCHIVE_PATH="$OUTPUT_PATH/dify-enterprise-offline-$VERSION.tar"

printf '%s\n' "${IMAGES[@]}" > "$IMAGES_PATH"

ENTERPRISE_COMMIT="$(git rev-parse HEAD)"

python3 - "$MANIFEST_PATH" "$IMAGES_PATH" "$VERSION" "$ENTERPRISE_COMMIT" "$BASELINE_TAG" "$BASELINE_COMMIT" <<'PY'
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

manifest_path, images_path, version, enterprise_commit, baseline_tag, baseline_commit = sys.argv[1:]
image_names = [line for line in Path(images_path).read_text(encoding="utf-8").splitlines() if line.strip()]


def docker_image_field(image: str, template: str) -> str:
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image, "--format", template],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    value = result.stdout.strip() if result.returncode == 0 else ""
    return "" if value == "<no value>" else value


manifest = {
    "version": version,
    "baseline": {"tag": baseline_tag, "commit": baseline_commit},
    "enterprise_commit": enterprise_commit,
    "image_tag": version,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "images": [
        {
            "name": name,
            "id": docker_image_field(name, "{{.Id}}"),
            "digest": docker_image_field(name, "{{index .RepoDigests 0}}"),
        }
        for name in image_names
    ],
}
Path(manifest_path).write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

echo "Manifest written: $MANIFEST_PATH"
echo "Images written  : $IMAGES_PATH"

if [[ "$CHECK_ONLY" == true ]]; then
  echo "Dry-run complete (no docker build/pull/save executed)."
  echo "Manifest: $MANIFEST_PATH"
  echo "Images : $IMAGES_PATH"
  exit 0
fi

echo "Saving offline image bundle to $ARCHIVE_PATH"
docker save -o "$ARCHIVE_PATH" "${IMAGES[@]}"

echo "Offline bundle ready."
echo "Manifest: $MANIFEST_PATH"
echo "Images : $IMAGES_PATH"
echo "Archive: $ARCHIVE_PATH"
