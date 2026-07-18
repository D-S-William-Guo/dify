# Enterprise 1.16.0 补丁决策矩阵

## 1. 判定规则

- `DROP_UPSTREAMED`：官方能力完整或旧代码仅重复官方行为，删除旧实现。
- `VERIFY_ONLY`：不重放代码，只保留回归用例或验收步骤。
- `KEEP_MINIMAL_PATCH`：官方覆盖主体，只补企业最小差距。
- `KEEP_REQUIREMENT_REIMPLEMENT`：业务需求仍存在，但按 1.16 架构重新实现。
- `DEFER`：现有证据不能形成安全、可测试的实现契约，且不阻塞升级。

任何 `KEEP_*` 都不授权 cherry-pick。旧提交和文件只提供需求、历史原因及测试样例。

## 2. 企业能力决策记录

### E01 企业默认工作区自动加入 — DROP_UPSTREAMED

- 企业业务需求：启用官方 Enterprise 服务时，新注册账号 best-effort 加入企业默认工作区；失败不能阻断注册。
- 旧实现提交和文件：旧候选把该能力列为业务基线；`api/services/enterprise/enterprise_service.py`、`api/services/account_service.py` 及相应单测已经位于官方 1.15 基线，并非候选新增补丁。
- 1.16 官方对应实现：`DefaultWorkspaceJoinResult`、`try_join_default_workspace`、`EnterpriseService.join_default_workspace`，以及 account 创建/注册调用点。
- 去留结论：删除任何平行实现；使用官方能力。
- 证据：当前文件调用 `/default-workspace/members`，1 秒超时、enterprise-disabled no-op、异常 soft-fail，官方单测覆盖成功/跳过/异常/注册失败路径。
- 风险：企业 inner API 未配置时只记录 warning；误把 soft-fail 改为事务失败会阻断注册。
- 实施任务：无业务代码；保留配置和运行验收。
- 前置依赖：有效 `ENTERPRISE_ENABLED`、Enterprise inner API URL/key、默认 workspace 配置。
- 单元测试：运行现有 `test_enterprise_service.py` 与 `test_account_service.py` 的 default workspace 用例。
- 集成验证：新账号注册后检查 enterprise API 调用、tenant join 幂等和当前 workspace 行为。
- volume 升级验证要求：旧账号/tenant join 数量不变；升级后新账号可加入默认 workspace，不批量修改历史 join。

### E02 注册和创建工作区策略 — KEEP_MINIMAL_PATCH

- 企业业务需求：企业发行物默认禁止公开注册和普通成员创建工作区，部署方可显式开启。
- 旧实现提交和文件：`d70f1c3bbd`；`api/configs/feature/__init__.py`、`docker/docker-compose.enterprise.yaml`、Web env。
- 1.16 官方对应实现：`ALLOW_REGISTER`、`ALLOW_CREATE_WORKSPACE`，`FeatureService` 和 `NEXT_PUBLIC_ALLOW_*` 已完整存在。
- 去留结论：不改官方 API/Web逻辑；企业 overlay 仅提供默认 `false` 并保证 API/Web 配置一致。
- 证据：1.16 `api/configs/feature/__init__.py`、`web/features/system-features/config.ts` 及 feature service 集成测试。
- 风险：仅设置后端或仅设置前端会产生“UI 允许、API 拒绝”或相反的不一致。
- 实施任务：在新 overlay/env 文档中映射官方变量，不新增同义变量。
- 前置依赖：E08 overlay。
- 单元测试：配置解析默认值与显式覆盖。
- 集成验证：注册页、邀请注册、workspace 创建按钮与 API 拒绝码一致。
- volume 升级验证要求：策略切换不能删除已有账号/workspace；旧 `.env` 缺变量时采用企业安全默认。

### E03 平台管理员 — KEEP_REQUIREMENT_REIMPLEMENT

- 企业业务需求：由 `PLATFORM_ADMIN_EMAILS` 授权跨 workspace 管理员，支持 workspace 列表/创建/重命名/归档、成员邀请/角色/移除、必要的密码重置和智慧广场审核。
- 旧实现提交和文件：`d70f1c3bbd`、`d83e4bb351`、`3f883e23b1`；`api/controllers/console/platform_admin.py`、`api/services/platform_admin_service.py`、`api/libs/platform_admin.py`、`web/.../platform-admin-page/`。
- 1.16 官方对应实现：普通 workspace/RBAC/member API 和生成契约存在；无 fork-local `platform-admin` endpoint 或 `PLATFORM_ADMIN_EMAILS`。
- 去留结论：保留需求，完全按 1.16 controller→service、显式 `Session`、Pydantic/生成契约、Jotai/bootstrap 重实现。
- 证据：旧候选提供 8 组 endpoint 与 service 测试；1.16 搜索无平台管理员实现；官方成员/RBAC 在 1.16 有权限和邀请状态修复。
- 风险：跨租户越权、owner/最后 workspace 破坏、密码重置缺审计、email 大小写授权、license seat 绕过、事务中途 commit。
- 实施任务：先定义权限模型与审计事件；实现纯授权 helper、session-injected service、DTO/controller、生成 contract、前端入口；删除危险操作或在安全评审后单独交付。
- 前置依赖：E15 migration 方案（若需审计表）、Console contract 生成链；Reviewer 先确认密码重置/归档需求。
- 单元测试：admin/non-admin、email 规范化、tenant scope、owner/last-workspace guard、seat limit、显式 session、rollback、DTO 错误码。
- 集成验证：跨 workspace CRUD、邀请 pending/active 账号、角色变更、当前 workspace 防删除、导航权限。
- volume 升级验证要求：已有 tenant/member/owner/current 标记不变；归档测试只用专用测试数据，禁止作用于迁移副本中的真实 workspace。

### E04 智慧广场后端 — KEEP_REQUIREMENT_REIMPLEMENT

- 企业业务需求：应用提交、本人提交列表、平台审核/拒绝/下架、已发布列表/详情，以及复制到调用者当前 workspace。
- 旧实现提交和文件：`d70f1c3bbd`；`api/controllers/console/enterprise_marketplace.py`、`api/services/enterprise_marketplace_service.py`、`api/models/model.py`、`c8f3d9d4a1be` migration。
- 1.16 官方对应实现：官方 plugin marketplace、recommended apps 和 DSL import/export 可复用，但无该企业资产/审核模型。
- 去留结论：按 1.16 架构重实现；状态机和历史字段作为需求输入，不复制 controller/service。
- 证据：旧 endpoint 覆盖 submit/list/get/use/review/unlist；`use_asset` 通过无 secret DSL export/import 复制。
- 风险：source app 跨租户泄漏、TOCTOU、发布后源 app 变化、secret 泄漏、依赖泄漏、重复提交、已删除 app、审核越权。
- 实施任务：定义不可变发布快照或明确“引用源 app”的产品语义；设计 owner-scoped 查询、状态机、审计、复制事务和依赖返回；进入 Console contract 生成。
- 前置依赖：E03 授权、E15 schema、产品确认发布快照语义。
- 单元测试：tenant scope、状态迁移、并发提交、source app 状态、无 secret export、复制目标 tenant、rollback、依赖泄漏列表。
- 集成验证：A workspace 提交→admin 审核→B workspace 查看/复制→新 app 可运行；拒绝/下架不可见。
- volume 升级验证要求：旧 `enterprise_marketplace_assets` 行数、状态、source IDs 和时间戳保持；对缺失 source app 的历史记录只隐藏/报告，不删除。

### E05 智慧广场前端与导航 — KEEP_REQUIREMENT_REIMPLEMENT

- 企业业务需求：app card 提交入口、智慧广场浏览/复制、平台审核页和导航可见性。
- 旧实现提交和文件：`d70f1c3bbd`、`76082745a8`、`dc8bf26789`；`web/app/components/explore/enterprise-marketplace/`、`submit-enterprise-marketplace-modal.tsx`、`web/service/use-enterprise-marketplace.ts`、`web/models/enterprise-marketplace.ts`、main nav。
- 1.16 官方对应实现：生成式 Console route/types、`consoleQuery`、Jotai account/permission state、新 main-nav route 结构。
- 去留结论：重实现 UI，不恢复手写 service/model 或旧 app context。
- 证据：1.16 提交 `93981cf75f`、`3ad06bebd9`、`61650d34ce` 及 Jotai 迁移系列。
- 风险：旧 API shape 导致 runtime 404/类型漂移；导航权限闪烁；硬编码文案；复制按钮重复提交。
- 实施任务：后端 contract 生成后实现 TanStack Query hooks、feature atoms、权限派生导航、所有 locale key 和行为测试。
- 前置依赖：E03、E04 contract 完成。
- 单元测试：route visibility、submit/review/use mutation、loading/error/empty、重复点击、i18n。
- 集成验证：平台 admin 与普通账号看到不同入口；深链刷新；跨 workspace 复制后跳转正确。
- volume 升级验证要求：使用迁移后的旧资产执行 UI 列表/详情/复制，不要求任何浏览器 localStorage 迁移。

### E06 企业会话管理 — DEFER

- 企业业务需求：来源清单只写“企业会话管理”，未说明是账号多设备会话、平台管理员强制下线、LLM conversation，还是 Agent shell/runtime session。
- 旧实现提交和文件：`1.15.0..旧候选` 无独立会话管理业务补丁；维护文档仅泛称 session-management refactor。
- 1.16 官方对应实现：已有 account sessions/OpenAPI、登录登出测试、Agent runtime sessions 和 shell session 管理，覆盖多个可能含义。
- 去留结论：不新增代码；先补产品契约。若仅指账号多设备会话则转为 `VERIFY_ONLY` 使用官方能力。
- 证据：旧候选搜索无专用 endpoint/model/UI；1.16 有 `api/controllers/openapi/account_sessions.py` 等官方路径。
- 风险：误解范围会新增高危全局踢下线能力，或与 Agent session 生命周期冲突。
- 实施任务：产品方给出 actor、对象、操作、审计、过期与验收用例；架构师再分类。
- 前置依赖：明确需求。
- 单元测试：延后；需求确认后至少覆盖 owner scope、token revocation 和幂等。
- 集成验证：延后；不得用 conversation 删除冒充账号 session 管理。
- volume 升级验证要求：升级不得清空账号 token/session、conversation 或 Agent runtime session；具体迁移待契约确认。

### E07 安装、登录和公开路由 — VERIFY_ONLY

- 企业业务需求：空库安装、登录/激活/邀请、公开 Web App 深链稳定且无开放重定向。
- 旧实现提交和文件：旧维护文档引用 `web/app/install/`、`web/app/signin/`、public context 和 fetch/service；旧候选未新增这些业务补丁。
- 1.16 官方对应实现：安装页测试、登录 redirect utility、OAuth/SSO redirect 修复和 open redirect 安全测试。
- 去留结论：不重放旧修复，只保留验证。
- 证据：官方 `c68e5e5ed3`、`e5b7281eb9`、`2c4d8ef098`；标签差异已大幅修改相关文件。
- 风险：企业导航/feature bootstrap 可能重新引入白屏或外部 redirect。
- 实施任务：新增企业 feature 之后扩展现有测试，不改官方 route 基线。
- 前置依赖：E03/E05 前端完成。
- 单元测试：redirect allow/deny、bootstrap、install form、invite activation。
- 集成验证：空库 `/install`→首次登录→`/apps`；同源回跳、恶意绝对 URL 拒绝、公开 route 深链。
- volume 升级验证要求：升级库应跳过 install；已登录 session 失效时安全回登录且不外跳。

### E08 Docker enterprise overlay — KEEP_REQUIREMENT_REIMPLEMENT

- 企业业务需求：保持官方 Compose 原文件不变，通过 overlay 覆盖企业镜像和企业默认变量。
- 旧实现提交和文件：`d70f1c3bbd`、`2699783f7a`、`06494810d0`；`docker/docker-compose.enterprise.yaml`。
- 1.16 官方对应实现：新增 agent_backend/local_sandbox，API/worker 新依赖，Web/Agent/env 变化，WebSocket worker 可配置。
- 去留结论：按 1.16 服务图重写最小 overlay；不得复制 1.15 YAML。
- 证据：官方 `docker/docker-compose.yaml` 的新服务/depends_on/env；Release upgrade guide 明示 customized Compose 必须重新审查。
- 风险：覆盖整个 service 会丢官方依赖或安全变量；api_websocket 使用官方镜像；agent key 不一致。
- 实施任务：只覆盖 api/worker/beat/websocket/web 的 image/build 和企业变量；用 `docker compose config` 比较合并结果。
- 前置依赖：E02、E03 配置名，官方镜像构建策略。
- 单元测试：YAML 静态断言或脚本检查服务 image/env/depends_on。
- 集成验证：本任务禁止启动 Docker；Builder 阶段执行 config、build、recreate 和 image ID 检查。
- volume 升级验证要求：overlay 不改变数据库、storage、Redis、plugin、vector、sandbox mount 目标；不得访问/复制 `docker/volumes` 于实现阶段。

### E09 企业 API/Web 镜像 — KEEP_MINIMAL_PATCH

- 企业业务需求：企业代码进入自建 `dify-api-enterprise:1.16.0-enterprise` 与 `dify-web-enterprise:1.16.0-enterprise`，所有 API runtime 使用同一 API image ID。
- 旧实现提交和文件：`d70f1c3bbd`、`06494810d0`；API/Web Dockerfile 和 overlay。
- 1.16 官方对应实现：官方 Dockerfile 与镜像 tag 已更新，Agent/contract/toolchain 构建内容变化。
- 去留结论：以官方 Dockerfile 为真，只补 image tag/build metadata；禁止恢复 1.15 Dockerfile。
- 证据：旧候选曾因 API/Web build context 漂移追加修复，说明复制 Dockerfile 风险高。
- 风险：api、worker、beat、websocket 镜像 ID 不一致；Web 生成契约缺失；COMMIT_SHA 不可追溯。
- 实施任务：最小 build args/labels，校验五个 runtime 的 image/tag/COMMIT_SHA。
- 前置依赖：E08。
- 单元测试：构建脚本参数与版本一致性检查。
- 集成验证：运行容器 inspect；浏览器验证必须针对本轮 image IDs。
- volume 升级验证要求：镜像重建不写入或打包 volumes；挂载必须指向 1.16 工作树/部署目录。

### E10 离线构建和镜像包 — KEEP_REQUIREMENT_REIMPLEMENT

- 企业业务需求：联网构建机产出完整 image tar、manifest、image list 和最小配置包，离线 Linux 使用完全相同的已验证镜像。
- 旧实现提交和文件：`d70f1c3bbd`、`2699783f7a`、`22d952089b`；`scripts/build-enterprise-offline.*`、config package scripts、部署说明。
- 1.16 官方对应实现：Compose 新增 agent backend/local sandbox 和 env 文件；官方不提供该 fork 的企业打包链。
- 去留结论：按新 Compose 解析并重实现，保留 `Mode=reuse` 可追溯原则。
- 证据：旧脚本通过两层 Compose `config --images` 解析，1.16 基础 Compose会自然加入新镜像，但 required-image 门禁/文档仍需更新。
- 风险：漏包 Agent 镜像、tag 存在但 ID 未验证、包内含 secret/volume、离线启动尝试 pull。
- 实施任务：manifest 记录版本/commit/image ID或digest；assert Agent 两镜像和企业五 runtime；配置包纳入新 env examples，排除 `.env`/volume/cache。
- 前置依赖：E08/E09、完整 runtime 验证。
- 单元测试：脚本 dry-run/fixture 测试，缺镜像/commit mismatch 必须失败。
- 集成验证：隔离网络目标 `docker load`、`config --images`、`up --pull never`、Agent/传统 app smoke。
- volume 升级验证要求：image/config archive 内容扫描不得含 `docker/volumes/**`；升级数据由运维独立备份/挂载，不由打包脚本复制。

### E11 插件离线安装 — KEEP_MINIMAL_PATCH

- 企业业务需求：受限网络/私有镜像源环境可安装 plugin，可信私有 `.difypkg` 有明确签名策略。
- 旧实现提交和文件：`b38235581a`；overlay 与 plugin daemon env 示例。
- 1.16 官方对应实现：官方 `PIP_MIRROR_AUTO_DETECT`、`PIP_MIRROR_URL`、本地 package 安装和签名校验。
- 去留结论：只透传官方变量和写验收，不建立平行 mirror/转发实现。
- 证据：旧维护文档已要求复用官方 knob；1.16 又含 plugin callback/cache/permission 修复。
- 风险：把 `PIP_INDEX_URL`/`UV_INDEX_URL` 强行等同可能破坏官方探测；默认关闭签名验证会降级安全。
- 实施任务：确认 1.16 plugin daemon 接受变量后最小映射；`FORCE_VERIFYING_SIGNATURE=false` 仅作为受控操作说明。
- 前置依赖：E08/E10。
- 单元测试：Compose 合并值和默认签名校验为 true。
- 集成验证：离线本地包、私有镜像依赖、失败签名、重启后已安装 plugin 可执行。
- volume 升级验证要求：保留 plugin daemon 持久化数据；核对已安装版本/权限/凭据，不复制进离线包。

### E12 Dataset 与 hit testing — VERIFY_ONLY

- 企业业务需求：数据集创建、索引、命中测试和高质量向量召回在升级后保持可用。
- 旧实现提交和文件：旧计划引用 dataset/hit-testing/vector 文件，但 1.15 候选没有对应业务代码差异。
- 1.16 官方对应实现：显式 session 重构、索引异常传播、RBAC、SQL 注入修复和大量 dataset tests。
- 去留结论：不重放旧源码；保留源测试和 runtime 验证。
- 证据：`31bb8abbf1`、`d9884efaee`，以及标签内 `test_hit_testing_service.py`/dataset controller tests。
- 风险：覆盖旧 vector 查询会回退 SQL 注入修复；只检查 Postgres 会漏掉 vector schema 丢失。
- 实施任务：只在失败用例证明官方仍有企业差距后另开补丁。
- 前置依赖：E15 数据升级、vector 服务可用。
- 单元测试：官方 hit testing、dataset session、metadata key validation。
- 集成验证：创建/索引/命中、权限隔离、索引异常可见。
- volume 升级验证要求：见 E13；Postgres 文档数与 vector class/collection 双向核对。

### E13 向量索引升级检查 — KEEP_REQUIREMENT_REIMPLEMENT

- 企业业务需求：检测“Postgres 有完成文档但 Weaviate/其他向量库缺 class/collection”的静默数据损坏，并提供受控修复。
- 旧实现提交和文件：`22d952089b`；`scripts/check-enterprise-vector-indexes.sh`。
- 1.16 官方对应实现：无等价企业升级脚本；vector provider/session API 已变化。
- 去留结论：保留需求，先实现 read-only 检查；repair 必须单独审批/任务。
- 证据：旧维护文档记录真实故障模式：知识页有数据但 hit testing 因 Weaviate 404 无结果。
- 风险：旧脚本假设旧 schema/class 命名；自动 repair 成本高且可能覆盖活跃索引。
- 实施任务：按 1.16 provider factory/collection naming 重写，默认只读、结构化输出；repair 做幂等、限流和审计。
- 前置依赖：确认支持的 vector stores；E15 升级完成。
- 单元测试：缺 class、空 dataset、低质量 dataset、provider error、read-only 不写。
- 集成验证：构造缺索引 fixture，先检测再经批准 repair，最后 hit testing 返回结果。
- volume 升级验证要求：在旧 volume 的只读副本/受控升级环境运行；本架构任务不访问、复制或修改 volume。

### E14 WebSocket 协作 — KEEP_MINIMAL_PATCH

- 企业业务需求：workflow collaboration 的 `api_websocket` 运行企业 API 代码且支持多 worker。
- 旧实现提交和文件：`2699783f7a`；overlay、offline scripts、启动文档。
- 1.16 官方对应实现：官方 Compose 已有 collaboration profile、可配置 worker amount，并修复多 worker collaboration（`e13271ba29`）。
- 去留结论：仅覆盖 `api_websocket` image/build；其余沿用官方。
- 证据：官方 service 使用 `langgenius/dify-api:1.16.0`，不覆盖会绕开企业代码。
- 风险：遗漏 profile 导致验证未启动；worker 配置回退硬编码；代理 upgrade header 不一致。
- 实施任务：overlay image 覆盖、offline required-image 断言、浏览器协作 smoke。
- 前置依赖：E08/E09。
- 单元测试：Compose config 中 websocket image 与 api 相同。
- 集成验证：两个浏览器协作、断线重连、多 worker、权限失败。
- volume 升级验证要求：WebSocket 不应修改持久化布局；迁移数据上的 workflow 打开/协作成功。

### E15 升级检查与 migration head — KEEP_REQUIREMENT_REIMPLEMENT

- 企业业务需求：官方 1.15、旧 1.15 企业候选和空库均能收敛到一个 1.16 企业 Alembic head，智慧广场数据保留。
- 旧实现提交和文件：`5f6219a16d`；`c8f3d9d4a1be`、`f1a14e1e9b41`、`e2f0a9b7c6d5`。
- 1.16 官方对应实现：官方 head `7a1c2d9e4b60`，从官方 1.15 实际新增 5 个 migration。
- 去留结论：审计重建历史 revision 可解析性，并新增 1.16 merge revision；不能复用旧 merge 作为新 head。
- 证据：旧企业 DB 的 `alembic_version` 可为 `e2f0a9b7c6d5`；删除旧 revision 会触发 “Can't locate revision”。
- 风险：多 head、重复建表、错误 stamp、三个 1.15 已存在 migration 在 1.16 被修改但不重跑。
- 实施任务：migration graph test；三条路径 upgrade（空库、官方 1.15、企业 1.15）；单 head 断言；禁止数据删除。
- 前置依赖：E04 最终 schema。
- 单元测试：Alembic heads/history、upgrade/downgrade 边界、已有表/数据保留。
- 集成验证：真实 PostgreSQL/MySQL 支持矩阵；升级后启动 API 并跑智慧广场/Agent/workflow smoke。
- volume 升级验证要求：先由运维备份；在隔离副本升级，记录前后 head、表/索引、行数/抽样哈希；绝不在本任务访问 `docker/volumes`。

### E16 OAuth 专用加密器 — DROP_UPSTREAMED

- 企业业务需求：系统 OAuth 参数可解密，且错误可定位。
- 旧实现提交和文件：`d70f1c3bbd`；`system_oauth_encryption.py` 及两个 service import。
- 1.16 官方对应实现：`system_encryption.py` 使用相同 SHA-256 key derivation、AES-CBC、随机 IV、PKCS padding 和 JSON 序列化。
- 去留结论：旧专用类行为等价，只增加重复全局状态；删除。
- 证据：两份实现的密文格式均为 `base64(iv + ciphertext)`，互相兼容。
- 风险：重放会产生两套错误类型/缓存实例并让后续安全修复分叉。
- 实施任务：无；可加一次兼容 fixture 验证后删除旧测试。
- 前置依赖：同一 `SECRET_KEY`。
- 单元测试：官方 encrypt/decrypt round-trip，加旧 fixture decrypt。
- 集成验证：迁移数据中的 builtin tool/trigger OAuth 凭据可用。
- volume 升级验证要求：不改密文、不轮换 `SECRET_KEY`；抽样只验证解密成功，不记录明文。

### E17 生成器 model mode 归一化 — KEEP_MINIMAL_PATCH

- 企业业务需求：prompt/code generator 面对 `agent-chat` 或 completion app mode 及旧 localStorage 时发送合法 `chat`/`completion` model mode。
- 旧实现提交和文件：`d70f1c3bbd`；`normalize-generator-model.ts`、automatic/code-generator 调用点和测试。
- 1.16 官方对应实现：相关组件已迁移 Vite+/TS/i18n 格式，但仍直接把 app mode cast 为 `ModelModeType`，未归一化。
- 去留结论：保留最小纯函数与聚焦测试，按 1.16 格式重写。
- 证据：当前 1.16 无 `normalizeGeneratorModel`；旧测试明确覆盖 agent app mode 和 stale `agent-chat` localStorage。
- 风险：直接复制旧测试会违反新 i18n/mock/toolchain；过度归一化可能掩盖未知 mode。
- 实施任务：先写纯函数参数化测试，再在读取、默认值、model change 和 API payload 边界统一调用；未知值选择 chat 的产品假设需记录。
- 前置依赖：无，独立任务。
- 单元测试：chat/completion/agent-chat/旧 completion/空值；两个 generator payload。
- 集成验证：创建 text generation、chat、传统 agent、Agent v2，打开生成器并执行一次。
- volume 升级验证要求：无数据库/volume 变化；保留浏览器 localStorage 作为升级输入验证。

### E18 旧 session 传递修复 — VERIFY_ONLY

- 企业业务需求：平台管理员成员查询/变更使用同一显式 session，事务可回滚。
- 旧实现提交和文件：`d83e4bb351`、`3f883e23b1`；`platform_admin_service.py` 和 tests。
- 1.16 官方对应实现：显式 session 已成为全局架构原则，但平台管理员本身不存在。
- 去留结论：不重放补丁代码；把用例作为 E03 的强制验收。
- 证据：1.16 `ab3e4daa95` 大范围 session propagation，repo 规则禁止 controller 新增 direct SQLAlchemy。
- 风险：新实现若再次使用 `db.session`，会重现旧 bug。
- 实施任务：E03 review checklist 加入 session ownership/commit/rollback。
- 前置依赖：E03。
- 单元测试：mock/SQLite session identity、rollback 后无部分写入。
- 集成验证：成员 invite/role/remove 与 workspace CRUD 事务一致。
- volume 升级验证要求：失败注入不得留下半完成 member join。

## 3. 旧企业候选提交逐项分类

以下每条均覆盖业务需求、旧文件、官方对应、结论、证据/风险、任务、依赖、测试和 volume 要求。

### C01 `d70f1c3bbd` feat: rebuild enterprise candidate 1.15.0 — KEEP_REQUIREMENT_REIMPLEMENT

- 业务/旧文件：混合提交，包含平台管理员、智慧广场、overlay、离线脚本、OAuth 重复抽象和生成器修复，共 57 文件。
- 官方对应/结论：1.16 架构大改；按 E02–E17 拆解，绝不 cherry-pick。
- 证据/风险：同一提交同时含应删除与应保留能力，机械重放会覆盖安全/contract/session 变化。
- 任务/依赖：Builder 按 E17→E15→E03/E04→E05→E08–E14 分任务；先 contract/schema，后 UI/部署。
- 测试/集成/volume：使用各 E 项测试；仅 E04/E13/E15 触及升级数据，必须走隔离副本验证。

### C02 `6970bd583b` docs: document enterprise upgrade data migration — VERIFY_ONLY

- 业务/旧文件：维护文档记录旧工作树数据继承与 volume 风险。
- 官方对应/结论：不复制旧文档；原则纳入 `VALIDATION_PLAN.md`。
- 证据/风险：运行数据不是源码；误提交/误覆盖 volume 风险极高。
- 任务/依赖：运维阶段准备备份和隔离副本；不属于 Builder 代码任务。
- 测试/集成/volume：执行前后 inventory/hash/head 检查；本任务不访问 volume。

### C03 `2699783f7a` fix: cover enterprise websocket startup — KEEP_MINIMAL_PATCH

- 业务/旧文件：overlay 覆盖 `api_websocket`，离线/启动文档包含 collaboration。
- 官方对应/结论：官方已有 service 与多 worker 修复，仅保留 image override 和验证，见 E14。
- 证据/风险：遗漏会让 websocket 跑官方 API image。
- 任务/依赖：E08/E09 后添加 Compose 静态断言。
- 测试/集成/volume：同 E14；无 volume 布局变化。

### C04 `c84cb7d9f5` docs: update refs and enterprise tool patches — KEEP_MINIMAL_PATCH

- 业务/旧文件：文档记录 OAuth 专用加密和生成器归一化。
- 官方对应/结论：文档本身丢弃；OAuth 按 E16 删除，生成器按 E17 最小保留。
- 证据/风险：把两个决策绑定会重放重复加密器。
- 任务/依赖：只创建 E17 独立 Builder 任务。
- 测试/集成/volume：生成器测试+OAuth 兼容抽样；不改 volume。

### C05 `b38235581a` fix: add uv mirror env vars — KEEP_MINIMAL_PATCH

- 业务/旧文件：plugin daemon overlay/env/启动文档。
- 官方对应/结论：透传 1.16 官方镜像源 knob，见 E11。
- 证据/风险：不应建立 `PIP_INDEX_URL`/`UV_INDEX_URL` 的平行契约或默认关签名。
- 任务/依赖：E08 后核对 plugin daemon 实际变量。
- 测试/集成/volume：本地包/私有源/签名失败；保留 plugin 数据。

### C06 `e0d417a164` docs: update enterprise candidate references — DROP_UPSTREAMED

- 业务/旧文件：只更新 1.15 候选名和版本描述。
- 官方对应/结论：由本轮五份 1.16 文档替代。
- 证据/风险：保留会传播过期分支/版本。
- 任务/依赖：无。
- 测试/集成/volume：文档链接检查；无 volume。

### C07 `76082745a8` fix: align enterprise frontend with 1.15 APIs — DROP_UPSTREAMED

- 业务/旧文件：调整旧平台管理员/智慧广场 UI 以适配 1.15 手写 API。
- 官方对应/结论：1.16 已迁移生成 contracts/Jotai，旧兼容修改全部丢弃；能力由 E03/E05 重实现。
- 证据/风险：复制会恢复手写 models/service 和旧组件 API。
- 任务/依赖：后端 contract 完成后从 1.16 UI 构建。
- 测试/集成/volume：E05；无直接 volume 变化。

### C08 `06494810d0` fix: align enterprise docker builds with 1.15 — VERIFY_ONLY

- 业务/旧文件：overlay build context 和 Web Dockerfile 修复。
- 官方对应/结论：不重放 1.15 Dockerfile；保留“build context/commit 必须可追溯”验收，见 E08/E09。
- 证据/风险：旧构建布局可能缺 1.16 contracts/Agent/monorepo packages。
- 任务/依赖：以官方 Dockerfile 做最小覆盖。
- 测试/集成/volume：build + COMMIT_SHA/image ID；不得加入 volume build context。

### C09 `5f6219a16d` fix: merge enterprise and 1.15 migration heads — KEEP_REQUIREMENT_REIMPLEMENT

- 业务/旧文件：新增 `e2f0a9b7c6d5` merge revision。
- 官方对应/结论：保留历史 revision 身份以升级旧库，再新增 1.16 merge，见 E15。
- 证据/风险：只复制旧 merge 会留下双 head；删除它会无法解析旧库。
- 任务/依赖：E04 schema 确定后实现图测试。
- 测试/集成/volume：三条数据库升级路径；隔离 volume 副本，不 stamp 跳迁移。

### C10 `d83e4bb351` fix: pass session to tenant member lookup — VERIFY_ONLY

- 业务/旧文件：平台管理员成员列表补 session。
- 官方对应/结论：不复制旧 service，作为 E03 显式 session 回归。
- 证据/风险：证明旧实现曾因隐式 session 出错。
- 任务/依赖：E03 service 测试。
- 测试/集成/volume：session identity/列表一致；只读验证不改 volume。

### C11 `dc8bf26789` fix: restore enterprise marketplace nav entry — KEEP_REQUIREMENT_REIMPLEMENT

- 业务/旧文件：main nav route、测试和 i18n。
- 官方对应/结论：导航需求保留，按 1.16 route/permission state 重写，见 E05。
- 证据/风险：旧入口曾在 API 对齐时丢失；需要权限和深链测试。
- 任务/依赖：E03/E04/E05。
- 测试/集成/volume：admin/normal route visibility；迁移资产可从入口访问。

### C12 `22d952089b` docs: add enterprise 1.15 upgrade checks — KEEP_REQUIREMENT_REIMPLEMENT

- 业务/旧文件：升级指南、vector index 检查脚本、配置包清单。
- 官方对应/结论：按 1.16 migration/Agent/offline 要求重写，见 E10/E13/E15。
- 证据/风险：旧脚本/API/schema 假设可能过期，但“关系库有数据、向量库为空”故障仍成立。
- 任务/依赖：先只读检查，再独立审批 repair。
- 测试/集成/volume：缺索引 fixture 和离线包内容扫描；在隔离 volume 副本验证。

### C13 `3f883e23b1` fix: pass session in platform admin flows — VERIFY_ONLY

- 业务/旧文件：平台管理员 workspace/member 写路径显式 session。
- 官方对应/结论：旧代码不重放；用例并入 E03/E18。
- 证据/风险：证明跨 service 事务边界是历史缺陷。
- 任务/依赖：E03 事务设计完成后测试失败回滚。
- 测试/集成/volume：invite/create/role 的单事务；失败不得污染升级数据。

### C14 `dd871a03ed` docs: localize enterprise upgrade guide — DROP_UPSTREAMED

- 业务/旧文件：1.14.2→1.15 指南中文化。
- 官方对应/结论：版本过期，由本轮 1.16 文档替代。
- 证据/风险：保留旧命令会使用错误 tag/head。
- 任务/依赖：无。
- 测试/集成/volume：仅文档审查；无 volume。

### C15 `b3af6ec907` docs: standardize enterprise upgrade terminology — DROP_UPSTREAMED

- 业务/旧文件：旧升级指南术语修订。
- 官方对应/结论：随旧指南一起丢弃。
- 证据/风险：无独立行为或测试价值。
- 任务/依赖：无。
- 测试/集成/volume：无。

## 4. 数量摘要

- `DROP_UPSTREAMED`：E01、E16；旧提交 C06、C07、C14、C15。
- `VERIFY_ONLY`：E07、E12、E18；旧提交 C02、C08、C10、C13。
- `KEEP_MINIMAL_PATCH`：E02、E09、E11、E14、E17；旧提交 C03、C04、C05。
- `KEEP_REQUIREMENT_REIMPLEMENT`：E03、E04、E05、E08、E10、E13、E15；旧提交 C01、C09、C11、C12。
- `DEFER`：E06，等待会话管理业务契约。
