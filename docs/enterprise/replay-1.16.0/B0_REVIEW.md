# B0 Review: Enterprise Replay Guardrails

## 审查身份

| 属性 | 值 |
| --- | --- |
| Reviewer | B0 Reviewer (独立) |
| 审查分支 | `ctyun/replay-116-b0-reviewer` |
| 审查日期 | 2026-07-24 |
| 审查轮次 | 2 (correction) |
| Builder 范围 | `d9089773e89d24cd0404a76bb840bfbf7069a854..1b8df896f75f520ed7f17143e0752a2009533927` |
| Checker 范围 | `1.16.0...HEAD` = 治理文档 11 个 + Builder 3 文件 = 共 14 文件 |
| 最终结论 | **CHANGES_REQUIRED** |

## 基线与提交

| 项目 | 值 |
| --- | --- |
| 官方标签 | `1.16.0` |
| 官方提交 | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| merge-base | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| Builder 起点 | `d9089773e89d24cd0404a76bb840bfbf7069a854` (`docs: correct enterprise 1.16.0 gate review chain`) |
| Builder 终点 | `1b8df896f75f520ed7f17143e0752a2009533927` (`ci: harden enterprise replay guardrails`) |
| 中间提交 | `e3e25ecae1` (`ci: add enterprise replay guardrails`) |
| 初轮 review commit | `bb80754e1f9ab7e823a6efe836ecef39b29a1837` |

验证命令：

```bash
$ git branch --show-current
ctyun/replay-116-b0-reviewer

$ git rev-parse HEAD
bb80754e1f9ab7e823a6efe836ecef39b29a1837

$ git status --porcelain
(空)

$ git merge-base 1.16.0 HEAD
5c6372d2f76d240265b92fd27c16bc772ffcb107
```

全部匹配预期。工作区干净。

## 实际文件范围

### Builder diff (3 文件，仅 Builder 新增)

```bash
$ git diff --name-status d9089773e89d24cd0404a76bb840bfbf7069a854..1b8df896f75f520ed7f17143e0752a2009533927
A  .github/workflows/enterprise-replay-guardrails.yml
A  scripts/ci/check-enterprise-replay-scope-tests.sh
A  scripts/ci/check-enterprise-replay-scope.sh
```

严格符合 ARCHITECT_HANDOFF §5 规定的 B0 Allowed write paths:
- `.github/workflows/enterprise-replay-*` ✓
- `scripts/ci/check-enterprise-replay-*` ✓

### Checker 运行范围 (14 文件，含治理文档)

```bash
$ git diff --name-status 1.16.0...HEAD
A  .github/workflows/enterprise-replay-guardrails.yml
A  ENTERPRISE_REPLAY_PLAN.md
A  docs/enterprise/replay-1.16.0/ARCHITECT_HANDOFF.md
A  docs/enterprise/replay-1.16.0/ARCHITECT_REREVIEW.md
A  docs/enterprise/replay-1.16.0/ARCHITECT_REVIEW.md
A  docs/enterprise/replay-1.16.0/B0_REVIEW.md
A  docs/enterprise/replay-1.16.0/DESIGN_GATE.md
A  docs/enterprise/replay-1.16.0/DESIGN_GATE_REREVIEW.md
A  docs/enterprise/replay-1.16.0/DESIGN_GATE_REVIEW.md
A  docs/enterprise/replay-1.16.0/OFFICIAL_RELEASE_ANALYSIS.md
A  docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md
A  docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md
A  scripts/ci/check-enterprise-replay-scope-tests.sh
A  scripts/ci/check-enterprise-replay-scope.sh
```

说明：Checker 通过 `1.16.0...HEAD` 检查整个分支（含此前治理阶段提交的 11 个文档），不仅仅是 Builder 的 3 文件。这一行为正确——Checker 应覆盖全分支，只是需要区分"Builder 交付物"和"Checker 扫描范围"。

无任何 `api/**`, `web/**`, `docker/**`, `dify-agent/**`, `packages/**`, `docker/volumes/**` 修改。

## 验证命令及结果

### Shell 语法检查

```bash
$ bash -n scripts/ci/check-enterprise-replay-scope.sh && echo "SYNTAX OK"
SYNTAX OK

$ bash -n scripts/ci/check-enterprise-replay-scope-tests.sh && echo "SYNTAX OK"
SYNTAX OK
```

### git diff --check

```bash
$ git diff --check d9089773e89d24cd0404a76bb840bfbf7069a854..1b8df896f75f520ed7f17143e0752a2009533927 && echo "DIFF CHECK OK"
DIFF CHECK OK
```

无空白问题。

### 自测

```bash
$ scripts/ci/check-enterprise-replay-scope-tests.sh
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
ok - legacy Console contract
ok - implicit service session
ok - legacy handwritten Web service
ok - invalid ref
ok - wrong baseline
all 16 enterprise replay scope tests passed
```

16 项全部通过——2 个成功场景（`current legal candidate diff`、`legal CI and documentation changes`）+ 14 个失败场景。

### 主 Checker 运行

```bash
$ scripts/ci/check-enterprise-replay-scope.sh 1.16.0 HEAD
enterprise replay scope check passed
baseline: 5c6372d2f76d240265b92fd27c16bc772ffcb107
range: 5c6372d2f76d240265b92fd27c16bc772ffcb107...bb80754e1f9ab7e823a6efe836ecef39b29a1837
dry-run only (not executed): pnpm --dir packages/contracts gen-api-contract
dry-run only (not executed): docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
```

当前 diff 通过所有检查。

## P0/P1/P2 Findings

### P0 — 无 (0)

### P1 — 1 项 (CHANGES_REQUIRED)

| ID | 严重级别 | 位置 | 描述 |
| --- | --- | --- | --- |
| P1-01 | P1 | `scripts/ci/check-enterprise-replay-scope.sh` 行 167 | **Controller SQLAlchemy 文本 fallback 未覆盖 AST guard 的全部拦截模式**。行 167 的 regex 仅覆盖 `db.paginate`、`db.session.{query,execute,scalar,scalars,add,delete,merge,refresh,rollback,get}`、`session.{query,execute,scalar,scalars,add,delete,merge,refresh,rollback}`。官方 AST 规则 `scripts/ast_grep_rules/no_new_controller_sqlalchemy.yml` 还包含以下未覆盖的 SQLAlchemy 模式（不含 commit/flush，因 Python guard 明确允许二者作为事务边界）： |

#### 缺口详细对比

AST 规则全部 48 个 pattern（来自 `no_new_controller_sqlalchemy.yml` 行 5-52），减去 `is_allowed_session_boundary` 明确放行的 `commit`/`flush`（4 个 pattern），有效拦截 pattern 共 44 个。文本 fallback 覆盖率如下：

| AST pattern | 分类 | 文本 fallback 覆盖？ | 说明 |
| --- | --- | --- | --- |
| `db.session.add` | session method | ✓ 已覆盖 | `db\.session\.(...\|add\|...)` |
| `db.session.add_all` | session method | **✗ 未覆盖** | 不在 alternation 中 |
| `db.session.begin` | session method | **✗ 未覆盖** | 不在 alternation 中 |
| `db.session.commit` | 事务边界 | — 豁免 | Python guard 放行，不纳入缺口 |
| `db.session.delete` | session method | ✓ 已覆盖 | |
| `db.session.execute` | session method | ✓ 已覆盖 | |
| `db.session.flush` | 事务边界 | — 豁免 | Python guard 放行，不纳入缺口 |
| `db.session.get` | session method | ✓ 已覆盖 | |
| `db.session.merge` | session method | ✓ 已覆盖 | |
| `db.session.refresh` | session method | ✓ 已覆盖 | |
| `db.session.rollback` | session method | ✓ 已覆盖 | |
| `db.session.scalar` | session method | ✓ 已覆盖 | |
| `db.session.scalars` | session method | ✓ 已覆盖 | |
| `session.add` | bare session | ✓ 已覆盖 | `session\.(...\|add\|...)` |
| `session.add_all` | bare session | **✗ 未覆盖** | 不在 alternation 中 |
| `session.begin` | bare session | **✗ 未覆盖** | 不在 alternation 中 |
| `session.commit` | 事务边界 | — 豁免 | Python guard 放行 |
| `session.delete` | bare session | ✓ 已覆盖 | |
| `session.execute` | bare session | ✓ 已覆盖 | |
| `session.flush` | 事务边界 | — 豁免 | Python guard 放行 |
| `session.get` | bare session | ⚠ 覆盖但有误报风险 | 文本 regex 会匹配 Flask `session.get('key')`；AST guard 通过 `is_flask_session_get` 豁免（见下） |
| `session.merge` | bare session | ✓ 已覆盖 | |
| `session.refresh` | bare session | ✓ 已覆盖 | |
| `session.rollback` | bare session | ✓ 已覆盖 | |
| `session.scalar` | bare session | ✓ 已覆盖 | |
| `session.scalars` | bare session | ✓ 已覆盖 | |
| `Session(...)` | constructor | **✗ 未覆盖** | 构造新 Session 是重大绕过 |
| `sessionmaker(...)` | factory | **✗ 未覆盖** | Session 工厂 |
| `select(...)` / `insert(...)` / `update(...)` / `delete(...)` / `text(...)` | 2.0 core (bare) | **5 个均未覆盖** | SQLAlchemy 2.0 核心 API |
| `sa.select(...)` / `sa.insert(...)` / `sa.update(...)` / `sa.delete(...)` / `sa.text(...)` | 2.0 core (sa.) | **5 个均未覆盖** | 别名导入 |
| `sqlalchemy.select(...)` / `sqlalchemy.insert(...)` / `sqlalchemy.update(...)` / `sqlalchemy.delete(...)` / `sqlalchemy.text(...)` | 2.0 core (sqlalchemy.) | **5 个均未覆盖** | 全限定导入 |
| `db.select(...)` / `db.insert(...)` / `db.update(...)` / `db.delete(...)` / `db.text(...)` | 2.0 core (db.) | **5 个均未覆盖** | Flask-SQLAlchemy db 快捷方式 |

汇总：有效拦截 pattern 共 44 个（48 个总 pattern minus 4 个 commit/flush）。文本 fallback 覆盖了 19 个（其中 1 个有 Flask 误报风险），**缺失 26 个**。

其中 `select`/`insert`/`update`/`delete`/`text`（20 个 pattern，含 4 种前缀）是 SQLAlchemy 2.0 最常用的核心 API——在 controller 中出现 `db.session.execute(select(Model))` 或直接 `select(Model)` 的概率远高于旧式 `db.session.query(Model)`。

Flask `session.get` 误报：AST guard (`check_no_new_controller_sqlalchemy.py` 行 19, 38-39) 通过正则 `^session\.get\(\s*['\"]` 识别 Flask 的 cookie session（参数为字符串字面量），从而豁免；文本 fallback 无法区分。这可能导致 controller 合法使用 `session.get('key')` 时触发误报。

#### 影响分析

- CI workflow 不安装任何依赖，`ast-grep`/`uvx` 在 CI 中不可用
- 因此 `scripts/check_no_new_controller_sqlalchemy.py` 在 CI 中永远不会执行
- 当未来 Builder（如 B3 平台管理员、B4 智慧广场）修改 controller 文件时，CI 仅执行不完整的文本 fallback
- "B0 当前无 controller diff" 是事实，但不能证明护栏面向未来有效

#### 所需整改

1. **扩充文本 fallback regex**（`check-enterprise-replay-scope.sh` 行 167），使其覆盖 AST 规则的全部有效拦截 pattern：`add_all`、`begin`、`Session`、`sessionmaker`、`select`/`insert`/`update`/`delete`/`text`（含 `sa.`/`sqlalchemy.`/`db.` 前缀）。可用单一扩展 regex 或多个 `has_added_match` 调用实现。须同时加入 Flask `session.get` 豁免逻辑（例如检测 `session.get(` 后紧跟 `'` 或 `"` 则跳过）。
2. **新增 fixture 测试**（`check-enterprise-replay-scope-tests.sh`），至少覆盖下列代表性子集：
   - `db.session.add_all(Model(...))` 或 `session.add_all([...])`
   - `db.session.begin()` 或 `session.begin()`
   - `Session()` 构造
   - `select(Model)` — bare SQLAlchemy 2.0 core
   - `db.select(Model)` — Flask-SQLAlchemy shortcut
   - `sqlalchemy.insert(table).values(...)` — 全限定路径
   - Flask `session.get('key')` 豁免验证 (不触发)
3. **补充 P2-01 中遗漏的测试**：同时为手写 `fetch('/console/api/` 和旧 app context (`useAppContext(`) 检测增加 fixture。
4. **AST guard fallback 消息**（行 211-213）：区分"AST guard 未运行"与"文本 fallback 已执行"；当 `controller_changed=1` 且 AST 不可用时，在 note 中列出文本 fallback 已知未覆盖的 pattern 类别（如 `Session`, `select`, `insert`, `update`, `delete`, `text`），避免向 Reviewer 暗示 fallback 覆盖了完整 AST 规则。

### P2 — 无 (0)

原初轮 P2-01（fetch/app-context 缺测试）已合并至 P1-01 整改要求第 3 项。

原初轮 P2-02（`workflow_dispatch` ref 透传）不是实际缺陷：`actions/checkout@v4` 正确切换 ref 后，`HEAD` 已指向目标提交，checker 的固定 `HEAD` 参数行为正确。删除该 finding。

## 逐项审查结果

### 1. 文件范围合规

仅新增 3 个文件，全部落入 ARCHITECT_HANDOFF 规定的 B0 allowlist。无业务代码、Docker、migration、依赖或配置变更。 **PASS**

### 2. 官方基线与 merge-base 锁定

`OFFICIAL_BASE_COMMIT` 在两个脚本中硬编码为 `5c6372d2f76d240265b92fd27c16bc772ffcb107`。Checker 验证 `$base_commit == $OFFICIAL_BASE_COMMIT` 和 `$merge_base == $OFFICIAL_BASE_COMMIT`。实测通过。 **PASS**

### 3. name-status -z 解析

Checker 行 46-62：使用 `git diff --name-status -z --find-renames --find-copies` + `read -d ''` 逐字段解析 NUL 分隔记录。正确处理：
- 普通状态 (A/D/M/T)：`<status>\0<path>\0` → 一次 read 拿到 path
- Rename (R*)：`R<score>\0<old>\0<new>\0` → 两次 read 拿到 old/new，`changed_statuses`/`changed_paths` 均追加两次
- Copy (C*)：同上

测试覆盖了带空格的路径 rename (3号测试: `safe/original name.txt` → `docker/volumes/runtime data.txt`)。路径中 `/`、空格、特殊字符均被 `-z` + `%q` 正确处理。 **PASS**

### 4. 拒绝 forbidden 路径

`classify_forbidden_path` 通过 `case "/$lower/" in` 做包含式匹配：

| 类别 | 匹配模式 | 测试覆盖 |
| --- | --- | --- |
| `docker/volumes/*` | `*/docker/volumes/*` | 3号 (rename), 4号 (delete) |
| `.env` (非 example) | basename `.env`, `.env.*`, `*.env`，通过 `is_safe_env_example` 排除 `.env.example`/`.env.sample`/`.env.template` | 5号 |
| secret/key/credential | basename 匹配 `credentials.json`, `service-account*.json`, `id_rsa`, `*.pem`, `*.key`, `*.p12`, `*.pfx`；目录匹配 `*/.secrets/*`, `*/secrets/*` | 6号 |
| `node_modules` | `*/node_modules/*` | 7号 |
| `.venv`/`venv` | `*/.venv/*`, `*/venv/*` | 8号 |
| cache | `*/.cache/*`, `*/.pytest_cache/*`, `*/.mypy_cache/*`, `*/.ruff_cache/*`, `*/.uv-cache/*`, `*/__pycache__/*`, `*/.turbo/*`, `*/.pnpm-store/*`, `*/.yarn/cache/*` | 9号 |
| build/dist/.next/coverage | `*/.next/*`, `*/build/*`, `*/dist/*`, `*/coverage/*`, `*/htmlcov/*` | 10号 |
| 编译产物 | basename 匹配 `*.pyc`, `*.pyo`, `*.class`, `*.o`, `*.so` | 未独立测试但正则正确 |

`is_safe_env_example` 对 full path 做后缀匹配，`docker/envs/agent.env.example` 可通过；`config/.env.production` 被拒绝。 **PASS**

### 5. 避免文档/测试/文件名误报

`is_production_source` (行 134-146) 将 checker 的生产模式检测限定在 `api/*.py`、`web/*.{js,jsx,ts,tsx}`，并显式排除 `api/tests/*`、`api/**/tests/*`、`web/**/__tests__/*`、`*.spec.*`、`*.test.*`。

1号测试 ("legal CI and documentation changes") 验证 `.md` 文件中出现 `db.session`、`console_ns.schema_model` 不会触发误报，以及路径包含 `venv` 作为文档名不被标记。 **PASS**

### 6. 生产代码模式检查

Checker 行 148-201：

| 模式 | 触发条件 | 文件范围 | 正则/匹配 | 测试 |
| --- | --- | --- | --- | --- |
| Controller 直接 SQLAlchemy | `has_added_match` 检测新增行 | `api/controllers/*.py` | 文本 fallback regex（行 167） | 11号 (仅覆盖 `db.session.query` 子集) |
| `console_ns.schema_model` | `has_added_match` 检测新增行 | `api/controllers/*.py` | 字面匹配 `console_ns\.schema_model` | 12号 |
| service/model 隐式 `db.session` | `has_added_match` 检测新增行 | `api/services/*.py`, `api/models/*.py` | `db\.session` 后接 `.` 或 `(`，前缀为非 alnum/`_` | 13号 |
| 旧手写 Console model/service | `is_production_source` 后精确路径匹配 | 全路径 | `web/models/enterprise-marketplace.ts`, `web/models/platform-admin.ts`, `web/service/use-enterprise-marketplace.ts`, `web/service/use-platform-admin.ts` | 14号 |
| 手写 `/console/api` fetch | `has_added_match` 检测新增行 | `web/*` | `fetch\([[:space:]]*['\"]/console/api/` | 未测试 |
| 旧 app context | `has_added_match` 检测新增行 | 路径含 `platform-admin` 或 `enterprise-marketplace` 的 `web/*` 文件 | `(@/context/app-context\|useAppContext[[:space:]]*\()` | 未测试 |

`has_added_match` 使用 `git diff --unified=0` 提取纯新增行后 `grep -Eq`，正确限制在新增代码。 **PASS** — 模式设计正确，但 controller SQLAlchemy 文本 fallback 覆盖不全（见 P1-01）。

### 7. AST guard 调用条件与 fallback

Checker 行 206-215：

```
if [[ "$controller_changed" -eq 1 && "$head_commit" == "$(git rev-parse HEAD)" ]]; then
  if command -v ast-grep >/dev/null 2>&1 || command -v uvx >/dev/null 2>&1; then
    python3 scripts/check_no_new_controller_sqlalchemy.py --base-rev "$base_commit" ...
  else
    printf ... "note: ast-grep is unavailable; the offline direct-SQLAlchemy fallback passed." ...
  fi
fi
```

行为：
- 仅在 `controller_changed=1` 且检查的是 HEAD 时进入
- 仅在 `ast-grep` 或 `uvx` 可用时运行 AST 检查
- 不可用时打印诚实 note，声明 "offline fallback passed"，不声称 AST 检查已运行

在 CI 中：workflow 不安装依赖，`ast-grep`/`uvx` 不可用，会打印 fallback note。此行为诚实——前提是 fallback 覆盖面足够。当前 fallback 未完整覆盖 AST 规则的 26 个 pattern，note 的 "passed" 措辞可能被误读为等效于 AST 检查通过。见 P1-01。

**需改进** (见 P1-01) — 总体设计合理，但 fallback 覆盖面不足。

### 8. 自动 scope checker 与人工 allowlist 边界

ARCHITECT_HANDOFF §5 明确声明：

> 是否增加自动 diff-owner 检查由 B0 在 Builder 开始前形成独立工具决策，但没有自动检查不降低人工门禁。

Checker 实现了：
- 全局 forbidden 路径拦截（docker/volumes、.env、secret、cache、构建产物）
- 生产代码反模式检测（controller SQLAlchemy、旧 contract、隐式 session、手写 fetch 等）

Checker 未实现、也不声称实现了：
- 按 Builder 任务 (B0-B9) 的精确文件所有权自动检查
- Per-Builder diff-owner 匹配

这完全符合 ARCHITECT_HANDOFF 的授权边界。 **PASS**

### 9. OpenAPI 与 Compose 仅 dry-run 命令输出

Checker 行 220-222：

```bash
printf '%s\n' \
  'dry-run only (not executed): pnpm --dir packages/contracts gen-api-contract' \
  'dry-run only (not executed): docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q'
```

这些是纯文本输出，无 eval、无 command substitution。未生成 contracts、未启动 Docker。 **PASS**

### 10. Workflow 配置

| 要求 | 状态 |
| --- | --- |
| `permissions: contents: read` | ✓ 行 18 |
| 不使用 secrets | ✓ 无 `secrets:` 块，无 `${{ secrets.* }}` |
| checkout `persist-credentials: false` | ✓ 行 33 |
| `fetch-depth: 0` (完整历史/tag) | ✓ 行 32 |
| push 分支过滤: `ctyun/replay-116-*`, `codex/enterprise-candidate-*` | ✓ 行 12-14 |
| PR 条件过滤: 同分支前缀 | ✓ 行 22-25，`startsWith` 判断 |
| `workflow_dispatch` 支持 `head-ref` 输入 | ✓ 行 4-10，默认 `HEAD` |
| `ref` 表达式正确处理 push/PR/dispatch 的 head | ✓ 行 34-37 |
| shell 语法检查 (`bash -n`) × 2 | ✓ 行 39-45 |
| 自测运行 | ✓ 行 47-49 |
| 主 checker 运行 | ✓ 行 51-53 |
| 不安装依赖 | ✓ 无 `npm install`/`pip install`/`uv` |
| 不构建镜像 | ✓ 无 Docker build/push |
| 不启动 Docker | ✓ 无 `docker compose up`/`docker run` |

关于 `workflow_dispatch` 的 `head-ref`：`actions/checkout@v4` 切换至指定 ref 后 `HEAD` 自动指向该提交，checker 固定传入 `HEAD` 行为正确，不存在关联缺陷。

**PASS**

### 11. 自测隔离与覆盖率

`check-enterprise-replay-scope-tests.sh`：

- `new_fixture()` 使用 `git clone --quiet --shared --no-tags` 在 `mktemp -d` 临时目录创建隔离仓库
- `trap 'rm -rf "$tmp_root"' EXIT` 保证清理
- 无网络访问（本地 clone）
- 无真实 secret、volume、Docker
- 2 个成功路径 + 14 个失败路径 = 16 个测试
- 失败场景覆盖：docker volumes (rename × 1, delete × 1)、.env、secret key、node_modules、.venv、cache、build artifact、controller SQLAlchemy (仅 `db.session.query` 子集)、legacy contract、implicit session、handwritten Web service、invalid ref、wrong baseline
- `expect_fail` 不仅验证退出码，还验证 stderr 包含特定诊断子串

**PASS** — 但扩展 fallback 后需新增对应 fixture（见 P1-01 整改要求第 2-3 项）。

### 12. 路径绕过、正则漏报、错误 ref、退出码、敏感输出

**路径绕过检查：**

- `classify_forbidden_path` 使用 `case "/$lower/" in */pattern/*)` 的包含式匹配，加斜杠避免部分匹配（如 `node_modules.md` 不走 `*/node_modules/*` 分支，`venv-migration-notes.md` 不走 `*/.venv/*` 分支）
- `.env` 检查通过 `is_safe_env_example` 甄别合法的 `.env.example`/`.env.sample`/`.env.template`
- 无已知绕过路径

**正则漏报检查：**

- 除 controller SQLAlchemy fallback gap (P1-01) 外，其余正则均正确
- `console_ns.schema_model`：字面匹配
- service/model `db.session`：`(^|[^[:alnum:]_])db\.session([.(]|$)` 合理解析
- 手写 fetch：`fetch\([[:space:]]*['"]/console/api/` 覆盖单双引号
- 旧 app context：`(@/context/app-context|useAppContext[[:space:]]*\()` 覆盖 import 和 hook 调用

**错误 ref / 退出码：**

- 无效 base/head ref：`git rev-parse --verify` 失败 → `fail()` → exit 1 ✓
- 错误的基线/merge-base：exit 1 with specific message ✓
- Forbidden path：exit 1 ✓
- Pattern failure：exit 1 ✓
- Usage error：exit 2 ✓
- `set -euo pipefail` 全局生效 ✓

**敏感输出：**

- 路径使用 `%q` 格式化（shell quoting）
- 错误信息不含 secret、key、token
- `fail()` 只输出描述性信息，不回显值

**CI 假通过检查：**

- 脚本内部 `set -euo pipefail` 保证错误退出
- `bash -n` 仅检查语法，不自证正确性；实际正确性由自测保证
- Workflow job 成功仅当所有 steps 退出码为 0

**PASS** (controller SQLAlchemy 正则覆盖率除外，见 P1-01)

## 自动护栏与人工 allowlist 边界

| 维度 | 自动实现 | 人工门禁 |
| --- | --- | --- |
| 全局 forbidden 路径 | `classify_forbidden_path` — 自动拦截 | — |
| 生产代码反模式 | `has_added_match` regex 检测 | — |
| 基线/merge-base 验证 | `OFFICIAL_BASE_COMMIT` 硬编码 + 运行时比较 | Reviewer 确认值正确 |
| AST 级 controller 检查 | 仅当 `ast-grep`/`uvx` 可用时运行；不可用时执行文本 fallback | Reviewer 确认 fallback 覆盖度 |
| Per-Builder diff-owner | 未实现（符合 ARCHITECT_HANDOFF 决策） | 每个 Builder 完成后，人工逐行对比 handoff 矩阵 |
| 新旧代码语义等价 | 未实现（不可自动化） | Reviewer 人工审查 |

边界清晰。当前唯一缺口：文本 fallback 未完整代表 AST guard 的拦截意图（P1-01）。

## 未运行项目及原因

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| `pnpm gen-api-contract` | 未执行 (dry-run only) | B0 checker 仅打印命令名，不生成 contracts。符合 plan — B4 才是唯一生成者 |
| `docker compose config -q` | 未执行 (dry-run only) | B0 阶段不启动 Docker。符合 plan — Phase E 在 B6 完成后执行 |
| `scripts/check_no_new_controller_sqlalchemy.py` (AST) | 未执行 | `controller_changed=0` (B0 不修改 controller)；ast-grep 环境不可用 |
| `flask db heads`/`flask db history` | 未执行 | 不在 B0 范围；ARCHITECT_HANDOFF line 170-171 注明受限网络无法获取锁定 Git 依赖 |

## 最终结论

**CHANGES_REQUIRED** — P1-01 必须解决后重新审查。

B0 的三个 Builder 文件在其他方面质量良好：基线锁定、文件范围、forbidden 路径拦截、name-status 解析、Workflow 配置、自测隔离和 AST fallback 架构均正确。但 `check-enterprise-replay-scope.sh` 行 167 的 controller SQLAlchemy 文本 fallback 仅覆盖 AST 规则 `no_new_controller_sqlalchemy.yml` 有效拦截 pattern 的 19/44（43%），缺失 `add_all`、`begin`、`Session`、`sessionmaker` 和 `select`/`insert`/`update`/`delete`/`text` 等 26 个 pattern。

由于 CI workflow 不安装 ast-grep/uvx 依赖，AST guard 在所有 CI 运行中均不执行。当后续 Builder 引入 controller 变更时，护栏将仅提供不完整的文本验证。这不是理论问题——SQLAlchemy 2.0 的 `select()`/`insert()` API 是现代 controller 代码中最可能出现的直接数据库调用形式，而当前 fallback 完全未覆盖。

**Builder 必须在下一提交中：**

1. 扩充行 167 的文本 fallback regex（或等效实现），覆盖 AST 规则全部有效拦截 pattern
2. 为扩展后的 fallback 新增代表性 fixture 测试
3. 补充 fetch(`/console/api/` 和 legacy app context 检测的 fixture
4. 完善 AST fallback note 措辞，注明已知未覆盖类别

不影响 B0 的其他评价——所有 PASS 项保持不变，仅 controller SQLAlchemy 护栏需补全。

## Review Artifacts

| 文件 | 状态 |
| --- | --- |
| `docs/enterprise/replay-1.16.0/B0_REVIEW.md` | 本文件 — 本轮覆盖写入 (round 2 correction) |
| `.github/workflows/enterprise-replay-guardrails.yml` | Builder 文件 — 未修改 |
| `scripts/ci/check-enterprise-replay-scope.sh` | Builder 文件 — 未修改 |
| `scripts/ci/check-enterprise-replay-scope-tests.sh` | Builder 文件 — 未修改 |
