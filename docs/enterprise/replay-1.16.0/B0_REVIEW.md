# B0 Review: Enterprise Replay Guardrails

## 审查身份

| 属性 | 值 |
| --- | --- |
| Reviewer | B0 Reviewer (独立) |
| 审查分支 | `ctyun/replay-116-b0-reviewer` |
| 审查日期 | 2026-07-24 |
| Builder 范围 | `d9089773e89d24cd0404a76bb840bfbf7069a854..1b8df896f75f520ed7f17143e0752a2009533927` |
| 最终结论 | **PASS** |

## 基线与提交

| 项目 | 值 |
| --- | --- |
| 官方标签 | `1.16.0` |
| 官方提交 | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| merge-base | `5c6372d2f76d240265b92fd27c16bc772ffcb107` |
| Builder 起点 | `d9089773e89d24cd0404a76bb840bfbf7069a854` (`docs: correct enterprise 1.16.0 gate review chain`) |
| Builder 终点 (HEAD) | `1b8df896f75f520ed7f17143e0752a2009533927` (`ci: harden enterprise replay guardrails`) |
| 中间提交 | `e3e25ecae1` (`ci: add enterprise replay guardrails`) |

验证命令：

```bash
$ git branch --show-current
ctyun/replay-116-b0-reviewer

$ git rev-parse HEAD
1b8df896f75f520ed7f17143e0752a2009533927

$ git status --porcelain
(空)

$ git merge-base 1.16.0 HEAD
5c6372d2f76d240265b92fd27c16bc772ffcb107
```

全部匹配预期。工作区干净。

## 实际文件范围

```bash
$ git diff --name-status d9089773e89d24cd0404a76bb840bfbf7069a854..HEAD
A  .github/workflows/enterprise-replay-guardrails.yml
A  scripts/ci/check-enterprise-replay-scope-tests.sh
A  scripts/ci/check-enterprise-replay-scope.sh

$ git diff --stat d9089773e89d24cd0404a76bb840bfbf7069a854..HEAD
 .github/workflows/enterprise-replay-guardrails.yml |  53 +++++
 scripts/ci/check-enterprise-replay-scope-tests.sh  | 176 ++++++++++++++++
 scripts/ci/check-enterprise-replay-scope.sh        | 222 +++++++++++++++++++++
 3 files changed, 451 insertions(+)
```

严格符合 ARCHITECT_HANDOFF §5 规定的 B0 Allowed write paths:
- `.github/workflows/enterprise-replay-*` ✓
- `scripts/ci/check-enterprise-replay-*` ✓

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
$ git diff --check d9089773e89d24cd0404a76bb840bfbf7069a854..HEAD && echo "DIFF CHECK OK"
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

16/16 全部通过。

### 主 Checker 运行

```bash
$ scripts/ci/check-enterprise-replay-scope.sh 1.16.0 HEAD
enterprise replay scope check passed
baseline: 5c6372d2f76d240265b92fd27c16bc772ffcb107
range: 5c6372d2f76d240265b92fd27c16bc772ffcb107...1b8df896f75f520ed7f17143e0752a2009533927
dry-run only (not executed): pnpm --dir packages/contracts gen-api-contract
dry-run only (not executed): docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
```

当前 diff（仅 B0 新增的 3 个文件）通过所有检查。

## P0/P1/P2 Findings

### P0 — 无 (0)

未发现 P0 问题：基线锁定、文件范围、merge-base 验证、路径解析、forbidden 拦截、生产模式检查均正确。

### P1 — 无 (0)

无 P1 问题。AST guard 的 fallback 行为诚实，无依赖安装、无 Docker 启动、无 secrets 使用。

### P2 — 2 项 (minor)

| ID | 严重级别 | 位置 | 描述 |
| --- | --- | --- | --- |
| P2-01 | P2 | `scripts/ci/check-enterprise-replay-scope-tests.sh` (无对应测试) | 自测未覆盖两处生产模式正则：(a) `fetch('/console/api/` 手写 fetch 检测 (checker 行 187-190)；(b) `@/context/app-context` / `useAppContext(` 旧 app context 检测 (checker 行 192-196)。正则本身正确，仅缺测试用例。建议：在后续迭代中补充 `handwritten-console-fetch` 和 `legacy-app-context` 两个 fixture 测试。 |
| P2-02 | P2 | `.github/workflows/enterprise-replay-guardrails.yml` 行 53 | `workflow_dispatch` 输入 `head-ref` 默认值为 `HEAD` (字符串)，checker 调用固定传入 `HEAD`。若通过 `workflow_dispatch` 指定了非 HEAD 的 ref (`head-ref: feature-branch`)，checkout ref 会正确切换，但 checker 参数 `HEAD` 仍正确指向当前 checkout 的 HEAD。行为一致，仅为可选可读性优化：若未来需要支持非 HEAD dispatch ref，可在 workflow 中通过 `github.event.inputs['head-ref']` 透传。当前不阻塞。 |

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

测试覆盖了带空格的路径 rename (test #3: `safe/original name.txt` → `docker/volumes/runtime data.txt`)。路径中 `/`、空格、特殊字符均被 `-z` + `%q` 正确处理。 **PASS**

### 4. 拒绝 forbidden 路径

`classify_forbidden_path` 通过 `case "/$lower/" in` 做包含式匹配：

| 类别 | 匹配模式 | 测试覆盖 |
| --- | --- | --- |
| `docker/volumes/*` | `*/docker/volumes/*` | Test #3 (rename), #4 (delete) |
| `.env` (非 example) | basename `.env`, `.env.*`, `*.env`，通过 `is_safe_env_example` 排除 `.env.example`/`.env.sample`/`.env.template` | Test #5 |
| secret/key/credential | basename 匹配 `credentials.json`, `service-account*.json`, `id_rsa`, `*.pem`, `*.key`, `*.p12`, `*.pfx`；目录匹配 `*/.secrets/*`, `*/secrets/*` | Test #6 |
| `node_modules` | `*/node_modules/*` | Test #7 |
| `.venv`/`venv` | `*/.venv/*`, `*/venv/*` | Test #8 |
| cache | `*/.cache/*`, `*/.pytest_cache/*`, `*/.mypy_cache/*`, `*/.ruff_cache/*`, `*/.uv-cache/*`, `*/__pycache__/*`, `*/.turbo/*`, `*/.pnpm-store/*`, `*/.yarn/cache/*` | Test #9 |
| build/dist/.next/coverage | `*/.next/*`, `*/build/*`, `*/dist/*`, `*/coverage/*`, `*/htmlcov/*` | Test #10 |
| 编译产物 | basename 匹配 `*.pyc`, `*.pyo`, `*.class`, `*.o`, `*.so` | 未独立测试但正则正确 |

`is_safe_env_example` 对 full path 做后缀匹配，`docker/envs/agent.env.example` 可通过；`config/.env.production` 被拒绝。 **PASS**

### 5. 避免文档/测试/文件名误报

`is_production_source` (行 134-146) 将 checker 的生产模式检测限定在 `api/*.py`、`web/*.{js,jsx,ts,tsx}`，并显式排除 `api/tests/*`、`api/**/tests/*`、`web/**/__tests__/*`、`*.spec.*`、`*.test.*`。

Test #1 ("legal CI and documentation changes") 验证 `.md` 文件中出现 `db.session`、`console_ns.schema_model` 不会触发误报，以及路径包含 `venv` 作为文档名不被标记。 **PASS**

### 6. 生产代码模式检查

Checker 行 148-201：

| 模式 | 触发条件 | 文件范围 | 正则/匹配 | 测试 |
| --- | --- | --- | --- | --- |
| Controller 直接 SQLAlchemy | `has_added_match` 检测新增行 | `api/controllers/*.py` | `db.paginate`, `db.session.(query\|execute\|...)`, bare `session.(query\|execute\|...)`，要求前缀为非 alnum/`_`，后缀为 `(` 或行尾 | Test #11 |
| `console_ns.schema_model` | `has_added_match` 检测新增行 | `api/controllers/*.py` | 字面匹配 `console_ns\.schema_model` | Test #12 |
| service/model 隐式 `db.session` | `has_added_match` 检测新增行 | `api/services/*.py`, `api/models/*.py` | `db\.session` 后接 `.` 或 `(`，前缀为非 alnum/`_` | Test #13 |
| 旧手写 Console model/service | `is_production_source` 后精确路径匹配 | 全路径 | `web/models/enterprise-marketplace.ts`, `web/models/platform-admin.ts`, `web/service/use-enterprise-marketplace.ts`, `web/service/use-platform-admin.ts` | Test #14 |
| 手写 `/console/api` fetch | `has_added_match` 检测新增行 | `web/*` | `fetch\([[:space:]]*['\"]/console/api/` | 未覆盖 (P2-01) |
| 旧 app context | `has_added_match` 检测新增行 | 路径含 `platform-admin` 或 `enterprise-marketplace` 的 `web/*` 文件 | `(@/context/app-context\|useAppContext[[:space:]]*\()` | 未覆盖 (P2-01) |

`has_added_match` 使用 `git diff --unified=0` 提取纯新增行后 `grep -Eq`，正确限制在新增代码。所有正则要求 `has_added_match` 只匹配 `+` 行 (删除了 `+++` 文件头行)。 **PASS** (含 P2-01 注记)

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

在 CI 中：workflow 不安装依赖，`ast-grep`/`uvx` 不可用，会打印 fallback note。由于 B0 不修改任何 controller，`controller_changed=0`，此块根本不进入，note 不会出现。 **PASS** — 行为诚实、安全。

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

**PASS**

### 11. 自测隔离与覆盖率

`check-enterprise-replay-scope-tests.sh`：

- `new_fixture()` 使用 `git clone --quiet --shared --no-tags` 在 `mktemp -d` 临时目录创建隔离仓库
- `trap 'rm -rf "$tmp_root"' EXIT` 保证清理
- 无网络访问（本地 clone）
- 无真实 secret、volume、Docker
- 覆盖：success path × 3 (当前 diff、合法 CI/docs 变更、错误的 ref/基线)；failure path × 13 (docker volumes × 2、.env、secret key、node_modules、.venv、cache、build artifact、controller SQLAlchemy、legacy contract、implicit session、handwritten Web service、invalid ref、wrong baseline)
- `expect_fail` 不仅验证退出码，还验证 stderr 包含特定诊断子串

**PASS** (含 P2-01 注记：缺 2 个 pattern 测试)

### 12. 路径绕过、正则漏报、错误 ref、退出码、敏感输出

**路径绕过检查：**

- `classify_forbidden_path` 使用 `case "/$lower/" in */pattern/*)` 的包含式匹配，加斜杠避免部分匹配（如 `node_modules.md` 不走 `*/node_modules/*` 分支，`venv-migration-notes.md` 不走 `*/.venv/*` 分支）
- `.env` 检查通过 `is_safe_env_example` 甄别合法的 `.env.example`/`.env.sample`/`.env.template`
- 无已知绕过路径

**正则漏报检查：**

- Controller SQLAlchemy 正则：`(^|[^[:alnum:]_])` 前缀防止 `mydb.session`、`_db.session` 误匹配；`([[:space:]]*\(|$)` 后缀确保是调用形式
- `console_ns.schema_model`：字面匹配，覆盖 dot access
- 无已知漏报

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

- Workflow 中的 `set -euo pipefail` 未显式设置（脚本自带），但脚本内部 `set -euo pipefail` 保证错误退出
- `bash -n` 仅检查语法，不自证正确性；实际正确性由自测保证
- Workflow job 成功仅当所有 steps 退出码为 0

**PASS**

## 自动护栏与人工 allowlist 边界

| 维度 | 自动实现 | 人工门禁 |
| --- | --- | --- |
| 全局 forbidden 路径 | `classify_forbidden_path` — 自动拦截 | — |
| 生产代码反模式 | `has_added_match` regex 检测 | — |
| 基线/merge-base 验证 | `OFFICIAL_BASE_COMMIT` 硬编码 + 运行时比较 | Reviewer 确认值正确 |
| AST 级 controller 检查 | 仅当 `ast-grep`/`uvx` 可用时运行；不可用时诚实 fallback | 需要时 Reviewer 手动运行 |
| Per-Builder diff-owner | 未实现（符合 ARCHITECT_HANDOFF 决策） | 每个 Builder 完成后，人工逐行对比 handoff 矩阵 |
| 新旧代码语义等价 | 未实现（不可自动化） | Reviewer 人工审查 |

边界清晰：自动检查覆盖语法级/路径级/模式级违规；语义级和架构级决策由人工 Reviewer 对照 ARCHITECT_HANDOFF 矩阵执行。这与 ARCHITECT_HANDOFF §5 的声明完全一致。

## 未运行项目及原因

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| `pnpm gen-api-contract` | 未执行 (dry-run only) | B0 checker 仅打印命令名，不生成 contracts。符合 plan — B4 才是唯一生成者 |
| `docker compose config -q` | 未执行 (dry-run only) | B0 阶段不启动 Docker。符合 plan — Phase E 在 B6 完成后执行 |
| `scripts/check_no_new_controller_sqlalchemy.py` (AST) | 未执行 | controller_changed=0 (B0 不修改 controller)；ast-grep 环境不可用 |
| `flask db heads`/`flask db history` | 未执行 | 不在 B0 范围；ARCHITECT_HANDOFF line 170-171 注明受限网络无法获取锁定 Git 依赖 |

## 最终结论

**PASS** — B0 基线与安全护栏通过独立审查。

3 个文件严格处于 ARCHITECT_HANDOFF 规定的 B0 allowlist 内，无业务代码、Docker、migration 或依赖修改。官方基线 `5c6372d2f76d240265b92fd27c16bc772ffcb107` 被硬编码锁定并运行时验证。16 个自测全部通过，覆盖成功/失败路径。Workflow 仅使用 `contents: read` 权限，不安装依赖、不构建镜像、不启动 Docker。AST guard 的 fallback 行为诚实且安全。OpenAPI/Compose 仅作为 dry-run 文本输出。

2 个 P2 注记（缺少 fetch 和 app-context 模式的测试用例）不阻塞合并，建议后续迭代补充。

## Review Artifacts

| 文件 | 状态 |
| --- | --- |
| `docs/enterprise/replay-1.16.0/B0_REVIEW.md` | 本文件 — 唯一新增 |
| `.github/workflows/enterprise-replay-guardrails.yml` | Builder 文件 — 未修改 |
| `scripts/ci/check-enterprise-replay-scope.sh` | Builder 文件 — 未修改 |
| `scripts/ci/check-enterprise-replay-scope-tests.sh` | Builder 文件 — 未修改 |
