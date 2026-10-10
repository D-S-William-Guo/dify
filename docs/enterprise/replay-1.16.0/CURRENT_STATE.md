# Dify Enterprise 1.16.0 协调窗口当前状态

更新时间：2026-10-07（Asia/Shanghai）

## 一分钟看懂

- 已完成：图片预览修复已进入候选源码，独立代码审查与合成回归通过。
- 尚未完成：运行中的 API 还是旧镜像，尚未验证修复后的历史图片预览；旧离线包也不包含本次修复。
- 当前正在做：用户已确认文档职责、冲突协调和换 harness 恢复约定；继续完善、核验文档草稿，不提交或 push，不执行运行环境操作。
- 后续顺序：文档确认后，再衔接本机 API 镜像切换和有窗体图片验证；冷备、回退依据和授权边界仍须先核对。不是生产发布。
- 按身份查文档见 [索引快速入口](DOCUMENT_INDEX.md#从这里开始按身份或问题选入口)。下面的精确 SHA、镜像与历史结果用于核验，不要求人类先读完才能了解进度。

## 定位与读取规则

本文件最初用于 GPT 额度不足、切换到 Codex＋DeepSeek 策略指挥窗口时交接现场；现在仍是**协调窗口换模型或换会话的恢复首页**，不是所有智能体的全量共享上下文。

- 通用调度规则从两个 Skill 读取，项目约束从根目录 ENTERPRISE_REPLAY_PLAN.md、AGENTS 与相关领域指南读取；缺失 Skill 不得静默跳过。完整职责和恢复路线见 DOCUMENT_INDEX，不在本文复制 SOP。
- 单个智能体以精确 SHA 阶段契约和任务相关计划/审查报告为依据；只按需读取本页。
- 本页只维护当前摘要、证据入口、未完成项、实例与授权边界。历史记录不再以“覆盖旧段落”无限追加。
- Git、实际命令与最终审查证据优先；计划、历史 PASS 和聊天均不能代替当前运行验证。
- 文档分类与读取路由见 [DOCUMENT_INDEX.md](DOCUMENT_INDEX.md)。
- 整理前 780 行原文完整保留在 [CURRENT_STATE_HISTORY_2026-10-07.md](CURRENT_STATE_HISTORY_2026-10-07.md)，其中旧“下一步”、实例数及授权均不是当前指令。

## 当前 Git 与代码状态

| 项目 | 当前可信记录 |
| --- | --- |
| 候选分支 | `codex/enterprise-candidate-1.16.0-20260718` |
| 本轮整理前 HEAD | `3638589aa4b43da5948ca175b91a87d979e94af3`，整理前工作区干净。本文不自引用未来 docs commit。 |
| 文档整理现场 | 本页与索引/历史快照为未提交整理；另协调总纲、验证计划、决策台账及旧指导的范围说明。实际 dirty 路径须用 git status/diff 核对，不要求新窗口误判为 clean，不自动丢弃或提交。 |
| 远端 checkpoint | 上一授权 push 后通过 git ls-remote 核验为同一精确 SHA；本轮整理不 push。 |
| 图片预览修复 | Builder `53f2ba6f335ca842cd4c2a9856615725841d7f6d` 和 Code Review `83a8d93aa2c96ab365fbeba4bea51834851f6c6f` 已集成并包含于上述远端 checkpoint。 |
| 代码验收 | Code Review PASS，无必须修复 finding；补齐共享召回签名、旧 query 消费和混合 URL 替换顺序。仅两份生产代码与三份既定测试改变。 |
| 单元证据 | Builder 与独立 Reviewer 各自聚焦 220、相关 219，合计各自 439/439；54 个安全用例为子集。协调窗口独立复跑三份修改测试 205/205。Ruff/空白检查通过。 |
| 关键报告 | [Architect](P0_IMAGE_PREVIEW_ARCHITECT_2026-10-06.md)、[Plan Review](P0_IMAGE_PREVIEW_PLAN_REVIEW_2026-10-06.md)、[Plan Rereview](P0_IMAGE_PREVIEW_PLAN_REREVIEW_2026-10-07.md)、[Code Review](P0_IMAGE_PREVIEW_CODE_REVIEW_2026-10-07.md)。 |

## 本机验证：已通过与尚未完成

本机是 Development / historical-data rehearsal。实际升级演练沿用上一版本的配置与历史挂载数据；空数据隔离项目只提供额外打包冒烟，不能取代历史数据升级验证。生产与灰度是另外的离线部署环境。

| 范围 | 证据与边界 |
| --- | --- |
| 历史数据召回 | 2026-09-24 两文档重索引后 PostgreSQL/Weaviate 63/63 严格对应；有窗体三条召回通过。是历史时点结果，不宣称今天重新对账。 |
| 历史应用 | 2026-10-04 三个应用运行版本显式使用 qwen3.8-flash，Agent、文本生成和文件工作流回归 PASS；文字召回与 DOCX 原件下载正常。 |
| 当前 API 镜像预检 | 2026-10-07 只读 docker inspect：四个 docker 项目 API 系列容器仍使用 `sha256:8d4ac68ef576d951a51dd941a51f09f91f91ed5372de241e08567e6438fc2319`，沿用原 app/storage 挂载。未切换。 |
| 图片修复运行验收 | 新 API 镜像重建/切换、有窗体历史召回卡片/详情图片预览 **NOT_RUN**；图片发布前要求仍未关闭。不需要仅为签名修复重新索引。 |
| 离线包 | `dist/offline/rehearsal-1cc8e60a` 是旧源码产物，曾真实 checker 5/0/0；不包含本次图片修复。新包重建/checker **NOT_RUN**。 |
| 空数据 load + boot | replay116lb9b59 曾基础入口和合成 JavaScript PASS；sandbox 配置必须初始化，示例 syscall 限制曾失败。非历史应用升级验收，非真正无外网主机验收。 |
| 尚存缺口 | 最新镜像/有窗体图片回归、新离线产物、完整发布功能矩阵与控制台错误分类、真正离线目标机和受保护发布审计未形成当前整体发布 PASS。不能用历史“FINAL”标题推断已可部署。 |

本机详细证据在忽略目录 output/playwright、output/offline 和 .playwright-cli；不提交原始页面、文档摘录、配置或凭据。入口见文档索引。

## 实例与运行现场

六个 Claude Squad 实例保留，不删除：

- replay-116-image-preview-architect-20261006
- replay-116-image-preview-plan-reviewer-20261006
- replay-116-image-preview-plan-fixer-20261007
- replay-116-image-preview-plan-rereviewer-20261007
- replay-116-image-preview-builder-20261007
- replay-116-image-preview-code-reviewer-20261007

最近创建核验 controller_count=0；这是当时观测，恢复时重新核对。Code Reviewer 的 repo_path 指向 Builder worktree，清理时必须按依赖顺序治理，不能先删来源 worktree。实例数量不等于所有角色都需并行执行。

本机 docker 历史数据项目与 replay116lb9b59 空数据项目均存在；本轮整理没有启停任何容器。其他开发服务不在范围内。

## 已接受决定与下一步

- 沿用现有有效连接配置；默认密码轮换保留为独立延期加固事项，不作为本次重放阻塞。
- 旧全层 secret 扫描计划已被最小离线门禁取代；旧 Plan B runbook 不是当前滚动升级指令。
- 新 API 切换后须检查 nginx 旧 upstream 解析问题，按 Skill 排查；不能凭经验自动重启未授权的 nginx。
- 用户已授权本机 API 重建/四个实际 API 系列容器切换：先确认冷备和旧镜像回退依据，显式 host-proxy，临时覆盖 MIGRATION_ENABLED=false，沿用配置/数据，验证健康和有窗体历史图片。失败即停，不自动回退。
- **随后用户要求优先重新分类整理文档，本机运行步骤暂停在预检阶段**。冷备与回退完整核验尚未完成；未构建、未切换、未运行浏览器。整理完先汇报差异与记录缺口，再衔接原授权，不把文档改动误当新增运行权限。
- 用户已确认本轮职责划分、冲突协调和换 harness 恢复约定；当前仅继续完善和核验草稿。后续新增实质性规则或范围变化须再次说明并确认，不能把认可整理方案等同于提交或运行授权。
- 不授权生产/灰度访问或部署、secret 轮换、历史数据改写/重索引、Web 更新、离线包重建、实例清理或本轮提交/push。

## 开放事项总表

开放事项先按下表定位。历史矩阵中的未完成项不自动成为今天的阻塞；关闭一项须补对应日期、来源 SHA/运行镜像、验收范围和证据，并回填来源矩阵。修改支持范围或接受延期由用户决定，不以新的 PASS 摘要隐式关闭。

| 开放项 | 分类 | 证据入口与关闭条件 |
| --- | --- | --- |
| 图片预览新镜像/有窗体验证、新离线包 | 发布前待验证 | 本页运行表均 NOT_RUN；分别以新镜像浏览器证据、新包 checker及来源身份核验关闭 |
| 冷备与回退依据 | 本机切换前置 | 尚未完整核验；须确认备份范围/时间、旧镜像与挂载身份及回退方式，不能仅核对备用 tag |
| E01、E16、E18 | 历史 NOT_RUN 待映射 | [E01–E18 矩阵](UPGRADE_REHEARSAL_VALIDATION_2026-08-18.md)：默认加入工作区、OAuth 兼容、旧 session；尚未找到当前关闭证据，逐项按范围授权验证或由用户接受限制 |
| E02、E03、E07、E11、E14 | 历史 PARTIAL 待映射 | 同矩阵：注册/建工作区策略、管理员允许操作/邀请、登录安全回跳、离线插件、协作重连；已有局部通过不代替剩余场景 |
| E10 | 历史离线 PARTIAL 已有后续变化 | 旧全层扫描要求被最小门禁取代；旧包曾 checker PASS，但最新图片修复包尚未生成，不恢复旧扫描为阻塞 |
| E04/E05/E08/E09/E12/E13/E15/E17 | 历史 PASS，需来源对应 | 同矩阵的功能结果保留；后续 63/63 对账和应用回归见本页。最新代码、模型、镜像改变后只补受影响验收，不声称今天全项重跑 |
| 真正无外网目标机、registry/签名、部署及生产回退验证 | 外部条件/交付范围待定 | [旧 preflight](PRODUCTION_RELEASE_PREFLIGHT.md) 项目不是自动指令；最终交付方式、必须验证项和授权由用户确认，开发机模拟不代替真实目标 |
| 默认密码轮换、B9 会话管理 | 已接受延期 | [后续决定](DECISION_RISK_LEDGER.md)、[Design Gate](DESIGN_GATE.md)；独立加固/需求澄清，不作为本次自动阻塞 |
| B7/B8 已接受 P3、.ps1、旧 OCI 内容扫描、受保护 pattern | 已接受限制或独立范围待定 | [历史限制清单](FINAL_VALIDATION_SUMMARY.md) 与后续最小门禁决定合读；不全归为必须加固，不用开发证据把受保护审计改写为 PASS |
| 六实例清理、Skill 安装一致性、文档交付 | 治理事项 | README/AGENTS 短入口已按授权完成并通过链接核验；本轮精确 11 份文档获准本地提交，本文记录提交前现场，不自引用未来提交 SHA。push、系统同步和实例清理未授权（CLEANUP_NOT_AUTHORIZED）；清理前须资格审计并处理 Code Reviewer 对 Builder 的依赖 |
| 1.16.1 候选线归属 | 用户待决 | Claude 2026-10-07 审计报告称远端 `codex/enterprise-candidate-1.16.1-20260728` 存在（SHA 前缀 `67e505d049bb`），这是外部复核记录，不是本轮 Codex 独立结论。本地 refs/对象未找到；2026-10-09 独立执行 `git ls-remote --exit-code origin refs/heads/codex/enterprise-candidate-1.16.1-20260728` 因无法连接服务器退出 128，远端存在性未重新核实。内容/维护归属仍待决，不得纳入、合并、删除或宣称替代本轮 |

## 新窗口最小恢复步骤

1. 按 DOCUMENT_INDEX 的换 harness 路线读取两个 Skill、本文、项目总纲、AGENTS 与当前任务证据；核对实际分支、HEAD/status及是否包含上述 checkpoint。远端读取须有相应网络权限；未查就标明未查。草稿来源不明或 Git 不符时停下核对，不自行修复。
2. 只读核对持久实例、worktree/分支、Agent 会话、controller 数量；多个 controller 即暂停治理操作。
3. 图片修复继续时读取最新 Architect 与 Code Review，不重读全部 B0–B8 或旧聊天。
4. 区分源代码、运行 image ID、数据状态、离线包来源 SHA；分别报告 PASS/FAIL/NOT_RUN。
5. 给出当前情况、下一步建议、仍有效授权和需要用户决策的边界；不得自动修复 Git 差异或连接生产。
