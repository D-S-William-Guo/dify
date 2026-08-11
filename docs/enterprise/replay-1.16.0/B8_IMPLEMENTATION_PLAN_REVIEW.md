# Dify Enterprise 1.16.0 Replay B8 Implementation Plan — Independent Review

- **Role**: Plan Reviewer
- **Instance**: `replay-116-b8-plan-reviewer`
- **Branch**: `ctyun/replay-116-b8-plan-reviewer`
- **Reviewed commit**: `66a57d42373e527b101f032e12de5a40f70103ce` "docs: plan enterprise replay B8 validation"
- **Reviewed range**: `b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4..66a57d42373e527b101f032e12de5a40f70103ce`
- **Range diff**: exactly `docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN.md`, **+590/-0**, diff SHA-256 `df5666c1f751a5719717029ba11e30d664a8a5093223599f60b704b6d142e719`
- **结论 / Verdict**: **CHANGES_REQUIRED**

本 Reviewer 未修改任何 product 文件、fixture、denylist 文件、`docs/enterprise/replay-1.16.0/evidence/**`
或 `B8_IMPLEMENTATION_PLAN.md`；唯一写入文件是本报告
`docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN_REVIEW.md`。未执行 commit、amend、push、merge、
rebase、reset、checkout 或 cherry-pick。

---

## RECOVERY

| item | expected | actual | result |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b8-plan-reviewer` | `ctyun/replay-116-b8-plan-reviewer` | PASS |
| HEAD | `66a57d42373e527b101f032e12de5a40f70103ce` | `66a57d42373e527b101f032e12de5a40f70103ce` | PASS |
| porcelain | empty | empty | PASS |
| `git status --short --branch` | clean | `## ctyun/replay-116-b8-plan-reviewer` | PASS |
| 范围唯一变更文件 | `B8_IMPLEMENTATION_PLAN.md` | `git diff --name-status b8dd2b3e3c..HEAD` = `A docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN.md` | PASS |
| 范围 diff 大小 | +590/-0 | `git diff --stat` = `1 file changed, 590 insertions(+)` | PASS |
| 范围 diff SHA-256 | `df5666c1f751a5719717029ba11e30d664a8a5093223599f60b704b6d142e719` | `git diff --binary b8dd2b3e3c..HEAD \| sha256sum` = `df5666c1...142e719` | PASS |
| `git diff --check`（范围） | clean | exit 0 | PASS |

## REQUIRED VERIFICATION EVIDENCE

| Command | Exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b8-plan-reviewer` |
| `git rev-parse HEAD` | 0 | `66a57d42373e527b101f032e12de5a40f70103ce` |
| `git status --short --branch` | 0 | clean |
| `git log --oneline -8` | 0 | 见下方 SHA 证据 |
| `wc -l docker/docker-compose.enterprise.yaml` | 0 | **74**（B6 overlay） |
| `ls scripts/check-enterprise-vector-indexes.*` | 1 | no-such-file（vector checker 不存在） |
| `ls docs/enterprise/replay-1.16.0/evidence` | 1 | no-such-dir（evidence 不存在） |
| `ls api/migrations/versions/` | 0 | 五个 B2/B4 revision 文件均在：`c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5`、`a71e16c0de01`、`b416e5c4e702` |
| `git merge-base 1.16.0 HEAD` | 0 | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| `wc -l /home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/scripts/check-enterprise-vector-indexes.sh` | 0 | **189** |
| `rg -n -- "--repair"` 旧 1.15 checker | 0 | line 6, 12, 24, 160（含 `--repair` 写路径） |
| `git diff --check` | 0 | clean（范围与工作树） |
| `git status --porcelain=v1` | 0 | empty |

### SHA 身份证据（`git log --oneline`）

```text
66a57d4237 docs: plan enterprise replay B8 validation      <- B8 Plan（受审）
b8dd2b3e3c docs: rereview enterprise replay B7 offline chain <- B7 Rereview
bb86a5e8aa fix: close B7 S-8 and bundle scan findings       <- B7 Fixer
93ab820b48 docs: review enterprise replay B7 offline chain  <- B7 Code Review
28f9f72e7d feat: add enterprise B7 offline artifact chain   <- B7 code
```

`git show --stat` 佐证：

| commit | 内容 |
| --- | --- |
| `28f9f72e7d` | B7 离线链 product 脚本 + fixtures/tests（feat） |
| `93ab820b48` | 仅 `B7_REVIEW.md`（docs review） |
| `bb86a5e8aa` | 仅 `scripts/ci/check-enterprise-offline.sh`/`-tests.sh`（fix，+82/-8） |
| `b8dd2b3e3c` | 仅 `B7_REREVIEW.md`（docs rereview） |

## FINDINGS

### B8PR-01 — P2 · `bb86a5e8aa` 被标注为「B7 Rereview」，实际是 B7 Fixer

**位置**：`B8_IMPLEMENTATION_PLAN.md:52`（§1.1）、`:64`（§1.2）、`:557`（§13 checklist）。

**现状**：
- `:52` — `bb86a5e8aa`（B7 Rereview）与 `28f9f72e7d`（B7 code review）在 HEAD
- `:64` — B7 最终 Rereview `bb86a5e8aa` 结论 `PASS`、`21/21` fixture PASS
- `:557` — 强制起点与 B7 ancestor 事实…`bb86a5e8aa` 在 HEAD

**事实**：`git log`/`git show` 证据：`bb86a5e8aa` = `fix: close B7 S-8 and bundle scan findings`
（B7 **Fixer**，只改 `check-enterprise-offline.sh`/`-tests.sh`）；B7 **Rereview** = `b8dd2b3e3c`
（`docs: rereview enterprise replay B7 offline chain`，即 `B7_REREVIEW.md` 所在提交）。

**违反的不变量**：current-state facts 必须真实、SHA 标签必须准确（B8 计划审查契约 item 11；
`CURRENT_STATE.md` §1「以 Git 为准」）。`:64` 的结论与 `21/21` 内容本身出自 `B7_REREVIEW.md`
（真实），但 SHA 标签错配。

**处置**：改 `:52` 为「`b8dd2b3e3c`（B7 Rereview）与 `93ab820b48`（B7 Code Review）在 HEAD」
（并可列 `bb86a5e8aa`（B7 Fixer）与 `28f9f72e7d`（B7 code））；`:64` 与 `:557` 同步改为 `b8dd2b3e3c`。

### B8PR-02 — P2 · `bb86a5e8aa` 被标注为「B7 review」，实际 B7 Code Review 是 `93ab820b48`

**位置**：`B8_IMPLEMENTATION_PLAN.md:506`（§11.1）；同族误标 `:52`（§1.1，`28f9f72e7d` 标为「B7 code review」）。

**现状**：
- `:506` — 含 B7 review `bb86a5e8aa`、B7 code `28f9f72e7d`
- `:52` — 与 `28f9f72e7d`（B7 code review）在 HEAD

**事实**：B7 Code Review = `93ab820b48`（`docs: review enterprise replay B7 offline chain`，即
`B7_REVIEW.md` 所在提交）；`bb86a5e8aa` = Fixer；`28f9f72e7d` = B7 code（feat）。`:506` 中
「HEAD 为 B7 Rereview `b8dd2b3e3c`」「B7 code `28f9f72e7d`」两项正确；「B7 review `bb86a5e8aa`」
错误。`:52` 中「`28f9f72e7d`（B7 code review）」错误。

**违反的不变量**：同 B8PR-01，SHA-role 映射必须准确。

**处置**：`:506` 改为「含 B7 review `93ab820b48`、B7 fixer `bb86a5e8aa`、B7 code `28f9f72e7d`」；
`:52` 改为「B7 code review `93ab820b48`」。

### B8PR-03 — P2 · §7.1 ancestor 检查用 fixer SHA `bb86a5e8aa` 而非最终 B7 Rereview SHA `b8dd2b3e3c`

**位置**：`B8_IMPLEMENTATION_PLAN.md:343`（§7.1 起点与范围）。

**现状**：

```bash
git merge-base --is-ancestor bb86a5e8aa85ca6fedbbf42004fd232074ae9ba3 HEAD
```

**事实**：该门禁的意图是验证 B7 最终状态（Rereview）已入 HEAD。`bb86a5e8aa` 是 B7 **Fixer**，
不是最终 B7 状态；B7 最终 Rereview 是 `b8dd2b3e3c`。当前两提交都在 HEAD（命令会返回 0），但该
检查无法证明 Rereview 在 HEAD —— 检查的是错误的提交。

**违反的不变量**：验证门禁必须验证其声称的对象；ancestor 检查应指向 B7 链最终提交。

**处置**：改为 `git merge-base --is-ancestor b8dd2b3e3cb8846e1b6225fe6e94e538e960c8c4 HEAD`。

### B8PR-04 — P2 · `scripts/ci/check-enterprise-validation-evidence.*` 超出 ARCHITECT_HANDOFF §5 B8 allowlist，需显式扩 scope 审批

**位置**：`B8_IMPLEMENTATION_PLAN.md:296-297`（§6.1 allowlist）、`:32-34`（§0.6）、`:275`（§5.1）、
`:549`（§12）。

**现状**：§6.1 allowlist 含 `scripts/ci/check-enterprise-validation-evidence.sh` 与
`-tests.sh`，并引 `ARCHITECT_HANDOFF §5 B8 验收命令“数据库/runtime/offline evidence
completeness check”` 作为依据。

**事实**：`ARCHITECT_HANDOFF.md:134`（§5 B8 行）的 **Allowed write paths** 精确为：
`scripts/check-enterprise-vector-indexes.*`、对应 fixtures/tests、经批准的
`docs/enterprise/replay-1.16.0/evidence/**`。它**不含** `scripts/ci/check-enterprise-validation-*`。
`ARCHITECT_HANDOFF.md:120` 明确规定：规范化 allowlist 中任何未声明文件出现即暂停合并并重新审批
范围；验收命令列是验收标准，不是写权限授权。`scripts/ci/check-enterprise-validation-evidence.*`
是新文件、不在 B8 行的 allowed write paths 内，因此需要**显式 allowlist 扩展审批**后才能由 B8
Builder 写入。本计划未记录该审批。

**违反的不变量**：allowlist 必须与 ARCHITECT_HANDOFF §5 B8 行精确一致；scope 变更必须显式审批。

**处置**：在 §0/§6.1 记录「`scripts/ci/check-enterprise-validation-evidence.sh`/`-tests.sh` 需协调者
显式扩 scope 审批后方可交付」，或将二者移出 B8 allowlist（completeness check 结果可仅落
`evidence/`，checker 逻辑并入 vector checker tests 或留待后续授权任务）。

## REVIEW CHECKLIST（12 items）

| # | Item | Result | Evidence |
| --- | --- | --- | --- |
| 1 | §1.1 current-state：branch/HEAD/clean、B7 ancestors、B6 overlay 74 行、vector checker absent、evidence absent、五迁移文件 | **FAIL** | 事实全部核实（74 行、no-such-file/no-such-dir、五文件均在）；但 B7 ancestor 行 SHA 标签错配（B8PR-01/02） |
| 2 | §2 official-first findings 与 enterprise gaps grounded | PASS | 逐条核对 `docker/docker-compose.yaml:773-798,1196`、`weaviate_config.py:10-33`、`weaviate.env.example`、B2_INVENTORY（PG 15.17、`e2f0a9b7c6d5`、Weaviate 1.27.0、class_prefix 匹配、UNKNOWN 字段、SSRF 1.14.2）均真实；无虚构 endpoint/class/镜像 |
| 3 | §3 checker 契约：输入、VECTOR_STORE 门禁、PG 只读断言、Weaviate GET-only、三态输出、脱敏、fixture、只读强制、no-repair、no-ps1 | PASS | §3.1-3.7 完整；no-ps1 理由真实（旧 1.15 链只有 `.sh`，无 `.ps1` 对照，已核实 `ls`） |
| 4 | §4 evidence 布局：批准路径、缺证据=NOT_RUN、脱敏、README 索引 | PASS | §4.1-4.2 完整，含越界校验 |
| 5 | §5 completeness matrix：A-H + B6 overlay + B7 离线链 + DB/migration + vector + plugin/Agent/HITL/WebSocket + auth/RBAC + secret 扫描 + --pull never + 回滚协议均有 owner artifact；D/F/G/H 默认 NOT_RUN；静态不冒充运行 | PASS | 每行有 owner artifact；`:263-269` D/F/G/H 默认 NOT_RUN + 协调者授权；`:281-282`、`:383` 静态不可 PASS |
| 6 | §6 allowlist/denylist 与 handoff §5 B8 行一致 | **FAIL** | denylist 完整；allowlist 多出 `scripts/ci/check-enterprise-validation-evidence.*`（B8PR-04，需显式扩 scope 审批） |
| 7 | §7 验证计划与 fixture 用例 runnable/honest，无隐藏写路径 | **FAIL** | fixture 用例诚实、无隐藏写路径；但 `:343` ancestor 检查用错 SHA（B8PR-03） |
| 8 | §8 ownership matrix 无共享文件冲突 | PASS | B8 只新增 §6.1 独立文件；`scripts/ci/` 目录仅新增不修改；evidence 唯一写者=B8 Builder/Validator |
| 9 | §9 串行门禁 + §14 gate 完整；无并行 Builder、无跳过 review | PASS | §9/§14 链完整：Architect→Reviewer→Fixer→Rereviewer→coordinator→Builder→Code Reviewer→Fixer→Rereviewer→coordinator→逐项授权→Validator |
| 10 | §10 known limitations 保持可见且不claim已解决 | PASS | B7R-03..06、B4 limitations、B2/B8 运行风险、Weaviate UNKNOWN、SSRF 1.14.2、volume provenance 均在 `:449-472`，声明「不声称已解决」 |
| 11 | SHA 标签准确 | **FAIL** | B8PR-01/02/03 确认成立（`git log` + `git show --stat` 证据） |
| 12 | §12 报告 schema 与最终命令可执行、可复现 | PASS | `git diff --name-status`/`git diff`/`git diff --check`/`git status` 均可执行；三态汇总 + 脱敏 + 证据索引可复核 |

## NOT_RUN（如实声明）

| Area | Status |
| --- | --- |
| `flask db heads/history` 实跑 | NOT_RUN（无锁定 Git 依赖/受限网络；计划已如实 NOT_RUN 于 §11.2） |
| `docker compose config`（两层）实跑 | NOT_RUN（无 `docker/.env`；B6 已验；计划留 §7.4 Builder 补跑） |
| vector checker / completeness check 运行 | NOT_RUN（B8 Builder 实现后） |
| Phase D/F/G/H 真实运行、`--pull never` smoke、`docker/volumes/**` 访问 | NOT_RUN（另行授权/禁止） |

## VERDICT

**CHANGES_REQUIRED** —— 全部硬事实（branch/HEAD/clean、范围 diff +590/-0 与 diff SHA、
B6 overlay 74 行、vector checker/evidence 不存在、五迁移文件、merge-base、旧 1.15 checker 189 行
含 `--repair`）均真实；§2/§3/§4/§5/§8/§9/§10/§12 检查项 PASS。但存在 4 个 P2：B8PR-01/02/03
（B7 SHA 标签错配，含 §7.1 ancestor 检查错提交）与 B8PR-04（`scripts/ci/check-enterprise-validation-*`
超出 handoff §5 B8 allowlist，需显式扩 scope 审批）。按审查契约「Verdict PASS only if … no P0/P1/P2 …
and SHA labels accurate」：存在 P2 且 SHA 标签不准确，故 CHANGES_REQUIRED，不允许直接进入 B8 Builder。

Fixer 处置建议（finding-scoped）：修正 `:52`、`:64`、`:506`、`:557`、`:343` 的 SHA 标签
（`b8dd2b3e3c`=Rereview、`93ab820b48`=Code Review、`bb86a5e8aa`=Fixer、`28f9f72e7d`=code），并在
§0/§6.1 记录 `scripts/ci/check-enterprise-validation-evidence.*` 的显式扩 scope 审批要求（或移出
allowlist）。不得触碰其他文件。

## VERIFICATION COMMAND LOG（命令层面汇总）

Checklist 12 项：**8 PASS / 4 FAIL / 0 NOT_RUN**（fail = items 1、6、7、11，均由 B8PR-01..04 驱动）。
Finding 层面：**0 P0 / 0 P1 / 4 P2**。

`git diff --check` result: **clean (exit 0)**（范围 `b8dd2b3e3c..HEAD` 与工作树）。

Current `git status`: clean（`## ctyun/replay-116-b8-plan-reviewer`，porcelain 空）。

## DECLARATION

- 未执行 commit、amend、push、merge、rebase、reset、checkout 或 cherry-pick；未创建 PR。
- 唯一写入文件为本报告 `docs/enterprise/replay-1.16.0/B8_IMPLEMENTATION_PLAN_REVIEW.md`；
  `B8_IMPLEMENTATION_PLAN.md` 及所有 forbidden 路径未被触碰；未访问/复制 `docker/volumes/**`、
  未启动 Docker、未修改外部系统/数据库/容器/远程。
- 提交/amend 仅在协调者检查真实 diff 并显式授权后进行。
