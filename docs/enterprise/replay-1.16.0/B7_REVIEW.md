# Dify Enterprise 1.16.0 Replay B7 Offline Artifact Chain — Independent Code Review

- **Role**: Code Reviewer（Docker/Offline Reviewer 视角）
- **Instance**: `replay-116-b7-reviewer`
- **Branch**: `ctyun/replay-116-b7-reviewer`
- **HEAD**: `28f9f72e7d93d5f2d1c3ca7b09ed2185836a71fd`
- **Reviewed range**: `a3e4ef617286a475e0b248278c0878aa5adf9d36..28f9f72e7d93d5f2d1c3ca7b09ed2185836a71fd`
- **Reviewed commit**: `28f9f72e7d` "feat: add enterprise B7 offline artifact chain"
- **Reviewed artifact**: 9-file B7 offline artifact chain（见 §REVIEW_RANGE）
- **结论**: `CHANGES_REQUIRED`

本报告是独立 Review 证据。本 Reviewer 未修改任何 product 文件或 denylist 文件；唯一写入
文件是本报告 `docs/enterprise/replay-1.16.0/B7_REVIEW.md`。未执行 commit、amend、push、
merge、rebase、reset、checkout 或 cherry-pick。

---

## RECOVERY

| item | expected | actual | result |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b7-reviewer` | `ctyun/replay-116-b7-reviewer` | PASS |
| HEAD | `28f9f72e7d93d5f2d1c3ca7b09ed2185836a71fd` | `28f9f72e7d93d5f2d1c3ca7b09ed2185836a71fd` | PASS |
| porcelain | empty | empty | PASS |
| `git status --short --branch` | clean | `## ctyun/replay-116-b7-reviewer` | PASS |
| range 唯一 commit | `28f9f72e7d` | `git log a3e4ef6172..HEAD` 唯一 commit `28f9f72e7d` | PASS |

## REVIEW_RANGE

- `git diff --name-status a3e4ef6172..HEAD`：**恰好 9 个路径**

```text
M  docker/envs/core-services/plugin-daemon.env.example
A  scripts/build-enterprise-config-package.ps1
A  scripts/build-enterprise-config-package.sh
A  scripts/build-enterprise-offline.ps1
A  scripts/build-enterprise-offline.sh
A  scripts/ci/check-enterprise-offline-fixtures/bin/fake-docker
A  scripts/ci/check-enterprise-offline-fixtures/bin/fake-git
A  scripts/ci/check-enterprise-offline-tests.sh
A  scripts/ci/check-enterprise-offline.sh
```

- `git diff --stat`：`9 files changed, 1699 insertions(+)`，与契约 **1699 insertions** 一致。
- `git diff --binary | sha256sum`：`36cb3de4c842693211753ad4bf580df7bc5be239c6b68fa8d4c26d3ff32cb40d`，与契约一致。
- `git diff --check a3e4ef6172..HEAD`：clean（exit 0）。
- 无官方 compose/overlay/volumes/真实 .env/业务源码/lockfile 修改；`docker/docker-compose.*.yaml`、`api/**`、`web/**`、`packages/**`、lockfiles 均未触碰。
- `docker/envs/core-services/plugin-daemon.env.example` diff 仅 **+6 行**：追加 `PIP_MIRROR_AUTO_DETECT=true` 及注释、`PIP_MIRROR_URL=` 及注释；`FORCE_VERIFYING_SIGNATURE=true`（line 9）原样保留。无平行 mirror/转发实现。符合 §5.1 透传语义。

## SOURCES_READ

- `docs/enterprise/replay-1.16.0/B7_IMPLEMENTATION_PLAN.md`、`B7_IMPLEMENTATION_PLAN_REREVIEW.md`
- `docs/enterprise/replay-1.16.0/VALIDATION_PLAN.md`（Phase E/F/G/H）
- `docs/enterprise/replay-1.16.0/PATCH_DECISION_MATRIX.md`（抽查 E10/E11/C05 引用）
- 提交的全部 9 个文件（逐行）
- 旧 1.15 只读证据：`dify-enterprise-1.15.0/scripts/build-enterprise-offline.sh`、`build-enterprise-offline.ps1`
- 仓库事实：`docker/envs/**/*.env.example` 计数（37）、`docker/envs/core-services/plugin-daemon.env.example`

## CHECKLIST VERIFICATION

### 1. Scope — PASS

diff 恰好 9 个 allowlist 路径，1699 insertions，diff SHA 与契约逐字节一致。plugin-daemon
env 示例只追加 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL` 两 knob，`FORCE_VERIFYING_SIGNATURE`
保留；无其他 env 示例/官方 compose/overlay/volumes/业务源码/lockfile 改动。

### 2. Reuse gate + docker build/pull/save 路径 — PASS

`scripts/build-enterprise-offline.sh`:

- reuse 门禁（`ensure_enterprise_image`/`build_enterprise_web_image`，line 119–156）：`docker image inspect`
  必须成功且 `COMMIT_SHA` == 期望 tag（`is_reusable_image` line 111–117，`get_image_commit_sha`
  line 105–109）；缺失或不匹配 → `exit 1` "not reusable"。`-CheckOnly` 与 `Mode=reuse` 都先于
  `docker build` 返回（line 125–132、151–158）。
- 依赖镜像 loop（line 230–241）：本地存在则复用；缺失时 `-CheckOnly` 只打印 dry-run 提示
  （line 234–235），非 dry-run 才 `docker pull`（line 237–239）——pull 仅限构建机、仅限依赖
  镜像，符合计划 §4.1。
- `docker save`（line 305）在 `-CheckOnly`（line 297–302 exit 0）之后，dry-run 绝不 save。
- `rg -n "docker build|docker pull|docker save|docker compose up|--pull never"`：build/pull/save
  仅出现在上述受保护路径；**无** `docker compose up`、**无** `--pull never`。S-10 保持。

`.ps1`（`build-enterprise-offline.ps1`）：`$CheckOnly -or $Mode -eq "reuse"` 分支先于 build
（line 106–112）；依赖 pull 由 `$CheckOnly` 守卫（line 180–186）；`docker save` 在 `$CheckOnly`
return（line 246–251）之后。行为与 `.sh` 一致。

### 3. images-*.txt == config --images | sort -u；required-image 断言 — PASS

`IMAGES = config --images | sed 去空行 | sort -u`（line 188–194），`printf '%s\n' "${IMAGES[@]}" >
"$IMAGES_PATH"`（line 247）——结构上即两层 Compose `config --images | sort -u`。断言（line
201–228）：企业 API tag 恰好一个且四 runtime 解析 4 次、企业 Web tag 恰 1 次、`langgenius/
dify-agent-backend:1.16.0` 与 `langgenius/dify-agent-local-sandbox:1.16.0` 必须出现。fixture 用
shim 断言 images 文件与 `config --images | sort -u` 相等且含 Agent 两镜像与企业 tag（PASS）。

### 4. Manifest schema — PASS

line 251–292：`version`、`baseline{tag,commit}`、`enterprise_commit`（`git rev-parse HEAD`）、
`image_tag`、`generated_at`（UTC ISO-8601）、`images[]{name,id,digest}`。`baseline` 固定为
`1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`（与 VALIDATION_PLAN 硬门禁 1 一致）。
`digest` 用 `{{index .RepoDigests 0}}`，`<no value>`/错误 → `""` 如实记录，不伪造。`.ps1`
（line 197–241）字段相同。fixture 断言 schema 完整且 `enterprise_commit` 来自 fake-git shim。

### 5. Config package 文件集 / 排除 — PASS

`build-enterprise-config-package.sh`：依赖 manifest+images 存在否则失败（line 33–37）；文件集 =
compose×2 + `.env.example` + 全部 37 个 `docker/envs/**/*.env.example`（`find` 全量）+ 两个目录
`docker/nginx`、`docker/ssrf_proxy` + `dist/offline/manifest-*.json` + `images-*.txt`（line
39–54）。tar `--exclude`：`*.env`、`*.env.production`、`docker/volumes`、`docker/volumes/*`、
`.git`、`.git/*`、`.cache`、`*/.cache/*`、`node_modules`、`*/node_modules/*`、`.venv`、
`*/.venv/*`、`.next`、`*/.next/*`（line 80–93）。无 1.15 专属文件、无 B8 前向依赖
（vector checker 属 B8，未引入）。`.ps1` 排除集与断言一致（line 59–76）。fixture 断言含 37
个 env 示例、无被禁条目、无 1.15-only 文件（PASS）。

### 6. check-enterprise-offline.sh 扫描覆盖 — 见 FINDINGS（B7R-01）

覆盖：images 文件（非空 + required-image + secret）、manifest（schema + 与 images 一致 +
secret）、config archive（listable + forbidden_path + 1.15-only + required 条目 + 全 env 示例 +
提取后 dev-default WARNING 相邻校验）、image bundle（顶层 docker-save 布局 + forbidden_path +
逐 layer `tar tzf` 扫描，不可列 layer 如实 NOT_RUN）、S-8 real-secret（无 pattern 文件时如实
NOT_RUN）。`forbidden_path` 覆盖 `docker/volumes`、`node_modules`、`.venv/venv`、cache、
`.git`、`.secrets`/`secrets`、dist/build/.next/coverage、真实 `.env`、credential/key 文件。

### 7. Fixture 测试 / dry-run / NOT_RUN — PASS（附 B7R-02 观察）

- `scripts/ci/check-enterprise-offline-tests.sh`：**17/17 PASS**，exit 0。
  - reuse 门禁：缺失镜像拒绝、COMMIT_SHA 不匹配拒绝、匹配通过且无 build/pull。
  - `-CheckOnly`：fake-docker 日志断言无 `docker build/pull/save`；写 images+manifest；不写 bundle。
  - image list == `config --images | sort -u`；manifest schema（含 fake-git commit）。
  - config 包缺 manifest/images 失败；config 包内容 37 env 示例 + compose + nginx/ssrf_proxy；无被禁条目。
  - check 脚本负向：真实 `.env`、dev-default 无 WARNING、`docker/volumes` 条目、空 images 均拒绝。
- 无伪造运行证据：manifest/digest 全部来自 shim；真实离线产物（`dist/offline/**`）本运行不生成。
- Phase F/G/H（`docker compose build/up`、`docker load`、`--pull never` smoke、五 runtime image
  ID 断言）**NOT_RUN**（另授权）；bundle 缺失时 check 脚本对 archive 段如实 `NOT_RUN`。
- `.ps1` 运行时 **NOT_RUN**（无 Windows/PowerShell 环境；未冒充等价已验证）。

### 8. 旧 1.15 链对照

`build-enterprise-offline.sh` 保留 1.15 的 `-Version/-OutputDir/-Mode`、`get_image_commit_sha`/
`is_reusable_image`、`smart/rebuild/reuse` 语义与 web 临时 context（build 路径）；manifest 扩展
baseline/enterprise_commit/image_tag/逐镜像 id/digest；依赖 pull 加 `-CheckOnly` dry-run 分支；
`api_count==4`/`web_count==1`/tag 唯一/Agent 两镜像 required-image 断言为新增。1.15 的 config
脚本（含 dify-env-sync、vector checker、1.15 文档）未移植，符合 §2.3 DROP_FROM_B7。

## FINDINGS

### B7R-01 — P2 — `scripts/ci/check-enterprise-offline.sh` S-8 真实 secret 扫描未覆盖打包内容

- **位置**: `scripts/ci/check-enterprise-offline.sh:150-176`（`scan_content_secrets`）、
  `:204`（images 文件）、`:255`（manifest）、`:426-434`（S-8 段）。
- **证据**: `scan_content_secrets` 只被调用于 images 文件与 manifest。config archive 提取后的
  每个成员（line 333–351）只做 `DEV_AGENT_SECRET` + WARNING 相邻校验，**不**用 `SECRETS_PATTERN`
  扫描；image bundle 逐 layer 内容（line 398–414）同样不跑 pattern 扫描。S-8 段（line 426–434）
  在 `-SecretsPattern` 提供且文件存在时打印 `PASS: real-secret pattern scan configured from
  protected environment`，但此时除 images/manifest 外没有任何打包内容被真实 pattern 扫描。
- **违反的 invariant**: B7_IMPLEMENTATION_PLAN §6 S-8「真实 secret 不进入任何打包内容——
  pattern 文件从受保护环境构造……扫描只输出目标+命中布尔」；§7.3 要求扫描命令覆盖 S-5…S-8
  （config tar、image bundle、manifest）。
- **修复边界**: 在 config archive 提取循环内对每个普通成员追加 `scan_content_secrets`；在
  bundle 段对每个可列 layer 条目同样追加；仅在确实对打包内容执行过 pattern 扫描后才计入 S-8
  PASS。禁止改动文件集、其他检查段或 check 脚本参数契约。
- **阻塞**: 是。本轮无受保护 pattern 文件，S-8 如实 NOT_RUN 满足「诚实」要求；但代码对 S-8
  的实现会在提供 pattern 文件时产生虚假信心（声称 configured 却未扫 archive/bundle）。作为
  安全门禁的落地缺陷列为 P2，需修复后 Rereview。

### B7R-02 — P3 — fixture 测试未覆盖 image bundle 扫描段

- **位置**: `scripts/ci/check-enterprise-offline-tests.sh:272-283`（clean-artifacts 用例）。
- **证据**: clean-artifacts 用例复用 `config-content` fixture，而该 fixture 的离线前置步骤是
  `-CheckOnly`（line 226），从不生成 `dify-enterprise-offline-*.tar`；三个 canary 负向用例传入的
  `-Archive` 路径同样不存在。因此 `check-enterprise-offline.sh` 第 4 段（bundle 顶层布局 +
  forbidden 条目 + 逐 layer 扫描）在自动化套件中只被 NOT_RUN 分支覆盖。本 Reviewer 用 shim 构造
  真实 bundle 后手动验证该段可正确工作（bundle listable/layout/forbidden/layer-scan 均 PASS），
  结论是**测试覆盖缺口而非代码缺陷**。
- **修复边界**: 在 tests.sh 增加一个完整 `-Mode reuse`（非 CheckOnly）产物 fixture，再对
  `-Archive` 指向真实 bundle 跑一次 check 脚本正例。

### B7R-03 — P3 — dev-default WARNING 校验为「同文件」而非「相邻」

- **位置**: `scripts/ci/check-enterprise-offline.sh:332-351`。
- **证据**: 校验只要求同一文件内存在 `WARNING`/`Replace this development default in production`
  之一，不要求与默认值相邻。计划 §4.6「必须相邻 WARNING」。官方 env 示例当前均为相邻布局，
  无实际绕过，但实现弱于计划语义。

### B7R-04 — P3 — check 脚本硬编码 1.16.0-enterprise

- **位置**: `scripts/ci/check-enterprise-offline.sh:56-61`（`REQUIRED_IMAGES`）。
- **证据**: required images 与 config required 条目固定 `dify-api-enterprise:1.16.0-enterprise`
  等；无 `-Version` 参数。非 1.16.0-enterprise 版本构建的 images/manifest 会被该固定门禁拒绝。
  对 1.16 发布门禁可接受，但与 build/config 脚本的版本参数化不对称。

### B7R-05 — P3 — ps1 产物存在 UTF-8 BOM 风险（Windows PowerShell 5.1）

- **位置**: `scripts/build-enterprise-offline.ps1:193,241`。
- **证据**: `Set-Content -Encoding UTF8` 在 Windows PowerShell 5.1 下写 BOM；首行 BOM 会破坏
  `check-enterprise-offline.sh:194` 的 `grep -Fxq` 精确匹配与 `json.load`。PowerShell 7+ 无 BOM。
  `.ps1` 运行时已如实 NOT_RUN，属被接受的 Windows 运维路径限制；若未来维护需改用无 BOM 写入。

### B7R-06 — P3 — `forbidden_path` 不拦裸 `docker/volumes` 目录项

- **位置**: `scripts/ci/check-enterprise-offline.sh:89-117`。
- **证据**: `*/docker/volumes/*` 要求尾部斜杠后有内容，裸 `docker/volumes`（无尾斜杠）不命中。
  配置包经显式文件集 + tar `--exclude` 实际不会产生该条目，属防御纵深弱项。

## VERDICT

**CHANGES_REQUIRED** —— 范围精确（9 路径 / 1699 insertions / diff SHA 一致）、reuse 门禁与
`-CheckOnly` 禁止 build/pull/save、required-image 断言、manifest schema、config 包文件集与排除、
fixture 17/17 均通过；无未授权写入。但存在 **1 个未关闭 P2**（B7R-01：S-8 真实 secret 扫描未
覆盖 config/bundle 内容，安全门禁落地缺陷），按 PASS 标准（无开放 P0/P1/P2）判定
**CHANGES_REQUIRED**。修复后需独立 Rereview。

## VERIFICATION COMMAND LOG

| Command | Exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b7-reviewer` |
| `git rev-parse HEAD` | 0 | `28f9f72e7d93d5f2d1c3ca7b09ed2185836a71fd` |
| `git status --short --branch` | 0 | clean |
| `git status --porcelain=v1` | 0 | empty |
| `git diff --name-status a3e4ef6172..HEAD` | 0 | 恰好 9 个 allowlist 路径 |
| `git diff --stat a3e4ef6172..HEAD` | 0 | 9 files, 1699 insertions(+) |
| `git diff --check a3e4ef6172..HEAD` | 0 | clean |
| `git diff --binary a3e4ef6172..HEAD \| sha256sum` | 0 | `36cb3de4c842693211753ad4bf580df7bc5be239c6b68fa8d4c26d3ff32cb40d` |
| `scripts/ci/check-enterprise-offline-tests.sh` | 0 | 17/17 PASS |
| `bash -n` ×4 脚本 | 0 | SYNTAX_OK |
| `rg -n "docker build\|docker pull\|docker save\|docker compose up\|--pull never"` | 0 | build/pull/save 仅受保护路径；无 up/`--pull never` |
| `git log a3e4ef6172..HEAD` | 0 | 唯一 commit `28f9f72e7d` |
| `git diff --check`（worktree） | 0 | clean |
| `git status --short --branch`（final） | 0 | clean |

### NOT_RUN（如实声明）

| Area | Status |
| --- | --- |
| 真实两层 Compose `config --images` 与 live `docker/.env` 展开比对 | NOT_RUN（无 `docker/.env`/daemon；结构一致由构造 + fixture shim 保证） |
| 真实 `docker save` 离线 bundle / config tar 生成 | NOT_RUN（Phase F/G/H 另授权） |
| `check-enterprise-offline.sh` 对真实离线产物全量扫描 | NOT_RUN（产物不存在；已用 shim 构造 bundle 手动验证扫描段 9 PASS） |
| S-8 真实 secret 扫描 | NOT_RUN（无受保护环境 pattern 文件；代码落地缺陷见 B7R-01） |
| `.ps1` 运行时 | NOT_RUN（无 Windows/PowerShell） |
| Phase F/G/H（compose build/up、`docker load`、`--pull never` smoke、五 runtime image ID 断言） | NOT_RUN（另授权） |
| `docker/volumes/**` 访问或复制 | NOT_RUN（禁止） |

Pass/Fail/NOT_RUN: **24 PASS / 0 FAIL / 6 NOT_RUN**（命令层面）；Finding 层面 1×P2 + 5×P3。

`git diff --check` result: **clean (exit 0)** for the reviewed range and the worktree.

Current `git status`: clean（`## ctyun/replay-116-b7-reviewer`，porcelain 空）。

## DECLARATION

- 未执行 commit、amend、push、merge、rebase、reset、checkout 或 cherry-pick；未创建 PR。
- 唯一写入文件为本报告 `docs/enterprise/replay-1.16.0/B7_REVIEW.md`；未修改任何 product 文件、
  denylist 文件、`docker/volumes/**` 或真实 `.env`；未访问/复制 volume、未启动 Docker 服务、
  未触碰外部系统/数据库/远程。
