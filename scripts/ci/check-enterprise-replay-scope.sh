#!/usr/bin/env bash

set -euo pipefail

readonly OFFICIAL_BASE_COMMIT="5c6372d2f76d240265b92fd27c16bc772ffcb107"

fail() {
  printf 'enterprise replay scope check failed: %s\n' "$1" >&2
  exit 1
}

usage() {
  printf 'usage: %s <base-ref> <head-ref>\n' "${0##*/}" >&2
}

if [[ $# -ne 2 ]]; then
  usage
  exit 2
fi

base_ref=$1
head_ref=$2

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || fail "run this command from a Git worktree"

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

base_commit=$(git rev-parse --verify --quiet "${base_ref}^{commit}") \
  || fail "base ref is not a valid commit"
head_commit=$(git rev-parse --verify --quiet "${head_ref}^{commit}") \
  || fail "head ref is not a valid commit"

[[ "$base_commit" == "$OFFICIAL_BASE_COMMIT" ]] \
  || fail "base ref does not resolve to the approved Dify 1.16.0 commit"

merge_base=$(git merge-base "$base_commit" "$head_commit") \
  || fail "base and head do not have a merge base"
[[ "$merge_base" == "$OFFICIAL_BASE_COMMIT" ]] \
  || fail "merge-base is not the approved Dify 1.16.0 commit"

declare -a changed_paths=()
declare -a changed_statuses=()

while IFS= read -r -d '' status; do
  IFS= read -r -d '' first_path \
    || fail "Git returned an incomplete name-status record"

  case "$status" in
    R*|C*)
      IFS= read -r -d '' second_path \
        || fail "Git returned an incomplete rename/copy record"
      changed_statuses+=("$status" "$status")
      changed_paths+=("$first_path" "$second_path")
      ;;
    *)
      changed_statuses+=("$status")
      changed_paths+=("$first_path")
      ;;
  esac
done < <(git diff --name-status -z --find-renames --find-copies "$base_commit...$head_commit")

is_safe_env_example() {
  case "$1" in
    *.env.example|*.env.sample|*.env.template|*/.env.example|*/.env.sample|*/.env.template)
      return 0
      ;;
  esac
  return 1
}

classify_forbidden_path() {
  local path=$1
  local lower=${path,,}
  local basename=${lower##*/}

  case "/$lower/" in
    */docker/volumes/*)
      printf 'docker/volumes is runtime data and must never enter the replay diff'
      return 0
      ;;
    */node_modules/*)
      printf 'node_modules is a dependency artifact'
      return 0
      ;;
    */.cache/*|*/.pytest_cache/*|*/.mypy_cache/*|*/.ruff_cache/*|*/.uv-cache/*|*/__pycache__/*|*/.turbo/*|*/.pnpm-store/*|*/.yarn/cache/*)
      printf 'cache content is not allowed'
      return 0
      ;;
    */.next/*|*/build/*|*/dist/*|*/coverage/*|*/htmlcov/*)
      printf 'generated build or coverage output is not allowed'
      return 0
      ;;
    */.secrets/*|*/secrets/*)
      printf 'secret-bearing directories are not allowed'
      return 0
      ;;
  esac

  if [[ "$basename" == ".env" || "$basename" == .env.* || "$basename" == *.env ]]; then
    if ! is_safe_env_example "$lower"; then
      printf 'real environment files are not allowed; commit only documented examples'
      return 0
    fi
  fi

  case "$basename" in
    credentials.json|service-account*.json|id_rsa|id_ed25519|*.pem|*.key|*.p12|*.pfx|*.pyc|*.pyo|*.class|*.o|*.so)
      printf 'credential, key, or compiled artifact paths are not allowed'
      return 0
      ;;
  esac

  return 1
}

path_failures=0
for index in "${!changed_paths[@]}"; do
  path=${changed_paths[$index]}
  status=${changed_statuses[$index]}
  if reason=$(classify_forbidden_path "$path"); then
    printf 'forbidden path (%s): %q — %s\n' "$status" "$path" "$reason" >&2
    path_failures=1
  fi
done
[[ "$path_failures" -eq 0 ]] \
  || fail "remove the reported runtime, secret, dependency, cache, or generated paths"

is_production_source() {
  case "$1" in
    api/*.py|api/**/*.py|web/*.js|web/**/*.js|web/*.jsx|web/**/*.jsx|web/*.ts|web/**/*.ts|web/*.tsx|web/**/*.tsx)
      case "$1" in
        api/tests/*|api/**/tests/*|web/**/__tests__/*|web/**/*.spec.*|web/**/*.test.*)
          return 1
          ;;
      esac
      return 0
      ;;
  esac
  return 1
}

has_added_match() {
  local path=$1
  local pattern=$2

  git diff --no-ext-diff --unified=0 "$base_commit" "$head_commit" -- "$path" \
    | awk '/^\+\+\+ / { next } /^\+/ { print substr($0, 2) }' \
    | grep -Eq -- "$pattern"
}

pattern_failures=0
controller_changed=0

for path in "${changed_paths[@]}"; do
  git cat-file -e "${head_commit}:${path}" 2>/dev/null || continue
  is_production_source "$path" || continue

  case "$path" in
    api/controllers/*.py|api/controllers/**/*.py)
      controller_changed=1
      if has_added_match "$path" '(^|[^[:alnum:]_])(db\.paginate|db\.session\.(query|execute|scalar|scalars|add|delete|merge|refresh|rollback|get)|session\.(query|execute|scalar|scalars|add|delete|merge|refresh|rollback))([[:space:]]*\(|$)'; then
        printf 'forbidden production pattern: %q adds direct controller SQLAlchemy; inject a service/session boundary\n' "$path" >&2
        pattern_failures=1
      fi
      if has_added_match "$path" 'console_ns\.schema_model'; then
        printf 'forbidden production pattern: %q adds the legacy Console schema_model contract\n' "$path" >&2
        pattern_failures=1
      fi
      ;;
    api/services/*.py|api/services/**/*.py|api/models/*.py|api/models/**/*.py)
      if has_added_match "$path" '(^|[^[:alnum:]_])db\.session([.(]|$)'; then
        printf 'forbidden production pattern: %q adds implicit db.session usage; use an explicit Session\n' "$path" >&2
        pattern_failures=1
      fi
      ;;
    web/models/enterprise-marketplace.ts|web/models/platform-admin.ts|web/service/use-enterprise-marketplace.ts|web/service/use-platform-admin.ts)
      printf 'forbidden production path: %q restores a legacy handwritten Console model/service\n' "$path" >&2
      pattern_failures=1
      ;;
    web/*|web/**/*)
      if has_added_match "$path" "fetch\\([[:space:]]*['\\\"]/console/api/"; then
        printf 'forbidden production pattern: %q adds a handwritten Console fetch; use generated consoleClient/consoleQuery\n' "$path" >&2
        pattern_failures=1
      fi
      case "$path" in
        *platform-admin*|*enterprise-marketplace*)
          if has_added_match "$path" "(@/context/app-context|useAppContext[[:space:]]*\\()"; then
            printf 'forbidden production pattern: %q restores enterprise state through the legacy app context\n' "$path" >&2
            pattern_failures=1
          fi
          ;;
      esac
      ;;
  esac
done

[[ "$pattern_failures" -eq 0 ]] \
  || fail "replace the reported legacy production pattern with the approved 1.16 architecture"

if [[ "$controller_changed" -eq 1 && "$head_commit" == "$(git rev-parse HEAD)" ]]; then
  if command -v ast-grep >/dev/null 2>&1 || command -v uvx >/dev/null 2>&1; then
    python3 scripts/check_no_new_controller_sqlalchemy.py --base-rev "$base_commit" \
      || fail "the repository controller SQLAlchemy guard rejected the candidate diff"
  else
    printf '%s\n' \
      "note: ast-grep is unavailable; the offline direct-SQLAlchemy fallback passed." \
      "      Install ast-grep to run scripts/check_no_new_controller_sqlalchemy.py as an additional AST check."
  fi
fi

printf 'enterprise replay scope check passed\n'
printf 'baseline: %s\n' "$OFFICIAL_BASE_COMMIT"
printf 'range: %s...%s\n' "$base_commit" "$head_commit"
printf '%s\n' \
  'dry-run only (not executed): pnpm --dir packages/contracts gen-api-contract' \
  'dry-run only (not executed): docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q'
