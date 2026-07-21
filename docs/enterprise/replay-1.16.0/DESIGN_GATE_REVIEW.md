# Dify Enterprise 1.16.0 Design Gate 审查记录

## 1. 审查基线与提交

- 审查分支：`ctyun/replay-116-gate-reviewer`
- 审查 HEAD：`e776629ef44f7f26ed92d8c6d51c66b86cd76b6f`
- 审查提交：`docs: record enterprise 1.16.0 design gate`
- Gate Reviewer-2 PASS 基线：`ffdd19e523077c1a51b7d59618ab92bafb0c706e`
- 变更范围：`ffdd19e523..e776629ef4`
- 审查日期：2026-07-21
- 审查者：Gate Reviewer

## 2. 实际变更文件清单

| 状态 | 文件 |
| --- | --- |
| A | `docs/enterprise/replay-1.16.0/DESIGN_GATE.md` |
| M | `ENTERPRISE_REPLAY_PLAN.md` |
| M | `docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md` |
| M | `docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md` |
| M | `docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md` |

变更统计：5 files, +208 −56

## 3. DG-01～DG-09 逐项结论

### DG-01 智慧广场

**结论：PASS**

DESIGN_GATE.md §3 DG-01（第 24–37 行）明确记载“审核通过/正式发布时生成不可变快照”，包含 12 条完整规则：提交保留 `source_app_id`、发布生成无 secret DSL 快照、保存版本/内容哈希/冻结时间/来源、复制只使用已审核快照、源应用修改/删除不影响发布版本、更新必须重新提交审核版本化、快照禁止凭据/密钥/私有插件凭据/不可跨 workspace 资源、旧数据回填规则、丢失/异常标记待处理、旧 `source_app_id` 保留为审计信息、复杂回填为独立可重试有 inventory 的数据迁移。

该决定在 ENTERPRISE_REPLAY_PLAN.md §2.9、ARCHITECT_HANDOFF.md §3.4、PATCH_DECISION_MATRIX.md E04、VALIDATION_PLAN.md Phase G 智慧广场中一致重复，无分歧措辞。

### DG-02 平台管理员首版

**结论：PASS**

DESIGN_GATE.md §3 DG-02（第 40–43 行）明确记载首版范围：身份判断、全局 workspace 查询、workspace 成员查询、基础邀请和成员管理、tenant scope/owner/最后 owner/最后 workspace/seat limit 保护、允许操作的测试和日志。明确延期：密码重置、workspace 强制归档/删除、需要新审计表的高风险操作及 break-glass。B3 首版不新增 audit model。

该决定在 ARCHITECT_HANDOFF.md B3、PATCH_DECISION_MATRIX.md E03 延期范围、VALIDATION_PLAN.md Phase G 平台管理员段中一致。E03 原先描述"workspace 列表/创建/重命名/归档、密码重置"已在本次提交中变更为精简首版范围。

### DG-03 企业会话管理

**结论：PASS**

DESIGN_GATE.md §3 DG-03（第 46–48 行）明确记载：本轮继续 `DEFER`；若仅指账号多设备 session 则沿用官方 1.16 并标记 `VERIFY_ONLY`；账号登录 session、conversation、Agent shell/runtime session 必须概念隔离；产品契约截止 B6 开始前，超时则不进入本轮代码范围。

该决定在 ENTERPRISE_REPLAY_PLAN.md §3、ARCHITECT_HANDOFF.md §3.10/§8.6、PATCH_DECISION_MATRIX.md E06 中一致，且本次提交补充了 PATCH_DECISION_MATRIX.md E06 概念边界说明。

### DG-04 候选分支与远端

**结论：PASS**

DESIGN_GATE.md §3 DG-04（第 50–52 行）明确记载：本地候选分支 `codex/enterprise-candidate-1.16.0-20260718` 已确认从官方 1.16.0 / `5c6372d2` 开始；Gate Reviewer 通过后推送到 `D-S-William-Guo/dify`；禁止向 `langgenius/dify` 创建企业 PR。

该约束在 ENTERPRISE_REPLAY_PLAN.md §1、ARCHITECT_HANDOFF.md §1、DESIGN_GATE.md §7 中一致。

### DG-05 数据库与向量库

**结论：PASS**

DESIGN_GATE.md §3 DG-05（第 54–57 行）明确记载：发布阻断组合为 PostgreSQL + Weaviate；必须完整验证旧企业 PostgreSQL 数据升级、migration 单一 head；MySQL 为条件验证、不是当前本地发布阻断项、不得声称本轮已完成 MySQL 兼容验证；PostgreSQL 18 验证保留；数据库大版本升级和 Dify 应用升级默认分开演练。

该决定在 VALIDATION_PLAN.md Phase D 兼容矩阵（MySQL 两行从"必须运行"改为"条件运行"）、PATCH_DECISION_MATRIX.md E15 集成验证、ENTERPRISE_REPLAY_PLAN.md §7 中一致。

### DG-06 Agent App

**结论：PASS**

DESIGN_GATE.md §3 DG-06（第 60–62 行）明确记载：沿用官方 1.16 实现、不重放企业平行实现；先对可信内部用户受控验证 `agent_backend`、`local_sandbox`、Landlock、secret 和 retention；local sandbox 默认不持久化；Agent run retention 初始使用官方 3 天；全面开放由运行验收后决定。

该决定在 ARCHITECT_HANDOFF.md §8.9/§8、VALIDATION_PLAN.md Phase G Agent App Beta 和 §3 retention/sandbox 条款中一致。

### DG-07 CAN_REPLACE_LOGO

**结论：PASS**

DESIGN_GATE.md §3 DG-07（第 64–66 行）明确记载：不修改官方源码默认 `false`；企业 Compose overlay 显式设置 `CAN_REPLACE_LOGO=true`；普通官方配置验证为 `false`，企业 overlay 展开后验证为 `true`。

该决定在 ARCHITECT_HANDOFF.md B6 logo 段、PATCH_DECISION_MATRIX.md E08 实施任务、VALIDATION_PLAN.md Phase E CAN_REPLACE_LOGO 检查项中一致。VALIDATION_PLAN.md 原先表述"未覆盖时最终值为官方 1.16 默认 `false`"已在本次提交改为"必须保持官方 1.16 默认 `false`"的强制表述。

### DG-08 首版离线交付范围

**结论：PASS**

DESIGN_GATE.md §3 DG-08（第 68–72 行）明确记载：支持 Linux amd64、PostgreSQL、Weaviate、Docker Compose、企业 API/Web 镜像、官方 `agent_backend`/`local_sandbox` 镜像、插件离线安装和 `Mode=reuse` 离线包。不承诺多 CPU 架构、全部 vector store、MySQL 发布阻断支持、Kubernetes、在线构建目标机器或 sandbox 永久共享存储。

该决定在 ENTERPRISE_REPLAY_PLAN.md §7、ARCHITECT_HANDOFF.md §8.7、PATCH_DECISION_MATRIX.md E10 不支持/不承诺 中一致。本次提交在 E10 新增了明确的不支持/不承诺条款。

### DG-09 Reviewer-2 补充

**结论：PASS**

DESIGN_GATE.md §3 DG-09（第 74–78 行）明确记载：`api/configs/enterprise/__init__.py` 在 B3/B6 仅作只读参考；B3 首版不新增 model；B3 handoff 必须列出 controller/route/DTO/schema 和测试；Agent App 文档中 API 路径均为期望路径、须与生成 OpenAPI 对齐、不得描述为已实现的事实。

该补充在 ARCHITECT_HANDOFF.md B3/B4/B6 read-only 引用、VALIDATION_PLAN.md Phase G Agent App 场景表路径表述中一致。本次提交将 VALIDATION_PLAN.md Agent App 场景表中的路径明确标注为"期望"并加了"（须与生成 OpenAPI 对齐）"限定语。

## 4. 文件范围与受保护文件检查

### 受保护文件（逐字未变）

| 文件 | 检查结果 |
| --- | --- |
| `docs/enterprise/replay-1.16.0/ARCHITECT_REVIEW.md` | 逐字未变（`git diff --shortstat` 无输出） |
| `docs/enterprise/replay-1.16.0/ARCHITECT_REREVIEW.md` | 逐字未变 |
| `docs/enterprise/replay-1.16.0/OFFICIAL_RELEASE_ANALYSIS.md` | 逐字未变 |

### 禁止修改类别检查

| 类别 | 检查结果 |
| --- | --- |
| 业务代码（`api/`、`web/`） | 无变更 |
| Docker 配置（`docker/`） | 无变更 |
| migration 文件 | 无变更 |
| 依赖（lockfile、packages） | 无变更 |
| volume（`docker/volumes/`） | 无访问、无变更 |
| 真实 `.env` 或 secret | 无变更 |
| 版本号或构建产物 | 无变更 |

变更范围严格限于本次允许修改的四份现有文档（ENTERPRISE_REPLAY_PLAN.md、ARCHITECT_HANDOFF.md、PATCH_DECISION_MATRIX.md、VALIDATION_PLAN.md）和新增的 DESIGN_GATE.md，共 5 份文件，无越界变更。

## 5. 矛盾与残留措辞检查

### 5.1 状态一致性

- DESIGN_GATE.md: `DESIGN_GATE_APPROVED_PENDING_RECORD_REVIEW`
- ENTERPRISE_REPLAY_PLAN.md: `DESIGN_GATE_APPROVED_PENDING_RECORD_REVIEW`
- ARCHITECT_HANDOFF.md: `DESIGN_GATE_APPROVED_PENDING_RECORD_REVIEW`
- PATCH_DECISION_MATRIX.md: 无独立状态字段，但所有决定已锚定到 Design Gate
- VALIDATION_PLAN.md: `DESIGN_GATE_APPROVED_PENDING_RECORD_REVIEW`

一致通过。

### 5.2 Builder 授权

DESIGN_GATE.md §5 明确仅授权 B0 和 B1；§6 明确 B2～B9 暂不启动。ENTERPRISE_REPLAY_PLAN.md §5 确认"当前阶段只授权 B0 和 B1。B2～B9 均不得启动"。ARCHITECT_HANDOFF.md §5 确认"当前阶段仅授权 B0/B1"。一致通过。

### 5.3 B2 只读 inventory 门禁

DESIGN_GATE.md §6 完整列出 B2 启动前 inventory 要求（Alembic head、marketplace 表结构/行数/状态/`source_app_id`、源应用正常/删除/异常数量、核心对象计数、PostgreSQL 版本、Weaviate class/index、运行镜像和 Compose 配置身份），明确 inventory 未完成时 B2 禁止启动。

该门禁在 ENTERPRISE_REPLAY_PLAN.md B2、ARCHITECT_HANDOFF.md B2、PATCH_DECISION_MATRIX.md E15 B2 启动门禁、VALIDATION_PLAN.md §1 B2 启动前只读 inventory 中一致。

### 5.4 计划测试未冒充已运行

VALIDATION_PLAN.md §1 明确声明"本文所有测试均为计划项，不代表已经运行通过"；Phase D 兼容矩阵标注"以下均为待执行计划"；Phase G Agent App 场景表标注"并非已经实现的事实"。所有测试描述使用"必须""将""应""期望"等未来语气，无任何声称已执行通过。一致通过。

### 5.5 MySQL 条件验证

DG-05 明确 MySQL 为条件验证，VALIDATION_PLAN.md Phase D 兼容矩阵将 MySQL 从"必须运行"改为"条件运行"，PATCH_DECISION_MATRIX.md E15 集成验证明确"本轮不得声称已完成 MySQL 兼容验证"。残留的"必须运行"描述已清除，无矛盾。

### 5.6 残留措辞检查

- ARCHITECT_HANDOFF.md §8 "未决问题"段在本次提交中替换为"Design Gate 已决事项与剩余截止项"——正确反映了人工决定已封闭。
- FIX-01 复审方法从"确认 Builder 前 Gate 结论"更新为"确认仅 B0/B1 获启动授权"——与当前授权状态一致。
- FIX-17 从"MySQL 空库与企业升级均必须运行"更新为"改为条件验证"——与 DG-05 一致。
- FIX-18 明确"保持 `CAN_REPLACE_LOGO=false` 官方默认，企业 overlay 显式 `true`"——与 DG-07 一致。
- PATCH_DECISION_MATRIX.md E10 新增不支持/不承诺条款——与 DG-08 一致。
- ENTERPRISE_REPLAY_PLAN.md §2.7 补充更多 migration 细节——不改变设计决定。
- ARCHITECT_HANDOFF.md B6 Read-only reference 新增 `api/configs/enterprise/__init__.py`（只读）、B3 实施任务加入该引用——与 DG-09 一致。

未发现残留的"推荐""建议""待产品确认""未决""Design Gate 待定"等不定措辞。所有原待定项已明确更新为已决。

## 6. 阻断项

### 阻断项 B1：文件范围记录歧义（DESIGN_GATE.md §9 第 122 行）

**严重级别：CHANGES_REQUIRED**

DESIGN_GATE.md 第 122 行原文：

> Gate Reviewer 仅复审本次允许修改的五份现有文档和新增 `DESIGN_GATE.md`

按字面解读，"五份现有文档 + 新增 DESIGN_GATE.md"等于 6 份。但 `ffdd19e523..e776629ef4` 实际变更仅为：

| 类型 | 文件 | 份数 |
| --- | --- | --- |
| 修改的现有文档 | `ENTERPRISE_REPLAY_PLAN.md`、`ARCHITECT_HANDOFF.md`、`PATCH_DECISION_MATRIX.md`、`VALIDATION_PLAN.md` | 4 |
| 新增文档 | `DESIGN_GATE.md` | 1 |
| **合计** | | **5** |

实际为 4 份现有文档 + 1 份新增文档 = 共 5 份。DESIGN_GATE.md 第 122 行的"五份"应改为"四份"，或改写为"共计五份（其中四份为现有文档修改，一份为新增）"以避免歧义。

该行属于 DESIGN_GATE.md，不在 Reviewer 可修改范围内。需由 Gate Recorder 整改后重新提交 Gate Reviewer 复审。

> 注：本审查文件（DESIGN_GATE_REVIEW.md）初版第 121、169 行同样存在"五份现有文档"的错误表述，已在本次纠正提交中修正为"四份现有文档和新增 DESIGN_GATE.md，共 5 份文件"。这部分属于 Reviewer 自查自纠，不是阻断理由。

## 7. 最终结论

**CHANGES_REQUIRED**

DG-01～DG-09 逐项审查全部通过，各项决定在所有文档间一致、忠实记录人工批准决定。受保护文件逐字未变。无业务代码、Docker、migration、依赖、volume、真实 .env 或 secret 变更。无计划测试冒充已运行通过。状态一致为 `DESIGN_GATE_APPROVED_PENDING_RECORD_REVIEW`，仅 B0/B1 获授权，B2 inventory 门禁完整。

唯一阻断项为 DESIGN_GATE.md 第 122 行"五份现有文档"与实际 4 份现有文档修改的数量歧义（§6 阻断项 B1），需 Gate Recorder 整改。DG-01～DG-09 内容决定本身无异议，整改不涉及重新批准 Gate 决定。

**需 Gate Recorder 整改：**
- **文件**：`docs/enterprise/replay-1.16.0/DESIGN_GATE.md`
- **位置**：第 122 行
- **问题**："五份现有文档"与实际 4 份现有文档修改不符
- **建议**：改为"四份现有文档"或"共计五份（其中四份为现有文档修改，一份为新增）"
