# B0 Re-review 2: Enterprise Replay Guardrails (Final Independent Review)

## 审查身份

| 属性 | 值 |
| --- | --- |
| Reviewer | B0 Re-reviewer-2 (独立最终复审) |
| 审查分支 | `ctyun/replay-116-b0-rereviewer2` |
| 审查日期 | 2026-07-24 |
| Fixer-2 审查提交 | `4458cecef61092e5ef909df158813e6bc17bbcf8` (ci: make session fallback context-safe) |
| 父提交 | `4bcad68636` (docs: correct enterprise replay B0 cross-hunk review) |
| 最终结论 | **PASS** |

## 审查链与提交范围

| 步骤 | 提交 | 说明 |
| --- | --- | --- |
| Builder 初稿 | `e3e25ecae1` | ci: add enterprise replay guardrails |
| Builder 预检整改 | `1b8df896f7` | ci: harden enterprise replay guardrails |
| Fixer 完成 fallback (原 P1-01) | `856e05fa95` | ci: complete enterprise replay controller fallback |
| Fixer 修复多行 Flask session | `a2ffd542cd` | ci: handle multiline Flask session fallback |
| Re-review (初次 PASS) | `598683f589` | docs: re-review enterprise replay B0 guardrails |
| Re-review (纠正 CHANGES_REQUIRED) | `4bcad68636` | docs: correct enterprise replay B0 cross-hunk review |
| **Fixer-2 (本文范围)** | `4458cecef6` | **ci: make session fallback context-safe** |

Fixer-2 仅修改两个文件：

```
M  scripts/ci/check-enterprise-replay-scope.sh      (+135/-28)
M  scripts/ci/check-enterprise-replay-scope-tests.sh (+81/-5)
```

严格限定在 B0 授权路径内。未修改其他文件。

## 已验证的提交和基线

```bash
$ git branch --show-current
ctyun/replay-116-b0-rereviewer2

$ git rev-parse HEAD
4458cecef61092e5ef909df158813e6bc17bbcf8

$ git merge-base 1.16.0 HEAD
5c6372d2f76d240265b92fd27c16bc772ffcb107
```

HEAD 严格匹配要求。工作区干净。

## 执行命令及结果

### 1. Shell 语法检查

```bash
$ bash -n scripts/ci/check-enterprise-replay-scope.sh && echo "SYNTAX OK"
SYNTAX OK
$ bash -n scripts/ci/check-enterprise-replay-scope-tests.sh && echo "SYNTAX OK"
SYNTAX OK
```

### 2. git diff --check

```bash
$ git diff --check 4bcad68636..HEAD && echo "DIFF CHECK OK"
DIFF CHECK OK
```

无空白问题。

### 3. 自测

43 项全部通过——包括所有原有 37 项测试和 Fixer-2 新增的 6 项（跨 hunk 对抗、历史调用豁免、参数变更、语法错误 fail-closed 等）：

```
ok - current legal candidate diff
ok - legal CI and documentation changes
ok - docker volumes rename with spaces
ok - docker volumes deletion
ok - real env path
ok - secret-like path
ok - node_modules path
ok - .venv dependency artifact
ok - cache artifact path
ok - build artifact path
ok - controller SQLAlchemy
ok - controller db.session.add_all fallback
ok - controller session.begin fallback
ok - controller Session fallback
ok - controller sessionmaker fallback
ok - controller SQLAlchemy session.get fallback
ok - controller session.get without arguments fallback
ok - controller bare select fallback
ok - controller db.select fallback
ok - controller sa.update fallback
ok - controller sqlalchemy.insert fallback
ok - Flask session.get single-quoted key fallback
ok - Flask session.get double-quoted key fallback
ok - Flask session.get multiline single-quoted key fallback
ok - Flask session.get multiline double-quoted key fallback
ok - controller multiline SQLAlchemy session.get fallback
ok - controller cross-hunk SQLAlchemy session.get fallback
ok - Flask session.get cross-hunk context key fallback
ok - controller SQLAlchemy session.get changed argument fallback
ok - historical untouched session.get fallback
ok - controller stdlib ast parse failure is closed
ok - request.session.get is not bare session fallback
ok - controller commit and flush boundaries fallback
ok - controller similar identifiers fallback
ok - dependency-free fallback diagnostic
ok - legacy Console contract
ok - implicit service session
ok - legacy handwritten Web service
ok - handwritten Console fetch
ok - legacy app context hook
ok - legacy app context import
ok - invalid ref
ok - wrong baseline
all 43 enterprise replay scope tests passed
```

### 4. 主 Checker

```bash
$ scripts/ci/check-enterprise-replay-scope.sh 1.16.0 HEAD
enterprise replay scope check passed
baseline: 5c6372d2f76d240265b92fd27c16bc772ffcb107
range: 5c6372d2f76d240265b92fd27c16bc772ffcb107...4458cecef61092e5ef909df158813e6bc17bbcf8
dry-run only (not executed): pnpm --dir packages/contracts gen-api-contract
dry-run only (not executed): docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
```

当前分支 diff 通过全部检查。

## 跨 Hunk 绕过的复现与验证

### 旧实现的缺陷（被 Fixer-2 替换）

`has_added_sqlalchemy_session_get` 的旧 awk 实现将 `added_lines`（来自 `git diff --unified=0`）中所有新增行拼接为单一字符串，然后用正则搜索 `session.get(` 并检查首字符是否为 `'` 或 `"` 来判断 Flask/SQLAlchemy。

跨 hunk 攻击构造：
1. Hunk 1：将已有调用的函数名从 `GitHubOAuth(` 替换为 `session.get(`（参数行不变，不出现在 `added_lines` 中）
2. Hunk 2：新增一行无关字符串 `"unrelated"`
3. `added_lines` 输出：`session.get(` 行 + `"unrelated"` 行 → 拼接后首参数看起来是字符串 → 按 Flask 豁免

### Fixer-2 的修复（已验证无法绕过）

Fixer-2 将 `has_added_sqlalchemy_session_get` 从 awk 拼接方案替换为基于 Python 标准库 `ast` 模块的实现：

**核心架构（`check-enterprise-replay-scope.sh:165-273`）：**

1. **独立解析 hunk 边界**：解析每个 `@@` hunk header，计算对应的新文件行区间 `(new_start, new_start + new_count - 1)`，验证 hunk 行计数一致性
2. **解析完整 HEAD 源文件**：通过 `git show HEAD:path` 获取完整文件内容，用 `ast.parse()` 构建 AST（仅使用 Python stdlib）
3. **精确匹配裸 session.get**：遍历 AST，匹配 `ast.Call` → `ast.Attribute.attr == "get"` → `ast.Name.id == "session"`。自动排除 `request.session.get`（`function.value` 是 `ast.Attribute` 而非 `ast.Name`）
4. **行区间交集检查**：只检查 `node.lineno <= range_end and range_start <= end_lineno` 落在 diff 范围内的调用
5. **Flask 豁免**：首位置参数为 `ast.Constant` 且值为 `str` 类型 → 豁免（Flask session）
6. **SQLAlchemy 拒绝**：首参数不是字符串常量、或无参数 → `sys.exit(0)`（报告违规）

### 对抗性验证结果

在独立临时仓库中对 Fixer-2 实现进行了以下对抗性测试（全部正确）：

| 测试 | 构造 | 预期 | 实际 |
| --- | --- | --- | --- |
| Flask session.get('key') | 新增文件，字符串 key | PASS | PASS |
| request.session.get(Model,id) | 新增文件，属性链 | PASS | PASS |
| Invalid Python 语法 | 语法错误文件 | BLOCK (fail-closed) | BLOCK |
| f-string 参数 | session.get(f'id-{x}') | BLOCK | BLOCK |
| 多行 session.get(Model,id) | 三行调用，Model 参数 | BLOCK | BLOCK |
| 历史 untouched session.get | 无关行变更，session.get 未变 | PASS | PASS |

跨 hunk 对抗性测试包含在测试套件中（测试 #27 "controller cross-hunk SQLAlchemy session.get fallback"），也验证通过。

## AST 精确匹配、行区间与 fail-closed 逐项分析

### AST 精确匹配

| 场景 | AST 节点结构 | 匹配结果 | 评估 |
| --- | --- | --- | --- |
| `session.get(...)` | `Call(func=Attribute(value=Name('session'), attr='get'))` | 匹配 | 正确拦截 SQLAlchemy |
| `request.session.get(...)` | `Call(func=Attribute(value=Attribute(...), attr='get'))` | `function.value` 不是 `Name` → 不匹配 | 正确排除 |
| `session_manager.get(...)` | `Name.id='session_manager'` | 不匹配 | 正确排除 |
| `session.get('key')` | 首参数 `Constant(value='key')` → string | 匹配但豁免 | 正确放行 Flask |
| `session.get(Model, id)` | 首参数 `Name(id='Model')` → 非 Constant | 匹配且拒绝 | 正确拦截 SQLAlchemy |
| `session.get()` | `args=[]` 空元组 → 跳过豁免条件 | 匹配且拒绝 | 正确拒绝 |
| `session.get(some_var)` | 首参数 `Name(id='some_var')` | 匹配且拒绝 | 正确拒绝 |
| `session.get(None)` | 首参数 `Constant(value=None)` → 非 str | 匹配且拒绝 | 正确拒绝 |
| `session.get(True)` | 首参数 `Constant(value=True)` → 非 str | 匹配且拒绝 | 正确拒绝 |

只使用 Python 标准库模块 `ast`、`re`、`subprocess`、`sys`。不依赖 ast-grep、uvx 或任何第三方包。

### 行区间计算安全性

| 检查项 | 实现方式 | 结论 |
| --- | --- | --- |
| 不同 hunk 不拼接 | 每个 `@@` header 独立解析，生成独立 `(start, end)` 区间 | 安全 |
| 不误报历史调用 | 交集检查 `node.lineno <= range_end and range_start <= end_lineno` | 安全 |
| 新文件处理 | 新文件无 context line，hunk 区间覆盖所有新行 | 安全 |
| 多行调用处理 | AST `end_lineno` 提供完整行跨度，部分重叠也算命中 | 安全 |
| 行计数不一致 | `old_seen != old_count or new_seen != new_count` → fail-closed | 安全 |
| 无 parseable hunk | `saw_hunk=False` → fail-closed | 安全 |

### Fail-closed 分析

所有异常路径通过 `fail_closed` 函数安全关闭（退出码 0 = 报告违规，阻止通过）：

| 异常条件 | fail-closed 触发点 | 行为 |
| --- | --- | --- |
| Git diff 无 parseable hunk | `not saw_hunk` | 阻止 diff |
| Hunk 行计数不一致 | `old_seen != old_count or new_seen != new_count` | 阻止 diff |
| HEAD 源无法解析 (SyntaxError) | `ast.parse()` 异常 | 阻止 diff |
| AST 节点缺少 `end_lineno` | `getattr(node, 'end_lineno', None)` 返回 None | 阻止 diff |
| Git 调用 OS 错误 | `subprocess.run()` 抛出 OSError | 阻止 diff |
| Git 非零退出 | `result.returncode != 0` | 阻止 diff |

所有 fail-closed 路径均向 stderr 输出诊断信息，说明原因。退出码 0 使 `has_added_sqlalchemy_session_get` 返回 true，`has_added_controller_sqlalchemy` 返回 true，最终 checker 报告 "adds direct controller SQLAlchemy"。

### 溢出 B0 授权范围检查

Fixer-2 未修改或弱化以下内容：
- 所有 43 个非 `session.get` 文本 fallback regex 模式（`has_added_controller_sqlalchemy` 行 279-286）保持不变
- `classify_forbidden_path` 路径拒绝逻辑不变
- `is_production_source` 文件过滤不变
- `console_ns.schema_model` 检测不变
- `db.session` 隐式使用检测不变
- 手写 Console fetch 和 legacy app context 检测不变
- Workflow 配置不变

## P0/P1/P2 Findings

### P0 — 无 (0)

### P1 — 无 (0)

原 P1-01（跨 hunk 上下文污染导致 bare `session.get` 误豁免）已在 Fixer-2 中通过基于 Python stdlib AST 的实现完全修复。

### P2 — 1 项 (信息性，不阻塞)

| ID | 严重级别 | 位置 | 描述 |
| --- | --- | --- | --- |
| P2-01 | P2 | `check-enterprise-replay-scope.sh:175-177` | `fail_closed` 触发时报告 "adds direct controller SQLAlchemy"，但实际原因可能是语法错误或 Git 错误。stderr 已输出精确原因，不影响功能。 |

## 逐项确认汇总

| # | 确认项 | 结论 |
| --- | --- | --- |
| 1 | 跨 hunk 绕过已堵住（AST 解析完整文件，非拼接 added_lines） | PASS |
| 2 | AST 精确匹配裸 `session.get`，不误匹配 `request.session.get` | PASS |
| 3 | 只检查新增/修改行涉及的 AST 调用 | PASS |
| 4 | 能识别参数行被修改的多行调用 | PASS |
| 5 | Flask session.get 第一个位置参数为字符串常量时豁免 | PASS |
| 6 | 无参数或第一个位置参数不是字符串时拒绝 | PASS |
| 7 | Git/diff/行区间/AST 解析失败时 fail-closed | PASS |
| 8 | 不依赖 ast-grep、uvx 或第三方 Python 包 | PASS |
| 9 | 行区间不错误拼接不同 hunk 文本 | PASS |
| 10 | 不误报未修改的历史 session.get | PASS |
| 11 | 新文件、修改文件、多行调用均正确处理 | PASS |
| 12 | fallback PATH 中包含 python3 | PASS |
| 13 | 明确排除 ast-grep 和 uvx | PASS |
| 14 | 跨 hunk 夹具确认为两个独立 hunk | PASS |
| 15 | 对抗测试验证真实绕过而非假结果 | PASS |
| 16 | 所有 43 项测试通过 | PASS |
| 17 | Fixer-2 未超出 B0 授权范围 | PASS |
| 18 | 未弱化其他安全规则 | PASS |
| 19 | 文件范围合规 | PASS |
| 20 | 基线锁定与 merge-base 验证 | PASS |
| 21 | name-status -z 解析正确 | PASS |
| 22 | forbidden 路径拦截完整 | PASS |
| 23 | 生产代码反模式覆盖 44/44 pattern | PASS |
| 24 | Workflow 配置安全 | PASS |
| 25 | OpenAPI/Compose 仅为 dry-run 文本输出 | PASS |
| 26 | 自测隔离（git clone --shared, mktemp, trap cleanup） | PASS |
| 27 | 退出码和错误消息准确 | PASS |
| 28 | CI 假通过风险已排除 | PASS |

## 未执行项目

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| `pnpm gen-api-contract` | 未执行 (dry-run only) | B0 checker 仅打印命令名 |
| `docker compose config -q` | 未执行 (dry-run only) | B0 阶段不启动 Docker |
| `scripts/check_no_new_controller_sqlalchemy.py` (AST) | 未执行 | `controller_changed=0`；ast-grep 环境不可用 |
| `flask db heads/flask db history` | 未执行 | 不在 B0 范围 |

## 最终结论

**PASS** — B0 可以进入人工合并门禁。

Fixer-2（`4458cecef6`）通过以下方式完全修复了原 P1-01 的跨 hunk 上下文污染问题：

1. **架构替换**：从 awk 拼接 `added_lines` 方案替换为 Python stdlib AST 方案，使用完整 HEAD 文件而非拼接增量行进行调用分析
2. **精确匹配**：AST 级别匹配 `session.get(...)`，仅匹配置名 `session` 的裸属性访问，排除 `request.session.get` 等属性链
3. **行区间过滤**：独立解析每个 diff hunk header 计算行区间，仅检查与变更行重叠的调用
4. **Flask 豁免**：通过 AST 类型检查区分字符串常量参数（Flask）与对象/变量参数（SQLAlchemy）
5. **Fail-closed**：所有异常路径（Git 错误、语法错误、AST 信息缺失、hunk 不一致）均安全关闭
6. **零依赖**：仅使用 Python 3 标准库（`ast`、`re`、`subprocess`、`sys`），无 ast-grep/uvx/第三方包

所有测试（原有 37 项 + 新增 6 项，共 43 项）通过。主 checker 对当前分支通过。对抗性测试 6 项全部验证正确。Fixer-2 严格限定在两个 B0 授权脚本内，未修改或弱化其他安全规则。除一项 P2 信息性发现外，无阻塞性问题。
