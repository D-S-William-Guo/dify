# Dify Enterprise 1.16.0 重放最终验证总结

更新时间：2026-08-14（Asia/Shanghai）

本文件是 B0–B8 重放与 Phase D/F/G/H 运行验证的最终总结，对应发布门禁决策单 G3/G4/G6 的落地输出。数据来源：`DECISION_RISK_LEDGER.md` 与 `/tmp/replay-116-final-gate-decision-sheet.md`。

## 1. 候选状态与 origin 一致性

| 项 | 值 |
| --- | --- |
| 候选分支 | `codex/enterprise-candidate-1.16.0-20260718` |
| 候选 HEAD | `83e1bd5418d645bc72929cb3b517c1fda5cd01fc` |
| origin | `83e1bd5418d645bc72929cb3b517c1fda5cd01fc`（本地 HEAD == origin，一致） |
| 官方基线 | `1.16.0` = `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| Alembic 唯一 head | `e7c0a9d2b8f3`（parent `b416e5c4e702`，Phase G 修复后） |

## 2. 已完成门禁总览（B0–B8）

| 门禁 | 内容 | 状态 | 证据 |
| --- | --- | --- | --- |
| B0 | 企业重放护栏（scope 检查 + guardrail） | ✅ 43 scope tests PASS；B0_REREVIEW_2 PASS | `evidence/phase-b/checker-fixture-tests.log`、`B0_REREVIEW_2.md` |
| B1 | Generator model mode 归一化 | ✅ 纯函数 + 组件测试 PASS；B1_REREVIEW PASS | `B1_REREVIEW.md` |
| B2 | Migration 历史恢复 + 只读 inventory | ✅ 16 migration graph tests PASS；B2_REVIEW PASS | `B2_REVIEW.md`、`evidence/phase-d/migration-graph-tests.log` |
| B3 | 平台管理员后端 | ✅ 精确 7 条 route；service/controller 测试 PASS | `B3_REVIEW.md` |
| B4 | 智慧广场后端 + schema + contracts | ✅ 398/398 PASS；contracts 两次 deterministic；B4_FINAL_REREVIEW PASS（0/0/0） | `evidence/phase-b/focused-backend.log`、`evidence/phase-c/contracts.log`、`B4_FINAL_REREVIEW.md` |
| B5 | 企业前端全链 | ✅ 295/295 PASS；type-check/i18n PASS；B5_FINAL_REVIEW PASS（0/0/0） | `B5_FULL_REGRESSION_REPORT.md`、`B5_FINAL_REVIEW.md` |
| B6 | Enterprise Compose overlay | ✅ overlay 74 行；Phase E 静态断言 S-1..S-9 PASS | `evidence/phase-e/compose-config.log`、`B6_REVIEW.md` |
| B7 | 离线 artifact chain | ✅ 21/21 fixture PASS；reuse gate 已加固 | `B7_REVIEW.md`、`B8_REUSE_GATE_REVIEW.md` |
| B8 | Vector checker + 发布验证准备 | ✅ 47/47 fixture；backend 158 passed；migration graph 61 passed | `evidence/vector-checker/`、`B8_REVIEW.md` |

## 3. 运行验证门禁（Phase D/F/G/H + reuse gate 加固）

| 阶段 | 内容 | 状态 | 证据 |
| --- | --- | --- | --- |
| Phase D | 真库升级矩阵 + 回滚 | ✅ 6/6 PASS + 备份/恢复回滚演练 | `evidence/phase-d/**` |
| Phase E | Compose 静态验证 | ✅ S-1..S-9 PASS | `evidence/phase-e/compose-config.log` |
| Phase F | 镜像构建 + 容器身份 | ✅ PASS（2026-08-11）；2026-08-14 从候选 HEAD 重建 PASS | `evidence/phase-f/**`、`evidence/phase-f-rebuild/**` |
| Phase G | 运行验收（install/login/platform-admin/Workflow/WebSocket/Agent 12 场景/浏览器/E2E/secret） | ✅ PASS；2 个 release-blocking bug 已修复 + Rereview PASS | `evidence/phase-g/**` |
| Phase H | 离线链 load + `--pull never` smoke | ✅ 第一轮 FAIL（离线镜像缺 Phase G 修复）；重建镜像 + 加固 gate 后 rerun **PASS**（fresh DB head `e7c0a9d2b8f3`，12 列 uuid） | `evidence/phase-h/**`、`evidence/phase-h-rerun/**` |
| B7 reuse gate 加固 | 拒绝同 tag 过期镜像内容漂移 | ✅ 只读内容核对（migration 文件集 + `_align_snapshot_to_composition`）接入 reuse/smart/CheckOnly 路径；fixture 测试全 PASS | `B8_REUSE_GATE_REVIEW.md`、`evidence/phase-f-rebuild/reuse-gate.log`、`evidence/phase-h-rerun/reuse-gate-checkonly.log` |

### 关键运行结果

- **Phase G 修复**：GPH-01 marketplace schema 类型不匹配 → 新 migration `e7c0a9d2b8f3`（ID/FK 列 `VARCHAR(36)` 改 `uuid`）；GPH-02 agent 绑定 knowledge 后对话失败 → `request_builder.py` 快照对齐。Rereview PASS，两个 release-blocking finding 关闭。
- **Phase H rerun（2026-08-14）**：B7 reuse gate 接受新 API image `sha256:566bdf4c88cf...`；manifest `enterprise_commit = c7c98b22`；fresh PG15 迁移 head `e7c0a9d2b8f3`（非 `b416e5c4e702`）；marketplace ID/FK 12 列全 `uuid`；nginx 18080 / api `/health` / web `/webpage/signin` smoke 全 200；`--pull never` 无 pull；check-offline 13 PASS / 0 FAIL / 1 NOT_RUN；teardown 无残留。

## 4. 证据路径

- `docs/enterprise/replay-1.16.0/evidence/phase-a/` — B0 静态范围
- `docs/enterprise/replay-1.16.0/evidence/phase-b/` — B0/B4/B8 单元/契约
- `docs/enterprise/replay-1.16.0/evidence/phase-c/` — B4 contracts 生成
- `docs/enterprise/replay-1.16.0/evidence/phase-d/` — Phase D 真库升级矩阵 + 回滚演练
- `docs/enterprise/replay-1.16.0/evidence/phase-e/` — Phase E Compose 静态验证
- `docs/enterprise/replay-1.16.0/evidence/phase-f/`、`phase-f-rebuild/` — Phase F 镜像构建/身份 + 候选 HEAD 重建
- `docs/enterprise/replay-1.16.0/evidence/phase-g/` — Phase G 运行验收（browser 截图、Agent 12 场景、secret 扫描）
- `docs/enterprise/replay-1.16.0/evidence/phase-h/`、`phase-h-rerun/` — Phase H 离线链（首轮 FAIL + rerun PASS）
- `docs/enterprise/replay-1.16.0/evidence/vector-checker/` — B8 vector checker

## 5. 已接受已知限制（G4，生产发布声明必须写明）

1. 真离线 Docker host（无外网）load + boot 未验证（同一 daemon 模拟）。
2. 镜像 bundle 层内 secret 扫描 NOT_RUN（Docker 29 OCI blob 布局，B7 门禁未覆盖）。
3. 真实受保护 secret pattern 未提供；只用 synthetic pattern。
4. `.ps1` 运行时 NOT_RUN（无 pwsh）；B7R-05 BOM 风险保持。
5. agent_backend 停止时返回 400 含 raw transport message（非 503）；无 crash，恢复正常。
6. inline agent（workflow agent-composer 节点）仅 API 未跑通（需 UI 路径）。
7. 迁移 dataset 的向量 class 对齐未验证（生产 Weaviate 数据在禁止路径）；新 dataset hit-testing PASS。
8. plugin remote-debug（5003）NOT_RUN。
9. B9 企业会话管理保持 DEFER。
10. completeness 两脚本未授权，人工审计兜底。
11. B7R-03..06、B8R-01/02/03、B8RGR-01/02 已接受 P3。

## 6. 最终结论（G6）

> 代码与验证闭环完成：静态/单元/契约/真库升级/镜像身份/运行验收/离线链均已通过（在记录的同一 daemon 与 synthetic-pattern 限制下）。生产发布仍须走正式发布流程：受保护 secret 扫描、真离线机验证、正式镜像签名/审计、独立环境部署演练。
