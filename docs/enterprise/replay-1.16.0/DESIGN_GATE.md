# Dify Enterprise 1.16.0 Design Gate

## 1. Gate 记录

- Gate 日期：2026-07-21
- 状态：`DESIGN_GATE_APPROVED_PENDING_RECORD_REVIEW`
- 批准者：Repository owner / human gate
- 人工批准声明：Repository owner / human gate 已批准本文件记录的 DG-01～DG-09。本文忠实记录最终决定，不授权记录者重新讨论、扩大或改变决定。

## 2. 基线、候选分支与审查链

- 官方基线：`1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`
- 本地候选分支：`codex/enterprise-candidate-1.16.0-20260718`
- 候选分支起点：已确认为官方 1.16.0 / `5c6372d2f76d240265b92fd27c16bc772ffcb107`
- Architect 初稿：`4fa0d53d49b9a77123e0c152e55a2c9262189c15`
- Reviewer：`caedca07e4938e8460c755b9ba37293d59417c8c`
- Architect 整改：`2af616e7e2de1939431b51b4521e6bf2b580be47`
- Reviewer-2 PASS：`ffdd19e523077c1a51b7d59618ab92bafb0c706e`

## 3. DG-01～DG-09 最终决定

### DG-01 智慧广场

采用“审核通过/正式发布时生成不可变快照”。

1. 提交阶段保留 `source_app_id`。
2. 审核通过/发布时生成不含 secret 的 DSL 快照。
3. 保存快照版本、内容哈希、冻结时间和来源信息。
4. 用户复制时只使用已审核快照。
5. 源应用后续修改不影响已发布版本。
6. 更新广场内容必须重新提交、重新审核、产生新版本。
7. 源应用删除后，已发布快照仍应可复制。
8. 快照禁止保存凭据、密钥、私有插件凭据或不可跨 workspace 资源。
9. 旧数据升级时，对仍存在的源应用生成无密钥快照。
10. 源应用丢失或异常的旧资产不得猜测数据，必须标记待处理或下架。
11. 旧 `source_app_id` 继续保留为来源和审计信息。
12. 复杂快照回填不得塞入普通 schema migration；必须设计为独立、可重试、有 inventory 和失败恢复的数据迁移步骤。

### DG-02 平台管理员首版

首版保留平台管理员身份判断、全局 workspace 查询、workspace 成员查询、基础邀请和成员管理，以及 tenant scope、owner、最后 owner/最后 workspace、seat limit 保护；同时交付允许操作的测试和日志。

首版延期密码重置、workspace 强制归档或删除、需要新审计表的高风险操作及 break-glass 紧急接管。B3 首版不新增 audit model；若后续恢复高风险操作，必须建立独立任务，重新设计并审查审计 model、migration、权限、恢复和通知机制。

### DG-03 企业会话管理

本轮继续 `DEFER`。若最终需求仅为账号多设备 session，则沿用官方 1.16 实现并标记 `VERIFY_ONLY`。账号登录 session、conversation 与 Agent shell/runtime session 必须保持概念隔离。产品契约截止 B6 开始前；超时则不进入本轮代码范围。

### DG-04 候选分支与远端

本地候选分支为 `codex/enterprise-candidate-1.16.0-20260718`，已确认从官方 1.16.0 / `5c6372d2` 开始。Design Gate 记录通过 Gate Reviewer 后，候选分支推送到用户 fork `D-S-William-Guo/dify`。禁止向 `langgenius/dify` 创建企业 PR。

### DG-05 数据库与向量库

当前发布阻断组合为 PostgreSQL + Weaviate。必须完整验证旧企业 PostgreSQL 数据升级、migration 单一 head、智慧广场数据与快照回填、用户/workspace/应用/工作流/知识库/插件、Weaviate class/index、hit testing 及完整备份恢复回滚。

MySQL 为条件验证，不是当前本地发布阻断项，不得声称本轮已经完成 MySQL 兼容验证。未来若对外交付声明支持 MySQL，再将 MySQL 空库和升级测试提升为必须运行。PostgreSQL 18 验证保留；数据库大版本升级和 Dify 应用升级默认分开演练。

### DG-06 Agent App

沿用官方 1.16 实现，不重放企业平行实现，保持官方服务结构和安全边界。先对可信内部用户受控验证 `agent_backend`、`local_sandbox`、Landlock、secret 和 retention；local sandbox 默认不持久化；Agent run retention 初始使用官方 3 天；是否全面开放在运行验收后决定。

### DG-07 CAN_REPLACE_LOGO

不修改官方源码默认 `false`。企业 Compose overlay 显式设置 `CAN_REPLACE_LOGO=true`；普通官方配置验证为 `false`，企业 overlay 展开后验证为 `true`。

### DG-08 首版离线交付范围

支持 Linux amd64、PostgreSQL、Weaviate、Docker Compose、企业 API/Web 镜像、官方 `agent_backend`/`local_sandbox` 镜像、插件离线安装和 `Mode=reuse` 离线包。

本轮不承诺多 CPU 架构、全部 vector store、MySQL 发布阻断支持、Kubernetes、在线构建目标机器或 sandbox 永久共享存储。

### DG-09 Reviewer-2 补充

1. `api/configs/enterprise/__init__.py` 在 B3/B6 仅作只读参考；不修改官方源码默认，企业行为由 B6 overlay 环境变量控制。
2. B3 首版不新增 model；高风险操作若需要审计 model，必须创建独立任务并重新审查。
3. B3 handoff 必须列出 controller、route、DTO、schema 和测试；B4 在 B3 已合并代码上负责 import、注册和最终 contract generation。
4. Agent App 文档中的具体 API 路径均为期望路径，每个路径都须与生成 OpenAPI 对齐，不得描述为已经实现的事实。

## 4. 批准、延期与不支持范围

明确批准：DG-01 不可变发布快照；DG-02 首版低风险平台管理范围；PostgreSQL + Weaviate 发布阻断组合；官方 Agent App 受控验证；企业 overlay 显式启用 logo 替换；DG-08 列出的首版离线交付范围；B0 和 B1 启动。

明确延期：平台管理员密码重置、workspace 强制归档/删除、需要新审计表的高风险操作、break-glass；企业会话管理；Agent App 全面开放决定。

明确不支持或不承诺：多 CPU 架构、全部 vector store、MySQL 作为当前本地发布阻断支持、Kubernetes、目标机器在线构建、sandbox 永久共享存储，以及任何未经重新审查的高风险平台管理员操作。

## 5. Builder 阶段授权

Design Gate 记录通过 Gate Reviewer 后，仅授权启动：

- B0：基线、安全护栏、文件所有权/diff 检查。
- B1：生成器 model mode 最小修复。

B2～B9 暂不授权启动。此授权不允许提前实施 migration、数据修复、业务代码、Docker overlay 或离线交付变更。

## 6. B2 只读 inventory 前置门禁

B2 启动前必须完成旧 1.15 数据库和 volume 的只读 inventory，至少记录：

- 实际 Alembic head；
- `enterprise_marketplace_assets` 表结构、行数和状态分布；
- `source_app_id` 是否仍存在；
- 源应用正常、删除、异常数量；
- tenant/member/app/workflow/dataset/document/plugin 计数；
- PostgreSQL 版本；
- Weaviate class/index inventory；
- 运行镜像和 Compose 配置身份。

只读 inventory 不授权 migration、修复或修改 volume。inventory 未完成或证据不完整时，B2 保持禁止启动。

## 7. PR 与远端安全约束

Gate Reviewer 通过本记录后，候选分支仅可推送到用户 fork `D-S-William-Guo/dify`。禁止向 `langgenius/dify` 创建企业 PR；禁止以 merge、rebase、reset、cherry-pick 或历史改写改变已确认的官方基线与审查链。

## 8. 决策变更流程

任何改变 DG-01～DG-09、Builder 授权、支持矩阵或远端约束的请求，都必须建立独立决策记录，说明变更原因、影响范围、数据与安全风险、migration/回滚/验证变化，并重新经过人工 Design Gate 与相应 Reviewer。Builder 不得通过实现细节、测试记录或临时运维操作隐式改变本决定。

## 9. Gate Reviewer 复审范围

Gate Reviewer 仅复审本次允许修改的五份现有文档和新增 `DESIGN_GATE.md` 是否忠实、一致地记录人工决定；确认 `ARCHITECT_REVIEW.md`、`ARCHITECT_REREVIEW.md` 与 `OFFICIAL_RELEASE_ANALYSIS.md` 逐字未变；确认未修改业务代码、Docker、migration、依赖、版本、volume、真实 `.env` 或 secret；确认状态为 `DESIGN_GATE_APPROVED_PENDING_RECORD_REVIEW`、仅 B0/B1 获授权、B2 inventory 门禁完整，且没有把计划测试写成已经运行通过。
