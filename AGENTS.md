# AGENTS.md

## Project Overview

Dify is an open-source platform for developing LLM applications with an intuitive interface combining agentic AI workflows, RAG pipelines, agent capabilities, and model management.

The codebase is split into:

- **Backend API** (`/api`): Python Flask application organized with Domain-Driven Design
- **Frontend Web** (`/web`): Next.js application using TypeScript and React
- **Docker deployment** (`/docker`): Containerized deployment configurations

## Backend Workflow

- Read `api/AGENTS.md` for details
- Run backend CLI commands through `uv run --project api <command>`.
- Integration tests are CI-only and are not expected to run in the local environment.

## Frontend Workflow

- Read `web/AGENTS.md` for details
- For enterprise Docker validation, image builds, or project-scoped image cleanup, read `docker/README.enterprise.md` and use `.agents/skills/enterprise-docker-workflow/`.

## Enterprise Agent Entrypoint

When Codex, Claude Code, or another coding agent enters this repository for enterprise work, read these files first and treat them as the current source of truth:

- `AGENTS.md`: repository-level agent rules and the enterprise branch truth.
- `README.enterprise-maintenance.md`: enterprise branch strategy, official-sync workflow, release rules, and stale-history warnings.
- `ENTERPRISE_REPLAY_PLAN.md`: required enterprise patch groups to replay on top of a clean upstream baseline.
- `docker/README.enterprise.md`: enterprise compose overlay, image rebuild, offline package, and verified-image rules.

Do not use old chat summaries, local memory, or the previous dirty `enterprise/main` tree as authority. The old `enterprise/main` state and `codex/protect-enterprise-main-20260424-103050` are historical references only; copy from them only when a patch is listed in the replay plan or re-proven by current-source tests and runtime validation.

## Enterprise Branch Strategy

- `main` tracks the official upstream baseline and must not contain enterprise work.
- `codex/enterprise-candidate-20260424` is the current clean enterprise candidate rebuilt from `upstream/main`.
- The next stable `enterprise/main` should be promoted from the clean candidate after review, cleanup, and release validation.
- The previous `enterprise/main` is considered a dirty historical branch because it contains long-cycle merge residue, broad performance experiments, local runtime artifacts, and old test drift.
- Future official syncs should start from the new upstream baseline and replay required enterprise patch groups, instead of mechanically merging official changes into the old dirty tree.

## Testing & Quality Practices

- Follow TDD: red → green → refactor.
- Use `pytest` for backend tests with Arrange-Act-Assert structure.
- Enforce strong typing; avoid `Any` and prefer explicit type annotations.
- Write self-documenting code; only add comments that explain intent.

## Language Style

- **Python**: Keep type hints on functions and attributes, and implement relevant special methods (e.g., `__repr__`, `__str__`). Prefer `TypedDict` over `dict` or `Mapping` for type safety and better code documentation.
- **TypeScript**: Use the strict config, rely on ESLint (`pnpm lint:fix` preferred) plus `pnpm type-check:tsgo`, and avoid `any` types.

## General Practices

- Prefer editing existing files; add new documentation only when requested.
- Inject dependencies through constructors and preserve clean architecture boundaries.
- Handle errors with domain-specific exceptions at the correct layer.

## Enterprise Sync Rule

- Do not treat "merge `upstream/main` into `enterprise/main`" as the default enterprise maintenance method anymore.
- The default method is: sync `main` to `upstream/main`, create a clean enterprise candidate from that official baseline, replay the required enterprise patch groups, validate each group, then promote the candidate.
- Enterprise workspace, platform-admin, and 智慧广场 are the business baseline that must survive each sync.
- If upstream is safer, more complete, or structurally better, keep upstream first and re-apply the minimum enterprise adjustment on top.
- Never carry local runtime data, build caches, `node_modules`, stale tests, or broad unproven UI/performance experiments into a new candidate.
- A release candidate is valid only after source checks, enterprise image rebuild, compose service recreation, browser-click validation, and log inspection all point to the same rebuilt image batch.

## CLAUDE.md Behavioral Guidelines

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```text
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Project Conventions

- Backend architecture adheres to DDD and Clean Architecture principles.
- Async work runs through Celery with Redis as the broker.
- Frontend user-facing strings must use `web/i18n/en-US/`; avoid hardcoded text.
