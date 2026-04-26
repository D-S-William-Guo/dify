# CLAUDE.md

This file is intentionally short. Claude Code and other agents should use `AGENTS.md` as the primary repository instruction file, then read these enterprise documents before changing enterprise behavior:

- `README.enterprise-maintenance.md`
- `ENTERPRISE_REPLAY_PLAN.md`
- `docker/README.enterprise.md`

Current enterprise truth:

- `codex/enterprise-candidate-20260424` is the clean candidate rebuilt from `upstream/main`.
- The previous `enterprise/main` and `codex/protect-enterprise-main-20260424-103050` are historical references only.
- Do not revive old dirty-branch assumptions unless a patch is explicitly listed in the replay plan or re-proven by current-source tests and runtime validation.

Behavioral rules:

- Think before coding: state assumptions, surface ambiguity, and stop when the requirement is unclear.
- Simplicity first: implement the minimum requested behavior without speculative abstractions.
- Surgical changes: touch only files needed for the task and do not clean unrelated code.
- Goal-driven execution: define verification, run the closest checks, rebuild enterprise images when runtime code changes, and validate browser behavior against the rebuilt containers.
