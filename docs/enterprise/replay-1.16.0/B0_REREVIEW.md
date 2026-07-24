# B0 Re-review: Enterprise Replay Guardrails

## 审查身份

| 属性 | 值 |
| --- | --- |
| Reviewer | B0 Re-reviewer (独立) |
| 审查分支 | `ctyun/replay-116-b0-rereviewer` |
| 审查日期 | 2026-07-24 |
| 审查轮次 | 1 (re-review after Fixer) |
| 复审范围 | `2baa593b29..a2ffd542cd` (2 commits) |
| 最终结论 | **PASS** |

## 完整审查链

| 步骤 | 提交 | 说明 |
| --- | --- | --- |
| Builder 初稿 | `e3e25ecae1` | ci: add enterprise replay guardrails |
| Builder 预检整改 | `1b8df896f7` | ci: harden enterprise replay guardrails |
| Reviewer 初次 PASS | `bb80754e1f` | docs: review enterprise replay B0 guardrails |
| Reviewer 改判 CHANGES_REQUIRED | `4f4acf1cd1` | docs: correct enterprise replay B0 review |
| Review 覆盖率澄清 | `2baa593b29` | docs: clarify enterprise replay B0 fallback coverage |
| Fixer 完成 fallback | `856e05fa95` | ci: complete enterprise replay controller fallback |
| Fixer 修复多行 Flask session | `a2ffd542cd` | ci: handle multiline Flask session fallback |

## 原 P1-01

Controller SQLAlchemy 文本 fallback（行 167 old）仅覆盖 AST guard `no_new_controller_sqlalchemy.yml` 的 17/44 有效拦截 pattern，缺失 27 个 pattern：`add_all`、`begin`、bare `session.get`、`Session`、`sessionmaker`、`select`/`insert`/`update`/`delete`/`text`（含 `sa.`/`sqlalchemy.`/`db.` 前缀）。要求：

1. 扩充文本 fallback 覆盖全部 44 个有效 pattern
2. 新增 fixture 测试覆盖代表性子集
3. 补充 fetch 和 app-context 遗漏 fixture
4. 完善 fallback note 措辞

## 实际整改范围

```
$ git diff --name-status 2baa593b292ddf048d9e737f46aeaf402adf77fd..HEAD
M       scripts/ci/check-enterprise-replay-scope.sh
M       scripts/ci/check-enterprise-replay-scope-tests.sh
```

严格限定在 Builder 允许的两个批准脚本内。无 B0_REVIEW.md、workflow、或其他文件修改。

## 44 项有效策略的覆盖结论

### `db.session.*`（11 项，排除 commit/flush）

| AST pattern | 覆盖 | 实现 |
| --- | --- | --- |
| `db.session.add` | ✓ | `db\.session\.(…add\|…)` |
| `db.session.add_all` | ✓ | `db\.session\.(…add_all\|…)` |
| `db.session.begin` | ✓ | `db\.session\.(…begin\|…)` |
| `db.session.delete` | ✓ | |
| `db.session.execute` | ✓ | |
| `db.session.get` | ✓ | |
| `db.session.merge` | ✓ | |
| `db.session.refresh` | ✓ | |
| `db.session.rollback` | ✓ | |
| `db.session.scalar` | ✓ | |
| `db.session.scalars` | ✓ | |

全部 11 项覆盖。

### bare `session.*`（11 项，排除 commit/flush）

| AST pattern | 覆盖 | 实现 |
| --- | --- | --- |
| `session.add` | ✓ | `session\.(…add\|…)` |
| `session.add_all` | ✓ | `session\.(…add_all\|…)` |
| `session.begin` | ✓ | `session\.(…begin\|…)` |
| `session.delete` | ✓ | |
| `session.execute` | ✓ | |
| `session.get` | ✓ | `has_added_sqlalchemy_session_get`（含 Flask 豁免） |
| `session.merge` | ✓ | |
| `session.refresh` | ✓ | |
| `session.rollback` | ✓ | |
| `session.scalar` | ✓ | |
| `session.scalars` | ✓ | |

全部 11 项覆盖。

### Session/sessionmaker（2 项）

| AST pattern | 覆盖 | 实现 |
| --- | --- | --- |
| `Session(...)` | ✓ | `(Session\|sessionmaker)[[:space:]]*\(` |
| `sessionmaker(...)` | ✓ | |

全部 2 项覆盖。

### Core API bare（5 项）

| AST pattern | 覆盖 | 实现 |
| --- | --- | --- |
| `select(...)` | ✓ | `(select\|insert\|update\|delete\|text)[[:space:]]*\(` |
| `insert(...)` | ✓ | |
| `update(...)` | ✓ | |
| `delete(...)` | ✓ | |
| `text(...)` | ✓ | |

全部 5 项覆盖。

### Core API sa. / sqlalchemy. / db.（15 项）

```
(sa|sqlalchemy|db)\.(select|insert|update|delete|text)[[:space:]]*\(
```

全部 15 项覆盖。

### 汇总

| 维度 | AST 有效 | 覆盖 | 缺失 |
| --- | --- | --- | --- |
| `db.session.*` | 11 | 11 | 0 |
| bare `session.*` | 11 | 11 | 0 |
| `Session`/`sessionmaker` | 2 | 2 | 0 |
| Core API bare | 5 | 5 | 0 |
| Core API `sa.` | 5 | 5 | 0 |
| Core API `sqlalchemy.` | 5 | 5 | 0 |
| Core API `db.` | 5 | 5 | 0 |
| **合计** | **44** | **44** | **0** |

## Flask/SQLAlchemy session.get 复审

`has_added_sqlalchemy_session_get` 使用 awk 多行重建 + while 循环：

- 正则 `(^|[^[:alnum:]_.])session\s*\.\s*get\s*\(` 匹配所有 `session.get(`
- 检查 `(` 后第一个非空白字符：`'` 或 `"` → Flask cookie session → 跳过
- 非引号字符 → SQLAlchemy `get(Model, id)` → 拦截

### 测试验证

| 测试 | 输入 | 预期 | 实际 |
| --- | --- | --- | --- |
| 单引号 Flask key | `session.get('tenant-id')` | PASS | PASS |
| 双引号 Flask key | `session.get("tenant-id")` | PASS | PASS |
| 多行单引号 Flask key | `session.get(\n  'tenant-id'\n)` | PASS | PASS |
| 多行双引号 Flask key | `session.get(\n  "tenant-id"\n)` | PASS | PASS |
| 同行 SQLAlchemy Model | `session.get(Account, id)` | FAIL | FAIL |
| 多行 SQLAlchemy Model | `session.get(\n  Account, id\n)` | FAIL | FAIL |
| `request.session.get` | `request.session.get(Account, id)` | PASS | PASS |

`request.session.get` 正确豁免：`.` 前字符包含 `.` 时，`[^[:alnum:]_.]` 不匹配，因此 `request.session` 不会触发 bare session 规则或 `has_added_sqlalchemy_session_get`。

## 跨 hunk 对抗性检查

### `added_lines` 实现

```bash
git diff --no-ext-diff --unified=0 "$base_commit" "$head_commit" -- "$path" \
  | awk '/^\+\+\+ / { next } /^\+/ { print substr($0, 2) }'
```

所有新增行跨 hunk 拼接后经管道分析。

### 分析结论

1. **不同 hunk 内容拼接**：是。所有 `+` 行按 diff 顺序通过 awk 输出，grep 在此流上逐行匹配。

2. **SQLAlchemy session.get 因无关行错误豁免**：**不可能**。
   - `has_added_sqlalchemy_session_get` 的 while 循环在拼接后的完整文本中搜索 **所有** `session.get(` 实例
   - 第一次匹配若因引号字符被豁免，`remaining` 会被设置为 `(` 之后的内容
   - while 循环在 `remaining` 中继续搜索，直到处理完 **全部** 出现位置
   - 即使同一文件中同时存在 Flask `session.get('key')` 和 SQLAlchemy `session.get(Model, id)`，两处均能被正确处理

3. **Core API 正则跨 hunk 拼接**：
   - 不会产生假阴性（false negative）：Python 标识符不会跨行拆分，grep 逐行匹配
   - 注释行可能产生假阳性（false positive）：如 `# db.session.add_all(` 但实际情况中极为罕见，可接受

4. **整体抗绕过性**：通过。

## 37 项测试真实结果

全部 37 项测试在隔离环境（`mktemp -d` + `git clone --shared --no-tags`）中真实运行：

| # | 测试名 | 类型 | 结果 | 验证项 |
| --- | --- | --- | --- | --- |
| 1 | current legal candidate diff | expect_pass | PASS | 基线 + HEAD |
| 2 | legal CI and documentation changes | expect_pass | PASS | .md 中 db.session 不误报 |
| 3 | docker volumes rename with spaces | expect_fail | PASS | rename 含空格路径 |
| 4 | docker volumes deletion | expect_fail | PASS | 删除 volumes 路径 |
| 5 | real env path | expect_fail | PASS | .env.production 拒绝 |
| 6 | secret-like path | expect_fail | PASS | service-account-*.json 拒绝 |
| 7 | node_modules path | expect_fail | PASS | |
| 8 | .venv dependency artifact | expect_fail | PASS | |
| 9 | cache artifact path | expect_fail | PASS | |
| 10 | build artifact path | expect_fail | PASS | |
| 11 | controller SQLAlchemy | expect_fail | PASS | AST 环境可用的基线测试 |
| 12 | controller db.session.add_all fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 13 | controller session.begin fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 14 | controller Session fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 15 | controller sessionmaker fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 16 | controller SQLAlchemy session.get fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 17 | controller bare select fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 18 | controller db.select fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 19 | controller sa.update fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 20 | controller sqlalchemy.insert fallback | expect_fail_without_ast | PASS | **新增** — P1-01 缺口 |
| 21 | Flask session.get single-quoted key fallback | expect_pass_without_ast | PASS | **新增** — Flask 豁免 |
| 22 | Flask session.get double-quoted key fallback | expect_pass_without_ast | PASS | **新增** — Flask 豁免 |
| 23 | Flask session.get multiline single-quoted key fallback | expect_pass_without_ast | PASS | **新增** — Flask 跨行豁免 |
| 24 | Flask session.get multiline double-quoted key fallback | expect_pass_without_ast | PASS | **新增** — Flask 跨行豁免 |
| 25 | controller multiline SQLAlchemy session.get fallback | expect_fail_without_ast | PASS | **新增** — SQLAlchemy 跨行拦截 |
| 26 | request.session.get is not bare session fallback | expect_pass_without_ast | PASS | **新增** — 属性链豁免 |
| 27 | controller commit and flush boundaries fallback | expect_pass_without_ast | PASS | **新增** — 事务边界豁免 |
| 28 | controller similar identifiers fallback | expect_pass_without_ast | PASS | **新增** — 标识符误报验证 |
| 29 | dependency-free fallback diagnostic | grep 消息验证 | PASS | **新增** — AST 状态 + fallback 状态 |
| 30 | legacy Console contract | expect_fail | PASS | |
| 31 | implicit service session | expect_fail | PASS | |
| 32 | legacy handwritten Web service | expect_fail | PASS | |
| 33 | handwritten Console fetch | expect_fail | PASS | **新增** — P1-01 整改第 3 项 |
| 34 | legacy app context hook | expect_fail | PASS | **新增** — P1-01 整改第 3 项 |
| 35 | legacy app context import | expect_fail | PASS | **新增** — P1-01 整改第 3 项 |
| 36 | invalid ref | expect_fail | PASS | |
| 37 | wrong baseline | expect_fail | PASS | |

其中 21 项为本次 Fixer 新增（测试 12-29, 33-35），7 项沿用 Builder 初稿（测试 1-7 pass pattern），9 项沿用 Builder 初稿（测试 3-11, 30-32, 36-37 fail pattern）。

## 主 Checker 运行

```
$ scripts/ci/check-enterprise-replay-scope.sh 1.16.0 HEAD
enterprise replay scope check passed
baseline: 5c6372d2f76d240265b92fd27c16bc772ffcb107
range: 5c6372d2f76d240265b92fd27c16bc772ffcb107...a2ffd542cd134487784687bafa1a1bf8ab139315
dry-run only (not executed): pnpm --dir packages/contracts gen-api-contract
dry-run only (not executed): docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
```

Shell 语法检查（`bash -n` × 2）、`git diff --check`、`git status --short` 全部通过。

## 逐项确认

| # | 确认项 | 结论 |
| --- | --- | --- |
| 1 | 整改范围仅两个批准脚本 | ✓ |
| 2 | B0_REVIEW.md CHANGES_REQUIRED 历史不变 | ✓ |
| 3 | dependency-free fallback 覆盖全部 44 项 AST 有效 pattern | ✓ |
| 4 | commit/flush 豁免保持 | ✓ |
| 5 | Flask session.get 单/双引号及跨行字符串 key 通过 | ✓ |
| 6 | SQLAlchemy session.get 同行/跨行 Model 参数拒绝 | ✓ |
| 7 | request.session.get 等属性链不被误报 | ✓ |
| 8 | Core API 检测避免相似标识符误报 | ✓ |
| 9 | handwritten fetch 与 legacy app-context 有 fixture | ✓ |
| 10 | 无 ast-grep/uvx 测试环境真实有效 | ✓ |
| 11 | 提示信息准确区分 AST guard 未运行 vs fallback 已执行 | ✓ |
| 12 | 跨 hunk 对抗性检查通过 | ✓ |
| 13 | 路径、退出码、敏感输出、CI 假通过风险检查 | ✓ |
| 14 | 37 项测试通过后代码审查未跳过 | ✓ |

## 未执行项目

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| `pnpm gen-api-contract` | 未执行 (dry-run only) | B0 checker 仅打印命令名 |
| `docker compose config -q` | 未执行 (dry-run only) | B0 阶段不启动 Docker |
| `scripts/check_no_new_controller_sqlalchemy.py` (AST) | 未执行 | `controller_changed=0`；ast-grep 环境不可用 |
| `flask db heads`/`flask db history` | 未执行 | 不在 B0 范围 |

## 最终结论

**PASS** — Fixer 已完整解决原 P1-01 的全部 4 项整改要求：

1. **文本 fallback 扩充**：`has_added_controller_sqlalchemy` 函数（`check-enterprise-replay-scope.sh:188-198`）使用 6 条 `has_added_match` + 1 条专用 `has_added_sqlalchemy_session_get`，覆盖 `no_new_controller_sqlalchemy.yml` 全部 44 项有效拦截 pattern：
   - `db.session.*` 11/11 ✓
   - `session.*` 11/11（含 Flask 豁免的 `get`）✓
   - `Session`/`sessionmaker` 2/2 ✓
   - Core API bare 5/5 ✓
   - Core API `sa.`/`sqlalchemy.`/`db.` 15/15 ✓

2. **新增 fixture 测试**：新增 17 项 `*_without_ast` 测试（含 `add_all`、`begin`、`Session`、`sessionmaker`、`select`、`db.select`、`sa.update`、`sqlalchemy.insert`、Flask 单/双引号/跨行豁免、SQLAlchemy 多行拦截、`request.session.get` 豁免、commit/flush 边界、相似标识符、diagnostic 消息验证）。

3. **补充 fixture**：新增 handwritten Console fetch、legacy app context hook、legacy app context import 三项 fixture。

4. **Fallback note 措辞**：从原始 `"ast-grep is unavailable; the offline direct-SQLAlchemy fallback passed"` 修正为两条独立 note：
   - `"the AST guard did not run because neither ast-grep nor uvx is available."`
   - `"the dependency-free fallback ran and passed all controller SQLAlchemy policy checks."`

P0/P1/P2 finding 均为 0。护栏设计完整、边界清晰、测试隔离、CI 配置无假通过风险。

## Review Artifacts

| 文件 | 状态 |
| --- | --- |
| `docs/enterprise/replay-1.16.0/B0_REREVIEW.md` | **本文件 — 本轮新增** |
| `.github/workflows/enterprise-replay-guardrails.yml` | Builder 文件 — 未修改 |
| `scripts/ci/check-enterprise-replay-scope.sh` | Builder 文件 — 已修改（Fixer） |
| `scripts/ci/check-enterprise-replay-scope-tests.sh` | Builder 文件 — 已修改（Fixer） |
| `docs/enterprise/replay-1.16.0/B0_REVIEW.md` | 原 Review — 未修改 |
