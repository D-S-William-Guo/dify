#!/usr/bin/env bash

set -euo pipefail

ARCHIVE=""
CONFIG_ARCHIVE=""
MANIFEST=""
IMAGES=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -Archive|--Archive) ARCHIVE="${2:?missing value for $1}"; shift 2 ;;
    -ConfigArchive|--ConfigArchive) CONFIG_ARCHIVE="${2:?missing value for $1}"; shift 2 ;;
    -Manifest|--Manifest) MANIFEST="${2:?missing value for $1}"; shift 2 ;;
    -Images|--Images) IMAGES="${2:?missing value for $1}"; shift 2 ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: ./scripts/ci/check-enterprise-offline.sh -Archive <tar> -ConfigArchive <tar.gz> -Manifest <json> -Images <txt>" >&2
      exit 1
      ;;
  esac
done

for required in ARCHIVE CONFIG_ARCHIVE MANIFEST IMAGES; do
  if [[ -z "${!required}" ]]; then
    echo "Missing required argument: $required" >&2
    exit 1
  fi
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${OFFLINE_GATE_REPO_ROOT:-$SCRIPT_DIR/../..}" && pwd)"

python3 - "$REPO_ROOT" "$ARCHIVE" "$CONFIG_ARCHIVE" "$MANIFEST" "$IMAGES" <<'PY'
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path, PurePosixPath

repo_root = Path(sys.argv[1]).resolve()
archive_path, config_path, manifest_path, images_path = map(Path, sys.argv[2:])
sha256_re = re.compile(r"^sha256:[0-9a-f]{64}$")
commit_re = re.compile(r"^[0-9a-f]{40}$")
version_re = re.compile(r"^[A-Za-z0-9._-]+$")
legacy_config_re = re.compile(r"^([0-9a-f]{64})\.json$")
docker29_config_re = re.compile(r"^blobs/sha256/([0-9a-f]{64})$")
dev_default = b"MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY"
warning_markers = (b"WARNING", b"Replace this development default in production")
fixed_sources = {
    "docker/docker-compose.yaml",
    "docker/docker-compose.enterprise.yaml",
    "docker/.env.example",
    "docker/nginx/conf.d/default.conf.template",
    "docker/nginx/docker-entrypoint.sh",
    "docker/nginx/https.conf.template",
    "docker/nginx/nginx.conf.template",
    "docker/nginx/proxy.conf.template",
    "docker/nginx/ssl/.gitkeep",
    "docker/ssrf_proxy/docker-entrypoint.sh",
    "docker/ssrf_proxy/squid.conf.template",
    "docker/ssrf_proxy/test_ssrf_proxy_config.sh",
}
pass_count = fail_count = notrun_count = 0


def passed(message: str) -> None:
    global pass_count
    print(f"PASS: {message}")
    pass_count += 1


def failed(message: str) -> None:
    global fail_count
    print(f"FAIL: {message}", file=sys.stderr)
    fail_count += 1


def canonical_member(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    path = PurePosixPath(name)
    canonical = path.as_posix()
    if not name or name.startswith("/") or "\\" in name or name not in (canonical, f"{canonical}/") or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"unsafe archive member: {name or '<empty>'}")
    return canonical


def bounded_members(bundle: tarfile.TarFile, limit: int, label: str) -> list[tarfile.TarInfo]:
    members = []
    for member in bundle:
        members.append(member)
        if len(members) > limit:
            raise ValueError(f"{label} has too many members")
    return members


def repository(name: str) -> str:
    name = name.split("@", 1)[0]
    slash = name.rfind("/")
    colon = name.rfind(":")
    return name[:colon] if colon > slash else name


def artifact_member(path: Path) -> str:
    resolved = path.resolve() if path.is_absolute() else (repo_root / path).resolve()
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise ValueError(f"generated artifact is outside the candidate tree: {path}") from exc


manifest = None
image_names: list[str] = []
manifest_images: dict[str, dict[str, str]] = {}

try:
    if not images_path.is_file() or images_path.stat().st_size == 0 or images_path.stat().st_size > 1024 * 1024:
        raise ValueError("images file missing, empty, or oversized")
    raw_lines = images_path.read_text(encoding="utf-8").splitlines()
    if not raw_lines or any(not line.strip() or line != line.strip() for line in raw_lines):
        raise ValueError("images file contains an empty or non-canonical line")
    image_names = raw_lines
    if image_names != sorted(set(image_names)):
        raise ValueError("image names must be unique and ordered")
    passed("image names are non-empty, unique, and ordered")
except (OSError, UnicodeError, ValueError) as exc:
    failed(f"images validation failed: {exc}")

try:
    if not manifest_path.is_file() or manifest_path.stat().st_size == 0 or manifest_path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("release manifest missing, empty, or oversized")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("release manifest root must be an object")
    version = manifest.get("version")
    if not isinstance(version, str) or not version_re.fullmatch(version):
        raise ValueError("missing manifest version")
    if not isinstance(manifest.get("generated_at"), str) or not manifest["generated_at"]:
        raise ValueError("missing manifest generation timestamp")
    required_images = {
        f"dify-api-enterprise:{version}",
        f"dify-web-enterprise:{version}",
        "langgenius/dify-agent-backend:1.16.0",
        "langgenius/dify-agent-local-sandbox:1.16.0",
    }
    if not required_images.issubset(image_names):
        raise ValueError("required image assertion failed")
    if manifest.get("baseline") != {"tag": "1.16.0", "commit": "5c6372d2f76d240265b92fd27c16bc772ffcb107"}:
        raise ValueError("baseline identity mismatch")
    if manifest.get("image_tag") != version:
        raise ValueError("version and image_tag must match")
    candidate = manifest.get("enterprise_commit")
    if not isinstance(candidate, str) or not commit_re.fullmatch(candidate):
        raise ValueError("candidate commit is missing or malformed")
    actual_candidate = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if candidate != actual_candidate:
        raise ValueError("release manifest candidate does not match the exact candidate tree")
    if manifest.get("mode") != "rebuild" or manifest.get("release_gate") is not True:
        raise ValueError("normal release provenance requires explicit rebuild")
    entries = manifest.get("images")
    if not isinstance(entries, list) or [entry.get("name") for entry in entries if isinstance(entry, dict)] != image_names:
        raise ValueError("manifest image names must uniquely match image-list order")
    for entry in entries:
        if not isinstance(entry, dict) or set(("name", "id", "digest")) - entry.keys():
            raise ValueError("manifest image entry is incomplete")
        name, image_id, digest = entry["name"], entry["id"], entry["digest"]
        if not isinstance(image_id, str) or not sha256_re.fullmatch(image_id):
            raise ValueError(f"missing or malformed immutable image ID: {name}")
        if not isinstance(digest, str):
            raise ValueError(f"malformed RepoDigest: {name}")
        if digest:
            if "@" not in digest:
                raise ValueError(f"malformed RepoDigest: {name}")
            digest_repo, digest_value = digest.rsplit("@", 1)
            if repository(digest_repo) != repository(name) or not sha256_re.fullmatch(digest_value):
                raise ValueError(f"repository-mismatched or malformed RepoDigest: {name}")
        manifest_images[name] = entry
    missing_registry_provenance = [entry["name"] for entry in entries if not entry["digest"]]
    if missing_registry_provenance:
        print(
            "WARNING: registry-origin provenance unavailable; image-ID bundle identity only: "
            + ", ".join(missing_registry_provenance)
        )
    passed("release manifest binds candidate, ordered names, immutable IDs, and matched RepoDigests")
except (OSError, UnicodeError, json.JSONDecodeError, subprocess.SubprocessError, ValueError) as exc:
    failed(f"manifest identity validation failed: {exc}")

try:
    tree = subprocess.run(
        ["git", "-C", str(repo_root), "ls-tree", "-r", "-z", "HEAD", "--", "docker/envs", "docker/nginx", "docker/ssrf_proxy", "docker/docker-compose.yaml", "docker/docker-compose.enterprise.yaml", "docker/.env.example"],
        check=True,
        capture_output=True,
    ).stdout
    tracked_regular: set[str] = set()
    for record in tree.split(b"\0"):
        if not record:
            continue
        metadata, raw_name = record.split(b"\t", 1)
        mode, kind, _object_id = metadata.decode("ascii").split()
        name = raw_name.decode("utf-8")
        if kind == "blob" and mode.startswith("100"):
            tracked_regular.add(name)
    env_examples = {name for name in tracked_regular if name.startswith("docker/envs/") and name.endswith(".env.example")}
    if len(env_examples) != 37 or not fixed_sources.issubset(tracked_regular):
        raise ValueError("candidate tree does not contain the accepted 49 source members")
    if manifest is None or not isinstance(manifest.get("version"), str):
        raise ValueError("valid release manifest required before config validation")
    version = manifest["version"]
    generated = {artifact_member(manifest_path), artifact_member(images_path)}
    if {Path(name).name for name in generated} != {f"manifest-{version}.json", f"images-{version}.txt"}:
        raise ValueError("generated config members are not version matched")
    expected = fixed_sources | env_examples | generated
    if len(expected) != 51:
        raise ValueError(f"expected 51 exact regular members, got {len(expected)}")
    if not config_path.is_file():
        raise ValueError("config archive not found")
    with tarfile.open(config_path, "r:gz") as bundle:
        members = bounded_members(bundle, 128, "config archive")
        seen: set[str] = set()
        regular: dict[str, tarfile.TarInfo] = {}
        allowed_dirs = {str(parent) for name in expected for parent in PurePosixPath(name).parents if str(parent) != "."}
        for member in members:
            name = canonical_member(member.name)
            if name in seen:
                raise ValueError(f"duplicate config member: {name}")
            seen.add(name)
            parts = set(PurePosixPath(name).parts)
            basename = PurePosixPath(name).name
            if "docker" in parts and "volumes" in parts:
                raise ValueError(f"docker/volumes runtime data: {name}")
            if parts & {".secrets", "secrets", "credentials"}:
                raise ValueError(f"credential-path member: {name}")
            allowed_env_suffixes = (".env.example", ".env.sample", ".env.template")
            if basename == ".env" or ((basename.endswith(".env") or ".env." in basename) and not basename.endswith(allowed_env_suffixes)):
                raise ValueError(f"real environment file: {name}")
            if basename.lower().endswith((".key", ".pem", ".p12", ".pfx", ".crt", ".cer", ".cert", ".der")) or basename in {"id_rsa", "id_ed25519", "credentials.json"}:
                raise ValueError(f"credential, key, or certificate member: {name}")
            if member.isdir() and name in allowed_dirs:
                continue
            if not member.isreg():
                raise ValueError(f"non-regular config member: {name}")
            if member.size > 2 * 1024 * 1024:
                raise ValueError(f"oversized config member: {name}")
            regular[name] = member
        missing = sorted(expected - regular.keys())
        extra = sorted(regular.keys() - expected)
        if missing:
            raise ValueError(f"missing config member: {missing[0]}")
        if extra:
            raise ValueError(f"unexpected config member: {extra[0]}")
        passed("config archive contains exactly 51 candidate-bound regular members")
        generated_content = {
            artifact_member(manifest_path): manifest_path.read_bytes(),
            artifact_member(images_path): images_path.read_bytes(),
        }
        for name, member in regular.items():
            stream = bundle.extractfile(member)
            if stream is None:
                raise ValueError(f"unable to read regular config member: {name}")
            data = stream.read(2 * 1024 * 1024 + 1)
            if name in generated_content and data != generated_content[name]:
                raise ValueError(f"generated config member does not match gate input: {name}")
            if dev_default in data and not any(marker in data for marker in warning_markers):
                raise ValueError(f"dev default present without required WARNING marker: {name}")
        passed("public development default appears only with its required warning")
except (OSError, UnicodeError, tarfile.TarError, subprocess.SubprocessError, ValueError) as exc:
    failed(f"config archive validation failed: {exc}")

try:
    if not archive_path.is_file():
        raise ValueError("image bundle archive not found")
    with tarfile.open(archive_path, "r:*") as bundle:
        members = bounded_members(bundle, 4096, "image bundle")
        by_name: dict[str, list[tarfile.TarInfo]] = {}
        for member in members:
            name = canonical_member(member.name)
            by_name.setdefault(name, []).append(member)
        manifests = by_name.get("manifest.json", [])
        if len(manifests) != 1 or not manifests[0].isreg():
            raise ValueError("manifest.json must be one regular top-level member")
        manifest_member = manifests[0]
        if manifest_member.size <= 0 or manifest_member.size > 1024 * 1024:
            raise ValueError("manifest.json is empty or oversized")
        stream = bundle.extractfile(manifest_member)
        if stream is None:
            raise ValueError("manifest.json cannot be read")
        save_manifest = json.loads(stream.read(1024 * 1024 + 1))
        if not isinstance(save_manifest, list) or not save_manifest or len(save_manifest) > 512:
            raise ValueError("Docker-save manifest root must be a bounded non-empty list")
        saved_tags: list[str] = []
        for record in save_manifest:
            if not isinstance(record, dict) or not isinstance(record.get("Config"), str) or not isinstance(record.get("RepoTags"), list):
                raise ValueError("Docker-save manifest entry is malformed")
            config = canonical_member(record["Config"])
            match = legacy_config_re.fullmatch(config) or docker29_config_re.fullmatch(config)
            if not match:
                raise ValueError(f"unsupported Docker-save Config metadata: {config}")
            config_digest = match.group(1)
            config_members = by_name.get(config, [])
            if len(config_members) != 1 or not config_members[0].isreg():
                raise ValueError(f"Docker-save Config member missing, duplicate, or non-regular: {config}")
            tags = record["RepoTags"]
            if not tags or any(not isinstance(tag, str) or not tag for tag in tags):
                raise ValueError("Docker-save RepoTags are malformed")
            for tag in tags:
                if tag not in manifest_images or manifest_images[tag]["id"] != f"sha256:{config_digest}":
                    raise ValueError(f"Docker-save Config digest does not bind release manifest ID: {tag}")
                saved_tags.append(tag)
        if saved_tags != image_names:
            raise ValueError("Docker-save RepoTags must uniquely match image-list order")
        passed("Docker-save top-level metadata binds ordered tags to release-manifest image IDs")
except (OSError, UnicodeError, json.JSONDecodeError, tarfile.TarError, ValueError) as exc:
    failed(f"image bundle metadata validation failed: {exc}")

print()
print(f"check-enterprise-offline summary: {pass_count} PASS / {fail_count} FAIL / {notrun_count} NOT_RUN")
raise SystemExit(1 if fail_count else 0)
PY
