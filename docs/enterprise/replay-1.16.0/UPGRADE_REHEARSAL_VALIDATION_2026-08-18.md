# 1.15.x → 1.16.0 本地升级验收矩阵

日期：2026-08-18 至 2026-08-19（Asia/Shanghai）
范围：开发机真实历史数据升级；不是生产/灰度部署。
候选：`c65e3a9445`，运行 image：`dify-api-enterprise:1.16.0-enterprise`、`dify-web-enterprise:1.16.0-enterprise`、Agent backend/local sandbox `1.16.0`。

## 已验证基础

- 旧运行容器停止后，实际 bind mount 复制到 1.16.0 目录：1.15 的 storage/PostgreSQL/Redis/plugin/certbot，1.14.2 的 Weaviate/sandbox dependencies；旧目录未改动。
- API、PostgreSQL、Redis、local sandbox 均 healthy；最终 `alembic_version = e7c0a9d2b8f3`。
- 迁移后核心计数：accounts 3、tenants 5、apps 6、datasets 4；Weaviate ready。
- 授权的历史管理员账号成功登录；历史 workspace、5 个应用、知识库、Agents beta、智慧广场和平台管理员导航均可见。
- 浏览器证据位于 `output/playwright/replay-116-upgrade/`：`signin-loading.png`、`platform-admin-workspaces.png`、`enterprise-marketplace.png`、`datasets.png`、`chat-started.png`、`historical-chat-result.png`。截图和日志不得包含凭据。
- 已在本机工作空间完成模型切换验证：OpenRouter 首次尝试的证据为 `openrouter-defaults-saved.png`、`knowledge-models-saved.png`；随后当前默认 LLM 改为 Tongyi `qwen3.7-plus`，该知识库明确使用 Tongyi `text-embedding-v4` 与 `qwen3-rerank`，证据为 `knowledge-tongyi-models-saved.png`。
- 两份历史文档已通过 Dify 官方重试完成真实重建，页面完整重载后均显示“可用”；分段数复核为 2 和 61。Dify worker 已确认该 dataset collection/schema 可用，且浏览器“召回测试”实际返回 HTTP 200。

## 重放任务状态

| ID | 当前验证 | 状态 | 后续最小验收 |
| --- | --- | --- | --- |
| E01 默认工作区 | 历史 workspace 可见；未创建专用新账号 | NOT_RUN | 隔离账号注册后验证 best-effort join，不改变历史 tenant join |
| E02 注册/建 workspace 策略 | 登录 UI 与导航正常 | PARTIAL | 隔离账号验证 register/create 的 UI/API 一致拒绝或显式允许 |
| E03 平台管理员 | 已用迁移管理员账号打开工作区列表，显示 5 个历史 workspace | PARTIAL | 专用测试 workspace 验证 7 条允许 route、non-admin 403、owner 保护；不改真实 workspace |
| E04 智慧广场后端 | 页面正常，当前 workspace 无已发布资产 | PARTIAL | 专用 A/B workspace 执行 submit→review→copy；验证快照和无 secret DSL |
| E05 智慧广场前端 | 导航和空列表正常 | PARTIAL | 随 E04 验证提交、审核、复制、深链与权限视图 |
| E06 会话管理 | 需求仍为 `DEFER` | DEFER | 获得产品契约后另开任务 |
| E07 登录/公开路由 | 历史账号登录成功；历史 Web App 可打开并创建会话；当前 `qwen3.7-plus` 对话流已在预览中得到直接回复 | PARTIAL | 另测安全回跳与公开深链；旧模型绑定问题见 E17 |
| E08 Compose overlay | 本机 1.16.0 Compose 解析、数据挂载和启动通过 | PASS | 生产前以实际主机挂载重做只读核对 |
| E09 企业镜像 | 运行 API/worker/beat/websocket 均为 enterprise 1.16.0，Web 为 enterprise 1.16.0 | PASS | 发布前比对离线 manifest 与目标 `docker load` image ID |
| E10 离线包 | 本机离线包可重建；配置/manifest/image 清单复扫通过 | PARTIAL | Docker 29 非压缩层导致真实 pattern 的 layer scan `NOT_RUN`，修复扫描器后重跑 |
| E11 插件离线安装 | 历史 Tongyi plugin 存储被读取，schema 与 invoke dispatch 均 200 | PARTIAL | 用受控 `.difypkg` 验证离线安装、签名失败和重启后执行 |
| E12 知识库/hit testing | 两份历史文档已用 Tongyi embedding 重建并在完整页面重载后显示可用；浏览器混合检索 hit-testing 返回 HTTP 200，reranker 配置已保存 | PASS | 发布前用同一受控查询复核命中数；不记录文档正文 |
| E13 向量检查器 | Weaviate ready；worker 的 collection/schema 调用成功；两文档均 completed，分段总数 63，真实 hit-testing 成功 | PASS | 发布前比对目标机的 dataset、collection 与分段计数 |
| E14 WebSocket 协作 | `api_websocket` 已使用 enterprise 1.16.0 image | PARTIAL | 两浏览器编辑同一专用 workflow，验证协作与重连 |
| E15 migration graph | 真实旧企业 head 经 merge 迁移至唯一最终 head | PASS | 保留本次迁移日志、前后计数和 image identity |
| E16 OAuth 加密兼容 | 未对真实 OAuth 凭据做调用 | NOT_RUN | 经授权用无敏感 fixture 验证旧密文解密和 builtin tool 调用 |
| E17 generator model mode | 已通过本机 Dify UI 将历史聊天、Agent、文本生成应用和工作流的显式 `qwen3.6-plus` 绑定迁至 `qwen3.7-plus` 并发布；三项应用受控重跑成功；历史工作流以普通文本 fixture 实测文档提取、变量传递和 LLM 输出，返回“水果是苹果” | PASS | 生产前按模型绑定清单逐项迁移；保留工作流的单次、1 秒间隔失败重试 |
| E18 旧 session 传递 | 新登录 session 正常；未复用升级前浏览器 cookie | NOT_RUN | 在升级前保存、升级后恢复专用浏览器 state，验证安全刷新与回跳 |

## 模型提供方记录：已解除知识库阻塞

历史“聊天助手-测试”和“Agent测试”均成功完成 Web UI → API → plugin daemon schema → plugin LLM invoke。它们的无敏感受控问答，以及历史“文本生成应用”的 completion，原先均以 `completion_request_error: Incorrect API key provided` 结束（浏览器证据：`historical-chat-model-error.png`）。历史“工作流测试”原先以临时无敏感文本文件运行，文件上传与文档提取器节点 succeeded，随后 LLM 节点以相同旧模型凭据错误结束（浏览器证据：`historical-workflow-model-error.png`）。这些应用和工作流均显式固定为 `qwen3.6-plus`，不会随工作区默认模型切换到 `qwen3.7-plus`。经授权，已通过本机 UI 显式改为 `qwen3.7-plus` 并逐项发布；聊天、Agent、文本生成和工作流均以相同受控输入重跑成功，证据为 `historical-chat-qwen37-pass.png`、`historical-agent-qwen37-pass.png`、`historical-text-qwen37-pass.png`、`historical-workflow-qwen37-pass.png`。工作流还以普通文本 fixture 复验：文档提取器文本变量已进入 LLM 提示，用户可见输出正确返回“水果是苹果”（证据：`historical-workflow-qwen37-file-content-pass.png`）。期间两次调用在 300 秒时由上游 DashScope 读取超时；本机同模型对话流即时成功，故将工作流 LLM 失败重试设为一次、间隔一秒，而非将其归因为升级或文件链路故障。

## 当前模型绑定兼容矩阵

| 实际绑定 | 自动化证据 | 结论 |
| --- | --- | --- |
| `qwen3.7-plus` | 当前对话流以“请只回复 OK”运行；历史文件工作流以普通文本 fixture 成功返回预期正文 | PASS |
| `qwen3-32b` | 历史 chatflow 以同一提示运行，工作流成功并直接回复 `OK` | PASS |
| `qwen3.6-plus` | 历史文本生成、聊天、Agent 及工作流原先均到达 plugin daemon/LLM 节点后返回旧凭据错误；已显式迁移至 `qwen3.7-plus` 并发布 | MIGRATED |

发布/升级指导必须包含此检查：默认模型切换不会重写已保存应用或 workflow 节点的 `provider`/`model`；先导出模型绑定清单，再逐项保留对应凭据或显式迁移到已验证模型。

OpenRouter embedding 首次重建曾两次返回 HTTP 403，故不将其记为升级回归。切换为 Tongyi embedding/reranker 后，首次重试曾有一批 embedding 请求在 300 秒读取超时；同一官方重试接口再次执行后，两份文档均 completed、错误字段清空。该过程证明存储属主修复、插件 dispatch、Qwen embedding、Weaviate 写入和混合检索均已在本机真实运行。

后续完成 E07 的受控 LLM 回复，以及 E04/E05 的可运行副本和 E14 协作 workflow。每行必须附浏览器截图、脱敏日志时间窗、运行 image ID 和 PASS/NOT_RUN/BLOCKED 原因。
