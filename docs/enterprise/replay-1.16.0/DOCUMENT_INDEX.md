# 1.16.0 文档分类与读取导航

更新时间：2026-10-07。用途是协调指挥与按需取证，不要求每个智能体阅读全目录。

## 从这里开始：按身份或问题选入口

| 你要做什么 | 最小阅读路线 | 不必先读 |
| --- | --- | --- |
| 人类：看进度、问题、下一步 | [当前状态](CURRENT_STATE.md) 的“本机验证”和“已接受决定与下一步”；有疑问再打开其中的证据链接 | 完整 SHA 链、所有 B0–B8 报告 |
| 新协调窗口：接手现场 | 本页“换 harness 的恢复契约” → [当前状态](CURRENT_STATE.md) → 总纲/AGENTS/两个 Skill → 当前任务报告 → 只读核验 | 八月旧启动提示词、全部历史聊天 |
| Architect / Plan Reviewer：设计或审查方案 | 精确任务契约 → 总纲/相关人工决定 → 当前任务计划与 findings → 所有权和验收标准 | 无关任务的运行日志 |
| Builder / Fixer：实现限定修改 | 精确任务契约及 SHA → 路径适用的 AGENTS/Skill → 已接受计划 → 指定 findings（Fixer）→ 验收命令 | 全项目历史交接；不得从旧报告另取写入权限 |
| Code Reviewer / Rereviewer：独立审查 | 精确任务契约 → 实际 Git diff → 已接受计划/findings → 原始测试证据与相关规范 | 仅凭 Builder 的 PASS 摘要作结论 |
| 验证 Agent：验证历史数据、镜像或浏览器 | 范围授权/任务契约 → [验证标准](VALIDATION_PLAN.md) 与后续决定 → 当前对象、镜像和备份身份 → 对应 evidence | 用单元测试或空库冒烟替代运行验证 |
| 运维/人类：查升级步骤 | [当前升级清单](OFFLINE_DEPLOYMENT_CHECKLIST.md) → [后续决定](DECISION_RISK_LEDGER.md)；执行前另行授权 | 直接执行旧 Plan B 或旧 preflight 占位命令 |
| 查“为什么这么决定”或旧证据 | [决策台账](DECISION_RISK_LEDGER.md) → 对应计划/Review/evidence；旧交接仅追溯 | 把历史结论当今天的现场 |

协调窗口启动提示词只适用于协调者，不要原样交给 Builder。执行 Agent 的精确契约仍须写明角色、SHA、allowlist、测试、权限和停止条件。不同 harness 是否自动读取 AGENTS/Skill 并不一致，契约须显式要求读取适用规范，不能假设加载成功。

阅读状态用语：**计划**＝尚未证明；**历史证据**＝只适用于记录的日期/来源；**PASS**＝指定范围有证据；**NOT_RUN**＝未执行；**PARTIAL**＝仅部分满足；**未核验**＝交接记载尚未与现场对照。任何一种都不自行授予执行权限。

## 使用约定

- 当前状态只读 CURRENT_STATE；换指挥模型时先恢复 Git/实例/授权，不先背诵历史。
- Skill 保存跨版本规则；/tmp 精确契约承载已批准的单实例范围，不是授权本身，也不保证跨机器持久存在。
- 计划不是执行记录；Review PASS 不是镜像/浏览器 PASS；旧 FINAL 只是该阶段结论。
- 全项目当前现场由 CURRENT_STATE 管理；其他文档描述状态须注明截至日期/checkpoint及适用范围。普通行为叙述中的“当前”（如当前 segment）不受此措辞约束。
- 以下按现有路径逻辑分类，不移动报告、不改历史判断。阶段报告依文件名对应 B0–B8 或具体 P0 修复链。
- 本次完成路径清单和交接结构整理，不声称106份文档全文一致性审计或全部功能已验证。

## 项目规范与文件职责

| 入口 | 唯一职责 |
| --- | --- |
| [根目录 ENTERPRISE_REPLAY_PLAN](../../../ENTERPRISE_REPLAY_PLAN.md) | 本版本重放总纲、基线、工作包、依赖及验收边界 |
| [根目录 AGENTS](../../../AGENTS.md)、[API AGENTS](../../../api/AGENTS.md)、[Web AGENTS](../../../web/AGENTS.md) | 项目与领域编码规范；API 契约细节见 [API_SCHEMA_GUIDE](../../../api/controllers/API_SCHEMA_GUIDE.md)，前端测试政策见 [test.md](../../../web/docs/test.md) |
| orchestrate-claude-squad / replay-dify-enterprise | 跨任务调度与跨版本重放方法；不由历史交接副本替代 |
| DESIGN_GATE / ARCHITECT_HANDOFF / PATCH_DECISION_MATRIX | 人工设计决定、文件所有权契约、旧改动取舍 |
| DECISION_RISK_LEDGER | 已接受决定、风险和后续替代关系；不以聊天代替持久记录 |
| VALIDATION_PLAN / 阶段报告 / evidence | 验收标准、来源明确的执行结论与脱敏证据 |
| OFFLINE_DEPLOYMENT_CHECKLIST | 当前升级指导；历史 PRODUCTION_* 须检查适用范围 |
| CURRENT_STATE / 本索引 | 当前现场与阅读路线，不兼任总规范、完整历史或运行授权 |

## 换 harness 的恢复契约

1. 先读取本页与 CURRENT_STATE，确认是协调窗口而非 Builder。读取两个 Skill 全文及任务触发的引用；若未安装，使用可访问的可信源读取（路径及各 harness 安装实测见本节下表），不自行安装、升级或静默跳过。
2. 读取根目录总纲与 AGENTS；按当前任务读取领域指南、相关人工决定、计划和最终审查。无需加载所有旧报告和聊天。
3. 核对 Git 分支、实际 HEAD、checkpoint 包含关系、status/diff；清点未提交文件并保留。远端 tracking ref 不等于新查询的远端状态，未查询须标明。
4. 只读核对实例、worktree、Agent 会话和 controller；运行时任务另按授权核对镜像、挂载、备份和产物来源，不能仅凭 YAML 或历史 PASS 推断。
5. 分别报告代码、数据、镜像、浏览器、离线产物的状态；列明暂停动作、尚有效的范围授权、待决事项与禁止事项。文档本身不授予权限；跨 harness 无法确认授权来源时先向用户确认再变更状态。

交接时记录 Skill 来源和版本依据，而非只写名字。本机 2026-10-07 可定位的源仓库为 `/home/ctyun/BigData/GitHub/codex-personal-skills`，观测 HEAD 为 `e214a81a64dab93762604ec13e2df0bf4b3c435b`。各 harness 安装不同，以下是本轮路径与 SKILL.md 哈希核验结果，不保证所有引用文件也已一致：

| harness | 安装根路径 | orchestrate-claude-squad | replay-dify-enterprise |
| --- | --- | --- | --- |
| Codex | `/home/ctyun/.codex/skills/` | 指向源仓库，主文件一致 | 指向源仓库，主文件一致 |
| Claude | `/home/ctyun/.claude/skills/` | 指向 cc-switch，主文件与源一致 | 未安装；需显式读取上述可信源，不假装已加载 |
| OpenCode | `/home/ctyun/.config/opencode/skills/` | 指向 cc-switch，主文件与源一致 | 指向 cc-switch 陈旧副本，哈希与源不一致；不能用其替代当前规则 |

cc-switch 副本位于 `/home/ctyun/.cc-switch/skills/`；陈旧 replay 副本缺少源版 gateway 等后续规则。此为来源快照，不声称源工作区干净或内容等于该提交，也不授权同步。读取前须核对实际文件及所需引用与源的一致性；不能盲目覆盖较新版本。另一个 `/mnt/datadir/GitHub/codex-personal-skills` 的 replay 主文件哈希与源一致，但镜像机制和责任尚未确认，不据此指定第二权威源。

`/tmp` 契约是本机单实例交付文件，不是持久的授权来源。阶段结束将必要的脱敏命令、退出码、测试摘要、来源 SHA 和证据入口记录到既有阶段报告/evidence；不能只依赖临时日志。若文件已丢失，明确缺口，不伪造日志或把聊天数字当原始证据。未提交草稿须记录实际状态；提交/push 仍另行授权。

### 新协调窗口启动提示词

```text
你是 Dify Enterprise 1.16.0 的新协调窗口，不是 Builder。
使用 orchestrate-claude-squad 和 replay-dify-enterprise，完整读取
Skill 及当前任务所需引用；缺失或来源不明先报告，不静默跳过。
先读 docs/enterprise/replay-1.16.0/CURRENT_STATE.md 与 DOCUMENT_INDEX.md，
按恢复路线读取项目总纲、AGENTS、人工决定与当前任务最终报告。
仅只读核验分支、HEAD、checkpoint、未提交现场和实例状态，保留草稿。
旧授权、旧提示词、历史 PASS 不自动成为当前执行权限或验收结论。
汇报当前结果、缺口、有效约束、下一步建议及准确的授权需求。
恢复完成前不得提交、push、创建/删除实例、运行 Docker/浏览器、
修改数据或连接生产/灰度；Git 或文档不符不得自行修复。
```

## 记录完整性与已知缺口

图片修复已具备 Architect、Plan Review、修订计划、Plan Rereview、Builder代码提交、Code Review；Builder/Reviewer合成日志在本机 /tmp，协调复跑结果此前只有聊天和 CURRENT_STATE 摘要，尚无独立持久日志归档。历史数据/浏览器与离线包另有 output 本机证据，不应提交原始敏感页面。

CURRENT_STATE 原文完整保留在历史快照，旧实例为零、旧不再创建 Builder、旧默认secret门禁等不能作为当前指令。当前镜像切换尚在预检，冷备路径/完整性、回退记录、运行图片结果及新离线包仍有待完成或核验的证据；“都记录了”不能等同于“都验证了”。真正离线机与生产/灰度证据尚不在本轮授权范围内。

## 原首页内容的归位规则

| 原混入首页的内容 | 应属位置 | 本轮处理 |
| --- | --- | --- |
| 通用治理/创建/提交 SOP | orchestrate-claude-squad Skill | 首页只链接当前 Skill；旧副本留历史，不复制成新规范 |
| B0–B8 SHA链、测试数、旧恢复提示 | 版本阶段报告和历史快照 | 保留原文及原报告，首页按任务链接 |
| B3/B4 routes、DTO、业务限制 | Architect/B3/B4方案与契约报告 | 首页不再内嵌；不另造重复设计文档 |
| 升级步骤、环境区别和迁移指导 | PRODUCTION_* / OFFLINE_DEPLOYMENT_CHECKLIST | 保留现有指导；旧Plan B注明非当前滚动指令 |
| 历史运行结果、哈希和截图 | evidence或本机output | 可提交脱敏证据归evidence；原始页面/secret不进Git |
| 当前SHA、实例、缺口、授权和下一步 | CURRENT_STATE | 仅当前摘要；不追加多套“最新覆盖” |

这些版本专属报告留在 docs/enterprise/replay-1.16.0 合理；没有证据需要把它们搬到通用 docs 或 Skill。通用规则若仍只存在历史md中，需要后续核对当前Skill后补齐，不能直接把旧SOP重新生效。

## 1. 协调恢复入口

- [CURRENT_STATE.md](CURRENT_STATE.md)

## 2. 历史交接快照

- [CURRENT_STATE_HISTORY_2026-10-07.md](CURRENT_STATE_HISTORY_2026-10-07.md)
- [HANDOFF_2026-08-17.md](HANDOFF_2026-08-17.md)

## 3. 基线设计与决策

- [ARCHITECT_HANDOFF.md](ARCHITECT_HANDOFF.md)
- [ARCHITECT_REREVIEW.md](ARCHITECT_REREVIEW.md)
- [ARCHITECT_REVIEW.md](ARCHITECT_REVIEW.md)
- [DECISION_RISK_LEDGER.md](DECISION_RISK_LEDGER.md)
- [DESIGN_GATE.md](DESIGN_GATE.md)
- [DESIGN_GATE_REREVIEW.md](DESIGN_GATE_REREVIEW.md)
- [DESIGN_GATE_REVIEW.md](DESIGN_GATE_REVIEW.md)
- [OFFICIAL_RELEASE_ANALYSIS.md](OFFICIAL_RELEASE_ANALYSIS.md)
- [PATCH_DECISION_MATRIX.md](PATCH_DECISION_MATRIX.md)

## 4. 分阶段计划、审查与修复证据

- [B0_REREVIEW.md](B0_REREVIEW.md)
- [B0_REREVIEW_2.md](B0_REREVIEW_2.md)
- [B0_REVIEW.md](B0_REVIEW.md)
- [B1_REREVIEW.md](B1_REREVIEW.md)
- [B1_REVIEW.md](B1_REVIEW.md)
- [B2_INVENTORY.md](B2_INVENTORY.md)
- [B2_INVENTORY_REVIEW.md](B2_INVENTORY_REVIEW.md)
- [B2_REVIEW.md](B2_REVIEW.md)
- [B3_IMPLEMENTATION_PLAN.md](B3_IMPLEMENTATION_PLAN.md)
- [B3_IMPLEMENTATION_PLAN_REREVIEW.md](B3_IMPLEMENTATION_PLAN_REREVIEW.md)
- [B3_IMPLEMENTATION_PLAN_REREVIEW2.md](B3_IMPLEMENTATION_PLAN_REREVIEW2.md)
- [B3_IMPLEMENTATION_PLAN_REVIEW.md](B3_IMPLEMENTATION_PLAN_REVIEW.md)
- [B3_REVIEW.md](B3_REVIEW.md)
- [B4_A_REREVIEW.md](B4_A_REREVIEW.md)
- [B4_A_REVIEW.md](B4_A_REVIEW.md)
- [B4_B_REREVIEW.md](B4_B_REREVIEW.md)
- [B4_B_REVIEW.md](B4_B_REVIEW.md)
- [B4_FINAL_REREVIEW.md](B4_FINAL_REREVIEW.md)
- [B4_FINAL_REVIEW.md](B4_FINAL_REVIEW.md)
- [B4_IMPLEMENTATION_PLAN.md](B4_IMPLEMENTATION_PLAN.md)
- [B4_IMPLEMENTATION_PLAN_REREVIEW.md](B4_IMPLEMENTATION_PLAN_REREVIEW.md)
- [B4_IMPLEMENTATION_PLAN_REVIEW.md](B4_IMPLEMENTATION_PLAN_REVIEW.md)
- [B5_A_REVIEW.md](B5_A_REVIEW.md)
- [B5_B_REVIEW.md](B5_B_REVIEW.md)
- [B5_CONTRACT_FIX_REREVIEW.md](B5_CONTRACT_FIX_REREVIEW.md)
- [B5_CONTRACT_FIX_REVIEW.md](B5_CONTRACT_FIX_REVIEW.md)
- [B5_C_REREVIEW.md](B5_C_REREVIEW.md)
- [B5_C_REVIEW.md](B5_C_REVIEW.md)
- [B5_D_REREVIEW.md](B5_D_REREVIEW.md)
- [B5_D_REVIEW.md](B5_D_REVIEW.md)
- [B5_E_I18N_REVIEW.md](B5_E_I18N_REVIEW.md)
- [B5_FINAL_REVIEW.md](B5_FINAL_REVIEW.md)
- [B5_FULL_REGRESSION_REPORT.md](B5_FULL_REGRESSION_REPORT.md)
- [B5_IMPLEMENTATION_PLAN.md](B5_IMPLEMENTATION_PLAN.md)
- [B5_IMPLEMENTATION_PLAN_REREVIEW.md](B5_IMPLEMENTATION_PLAN_REREVIEW.md)
- [B5_IMPLEMENTATION_PLAN_REVIEW.md](B5_IMPLEMENTATION_PLAN_REVIEW.md)
- [B6_IMPLEMENTATION_PLAN.md](B6_IMPLEMENTATION_PLAN.md)
- [B6_IMPLEMENTATION_PLAN_REVIEW.md](B6_IMPLEMENTATION_PLAN_REVIEW.md)
- [B6_REVIEW.md](B6_REVIEW.md)
- [B7_IMPLEMENTATION_PLAN.md](B7_IMPLEMENTATION_PLAN.md)
- [B7_IMPLEMENTATION_PLAN_REREVIEW.md](B7_IMPLEMENTATION_PLAN_REREVIEW.md)
- [B7_IMPLEMENTATION_PLAN_REVIEW.md](B7_IMPLEMENTATION_PLAN_REVIEW.md)
- [B7_REREVIEW.md](B7_REREVIEW.md)
- [B7_REVIEW.md](B7_REVIEW.md)
- [B8_IMPLEMENTATION_PLAN.md](B8_IMPLEMENTATION_PLAN.md)
- [B8_IMPLEMENTATION_PLAN_REREVIEW.md](B8_IMPLEMENTATION_PLAN_REREVIEW.md)
- [B8_IMPLEMENTATION_PLAN_REREVIEW2.md](B8_IMPLEMENTATION_PLAN_REREVIEW2.md)
- [B8_IMPLEMENTATION_PLAN_REVIEW.md](B8_IMPLEMENTATION_PLAN_REVIEW.md)
- [B8_PHASE_G_REREVIEW.md](B8_PHASE_G_REREVIEW.md)
- [B8_REUSE_GATE_REVIEW.md](B8_REUSE_GATE_REVIEW.md)
- [B8_REVIEW.md](B8_REVIEW.md)
- [MARKETPLACE_REPLAY_REREVIEW_2026-08-27.md](MARKETPLACE_REPLAY_REREVIEW_2026-08-27.md)
- [MARKETPLACE_REPLAY_REVIEW_2026-08-26.md](MARKETPLACE_REPLAY_REVIEW_2026-08-26.md)
- [P0_DOCKER_SAVE_ORDER_REREVIEW_2026-09-11.md](P0_DOCKER_SAVE_ORDER_REREVIEW_2026-09-11.md)
- [P0_HOST_PROXY_CODE_REVIEW_2026-09-03.md](P0_HOST_PROXY_CODE_REVIEW_2026-09-03.md)
- [P0_HOST_PROXY_REREVIEW_2026-09-04.md](P0_HOST_PROXY_REREVIEW_2026-09-04.md)
- [P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md](P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md)
- [P0_IMAGE_PREVIEW_CODE_REVIEW_2026-10-07.md](P0_IMAGE_PREVIEW_CODE_REVIEW_2026-10-07.md)
- [P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md](P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md)
- [P0_IMAGE_PREVIEW_PLAN_REVIEW_2026-10-06.md](P0_IMAGE_PREVIEW_PLAN_REVIEW_2026-10-06.md)
- [P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md](P0_MINIMUM_OFFLINE_GATE_ARCHITECT_2026-08-30.md)
- [P0_MINIMUM_OFFLINE_GATE_CODE_REVIEW_2026-09-02.md](P0_MINIMUM_OFFLINE_GATE_CODE_REVIEW_2026-09-02.md)
- [P0_MINIMUM_OFFLINE_GATE_PLAN_REREVIEW_2026-08-30.md](P0_MINIMUM_OFFLINE_GATE_PLAN_REREVIEW_2026-08-30.md)
- [P0_MINIMUM_OFFLINE_GATE_PLAN_REVIEW_2026-08-30.md](P0_MINIMUM_OFFLINE_GATE_PLAN_REVIEW_2026-08-30.md)
- [P0_SECRET_SCAN_ARCHITECT_2026-08-28.md](P0_SECRET_SCAN_ARCHITECT_2026-08-28.md)
- [P0_SECRET_SCAN_PLAN_REVIEW_2026-08-28.md](P0_SECRET_SCAN_PLAN_REVIEW_2026-08-28.md)
- [P0_WEAVIATE_DOC_ID_CODE_REVIEW_2026-09-20.md](P0_WEAVIATE_DOC_ID_CODE_REVIEW_2026-09-20.md)
- [P0_WEAVIATE_DOC_ID_REREVIEW_2026-09-22.md](P0_WEAVIATE_DOC_ID_REREVIEW_2026-09-22.md)

## 5. 验证计划与阶段总结

- [FINAL_VALIDATION_SUMMARY.md](FINAL_VALIDATION_SUMMARY.md)
- [UPGRADE_REHEARSAL_VALIDATION_2026-08-18.md](UPGRADE_REHEARSAL_VALIDATION_2026-08-18.md)
- [VALIDATION_PLAN.md](VALIDATION_PLAN.md)

## 6. 环境与升级指导

- [OFFLINE_DEPLOYMENT_CHECKLIST.md](OFFLINE_DEPLOYMENT_CHECKLIST.md)
- [PRODUCTION_ENVIRONMENTS.md](PRODUCTION_ENVIRONMENTS.md)
- [PRODUCTION_PLAN_B_RUNBOOK.md](PRODUCTION_PLAN_B_RUNBOOK.md)
- [PRODUCTION_RELEASE_PREFLIGHT.md](PRODUCTION_RELEASE_PREFLIGHT.md)

## 7. 可提交的阶段证据

- [evidence/README.md](evidence/README.md)
- [evidence/phase-d/db-matrix/README.md](evidence/phase-d/db-matrix/README.md)
- [evidence/phase-d/db-matrix/notrun.md](evidence/phase-d/db-matrix/notrun.md)
- [evidence/phase-d/db-matrix/row-1-prod-pg15-enterprise-upgrade.md](evidence/phase-d/db-matrix/row-1-prod-pg15-enterprise-upgrade.md)
- [evidence/phase-d/db-matrix/row-2-official-115-enterprise-upgrade.md](evidence/phase-d/db-matrix/row-2-official-115-enterprise-upgrade.md)
- [evidence/phase-d/db-matrix/row-3-pg18-empty-enterprise-upgrade.md](evidence/phase-d/db-matrix/row-3-pg18-empty-enterprise-upgrade.md)
- [evidence/phase-d/db-matrix/row-4-pg18-app-upgrade-enterprise.md](evidence/phase-d/db-matrix/row-4-pg18-app-upgrade-enterprise.md)
- [evidence/phase-d/db-matrix/row-5-official-116-enterprise-upgrade.md](evidence/phase-d/db-matrix/row-5-official-116-enterprise-upgrade.md)
- [evidence/phase-d/rollback-drill/row-6-backup-restore-rollback.md](evidence/phase-d/rollback-drill/row-6-backup-restore-rollback.md)
- [evidence/phase-f-rebuild/PLAN.md](evidence/phase-f-rebuild/PLAN.md)
- [evidence/phase-f-rebuild/README.md](evidence/phase-f-rebuild/README.md)
- [evidence/phase-f/PLAN.md](evidence/phase-f/PLAN.md)
- [evidence/phase-f/README.md](evidence/phase-f/README.md)
- [evidence/phase-g/PLAN.md](evidence/phase-g/PLAN.md)
- [evidence/phase-g/README.md](evidence/phase-g/README.md)
- [evidence/phase-h-rerun/PLAN.md](evidence/phase-h-rerun/PLAN.md)
- [evidence/phase-h-rerun/README.md](evidence/phase-h-rerun/README.md)
- [evidence/phase-h/PLAN.md](evidence/phase-h/PLAN.md)
- [evidence/phase-h/README.md](evidence/phase-h/README.md)

## 本机未提交证据入口

- output/playwright/replay-116-regression-20260930.md：历史应用与图片问题。
- output/playwright/replay-116-final-switch-20260930.md：旧镜像切换及nginx upstream问题。
- output/playwright/replay-116-weaviate-20260924/RESULTS.md：历史知识库索引/召回。
- output/offline/rehearsal-1cc8e60a/RESULTS.md 与 loadboot/RESULTS.md：旧包/checker和隔离启动。
- /tmp/ippr-synthetic-94__v64p/commands.log、/tmp/ippr-review-synthetic-hg5ej18q/commands.log：本轮合成测试。临时文件可丢失，不是永久归档。

新增文档应放入对应分类并更新索引；更新当前状态不改旧报告，使每份历史证据保留来源时间和SHA。
