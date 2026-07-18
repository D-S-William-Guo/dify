# Dify 1.16.0 官方发布分析

## 1. 分析边界与结论

- 实现基线：官方标签 `1.16.0`，提交 `5c6372d2f76d240265b92fd27c16bc772ffcb107`。
- 对比基线：官方标签 `1.15.0`，提交 `3aa26fb6374bbd47e5469f7d7cc25f3e0075a60c`。
- 标签差异规模：`8,708 files changed, 441,288 insertions, 362,271 deletions`。该范围包含大规模生成文件、格式化和依赖变化，不能按文件数量估算企业重放工作量。
- [官方 Release](https://github.com/langgenius/dify/releases/tag/1.16.0) 仅作为线索；本报告中的 migration、配置和代码结论均由上述两个标签的 Git 对象复核。
- 总结：1.16.0 不是可在旧企业树上做小幅 merge 的版本。Agent App、Console API 合约、前端状态、数据库 session 和工具链均已换代。企业能力只能从官方标签重新实现最小差距，禁止 cherry-pick 旧候选。

## 2. Agent App Beta、agent_backend 与 local_sandbox

Agent App 在 1.16.0 默认开启，`NEXT_PUBLIC_ENABLE_AGENT_V2=true` 取代 `ENABLE_AGENT_V2=false`。官方实现包含 Agent roster、Skills/文件、工作流 Agent v2 节点、Web App、sandbox 信息及 API/worker 到 agent backend 的运行协议。

关键实现证据：

- API 客户端与运行链：`api/clients/agent_backend/`、`api/core/app/apps/agent_app/`、`api/core/workflow/nodes/agent_v2/`。
- 前端：`web/features/agent-v2/`、`web/app/components/workflow/nodes/agent-v2/`。
- Agent 服务：`dify-agent/src/dify_agent/`；shell provider 在 1.16 中重构为适配器/协议层。
- Compose 新增 `agent_backend` 和 `local_sandbox`；`api`、`worker` 依赖 `agent_backend`。
- `agent_backend` 依赖 Redis、plugin daemon 和 local sandbox，且通过 `DIFY_AGENT_INNER_API_KEY` 调用 Dify inner API。该 key 必须匹配 `INNER_API_KEY_FOR_PLUGIN`，不能误用通用 `INNER_API_KEY`。
- `DIFY_AGENT_SERVER_SECRET_KEY` 用于 Agent Stub bearer token 的 JWE 派生；官方默认值只适合开发，生产必须替换。
- Landlock 加固见提交 [`71709f03c3`](https://github.com/langgenius/dify/commit/71709f03c3)，路径隔离默认开启；企业 overlay 不得关闭或放宽默认隔离。

企业影响：

1. 企业 API/Web 镜像必须保留官方 Agent App 源码和生成产物，不能从 1.15 Dockerfile 复制构建阶段。
2. 离线镜像包新增至少 `langgenius/dify-agent-backend:1.16.0` 和 `langgenius/dify-agent-local-sandbox:1.16.0`；最终清单以两层 Compose 的 `config --images` 为准。
3. 企业 overlay 只能覆盖企业 API/Web 镜像及必要企业变量，不能重写这两个官方服务的网络、依赖、healthcheck 或安全变量。
4. 验证必须覆盖 roster Agent、inline Agent、Agent Web App、工作流 Agent v2、shell/Skills 和失败清理；仅验证传统 Agent 节点不足以发布。

## 3. Docker Compose 与环境变量

标签代码对 `api/.env.example`、`web/.env.example` 和 `docker/envs/**/*.env.example` 的变量集合进行比较后，得到 28 个新增变量、1 个移除变量和 1 个默认值修改，与 Release 升级说明一致：

- 新增 28 个：4 个 `AGENT_BACKEND_*`、`API_WEBSOCKET_WORKER_AMOUNT`、13 个 `DIFY_AGENT_*`、2 个新用户默认插件/模型变量、`NEXT_PUBLIC_WORKFLOW_GENERATION_TIMEOUT_MS`、4 个 Redis keepalive 变量、`SHELLCTL_ENABLE_PATH_ISOLATION`、`WORKFLOW_GENERATION_TIMEOUT_MS`、`WORKFLOW_GENERATOR_NODE_BUILDER_MAX_WORKERS`。
- 移除：`ENABLE_AGENT_V2`。
- 修改：`NEXT_PUBLIC_ENABLE_FEATURE_PREVIEW` 从 `false` 改为 `true`。
- `NEXT_PUBLIC_ENABLE_AGENT_V2` 在 1.15 的 Web 示例中已经存在，但 1.16 将 Docker Web env 从旧 `ENABLE_AGENT_V2` 切换到它并默认开启，因此不计入“全局新增变量”。

Compose 还将 `API_WEBSOCKET_WORKER_AMOUNT` 从硬编码 `1` 改为可配置。企业 overlay 必须继续让 `api_websocket` 使用企业 API 镜像，否则协作路径会绕过企业补丁。

## 4. Database migrations：9、8 与实际代码

Release 的 “Database Migrations” 标题声称 9 个，实际只列出 8 个；Upgrade Guide 又写 8 个。标签差异给出第三个、更准确的事实：

- `1.15.0..1.16.0` **新增 5 个 migration 文件**：
  1. `a6f1c9d2e8b4`：sites 输入占位符。
  2. `e4f5a6b7c8d9`：Agent config drafts。
  3. `a2b3c4d5e6f7`：Agent backing app id。
  4. `c3d4e5f6a7b8`：Agent active config published 标记。
  5. `7a1c2d9e4b60`：workflow run archive bundle 索引表。
- Release 列表中的前三个 migration（`97e2e1a644e8`、`0b2f2c8a9d1e`、`b2515f9d4c2a`）已存在于 `1.15.0`，在 1.16 只修改了 migration 源码。
- 因此，从已经迁移到官方 1.15 head 的数据库升级时，Alembic 实际执行 5 个新增 revision；全新数据库会执行完整历史链，并使用上述三个文件的 1.16 最终内容。
- 官方 1.16 静态迁移链 head 为 `7a1c2d9e4b60`。本次尝试运行 `uv run --project api flask db heads` 时因受限网络无法下载锁定的 Git 依赖 `flask-restx` 而未完成；Builder 必须在依赖完整环境中再次执行该命令。

需要特别注意：三个已存在 migration 的 1.16 修改不会在已完成 1.15 migration 的数据库上重新执行。企业升级验证必须同时覆盖“旧企业数据升级”和“空库完整安装”，不能用其中一个替代另一个。

旧企业候选的 Alembic head 是 `e2f0a9b7c6d5`，它合并 `f1a14e1e9b41` 与官方 1.15 head `d9e8f7a6b5c4`。1.16 重放必须保留旧 revision 可解析性，并增加一个合并 `e2f0a9b7c6d5` 与 `7a1c2d9e4b60` 的新 revision；不得直接把旧库 stamp 到官方 head。

## 5. Console OpenAPI 合约与前端生成式路由/类型

1.16 将 Console API 迁移到 Pydantic/BaseModel 契约，并将前端路由、类型和 Zod schema 生成到 `@dify/contracts`。代表性提交：

- [`93981cf75f`](https://github.com/langgenius/dify/commit/93981cf75f)：Console contracts 迁移到生成式 routes。
- [`3ad06bebd9`](https://github.com/langgenius/dify/commit/3ad06bebd9)：前端迁移到生成 types。
- [`61650d34ce`](https://github.com/langgenius/dify/commit/61650d34ce)：删除自定义 Console contract loaders。

当前调用入口是 `web/service/client.ts` 的 `consoleClient` / `consoleQuery`，契约来自 `packages/contracts/generated/api/console/**`。旧智慧广场和平台管理员 controller 使用 `console_ns.schema_model`/手写返回 dict，前端使用 `web/models/*.ts` 与 `web/service/use-*.ts` 手写 API 类型；这些实现不得原样重放。

新企业 endpoint 必须：

1. 后端用 Pydantic request/response DTO，遵守 `api/controllers/API_SCHEMA_GUIDE.md`。
2. 进入 Console OpenAPI 生成流程，提交规范允许的生成产物，不手改生成文件。
3. 前端通过生成 route/type 和 `consoleQuery`/`consoleClient` 调用。
4. 为 schema 注册、权限错误和客户端类型增加契约测试。

## 6. 后端显式数据库 session

1.16 在大量 controller、service、task、RAG、workflow 和 account 路径显式传递 SQLAlchemy `Session`。代表提交包括 [`3f2ef24755`](https://github.com/langgenius/dify/commit/3f2ef24755) 和大范围的 [`ab3e4daa95`](https://github.com/langgenius/dify/commit/ab3e4daa95)。同时加入“controller 禁止新增直接 SQLAlchemy”规则。

旧平台管理员和智慧广场服务大量直接使用 `db.session`、`db.paginate`、模型属性隐式查询与内部 commit；这会破坏 1.16 的事务所有权和测试边界。新设计要求：

- controller 只校验请求、权限和序列化；不执行查询。
- service 通过构造器或关键字参数接收 `Session`，由调用者拥有事务。
- 跨表列表查询显式 tenant/owner scope，禁止依赖模型 property 发起隐式查询。
- App DSL 复制在同一明确事务中执行，并为异步/依赖检查定义提交边界。
- 旧提交 `d83e4bb351`、`3f883e23b1` 仅保留为“所有路径都必须传 session”的回归用例，不重放其代码。

## 7. Jotai 状态迁移

1.16 删除旧 `app-context-provider`/`app-context`，将账号、权限、workspace、system feature 和版本状态拆到 Jotai 原子与 bootstrap 边界。代表提交：`caf1a22020`、`d67123e5fd`、`94ba597d32`、`dce45ef6ae`、`503d80be1d`。

企业前端不得恢复旧 Context Provider，也不得把平台管理员/智慧广场状态塞入全局 app context。建议：

- server state 使用 `consoleQuery` + TanStack Query；
- 当前账号的 `is_platform_admin` 进入现有 account/permission bootstrap 状态；
- 仅跨同一 feature 组件共享的 UI 状态使用 feature-owned Jotai atoms；
- 导航可见性从权限派生，不用全局事件或重复 fetch。

## 8. TypeScript、Vite 与 ESLint

- TypeScript 原生预览：`@typescript/native` 指向 `typescript@7.0.2`；普通 `typescript` catalog 指向 TypeScript 6 兼容包。
- Vite+：`vite-plus@0.2.5`，`vite` 映射到 `@voidzero-dev/vite-plus-core@0.2.5`。
- ESLint：`10.7.0`，主检查为 `vp check && pnpm lint:eslint`，并启用更严格规则。
- 代表提交：`512f39dede`（TypeScript 7）、`6ac7ff6586`/`2a008423d8`（Vite+）、`eb71e47f3b`（lint 迁移）。

旧企业前端存在宽泛 dict、手写 models、旧 i18n 调用和旧格式；Builder 必须按 1.16 类型/格式重写，不能用 `any`、类型断言或 ESLint suppression 掩盖不兼容。

## 9. Workflow、HITL、Plugin 与 Dataset

需要以官方实现为默认并保留其测试：

- HITL 主逻辑从 graphon 迁回 Dify：[`f4ec608ef4`](https://github.com/langgenius/dify/commit/f4ec608ef4)；恢复响应状态等修复见 `10da5e8f9d`。
- 多 worker workflow collaboration：`e13271ba29`；重试详情：`7dc3126ff4`；暂停/恢复 stream state：`d72ee32ba1`。
- Plugin provider cache stampede：[`200f8b800f`](https://github.com/langgenius/dify/commit/200f8b800f)；marketplace callback：[`f816ae2e95`](https://github.com/langgenius/dify/commit/f816ae2e95)；权限设置：`4303103304`。
- Dataset/RAG：文档索引错误不再吞掉（[`31bb8abbf1`](https://github.com/langgenius/dify/commit/31bb8abbf1)）、批量删除不再死循环（[`089c3f4af0`](https://github.com/langgenius/dify/commit/089c3f4af0)）、多模态 segment 索引修复等。

旧候选在这些目录没有形成可独立证明仍需要的业务补丁，除生成器 model mode 归一化外一律先 `VERIFY_ONLY`，不得将 1.13/1.15 的 workflow、HITL、plugin 或 dataset 文件覆盖到 1.16。

## 10. Authentication、RBAC 与成员管理

- 开放重定向修复：[`c68e5e5ed3`](https://github.com/langgenius/dify/commit/c68e5e5ed3)，集中到登录重定向校验并补 E2E。
- OAuth/SSO redirect state：`82ff93cbdd`、`2c4d8ef098`；保持同部署跳转：`e5b7281eb9`。
- 编辑者禁止管理成员：`faaa4708a6`；trace config 要求 edit 权限：[`0035d90e36`](https://github.com/langgenius/dify/commit/0035d90e36)。
- 成员邀请状态与生成契约：[`323654afe2`](https://github.com/langgenius/dify/commit/323654afe2)、[`509a8b1452`](https://github.com/langgenius/dify/commit/509a8b1452)。
- Dataset/app RBAC migration 与 scope 修复：`528bf95d1b`、`5ce13d1773`、`7e05f28a46`、`7dfd84472f`。

平台管理员重实现必须在这些规则之上增加独立授权，不得通过伪造 workspace role、修改 current tenant 或复用普通成员 endpoint 绕过 1.16 RBAC。删除、重置密码、转移 owner 等高风险操作必须有独立审计与明确 scope。

## 11. 安全修复不可回退清单

| 领域 | 官方证据 | 企业重放门禁 |
| --- | --- | --- |
| SQL 注入 | [`d9884efaee`](https://github.com/langgenius/dify/commit/d9884efaee)，MyScale metadata key 校验 | 禁止旧 vector/hit-testing 查询覆盖；非法 metadata key 测试必须通过 |
| SSRF | [`ae0d6ee214`](https://github.com/langgenius/dify/commit/ae0d6ee214)，API tool schema fetch 改走 SSRF helper | 智慧广场/复制不得增加原始 `httpx.get` 或任意 URL fetch |
| 开放重定向 | `c68e5e5ed3` | 登录/公开路由只保留同源或允许的相对跳转 |
| Sandbox plan | [`38aec8b506`](https://github.com/langgenius/dify/commit/38aec8b506)、[`7311f1ba6d`](https://github.com/langgenius/dify/commit/7311f1ba6d) | 企业公开路由不得绕过 workflow_id/plan 检查 |
| Landlock | `71709f03c3` | overlay 和离线示例不得默认关闭路径隔离 |
| 依赖 CVE | Release 列出的 httplib2、setuptools、wandb、python-engineio/socketio、fickling、pillow、click | 不恢复 1.15 lockfile/Docker 层 |
| Owner scope | `62cb5b5865` | 智慧广场 source app、tenant、reviewer 查询必须显式 scope |

## 12. 离线部署新增要求

离线发布不再只有 API/Web、plugin daemon、sandbox 和数据库镜像。Builder 必须：

1. 用 1.16 官方 Compose 加企业 overlay 解析完整镜像集合。
2. 显式确认镜像清单包含 `dify-agent-backend:1.16.0`、`dify-agent-local-sandbox:1.16.0`、企业 API/Web、plugin daemon、sandbox、ssrf proxy 及选用的数据库/vector 服务。
3. 在联网构建机预拉取并保存依赖镜像；离线目标使用 `--pull never`。
4. 配置包包含新增 `dify-agent.env.example`、`local-sandbox.env.example` 和安全 env 示例，但不包含真实 secret、`.env` 或 `docker/volumes/**`。
5. `Mode=reuse` 只能导出已经通过同一轮 runtime 验证的镜像 ID；manifest 同时记录 tag、digest/image ID 和构建提交。
6. 对私有 `.difypkg` 的签名策略沿用官方 `FORCE_VERIFYING_SIGNATURE`，只在明确可信的私有包场景关闭，且必须重建/recreate plugin daemon；不能把关闭签名校验写成默认值。

## 13. 官方变化的重放结论

- Agent App、workflow/HITL/plugin/dataset、auth/RBAC 与安全修复：以官方代码为准，旧同类补丁 `DROP_UPSTREAMED` 或 `VERIFY_ONLY`。
- Console contract、显式 session、Jotai、TypeScript/Vite/ESLint：是企业重实现的强制架构边界。
- Docker/offline：保留企业需求，但按 1.16 Compose 服务图重写。
- migration：以 5 个实际新增 revision 作为 1.15→1.16 执行预期，同时兼容旧企业 `e2f0a9b7c6d5` head。
