# Dify Enterprise 1.16.0 Replay B7 Implementation Plan — Independent Plan Review

- **Role**: Independent B7 Plan Reviewer
- **Instance**: `replay-116-b7-plan-reviewer`
- **Branch**: `ctyun/replay-116-b7-plan-reviewer`
- **HEAD**: `f9e96105e9cb7595ff4a94cc608d582a4ab40c35`
- **Plan parent**: `20672fcef71530dcff1483c17cb2ab3205a75228`（B6 Review）
- **Reviewed commit**: `f9e96105e9cb7595ff4a94cc608d582a4ab40c35` "docs: plan enterprise replay B7 offline"
- **Reviewed artifact**: `docs/enterprise/replay-1.16.0/B7_IMPLEMENTATION_PLAN.md`（561 lines）
- **结论**: `CHANGES_REQUIRED`

本报告是独立 Review 证据，不是 Architect 计划的改写。本 Reviewer 未修改计划或任何
denylist 文件；唯一写入文件是本报告。

---

## RECOVERY

| item | expected | actual | result |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b7-plan-reviewer` | `ctyun/replay-116-b7-plan-reviewer` | PASS |
| HEAD | `f9e96105e9cb7595ff4a94cc608d582a4ab40c35` | `f9e96105e9cb7595ff4a94cc608d582a4ab40c35` | PASS |
| porcelain | empty | empty | PASS |
| `git status --short --branch` | clean | `## ctyun/replay-116-b7-plan-reviewer` | PASS |

未执行 merge、rebase、reset、checkout、cherry-pick、commit、amend、push。

## REVIEW_RANGE

- Range: `20672fcef71530dcff1483c17cb2ab3205a75228..HEAD`
- `git diff --name-status`: exactly `A docs/enterprise/replay-1.16.0/B7_IMPLEMENTATION_PLAN.md`
- `git diff --check`: clean (exit 0) for range and worktree.
- No other file added/modified in range; no product files touched.

## SOURCES_READ

- `docs/enterprise/replay-1.16.0/B7_IMPLEMENTATION_PLAN.md`（逐行）
- `docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md`
- `docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md`
- `docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md`
- `docs/enterprise/replay-1.16.0/B6_IMPLEMENTATION_PLAN.md`
- `docs/enterprise/replay-1.16.0/B6_REVIEW.md`
- `docs/enterprise/replay-1.16.0/CURRENT_STATE.md`
- `docker/docker-compose.enterprise.yaml`（74 lines）
- `docker/docker-compose.yaml`（官方；plugin_daemon/sandbox/agent_backend/local_sandbox 段）
- `docker/.env.example`、`docker/envs/core-services/plugin-daemon.env.example`、
  `docker/envs/core-services/dify-agent.env.example`、`docker/envs/core-services/sandbox.env.example`、
  `docker/envs/middleware.env.example`
- 旧 1.15 链只读证据：`dify-enterprise-1.15.0/scripts/build-enterprise-offline.sh`、
  `dify-enterprise-1.15.0/scripts/build-enterprise-config-package.sh`
- Git 事实：`git show d218e48f28:docker/docker-compose.enterprise.yaml`、`git log`、ancestor 检查

## CHECKLIST VERIFICATION

### 1. Recovery/gates — PASS

- `d218e48f28`（B6 overlay）是 HEAD 祖先（`git merge-base --is-ancestor d218e48f28 HEAD` exit 0）。
- `git show d218e48f28:docker/docker-compose.enterprise.yaml | wc -l` = **74**，与计划 §1.1/§12.1 一致。
- `20672fcef7`（B6 Review）是计划 commit 的 parent（git log 确认）。
- 当前仓库无 B7 脚本：`scripts/build-enterprise-offline.*`、`scripts/build-enterprise-config-package.*`、
  `scripts/*enterprise*config*` 均不存在；`scripts/ci/` 仅有 B0 的
  `check-enterprise-replay-scope.sh` / `-tests.sh`（计划 §8 声明一致）。
- `find docker/envs -name "*.env.example" | wc -l` = **37**，与计划 §1.1 一致。

### 2. Allowlist/denylist — PASS

- §3.1 allowlist 精确：4 个 product 脚本（offline/config 的 `.sh`+`.ps1`）+ 2 个 CI
  检查脚本 + `check-enterprise-offline-fixtures/**` + 唯一 env 示例修改
  `docker/envs/core-services/plugin-daemon.env.example`；无新 Dockerfile、无新 docs、
  无其他 env 示例。与任务契约“4 scripts + ci check scripts + fixtures + only
  plugin-daemon.env.example”一致。
- §3.2 read-only reference paths 与 ARCHITECT_HANDOFF §5 B7 行一致。
- §9 denylist 覆盖 overlay、`docker/volumes/**`、真实 `.env`/非 example env、
  `docker/envs/**`（除一个文件）、业务源码（api/web/dify-agent/packages）、lockfiles、
  旧 1.15 内容恢复、联网副作用边界。overlay/volumes/real env/business source/lockfile 全部禁止。
- `.ps1` 允许条目与“默认保留双实现、移除需申请”的说明内部一致（§3.1 注）。

### 3. Offline contract — PASS

- `Mode=reuse` 唯一默认授权；reuse 门禁 = `docker image inspect` 成功且
  `COMMIT_SHA`==`$DIFY_ENTERPRISE_VERSION`（tag，非 hash），缺失/不一致直接失败，
  不降级为 build/pull（§4.1）。与旧 1.15 `is_reusable_image`/`ensure_enterprise_image`
  reuse 分支语义一致，且符合 VALIDATION_PLAN Phase H 第 1 条与 B6R-01。
- `images-*.txt` == 两层 Compose `config --images | sort -u`（§4.2，命令与旧脚本逐字一致，
  含 `--env-file` 与 `sed`/`sort -u`）。
- required-image 断言（§4.2）：企业 API tag 唯一且四 runtime 一致、Web tag 唯一、
  `langgenius/dify-agent-backend:1.16.0` 与 `langgenius/dify-agent-local-sandbox:1.16.0`
  必须出现。官方 compose 已核验：`agent_backend: langgenius/dify-agent-backend:1.16.0`
  （line 645）、`local_sandbox: langgenius/dify-agent-local-sandbox:1.16.0`（line 540）、
  四 API runtime `langgenius/dify-api:1.16.0`、`web` `langgenius/dify-web:1.16.0`。
- manifest（§4.3）：`version`、`baseline{tag,commit}`、`enterprise_commit`、`image_tag`、
  `generated_at`、逐镜像 `name`/`id`/`digest`；`baseline` 固定
  `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`（commit 对象存在；与
  ARCHITECT_HANDOFF/VALIDATION_PLAN/CURRENT_STATE 一致）。缺 digest 如实记空串，不伪造。
- `-CheckOnly` dry-run 禁止 build/pull/save（§4.1/§7.2）；离线目标 `--pull never` smoke
  归 Phase H NOT_RUN（§4.7/S-10）。

### 4. Config package — PASS

- §4.5 文件集为 1.16 定义：`docker/docker-compose.yaml`、`docker-compose.enterprise.yaml`、
  `docker/.env.example`、全量 `docker/envs/**/*.env.example`（37，含 dify-agent/local-sandbox）、
  `docker/nginx/**`、`docker/ssrf_proxy/**`、manifest、images。不含旧 1.15 专属文件
  （`ENTERPRISE_DEPLOY_STARTUP.md`、`UPGRADE_*.md`、`dify-env-sync.*`、`README.enterprise.md`、
  `check-enterprise-vector-indexes.sh`）——已对照旧 1.15 config 脚本 required_files 逐一核验，
  §2.3 disposition 表准确；无 B8 前向依赖。
- tar 显式 exclude：`*.env`（非 example）、`docker/volumes/**`、`.git`、cache、`node_modules`、
  `.venv`、`.next`、业务源码/产物（§4.5）；S-5 tar 扫描门禁兜底。
- Agent server secret（§4.6）：开发默认 `MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY` 只允许
  在 `docker/.env.example:276` 与 `dify-agent.env.example:31`（均带相邻
  `Replace this development default in production` WARNING）；生产随机 secret 生成归 Phase H
  第 7 条 NOT_RUN。已逐处核验。

### 5. Plugin mirror/signature — CHANGES_REQUIRED（见 B7PR-01）

- 只透传官方 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE`，无平行
  mirror/索引/转发实现（§0.5/§2.1/§5.1/E11/C05）——行为正确。
- 已核验的坐标者 P3 证据：
  - 当前 `docker/envs/core-services/plugin-daemon.env.example` **只含**
    `FORCE_VERIFYING_SIGNATURE=true`（无 PIP_MIRROR_URL，无 PIP_MIRROR_AUTO_DETECT）。
  - `PIP_MIRROR_URL` 出现在 `docker/.env.example:207`、`docker/envs/middleware.env.example:182`、
    `docker/envs/core-services/sandbox.env.example:8`，并被官方 compose 的
    `plugin_daemon`（line 594）与 `sandbox`（line 529）interpolation 透传。
  - `PIP_MIRROR_AUTO_DETECT` 在当前仓库 `docker/` 下 0 处出现。
- 计划对上述证据的引用有准确性/一致性问题，见 **B7PR-01**。

### 6. Validation — PASS

- §7.2 fixture/dry-run：reuse 门禁正/负、image list 一致、`-CheckOnly` 禁止 build/pull/save、
  manifest schema、config 包依赖与内容、secret/默认 key 扫描、负向 `.env`/volume 拒绝——覆盖完整。
- §7.3 archive/secret/default-key/volume 扫描对应 §6 S-5…S-8；S-6 image bundle 顶层/逐 layer
  扫描带“不可列出 layer 如实记 NOT_RUN”的诚实上限（§6 note）。
- Phase F/G/H 全部 NOT_RUN 且如实声明（§7.4/§4.7/§12.2）；静态 manifest/tag 结果不冒充
  运行 image ID 证据。无伪造运行证据。

### 7. Plan quality — PASS

- §8 ownership matrix：每文件唯一 owner、依赖、merge order 明确；`scripts/ci/` 与 B0 文件
  边界声明准确；plugin-daemon env 示例唯一写者声明准确（B6 未动 envs）。
- §5 env 矩阵、§6 security matrix（S-1…S-10 + S-6 note）、§7 validation plan、§11
  risks/decisions/stop conditions 完整。§14 Plan Reviewer checklist 与正文一致（除 B7PR-01
  涉及的内部一致性）。

## FINDINGS

### B7PR-01 — P2（非阻断，但必须修正）— Plan Reviewer checklist 第 5 项 / 内部一致性

- **位置**: `B7_IMPLEMENTATION_PLAN.md` §0.5（lines 28–30）、§2.1（line 103）、§12.1（line 488）。
- **证据**:
  - 当前 `docker/envs/core-services/plugin-daemon.env.example` **只含**
    `FORCE_VERIFYING_SIGNATURE=true`（grep 仅 line 9 命中；无 `PIP_MIRROR_URL`、无
    `PIP_MIRROR_AUTO_DETECT`）。
  - `PIP_MIRROR_URL` 实际位于 `docker/.env.example:207`、`docker/envs/middleware.env.example:182`、
    `docker/envs/core-services/sandbox.env.example:8`，并被官方 compose `plugin_daemon`（line 594）
    与 `sandbox`（line 529）interpolation 透传。
  - `PIP_MIRROR_AUTO_DETECT` 在仓库 `docker/` 下 0 处出现（grep exit 1）。
  - §0.5/§2.1/§12.1 声称“官方 plugin-daemon `.env.example` 原文核验”确认
    `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE` 三个 knob——
    与仓库内该文件的真实内容不符。
  - 内部不一致：§2.2（line 116–117）已正确说明“官方 env 示例未收录 `PIP_MIRROR_AUTO_DETECT`”，
    与 §0.5/§2.1 的“原文核验确认”表述直接矛盾。
- **违反的不变量**: Plan Reviewer checklist 第 5 项要求对插件 knob 证据诚实核对/归类；
  §14 要求 checklist 完整且内部一致。证据引用不准确会导致 Builder/后续 Reviewer 对
  “官方 knob 的证据在哪”产生误读。
- **修复边界**: 仅改文字，不改 scope/行为——把 §0.5/§2.1/§12.1 的引用改为：三个 knob 是
  dify-plugin-daemon 官方项目自身 `.env.example`（由 `docker/envs/middleware.env.example:185`
  链接）提供的官方 knob；仓库内 `docker/envs/core-services/plugin-daemon.env.example`
  当前只含 `FORCE_VERIFYING_SIGNATURE`，B7 将按 §5.1 追加 `PIP_MIRROR_AUTO_DETECT`/
  `PIP_MIRROR_URL` 透传行；`PIP_MIRROR_URL` 已在 `docker/.env.example`、`middleware.env.example`、
  `sandbox.env.example` 与官方 compose interpolation 出现。
- **阻断状态**: 不阻断 Builder 执行（§5.1 可执行规格明确且正确），但作为开放 P2 使本计划
  门禁为 `CHANGES_REQUIRED`。

### P3 observations（非阻断）

- **B7PR-P3-01**: `docker/envs/middleware.env.example` 也含 `PIP_MIRROR_URL`，§5.1 的“不在 B7
  修改”表只列了 `docker/.env.example`、`sandbox.env.example`，未列 middleware.env.example；
  因 middleware.env.example 非 B7 修改目标，仅为引用完备性建议补一行。
- **B7PR-P3-02**: `config --images` 依赖部署 `docker/.env` 的 profile/变量展开，不同部署 `.env`
  得不同镜像集合——计划 §11.1 已如实声明为操作约束；建议 B7 报告固定记录所用 `.env` 来源。

## VERDICT

**CHANGES_REQUIRED** —— 范围精确、无 P0/P1、除 accepted NOT_RUN 外证据完整、无未授权写入；
但存在一个开放 P2（B7PR-01）。修复为 finding-scoped 文字更正（引用澄清），不改变 scope、
行为或 allowlist。修复后应由独立 Rereviewer 关闭。

## VERIFICATION COMMAND LOG

| Command | Exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b7-plan-reviewer` |
| `git rev-parse HEAD` | 0 | `f9e96105e9cb7595ff4a94cc608d582a4ab40c35` |
| `git status --short --branch` | 0 | clean |
| `git status --porcelain=v1` | 0 | empty |
| `git diff --name-status 20672fcef7..HEAD` | 0 | exactly `A docs/enterprise/replay-1.16.0/B7_IMPLEMENTATION_PLAN.md` |
| `git diff --check` | 0 | clean |
| `git show d218e48f28:docker/docker-compose.enterprise.yaml \| wc -l` | 0 | 74 |
| `git merge-base --is-ancestor d218e48f28 HEAD` | 0 | ancestor=true |
| `find docker/envs -name "*.env.example" \| wc -l` | 0 | 37 |
| `cat docker/envs/core-services/plugin-daemon.env.example` | 0 | only `FORCE_VERIFYING_SIGNATURE=true` among the three knobs |
| grep `PIP_MIRROR` in docker envs/.env.example | 0 | locations as recorded above |
| grep `PIP_MIRROR_AUTO_DETECT` in `docker/` | 1 | 0 occurrences |
| grep official compose plugin_daemon/sandbox interpolation | 0 | `PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE` present |
| grep agent_backend/local_sandbox/api/web images in official compose | 0 | official 1.16 images confirmed |
| `git status --short --branch` (final) | 0 | clean |

Pass/Fail/NOT_RUN: **19 PASS / 0 FAIL** among this reviewer's verification commands（另有 1 项
P2 finding B7PR-01；Phase F/G/H 为 accepted NOT_RUN，非本 reviewer 命令范围）。

`git diff --check` result: **clean (exit 0)** for the reviewed range and the worktree.

Current `git status`: clean（`## ctyun/replay-116-b7-plan-reviewer`，porcelain 空）。

## DECLARATION

- No commit, amend, push, merge, rebase, reset, or cherry-pick occurred during this review.
- The only intended write is this report at `docs/enterprise/replay-1.16.0/B7_IMPLEMENTATION_PLAN_REVIEW.md`.
- No external system, database, container, volume, remote, or production state was modified;
  no `docker/volumes/**` was accessed or copied.
