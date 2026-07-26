# Dify Enterprise 1.16.0 Replay B2 独立审查报告

## 1. 结论

**PASS**

本结论仅确认 Builder commit 在 B2 授权范围内正确恢复三个历史 migration、增加
一个无操作的 1.16 merge revision，并提供 focused migration graph test。它不
等于授权执行真实数据库 migration、运行时升级、B3、B4、生产升级或生产发布。

## 2. 审查身份、基线与前置核验

- 身份：独立 B2 Reviewer，不是 Builder
- 审查分支：`ctyun/replay-116-b2-reviewer`
- Builder commit：`b4df8cb6862964f94c9a5cf0f0c9bf90b1908440`
- 审查基线：`f41970d01058155c3f01ee500c23da4abc0a3cbd`
- 权威历史 ref：`origin/codex/enterprise-candidate-1.15.0-20260626`
  （本地解析为 `4ecce9483fd6d34ae4b4dd7ccfd93ec9c58aee30`）
- 前置核验：分支与 HEAD 精确匹配要求；`git status --short` 无输出，工作区干净
- 完整阅读：
  - `ARCHITECT_HANDOFF.md`
  - `PATCH_DECISION_MATRIX.md`
  - `VALIDATION_PLAN.md`
  - `B2_INVENTORY.md`
  - `B2_INVENTORY_REVIEW.md`

前置核验后未执行 merge、rebase、reset、cherry-pick 或 push。

## 3. 文件范围审计

命令：

```bash
git diff --name-status \
  f41970d01058155c3f01ee500c23da4abc0a3cbd..b4df8cb6862964f94c9a5cf0f0c9bf90b1908440
git diff --stat \
  f41970d01058155c3f01ee500c23da4abc0a3cbd..b4df8cb6862964f94c9a5cf0f0c9bf90b1908440
git diff --check \
  f41970d01058155c3f01ee500c23da4abc0a3cbd..b4df8cb6862964f94c9a5cf0f0c9bf90b1908440
```

结果：仅新增以下五个文件，共 305 行；`git diff --check` 退出 0。

1. `api/migrations/versions/2026_04_30_2100-c8f3d9d4a1be_add_enterprise_marketplace_assets.py`
2. `api/migrations/versions/2026_05_19_2000-f1a14e1e9b41_merge_1_14_2_enterprise_heads.py`
3. `api/migrations/versions/2026_06_27_1145-e2f0a9b7c6d5_merge_1_15_0_enterprise_heads.py`
4. `api/migrations/versions/2026_07_21_1000-a71e16c0de01_merge_1_16_0_enterprise_heads.py`
5. `api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py`

未修改 models、services、controllers、contracts、Web、Docker、volume 或文档；
未出现范围外业务代码、生成物或运行数据。

## 4. 三个历史文件真实性

对每个文件同时执行本地 `sha256sum`、权威 ref 内容的 SHA-256，以及本地
`git hash-object` 与权威 ref blob ID 比较。三组 blob ID 完全相同，证明完整
文件字节一致，不只是字段或语义相似。

| revision | SHA-256（本地与权威 ref） | Git blob（本地与权威 ref） | 结论 |
| --- | --- | --- | --- |
| `c8f3d9d4a1be` | `1b58dedab633906c444aa326372ab9c701274009eac506b9d579a8fcdf1c264b` | `2bc25428fb67cf946ca4e5b6cd1854c04ebca416` | 逐字节一致 |
| `f1a14e1e9b41` | `9fb231dd5e1caedc199dd9e219da5b6f09373e1851a4e4150f91b6dd441736c1` | `ae7085e4e6c194697b47a8850db82b48eba21285` | 逐字节一致 |
| `e2f0a9b7c6d5` | `f49b863cf24522bd8ae7f16bc9095398048383caab9838f4f8e898ba762ec7fe` | `80392d8e5ec05f68c886f6dbc96851e80b44d78f` | 逐字节一致 |

因此以下内容均未改变：

- `revision`、`down_revision`、`branch_labels`、`depends_on`
- `upgrade()`、`downgrade()`
- `c8f3d9d4a1be` 的表、16 列、默认值、主键、唯一约束和两个索引
- 两个历史 merge 的无操作语义

恢复文件的 DDL 兼容性风险没有被 B2 重新设计或掩盖；B2 的要求是保持既有
历史身份和语义，逐字节相同满足该边界。

## 5. 1.16 空 merge 审查

文件：
`api/migrations/versions/2026_07_21_1000-a71e16c0de01_merge_1_16_0_enterprise_heads.py`

独立静态与 AST 检查确认：

- `revision = "a71e16c0de01"`
- `down_revision = ("e2f0a9b7c6d5", "7a1c2d9e4b60")`
- `branch_labels = None`
- `depends_on = None`
- `upgrade()` 和 `downgrade()` 的 AST 函数体均精确为一个 `pass`
- import 数为 0
- 不含 `op`、SQLAlchemy、原始 SQL、DDL 或数据迁移
- `a71e16c0de01` 在全部 migration 文件中只定义一次
- `b416e5c4e702` 的 revision 定义为 0，未被创建或引用

## 6. Alembic migration graph

### 6.1 独立 ScriptDirectory 证据

在不连接数据库的进程中，使用真实 Alembic `Config` 和
`ScriptDirectory.from_config()` 扫描当前工作树的 `api/migrations`。由于本
工作树没有 1.16 锁定虚拟环境，进程内只为历史 migration 导入所需的
`models.types`、`models.enums`、`constants.UUID_NIL` 和
`libs.uuid_utils.uuidv7` 提供最小无 I/O 占位；没有替换 Alembic 图解析。

结果（退出 0）：

```text
heads=a71e16c0de01
enterprise_chain=c8f3d9d4a1be->f1a14e1e9b41->e2f0a9b7c6d5->a71e16c0de01
official_chain=7a1c2d9e4b60->a71e16c0de01
required_ancestry=all_present
b416e5c4e702_present=false
```

解析到的关键关系：

```text
227822d22895 -> c8f3d9d4a1be --\
                                      f1a14e1e9b41 --\
a4f2d8c9b731 -------------------/                    \
                                                          e2f0a9b7c6d5 --\
d9e8f7a6b5c4 ----------------------------------------/                    \
                                                                              a71e16c0de01
7a1c2d9e4b60 ---------------------------------------------------------------/
```

结论：

- 三个历史 revision 均可被 ScriptDirectory 解析。
- `c8f3d9d4a1be → f1a14e1e9b41 → e2f0a9b7c6d5` 关系正确。
- 旧企业 head 与官方 1.16 head 精确汇合到 `a71e16c0de01`。
- 当前唯一 head 是 `a71e16c0de01`。
- 两个起点都能汇合，所需历史 ancestry 完整。
- 当前 B2 head 不是未来 B4 head `b416e5c4e702`。

### 6.2 Flask CLI 尝试

按要求从 `api/` 目录尝试：

```bash
ALL_PROXY= all_proxy= \
  /home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/api/.venv/bin/flask db heads
ALL_PROXY= all_proxy= \
  /home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/api/.venv/bin/flask db history
```

两条命令均退出 1，未得到 CLI graph 输出。原因是借用的 1.15 环境与当前
1.16 源码依赖不匹配：加载应用时
`PauseReasonType.LEGACY_HUMAN_INPUT_REQUIRED` 不存在。命令在应用导入阶段
失败，未执行 migration，也未连接或修改真实数据库。

## 7. Focused test 质量与实际结果

### 7.1 测试质量

审查结论：

- 测试通过真实 Alembic `ScriptDirectory` 扫描完整 migration 目录，不是只
  验证自定义常量。
- 常量作为外部期望值，与 ScriptDirectory 解析出的实现图比较；未发现“实现
  与测试复用同一自定义图而同时写错仍通过”的明显自证式缺口。
- 有效覆盖三个历史 revision 可解析、历史 ancestry、merge 双 parent、唯一
  head、两分支汇合及空 merge no-op。
- no-op 测试实际导入 merge module、执行两个函数，并检查无 Alembic 调用及
  无 `op`/`sa` 属性；独立 AST 检查又确认函数体严格为 `pass`。
- 测试不创建 engine/session，不读取数据库 URL，不连接真实数据库。
- 测试不执行 upgrade/downgrade CLI，不修改 migration、数据库或运行状态。

### 7.2 标准命令尝试

第一条用户建议命令：

```bash
api/.venv/bin/python -m pytest -o addopts='' -p no:cacheprovider \
  api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py -q
```

结果：退出 127，`api/.venv/bin/python` 不存在。

随后为避免安装依赖尝试：

```bash
ALL_PROXY= all_proxy= UV_CACHE_DIR=.uv-cache \
  uv run --project api --no-sync python -m pytest -o addopts='' \
  -p no:cacheprovider \
  api/tests/unit_tests/migrations/test_enterprise_1_16_migration_graph.py -q
```

结果：退出 1。`uv` 创建空 `api/.venv` 后报告 `No module named pytest`；
没有下载或安装依赖。该临时空目录已删除，工作区恢复干净。

系统 Python 的标准运行被 Python 版本/缺失依赖阻断；借用现有 1.15 Python
3.12 环境的标准运行也被上述 1.15/1.16 依赖漂移阻断。它们均在测试收集或
ScriptDirectory 加载阶段失败，不是测试断言失败。

### 7.3 隔离依赖实际通过结果

最终在现有 Python 3.12 环境中禁用第三方 pytest plugin 自动加载，并以进程内
最小 migration import 占位隔离不相关应用依赖，运行原测试文件和原 16 个
测试：

```text
................                                                         [100%]
16 passed, 1 warning in 0.33s
```

唯一 warning：

```text
PytestConfigWarning: Unknown config option: env
```

这是借用环境未安装处理 pytest `env` 配置项的开发插件所致，不影响 16 个
测试断言。较早一次未禁用 plugin 自动加载的通过运行另出现 LiteLLM 无法获取
远程 model cost map、回退本地备份的 warning；最终记录运行已禁用该无关插件。

## 8. P0 / P1 / P2 findings

### P0：0

未发现阻断 B2 migration graph 合并的问题。

### P1：1（继承的未闭环条件）

| ID | finding | B2 disposition |
| --- | --- | --- |
| P1-01 | 当前运行中的 SSRF Proxy 使用 1.14.2 entrypoint/template，未采用 1.15 private destination 默认拒绝和 allowlist 安全增强。 | 本安全配置漂移仍未闭环；它属于后续独立运维/安全整改，不要求 B2 migration Builder 修复，B2 也没有处理或掩盖它。 |

### P2：2（继承的未闭环条件）

| ID | finding | B2 disposition |
| --- | --- | --- |
| P2-01 | Weaviate/Sandbox 实际 mount provenance 仍属于 1.14.2 路径。 | 后续备份与隔离升级必须按实际路径处理；B2 未修改容器、Compose 或 volume。 |
| P2-02 | Weaviate 未显式返回 `vectorIndexType`、`vectorizer`、`vectorIndexConfig`，仍为 `UNKNOWN`。 | B2 未把 UNKNOWN 写成已验证；对象/向量数量、完整性与 hit testing 仍待后续验证。 |

## 9. Inventory 条件与未闭环事项

B2 diff 和本次审查均没有：

- 执行真实 migration；
- 修改现有 PostgreSQL 或 Weaviate；
- 处理、修复或掩盖 SSRF P1；
- 把 Weaviate `UNKNOWN` 写成已验证；
- 宣称生产升级、数据迁移、备份恢复、hit testing 或业务 smoke 已通过。

仍未闭环：

- SSRF P1 安全配置漂移；
- Weaviate/Sandbox mount provenance；
- Weaviate vector index 配置、对象/向量数量、document segment 完整性和
  hit testing；
- plugin daemon 持久化数据完整性；
- 备份可恢复性与隔离升级副本；
- 真实 PostgreSQL 升级路径和运行时/生产验证；
- 未来 B4 schema/data migration `b416e5c4e702`。

## 10. NOT_RUN

| 项目 | 原因 |
| --- | --- |
| 锁定 1.16 环境中的标准 pytest | 当前工作树没有 `api/.venv`；禁止安装依赖。已以隔离依赖方式运行原测试，16 项通过。 |
| `uv run --project api flask db heads/history` 的锁定依赖版本 | 运行会需要创建/同步当前环境，违反禁止安装依赖；借用现有 1.15 环境的 CLI 已尝试并因依赖漂移退出 1。 |
| `flask db upgrade/downgrade/stamp` | 明确禁止；也不属于静态 B2 review。 |
| 真实 PostgreSQL/MySQL migration | 明确禁止连接/写入真实数据库；本报告不声称升级成功。 |
| Docker/Compose、容器、volume、Weaviate runtime 操作 | 明确禁止；本次只审查源码、历史 ref、图和测试。 |
| B3、B4、运行时升级、生产发布验证 | 不属于 B2 范围，且未获授权。 |

## 11. 最终边界

PASS 只表示 B2 的五文件提交在已审范围内通过：历史文件真实、空 merge 正确、
Alembic 图在独立 ScriptDirectory 中形成唯一 B2 head、focused tests 在隔离
依赖运行中通过。PASS **不授权**：

- 对任何真实数据库执行 migration；
- 在现有或生产 volume 上升级、stamp、downgrade 或修复；
- 修改/重建 SSRF Proxy、Weaviate、容器或 Compose；
- 启动 B3 或 B4；
- 声称运行时升级、数据迁移、备份恢复或生产发布已经通过；
- push。
