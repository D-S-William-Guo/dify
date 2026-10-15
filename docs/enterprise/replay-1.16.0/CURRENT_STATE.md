# Dify Enterprise 1.16.0 协调窗口当前状态

更新时间：2026-10-15（Asia/Shanghai）

## 一分钟看懂

- 已完成：2026-10-15 最终包 API/Web 已切换到本机历史数据栈；健康与入口、历史账号登录、召回卡片 15/15 和详情 12/12 图片、一个对话流及一个文件工作流重点回归通过。
- 已打包：来源 checkpoint `82e50fff1b29b576d0e153b2e4316dc80d183de2` 的离线包真实 checker 5/0/0，四产物转存及 SHA-256 一致性通过；本次仅使用其本地精确镜像，不重新打包。
- 尚未完成：会话失效原因与完整网络证据、完整发布验收和真正离线目标机验证仍未完成；新包 tar 的重新 load 未做。新空数据项目已按用户决定不启动，不自动作为本轮历史数据回归的阻塞。
- 当前正在做：仅补记旧演练栈已停止及当前栈与最终包镜像一致的核验结果，草稿待用户审阅；不提交、push 或操作运行环境。
- 后续顺序：先审阅本页 diff；后续验证和实例治理分别确认范围与授权。不是生产发布。
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
| 远端 checkpoint | 2026-10-15 push 后独立 `git ls-remote` 核验为 `03f6dbbd16a3643cf0beb6cb7716f5fa2e77e1e3`，包含治理入口与离线包结果记录。这是上次远端实测，恢复时重查；本次补记不追认其后提交，也不自引用未来 SHA。 |
| 项目规范入口 | 用户确认由 OpenCode 按授权补充治理提交 `db854c27ef3c83f47e339d755fbf78a46d2874d1`，2026-10-15 核验包含于本地 HEAD；仅新增 AGENTS 两行要求。AGENTS 明确所有 harness 加载两个 Skill，失败读可信源并报告，每份任务契约重申。已跟踪的 `CLAUDE.md` 为有效符号链接，指向 AGENTS.md，不维护第二套规则；本页不自引用其后补记提交。 |
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
| 最终 API/Web 镜像与切换 | 2026-10-15，协调 checkpoint `03f6dbbd16a3643cf0beb6cb7716f5fa2e77e1e3`，包来源仍为 `82e50fff1b29b576d0e153b2e4316dc80d183de2`。四个 API 服务切换到 `sha256:51e7f13265df63320784b8376cda4e814b4184689e9f4dfe589908d78217eb4c`，Web 到 `sha256:397a3e129b1e20ce9721c87d09c7cc3e2e26a28b438731581de1b9822b4352ee`；项目和五服务挂载核验不变，四 API 迁移禁用，仅重建容器、未 build/pull。nginx reload 成功。首次 setup 请求20秒超时后停测，API 随后 healthy、重启计数0；另获一次有界复查授权，setup 返回200，signin 返回200。 |
| 图片修复运行验收 | 2026-10-13 有窗体 Playwright，第一历史账号通过界面进入知识库 `947ef84b-81e2-44db-a45a-92ae9458417d`，重跑 `智能体平台`：卡片 15/15 图片真实加载且签名存在；Chunk-09 段落详情 12/12 同样通过。此范围 **PASS**，不代表全功能回归。未重索引或修改历史文档。 |
| 离线包 | 2026-10-14 从精确 checkpoint `82e50fff1b29b576d0e153b2e4316dc80d183de2` 完整临时源码显式 rebuild + host-proxy，API/Web 均构建完成，依赖全部本地复用，无 pull。新目录 `dist/offline/rehearsal-82e50fff` 四产物复制前后 SHA-256 一致；真实 checker **5 PASS / 0 FAIL / 0 NOT_RUN**，配置包精确 51 个允许文件。旧 `rehearsal-1cc8e60a` 保留，不再代表最新包；新包 load + boot **NOT_RUN**。 |
| 打包与运行身份 | 10-14 打包未切换服务；10-15 已单独授权切换并在最终包精确 API/Web 镜像上完成本页重点回归，不再沿用旧镜像的浏览器结果代替。此次使用本地已有且与 manifest 匹配的镜像，未重新 docker load；不宣称完成新包 load + boot 或真正离线机验收。API/Web 无 registry RepoDigest，checker 按不可变 image ID 绑定包身份；不等于 registry 来源认证。 |
| 最终镜像有窗体重点回归 | 历史账号登录 PASS；历史知识库 `947ef84b-81e2-44db-a45a-92ae9458417d` 查询“智能体平台”，卡片图片15/15加载且签名存在，Chunk-09详情图片12/12加载。对话流运行入口 `ec6ad24d-9e99-4b33-b108-76d9475f7a15` 在下述授权发布调整后，唯一一次复测“请只回复OK”返回OK且显示运行成功。文件工作流入口 `545dafd2-b692-4cdb-b451-2930117766c1`，19字节合成文本上传后，文档提取器/LLM/输出完成，返回“水果是苹果。”。不代表全功能矩阵通过，未重索引。 |
| 指定对话流发布调整 | 同名应用有两个；本次失败运行明确属于 `1f3d1089-543b-43a4-84ea-15ecf7a3f857`，不是 `edd0efdc-5c13-4372-adda-882009b01989`。只读核对已发布版（2026-08-19）为通义qwen3.7-plus，草稿曾显示qwen3.8-max。初次最终镜像回归停于通义凭据错误；用户另行授权只将此应用改为通义qwen3.8-flash，保存并发布，随后复测成功。未改密钥、全局模型、其他应用配置；未确认旧模型凭据错误的更深层原因，不将其写成镜像故障或密钥已修复。 |
| 空数据 load + boot | replay116lb9b59 曾基础入口和合成 JavaScript PASS；sandbox 配置必须初始化，示例 syscall 限制曾失败。2026-10-15 按授权停止其14个运行容器，未删除容器、镜像、卷或文件。该历史冒烟不是历史应用升级验收，也不是真正无外网主机验收。 |
| 控制台错误分类 | 2026-10-13 只读分析已有日志 `.playwright-cli/console-2026-10-13T03-31-37-787Z.log`：9 条＝7 条 HTTP 401（登录页身份/令牌接口 2 条，闲置约 2.5 小时后知识库相关接口 5 条）＋2 条查询取消 AbortError（堆栈含 cancel/removeObserver/onUnsubscribe）。后 5 条疑似会话失效，但原因仍为推断；未找到独立完整网络记录，不能确认刷新过程或宣称会话功能全量通过。卡片/详情验证前后均为 9 条，无新增图片错误，现有日志未见 file-preview 400；图片局部 PASS 保持有效，不据此启动代码修复或关闭会话验收缺口。 |
| 尚存缺口 | 完整发布功能矩阵、会话问题的根因与完整网络证据、真正离线目标机和受保护发布审计仍未形成整体发布 PASS；新包 tar load 未执行。用户决定先不做新空数据项目，历史数据升级验证为主线，额外空库冒烟不能自动升级为阻塞。不用本页重点回归或历史“FINAL”推断生产可部署。 |

本机详细证据在忽略目录 output/playwright、output/offline 和 .playwright-cli；不提交原始页面、文档摘录、配置或凭据。入口见文档索引。

本次脱敏结果：`output/playwright/replay-116-image-preview-switch-20261013.md`；本机截图：`output/playwright/image-preview-cards-20261013.png`、`output/playwright/image-preview-detail-20261013.png`，含历史内容，仅本机保留。初次 CLI 因沙箱网络权限失败后停止，另获授权恢复有窗体通道后完成上述验收。

最终镜像重点回归记录：`output/playwright/final-82e50fff-switch-20261015.md`，有窗体会话 `final-82e50fff`。截图 `final-82e50fff-{cards,detail,chatflow-failure,chatflow-pass,file-workflow-pass}-20261015.png` 位于同一 output/playwright 目录，仅本机保留、不提交。报告保留启动超时和旧运行版模型失败的先后过程，后续授权通过不抹去早期失败。

### 新离线包 SHA-256（2026-10-14）

以下对应 `dist/offline/rehearsal-82e50fff`，来源均为 `82e50fff1b29b576d0e153b2e4316dc80d183de2`；四文件从临时源码产物目录复制后复算一致。

| 文件 | SHA-256 |
| --- | --- |
| dify-enterprise-offline-1.16.0-enterprise.tar | `0b96f6d02eb0654c87e93de1672a516b331a71ba44a765d580c86cb24aed9aa1` |
| dify-enterprise-config-1.16.0-enterprise.tar.gz | `59065f2bc07a200cda66c3b60a359b3ae6f50256514b1d120416ca316cf30fe1` |
| manifest-1.16.0-enterprise.json | `2acc1d297c3dc23e383274fbcbcf5f7b777ea4b3699dd84e9855963219193f95` |
| images-1.16.0-enterprise.txt | `5fe37b7903925458880230bef8e677e72dc942f78dcac9beaf283d15151256b8` |

构建临时源码 `/tmp/replay-116-offline-82e50fff.2GpekG`；开发 `.env` 仅临时链接用于解析，未复制或打包。首次 Web registry 请求 EOF 后停止，单独授权的第 1 次重试通过；docker save 耗时较长后自行 exit 0，未终止或重启 Docker。临时产物目录中的 BUILD_FAILURE.md、RETRY_STATUS.md 是当时中间状态，导出/checker/转存最终结果以上表和本页为准；临时记录不是永久日志，不宣称完整构建日志已归档。

## 实例与运行现场

六个 Claude Squad 实例保留，不删除：

- replay-116-image-preview-architect-20261006
- replay-116-image-preview-plan-reviewer-20261006
- replay-116-image-preview-plan-fixer-20261007
- replay-116-image-preview-plan-rereviewer-20261007
- replay-116-image-preview-builder-20261007
- replay-116-image-preview-code-reviewer-20261007

最近创建核验 controller_count=0；这是当时观测，恢复时重新核对。Code Reviewer 的 repo_path 指向 Builder worktree，清理时必须按依赖顺序治理，不能先删来源 worktree。实例数量不等于所有角色都需并行执行。

2026-10-15 按授权只停止旧空数据项目 `replay116lb9b59` 的14个运行容器，docker stop exit 0；停止后该项目运行数为0，14个目标容器均仍存在且已停止，未删除镜像、卷或文件。

随后逐项核验当前 `docker` 历史数据栈：15/15容器镜像 ID 均属于最终包 `rehearsal-82e50fff` 的 manifest，Compose 工作目录均为本次1.16.0工程的 docker 目录；14个服务运行，init_permissions 正常退出且 exit 0。有健康检查的 API、sandbox、PostgreSQL、Redis、local_sandbox 均 healthy；其余服务没有配置健康检查，不宣称其 healthcheck PASS。四个 API 服务均保持 MIGRATION_ENABLED=false。

停机前后对照所有非目标容器，其容器 ID、镜像 ID、运行布尔状态、StartedAt 和 RestartCount 均未变化，当前栈及其他项目未受此次停机影响。该结论只适用于本次前后核验，不代替未来现场检查。本次状态补记不操作运行环境，也不授予清理旧资源或重新启动旧演练栈的权限。

## 已接受决定与下一步

- 沿用现有有效连接配置；默认密码轮换保留为独立延期加固事项，不作为本次重放阻塞。
- 旧全层 secret 扫描计划已被最小离线门禁取代；旧 Plan B runbook 不是当前滚动升级指令。
- 本次 API 切换已按单独授权刷新 nginx 并验证入口；不将本次 reload 当作以后自动操作网关的权限。
- 最终包五个应用容器已切换并完成重点回归，API回退标签 `dify-api-enterprise:rollback-pre-final-82e50fff` 绑定 `sha256:50ad27bc4e8c10fcba2863c99016d7481411e1dee7b8e110adc56d6e5a6c3ed0`，Web回退标签 `dify-web-enterprise:rollback-pre-final-82e50fff` 绑定 `sha256:4eb9291e71ef94681c1bddd4863a93737e701273bcfc9f8698cfa87e9b0782a2`。更早回退镜像保留，未自动回退。旧冷备早于后续索引变更，不作当前数据无损回退。
- sparse checkout 排除了 Compose 和构建文件；按授权在 `/tmp/replay-116-api-source-fa1be4bc.HMeUyf` 准备本地完整源码，临时 Compose 在 `/tmp/replay-116-api-switch-fa1be4bc.o6J90J`，未改变原工作区 sparse 设置。真实 Compose 仅在内存核验，未持久化配置或代理值；恢复时核对临时文件是否仍存在，不直接照抄旧命令。
- 文档治理、错误分类及离线包记录已交付至上述远端实测 checkpoint；OpenCode 的项目级 Skill 要求和共享 CLAUDE 入口已核验。当前仅补记最终镜像重点回归，新增规则或范围变化仍须确认。
- 本机离线构建、checker、转存、最终镜像切换及指定对话流发布已按各自授权完成，不延伸为再次构建或部署权限。当前不授权生产/灰度访问或部署、secret轮换、重索引、其他历史应用/模型配置调整、新空数据项目、实例清理或本轮提交/push。

## 开放事项总表

开放事项先按下表定位。历史矩阵中的未完成项不自动成为今天的阻塞；关闭一项须补对应日期、来源 SHA/运行镜像、验收范围和证据，并回填来源矩阵。修改支持范围或接受延期由用户决定，不以新的 PASS 摘要隐式关闭。

| 开放项 | 分类 | 证据入口与关闭条件 |
| --- | --- | --- |
| 图片预览新镜像/有窗体验证、新离线包 | 最终镜像历史数据重点回归与包 checker通过 | 10-14 来源82e50fff新包 checker5/0/0、四哈希与转存一致；10-15实际切换到其精确镜像，登录、召回图片、授权模型发布后的对话流和文件工作流 PASS。新包 tar load未做；新空数据项目不启动，真正离线目标验收另议 |
| 冷备与回退依据 | 本次切换前置已核验；恢复演练未做 | `/home/ctyun/BigData/.system-data/tmp/replay116-backup.XH7lLm/docker-data-config.tar`，13,639,835,648 字节；复算 SHA-256 `3a011abd2d8841b0a59e637cfde9b145ddc0a25f384aa14cd8caffa7f18148c9` 与原记录一致。历史 README 记载停机冷备；完整恢复未演练，且备份早于后续重索引。当前镜像已保留，四 API 挂载与迁移开关已核验；不授权恢复整库 |
| E01、E16、E18 | 历史 NOT_RUN 待映射 | [E01–E18 矩阵](UPGRADE_REHEARSAL_VALIDATION_2026-08-18.md)：默认加入工作区、OAuth 兼容、旧 session；尚未找到当前关闭证据，逐项按范围授权验证或由用户接受限制 |
| E02、E03、E07、E11、E14 | 历史 PARTIAL 待映射 | 同矩阵：注册/建工作区策略、管理员允许操作/邀请、登录安全回跳、离线插件、协作重连；已有局部通过不代替剩余场景 |
| E10 | 历史离线 PARTIAL 已有后续变化 | 旧全层扫描要求被最小门禁取代；最新图片修复包已生成且最小 checker PASS，但新包启动与真正离线目标验收未做，不恢复旧扫描为阻塞，也不将历史矩阵全项改为 PASS |
| E04/E05/E08/E09/E12/E13/E15/E17 | 历史 PASS，需来源对应 | 同矩阵的功能结果保留；后续 63/63 对账和应用回归见本页。最新代码、模型、镜像改变后只补受影响验收，不声称今天全项重跑 |
| 真正无外网目标机、registry/签名、部署及生产回退验证 | 外部条件/交付范围待定 | [旧 preflight](PRODUCTION_RELEASE_PREFLIGHT.md) 项目不是自动指令；最终交付方式、必须验证项和授权由用户确认，开发机模拟不代替真实目标 |
| 默认密码轮换、B9 会话管理 | 已接受延期 | [后续决定](DECISION_RISK_LEDGER.md)、[Design Gate](DESIGN_GATE.md)；独立加固/需求澄清，不作为本次自动阻塞 |
| B7/B8 已接受 P3、.ps1、旧 OCI 内容扫描、受保护 pattern | 已接受限制或独立范围待定 | [历史限制清单](FINAL_VALIDATION_SUMMARY.md) 与后续最小门禁决定合读；不全归为必须加固，不用开发证据把受保护审计改写为 PASS |
| 六实例清理、Skill 安装一致性、文档交付 | 治理事项 | 文档及错误分类已交付至远端实测 82e50fff；AGENTS 跨 harness Skill 要求与已跟踪 CLAUDE 链接已核验，未改 OpenCode 成果。replay Skill 先前按源提交 e8cb84506e5d14f0418a073a2b1811a736ac2727 完成三 harness 文件一致性核验，这是历史结果，不声称今天重新核验副本。实例清理仍未授权（CLEANUP_NOT_AUTHORIZED）；清理前须资格审计并处理 Code Reviewer 对 Builder 的依赖。本次补记待审阅，未授权提交/push |
| 1.16.1 候选线归属 | 用户待决 | Claude 2026-10-07 审计报告称远端 `codex/enterprise-candidate-1.16.1-20260728` 存在（SHA 前缀 `67e505d049bb`），这是外部复核记录，不是本轮 Codex 独立结论。本地 refs/对象未找到；2026-10-09 独立执行 `git ls-remote --exit-code origin refs/heads/codex/enterprise-candidate-1.16.1-20260728` 因无法连接服务器退出 128，远端存在性未重新核实。内容/维护归属仍待决，不得纳入、合并、删除或宣称替代本轮 |

## 新窗口最小恢复步骤

1. 按 DOCUMENT_INDEX 的换 harness 路线读取两个 Skill、本文、项目总纲、AGENTS 与当前任务证据；核对实际分支、HEAD/status及是否包含上述 checkpoint。远端读取须有相应网络权限；未查就标明未查。草稿来源不明或 Git 不符时停下核对，不自行修复。
2. 只读核对持久实例、worktree/分支、Agent 会话、controller 数量；多个 controller 即暂停治理操作。
3. 图片修复继续时读取最新 Architect 与 Code Review，不重读全部 B0–B8 或旧聊天。
4. 区分源代码、运行 image ID、数据状态、离线包来源 SHA；分别报告 PASS/FAIL/NOT_RUN。
5. 给出当前情况、下一步建议、仍有效授权和需要用户决策的边界；不得自动修复 Git 差异或连接生产。
