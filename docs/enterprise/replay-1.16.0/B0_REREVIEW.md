# B0 Re-review: Enterprise Replay Guardrails

## 审查身份

| 属性 | 值 |
| --- | --- |
| Reviewer | B0 Re-reviewer (独立) |
| 审查分支 | `ctyun/replay-116-b0-rereviewer` |
| 审查日期 | 2026-07-24 |
| 审查轮次 | 2 (corrected after adversarial cross-hunk finding) |
| 复审范围 | `2baa593b29..a2ffd542cd` (2 commits) |
| 最终结论 | **CHANGES_REQUIRED** |

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
| Re-review 纠正 | `598683f589` | docs: re-review enterprise replay B0 guardrails (initial PASS) |
| **本纠正** | *当前提交* | **docs: correct enterprise replay B0 cross-hunk review (CHANGES_REQUIRED)** |

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

## 44 项有效策略的覆盖结论（名义覆盖）

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
| `session.get` | **✗ 跨 hunk 可绕过** | `has_added_sqlalchemy_session_get` 跨 hunk 拼接导致上下文参数可被污染 |
| `session.merge` | ✓ | |
| `session.refresh` | ✓ | |
| `session.rollback` | ✓ | |
| `session.scalar` | ✓ | |
| `session.scalars` | ✓ | |

`session.get` 名义上通过 `has_added_sqlalchemy_session_get` 覆盖，但该实现存在跨 hunk 绕过（见新 P1），实际拦截不可靠。

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

### 名义覆盖率汇总

| 维度 | AST 有效 | 名义覆盖 | 实际可靠覆盖 | 缺口 |
| --- | --- | --- | --- | --- |
| `db.session.*` | 11 | 11 | 11 | 0 |
| bare `session.*` | 11 | 11 | 10* | **1 (session.get)** |
| `Session`/`sessionmaker` | 2 | 2 | 2 | 0 |
| Core API bare | 5 | 5 | 5 | 0 |
| Core API `sa.` | 5 | 5 | 5 | 0 |
| Core API `sqlalchemy.` | 5 | 5 | 5 | 0 |
| Core API `db.` | 5 | 5 | 5 | 0 |
| **合计** | **44** | **44** | **43** | **1** |

\*`session.get` 的 regex 存在于代码中，但因跨 hunk 上下文污染可被绕过。

## 新 P1-01：跨 hunk 上下文丢失导致 `has_added_sqlalchemy_session_get` 可绕过

### 严重级别

P1 — 存在可实际构造的绕过路径。

### 根因

`has_added_sqlalchemy_session_get` 依赖 `added_lines()` 的输出：

```bash
git diff --no-ext-diff --unified=0 "$base_commit" "$head_commit" -- "$path" \
  | awk '/^\+\+\+ / { next } /^\+/ { print substr($0, 2) }'
```

该函数仅输出纯新增行（`+` 开头行），**丢弃 diff context 和 hunk 边界**。不同 hunk 的新增行被无差别拼接。当 `session.get(` 调用跨越多行且仅首行为新增行时（如将已有调用的函数名从 `GitHubOAuth(` 替换为 `session.get(`），参数行属于未修改 context 而不出现在 `added_lines` 中。

### 攻击构造

1. **已有 controller 文件**中存在一个多行调用：
   ```python
   github_oauth = GitHubOAuth(
       client_id=app.config['GITHUB_CLIENT_ID'],
       client_secret=app.config['GITHUB_CLIENT_SECRET'],
   )
   ```

2. **Hunk 1**：将首行替换为 `session.get(`：
   ```diff
   -    github_oauth = GitHubOAuth(
   +    github_oauth = session.get(
   ```
   参数行不变，不出现在新增行中。

3. **Hunk 2**（同一文件，不同位置）新增一行**无关字符串**：
   ```diff
   +"unrelated"
   ```

4. `added_lines` 输出：
   ```
   github_oauth = session.get(
   "unrelated"
   ```

5. `has_added_sqlalchemy_session_get` 的 awk 将拼接内容视为连续源：
   - 匹配 `session.get(`
   - 提取参数：`\n"unrelated"`
   - 去首空白后首字符为 `"` → **按 Flask cookie session 豁免**
   - exit 0 → checker 放行

### 为什么前期分析错误

原分析声称 "不可能" 的理由是 while 循环会搜索所有 `session.get(` 实例。这个逻辑在**同一完整源文本**中正确——但如果 `session.get(` 只出现**一次**（仅 hunk 1 的首行），而参数上下文（hunk 2 的无关字符串）被跨 hunk 拼接污染，while 循环无法知道真正的参数来自未出现在 `added_lines` 中的 context 行。

核心缺陷：**`has_added_sqlalchemy_session_get` 无法区分新增行中 `session.get(` 的真实调用参数与来自不同 hunk 的无关字符串。**

### 受影响范围

- **bare `session.get` 的 Flask/SQLAlchemy 区分逻辑**：可绕过。
- **`db.session.get`**：不受影响，因为 `has_added_match` 使用简单 regex 匹配，不检查参数。
- **其他 42 个 pattern**：不受影响，均使用不依赖参数上下文的简单 regex 匹配。
- **跨行合法 Flask `session.get`**：若 `session.get('key')` 的所有行在同一 hunk 的新增行中，仍正确豁免。

### 影响分析

- 当未来 Builder 修改 controller 文件时，可将一个已有调用的函数名改为 `session.get(`，利用原参数行不产生新增行的特点避免被拦截。
- 仅需在同一文件的另一个独立位置增加任意字符串字面量，即可触发"假 Flask 豁免"。
- CI 中 `ast-grep`/`uvx` 不可用，仅执行文本 fallback，该 bypass 在 CI 中有效。
- 37 项现有测试均在同一 hunk 内构造新增行，未覆盖跨 hunk 上下文污染场景。

### 所需整改

1. **修复 `has_added_sqlalchemy_session_get` 的跨 hunk 上下文丢失问题**。不得使用跨 hunk 拼接后重分析参数的方式。可选方案：
   - 使用 `--unified` 保留足够 context 并在每个 hunk 内独立分析；
   - 使用 Python stdlib `ast` 模块解析 HEAD 文件完整 AST，然后只报告落在 `base_commit..head_commit` diff 范围（通过 `git diff` 的行范围）内的违规节点；
   - 或其他不拼接不同 hunk、能保留每个调用真实参数上下文的无第三方依赖实现。

2. **新增对抗性 fixture**（使用已有的 `expect_fail_without_ast` / `expect_fail` 机制）：
   - 在官方已有 controller 中找到多行调用（如类似 `GitHubOAuth(` 的模式）；
   - 将其首行替换为 `session.get(`，参数行保持不变；
   - 在同一文件的独立位置增加字符串字面量；
   - `--unified=0` 后新增行仅包含 `session.get(` 行和无关字符串行；
   - 在 `PATH` 排除 `ast-grep`/`uvx` 后必须被拒绝（exit non-zero）。

3. **验证合法跨行 Flask `session.get` 仍通过**：在相同跨 hunk 场景下，确认真正的 Flask `session.get('key')` 不被误报。

4. **保留现有 44 类名义覆盖**：其他 43 个 pattern 的 regex 实现不受跨 hunk 问题影响。仅需修复 `has_added_sqlalchemy_session_get` 的架构。

### P0/P1/P2 汇总

| ID | 级别 | 位置 | 描述 | 状态 |
| --- | --- | --- | --- | --- |
| P1-01 | P1 | `check-enterprise-replay-scope.sh:162-186` | `has_added_sqlalchemy_session_get` 跨 hunk 上下文污染导致 Flask/SQLAlchemy 区分可绕过 | **未解决** |
| 原 P1-01 | P1 | 原行 167 | 43/44 名义覆盖已解决；`session.get` 仍存在可绕过实现 | 已部分解决，新 P1-01 跟踪残留缺口 |

## Flask/SQLAlchemy session.get 复审（纠正版）

`has_added_sqlalchemy_session_get` 的 awk 实现：

- 正则匹配 `session.get(` ✓（语法正确）
- 检查首参数是否为引号字符串 ✓（逻辑正确）
- 跨 hunk 拼接导致参数上下文可被污染 ✗（架构缺陷）

**在当前实现下，Flask `session.get` 的豁免和 SQLAlchemy `session.get` 的拦截均不可靠**——当调用跨行且仅首行是新增行时，`added_lines` 不包含真实参数，后续无关 hunk 的新增行可被误当作参数。

唯一安全的方式是保留每个 hunk 内新增行的真实调用上下文，或将分析移至 Python AST 层。

## 跨 hunk 对抗性检查（纠正版）

| 检查项 | 原结论 | 纠正后 |
| --- | --- | --- |
| 不同 hunk 内容拼接 | 是 | 是 |
| SQLAlchemy session.get 因无关行错误豁免 | 不可能 | **可能** — 当仅首行为新增行时 |
| 同一文件内多个 session.get 均被检查 | 正确 | 正确，但不覆盖跨 hunk 污染场景 |
| 整体抗绕过性 | 通过 | **未通过** — 存在可构造绕过 |

## 37 项测试真实结果

37 项测试全部在隔离环境中真实运行并 PASS。但现有测试均在**同一 hunk 内**构造新增行，跨 hunk 对抗场景无覆盖。

## 主 Checker 运行

```
$ scripts/ci/check-enterprise-replay-scope.sh 1.16.0 HEAD
enterprise replay scope check passed
```

Shell 语法检查（`bash -n` × 2）、`git diff --check`、`git status --short` 全部通过。

## 逐项确认

| # | 确认项 | 结论 |
| --- | --- | --- |
| 1 | 整改范围仅两个批准脚本 | ✓ |
| 2 | B0_REVIEW.md CHANGES_REQUIRED 历史不变 | ✓ |
| 3 | dependency-free fallback 名义覆盖 44 项 AST 有效 pattern | ✓（43 可靠，1 可绕过） |
| 4 | commit/flush 豁免保持 | ✓ |
| 5 | Flask session.get 单/双引号及跨行字符串 key 通过（同 hunk） | ✓ |
| 6 | SQLAlchemy session.get 同行/跨行 Model 参数拒绝（同 hunk） | ✓ |
| 7 | request.session.get 等属性链不被误报 | ✓ |
| 8 | Core API 检测避免相似标识符误报 | ✓ |
| 9 | handwritten fetch 与 legacy app-context 有 fixture | ✓ |
| 10 | 无 ast-grep/uvx 测试环境真实有效 | ✓ |
| 11 | 提示信息准确区分 AST guard 未运行 vs fallback 已执行 | ✓ |
| 12 | 跨 hunk 对抗性检查 | **✗ 可绕过** |
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

**CHANGES_REQUIRED** — `has_added_sqlalchemy_session_get` 的跨 hunk 上下文污染导致 bare `session.get` 的 Flask/SQLAlchemy 区分可被绕过。

原 P1-01 的 4 项要求中有 3 项已正确完成：43/44 名义 pattern 覆盖、补充 fixture（不含跨 hunk 对抗）、补充 fetch/app-context fixture、fallback note 措辞。

但 `has_added_sqlalchemy_session_get` 的 awk 实现存在架构缺陷——`added_lines` 拼接不同 hunk 的新增行后，无法区分 `session.get(` 的真实调用参数与无关 hunk 的字符串。当仅替换一个已有调用的函数名为 `session.get(` 时（参数行不变），新增行中不包含真实参数；来自另一 hunk 的无关字符串可被误当作首参数，导致 SQLAlchemy `session.get(Model, id)` 被按 Flask `session.get('key')` 豁免。

**Fixer 必须在下一提交中：**

1. 修复 `has_added_sqlalchemy_session_get`，使用不拼接跨 hunk 上下文的方式（如逐 hunk 分析、Python stdlib AST、或逐行 regex 配合文件全文回退）来区分 Flask/SQLAlchemy `session.get`。
2. 新增真实跨 hunk 对抗 fixture，验证：
   - 仅首行新增的 `session.get(` 被无关 hunk 字符串污染时仍被拒绝；
   - 合法跨行 Flask `session.get('key')` 在跨 hunk 场景下仍通过。
3. 保留现有同 hunk 测试不变（测试 21-27 仍然有效）。

不影响 B0 的其他评价——除 `has_added_sqlalchemy_session_get` 外，文件范围、基线锁定、forbidden 路径拦截、name-status 解析、Workflow 配置、自测隔离和其余 43 个 pattern 的 fallback 覆盖均正确。

## Review Artifacts

| 文件 | 状态 |
| --- | --- |
| `docs/enterprise/replay-1.16.0/B0_REREVIEW.md` | **本文件 — 本轮纠正** |
| `.github/workflows/enterprise-replay-guardrails.yml` | Builder 文件 — 未修改 |
| `scripts/ci/check-enterprise-replay-scope.sh` | Builder 文件 — 已修改（Fixer），待进一步修复 |
| `scripts/ci/check-enterprise-replay-scope-tests.sh` | Builder 文件 — 已修改（Fixer），待进一步修复 |
| `docs/enterprise/replay-1.16.0/B0_REVIEW.md` | 原 Review — 未修改 |
