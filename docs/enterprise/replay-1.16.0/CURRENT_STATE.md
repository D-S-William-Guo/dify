# Dify Enterprise 1.16.0 协调窗口当前状态

更新时间：2026-10-13（Asia/Shanghai）

## 一分钟看懂

- 已完成：图片预览修复的代码审查、合成回归、本机 API 镜像切换及有窗体历史图片验证通过；召回卡片 15/15、段落详情 12/12 图片加载成功且签名存在。
- 尚未完成：旧离线包不包含本次图片修复，新包尚未重建；浏览器控制台错误仍未分类，完整发布验收尚未完成。
- 当前正在做：仅补记来源 checkpoint `fa1be4bcfde54b6faa75d41a129da5165e68f734` 的本机运行结果，草稿待用户审阅；不提交、push 或操作运行环境。
- 后续顺序：先审阅本页 diff；后续控制台错误分类及新离线包工作分别确认范围与授权。不是生产发布。
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
| 文档整理交付 | checkpoint `e8f98a7a3e`（本页、索引、历史快照及范围说明均已入库）；恢复时核验实际 HEAD 包含该 checkpoint。交付时工作区 clean；本页不追认其后的记录性提交。 |
| 远端 checkpoint | `e8f98a7a3e` 已 push；本机 `git ls-remote` 核验 origin 分支 tip 与该 SHA 一致（远端可达性不稳定，恢复时重查）。 |
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
| 当前 API 镜像与切换 | 2026-10-13，从 checkpoint `fa1be4bcfde54b6faa75d41a129da5165e68f734` 的本地完整源码副本、显式 host-proxy 构建；仅切换 api/worker/worker_beat/api_websocket。四者均运行 `sha256:50ad27bc4e8c10fcba2863c99016d7481411e1dee7b8e110adc56d6e5a6c3ed0`，API healthy，迁移均禁用，项目和原挂载保持一致。已授权 nginx reload；经 nginx 的 `/console/api/setup` 与 `/signin` 均 HTTP 200，Web 未重建或切换。 |
| 图片修复运行验收 | 2026-10-13 有窗体 Playwright，第一历史账号通过界面进入知识库 `947ef84b-81e2-44db-a45a-92ae9458417d`，重跑 `智能体平台`：卡片 15/15 图片真实加载且签名存在；Chunk-09 段落详情 12/12 同样通过。此范围 **PASS**，不代表全功能回归。未重索引或修改历史文档。 |
| 离线包 | `dist/offline/rehearsal-1cc8e60a` 是旧源码产物，曾真实 checker 5/0/0；不包含本次图片修复。新包重建/checker **NOT_RUN**。 |
| 空数据 load + boot | replay116lb9b59 曾基础入口和合成 JavaScript PASS；sandbox 配置必须初始化，示例 syscall 限制曾失败。非历史应用升级验收，非真正无外网主机验收。 |
| 尚存缺口 | 新离线产物、完整发布功能矩阵与控制台错误分类、真正离线目标机和受保护发布审计未形成整体发布 PASS。浏览器本次召回前已有 9 条控制台错误，卡片/详情验证后仍为 9；未分类，不能隐式关闭。不能用图片局部 PASS 或历史“FINAL”标题推断已可部署。 |

本机详细证据在忽略目录 output/playwright、output/offline 和 .playwright-cli；不提交原始页面、文档摘录、配置或凭据。入口见文档索引。

本次脱敏结果：`output/playwright/replay-116-image-preview-switch-20261013.md`；本机截图：`output/playwright/image-preview-cards-20261013.png`、`output/playwright/image-preview-detail-20261013.png`，含历史内容，仅本机保留。初次 CLI 因沙箱网络权限失败后停止，另获授权恢复有窗体通道后完成上述验收。

## 实例与运行现场

六个 Claude Squad 实例保留，不删除：

- replay-116-image-preview-architect-20261006
- replay-116-image-preview-plan-reviewer-20261006
- replay-116-image-preview-plan-fixer-20261007
- replay-116-image-preview-plan-rereviewer-20261007
- replay-116-image-preview-builder-20261007
- replay-116-image-preview-code-reviewer-20261007

最近创建核验 controller_count=0；这是当时观测，恢复时重新核对。Code Reviewer 的 repo_path 指向 Builder worktree，清理时必须按依赖顺序治理，不能先删来源 worktree。实例数量不等于所有角色都需并行执行。

本机 docker 历史数据项目与 replay116lb9b59 空数据项目均存在；2026-10-13 仅按授权重建/切换四个 API 容器并 reload 本机 nginx。其他开发服务不在范围内；本次状态补记不操作运行环境。

## 已接受决定与下一步

- 沿用现有有效连接配置；默认密码轮换保留为独立延期加固事项，不作为本次重放阻塞。
- 旧全层 secret 扫描计划已被最小离线门禁取代；旧 Plan B runbook 不是当前滚动升级指令。
- 本次 API 切换已按单独授权刷新 nginx 并验证入口；不将本次 reload 当作以后自动操作网关的权限。
- 本机 API 重建、四容器切换、禁用迁移、沿用配置/挂载及有窗体图片验收已完成。旧镜像保留为 `dify-api-enterprise:rollback-pre-image-preview-fa1be4bc`，绑定 `sha256:8d4ac68ef576d951a51dd941a51f09f91f91ed5372de241e08567e6438fc2319`；未自动回退。旧冷备早于后续索引变更，不作当前数据无损回退。
- sparse checkout 排除了 Compose 和构建文件；按授权在 `/tmp/replay-116-api-source-fa1be4bc.HMeUyf` 准备本地完整源码，临时 Compose 在 `/tmp/replay-116-api-switch-fa1be4bc.o6J90J`，未改变原工作区 sparse 设置。真实 Compose 仅在内存核验，未持久化配置或代理值；恢复时核对临时文件是否仍存在，不直接照抄旧命令。
- 用户已确认本轮职责划分、冲突协调和换 harness 恢复约定；当前仅继续完善和核验草稿。后续新增实质性规则或范围变化须再次说明并确认，不能把认可整理方案等同于提交或运行授权。
- 不授权生产/灰度访问或部署、secret 轮换、历史数据改写/重索引、Web 更新、离线包重建、实例清理或本轮提交/push。

## 开放事项总表

开放事项先按下表定位。历史矩阵中的未完成项不自动成为今天的阻塞；关闭一项须补对应日期、来源 SHA/运行镜像、验收范围和证据，并回填来源矩阵。修改支持范围或接受延期由用户决定，不以新的 PASS 摘要隐式关闭。

| 开放项 | 分类 | 证据入口与关闭条件 |
| --- | --- | --- |
| 图片预览新镜像/有窗体验证、新离线包 | 图片运行验收已通过；离线产物待验证 | 2026-10-13 新镜像卡片 15/15、详情 12/12 PASS，证据见本页；仅关闭此图片范围。最新离线包重建/checker仍 NOT_RUN |
| 冷备与回退依据 | 本次切换前置已核验；恢复演练未做 | `/home/ctyun/BigData/.system-data/tmp/replay116-backup.XH7lLm/docker-data-config.tar`，13,639,835,648 字节；复算 SHA-256 `3a011abd2d8841b0a59e637cfde9b145ddc0a25f384aa14cd8caffa7f18148c9` 与原记录一致。历史 README 记载停机冷备；完整恢复未演练，且备份早于后续重索引。当前镜像已保留，四 API 挂载与迁移开关已核验；不授权恢复整库 |
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
