# Dify Enterprise 1.16.0 Replay B7 Offline Artifact Chain — Independent Rereview

- **Role**: Rereviewer（Docker/Offline Reviewer 视角）
- **Instance**: `replay-116-b7-rereviewer`
- **Branch**: `ctyun/replay-116-b7-rereviewer`
- **HEAD**: `bb86a5e8aa85ca6fedbbf42004fd232074ae9ba3`
- **Reviewed commit**: `bb86a5e8aa` "fix: close B7 S-8 and bundle scan findings"
- **Fixer range**: `93ab820b48b78e39ca197fc2391e30b0de4a3ead..bb86a5e8aa85ca6fedbbf42004fd232074ae9ba3`
- **结论**: `PASS`

本报告是独立 Rereview 证据。本 Rereviewer 未修改任何 product 文件、fixture 或 denylist 文件；
唯一写入文件是本报告 `docs/enterprise/replay-1.16.0/B7_REREVIEW.md`。未执行 commit、amend、
push、merge、rebase、reset、checkout 或 cherry-pick。

---

## RECOVERY

| item | expected | actual | result |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b7-rereviewer` | `ctyun/replay-116-b7-rereviewer` | PASS |
| HEAD | `bb86a5e8aa85ca6fedbbf42004fd232074ae9ba3` | `bb86a5e8aa85ca6fedbbf42004fd232074ae9ba3` | PASS |
| porcelain | empty | empty | PASS |
| `git status --short --branch` | clean | `## ctyun/replay-116-b7-rereviewer` | PASS |
| fixer 范围唯一 commit | `bb86a5e8aa` | `git log 93ab820b48..HEAD` 唯一 commit `bb86a5e8aa` | PASS |

## FIXER_RANGE

- `git diff --name-status 93ab820b48..HEAD`：**恰好 2 个 allowlist 路径**

```text
M  scripts/ci/check-enterprise-offline-tests.sh
M  scripts/ci/check-enterprise-offline.sh
```

- `git diff --stat`：`2 files changed, 82 insertions(+), 8 deletions(-)`，与契约 **+82/-8** 一致。
- `git diff --binary | sha256sum`：`0bba9bc67d5d672a7407ad9134625583ca09682f2d39bf18f181b716f7330f84`，与契约一致。
- `git diff --check 93ab820b48..HEAD`：clean（exit 0）。
- 范围无 product 文件、fixture、docker/api/web/packages/dify-agent、B7_REVIEW.md 或其他报告触碰
  （`git diff 93ab820b48..HEAD -- docs/` 为空）。

## B7R-01 DISPOSITION — 已关闭（实现完整）

**现状（`scripts/ci/check-enterprise-offline.sh`）**：

1. **config archive 每个普通成员 pattern 扫描**：提取循环（line 341–374）在既有 dev-default +
   WARNING 校验之外，对每个 `[[ -f ]]` 成员追加 `scan_content_secrets`（line 365–369），命中计数
   `config_members_hit`，干净计数 `config_members_clean`。
2. **image bundle 每个可列 layer 文件 pattern 扫描**：layer 段（line 405–451）对每个可列
   `layer.tar` 先 `tar xzf` 提取内容（line 428），再 `find -type f -print0` 逐文件
   `scan_content_secrets`（line 429–435），命中计数 `layer_scan_hits`，干净 layer 计数
   `layer_scan_passes`；layer 无法列出/提取时如实 NOT_RUN（line 437–441、447–450）。
3. **S-8 三态**（line 464–476）：
   - pattern 文件不存在 → `fail`；
   - `config_members_hit>0 || layer_scan_hits>0` → `fail "real-secret pattern scan (S-8) found
     secrets in packaged content"`；
   - `config_members_clean>0 && layer_scan_passes>0` → `pass "real-secret pattern scan (S-8) clean
     for images, manifest, config archive members, and image bundle layers"`；
   - 否则 → `notrun "covered no packaged content"`。
   S-8 PASS 仅在实际对 config 成员与可列 layer 均执行过 pattern 扫描且干净后给出。
4. **参数契约不变**：`-Archive/-ConfigArchive/-Manifest/-Images/-SecretsPattern` 解析与 required
   校验（line 5–46）逐字节未改。
5. 配套豁免：`scan_content_secrets` 内 dev-default 命中需 WARNING marker 才免 FAIL（line 171–184）。
   该豁免为 B7R-01 必需——config 成员合法包含带 WARNING 的 dev-default env 示例，无此豁免全部误
   FAIL；且负向用例 `check rejects dev default secret without WARNING` 仍通过（无回归）。

独立行为验证（真实 bundle fixture，`-SecretsPattern`）：见下文「独立 S-8 行为检查」。

## B7R-02 DISPOSITION — 已关闭（测试覆盖到位）

`scripts/ci/check-enterprise-offline-tests.sh`（line 285–315）新增 `bundle-positive` fixture：

1. 以 `-Mode reuse`（非 CheckOnly）跑 `build-enterprise-offline.sh`，fake-docker `save` 写出真实
   `dify-enterprise-offline-1.16.0-enterprise.tar`（含 manifest.json + repositories + 真实
   `ab12cd34/layer.tar`，其中含 `layer.txt` 内容）；
2. 以同一 reuse 产物跑 `build-enterprise-config-package.sh` 产出 config tar.gz；
3. 对真实 bundle/config/manifest/images 跑 `check-enterprise-offline.sh -Archive ...`，并断言输出
   含 4 个 marker：`image bundle archive is listable`、`image bundle has a docker-save top-level
   layout`、`image bundle contains no forbidden paths`、`image bundle layer scans clean`。

该用例使 bundle 段（listable/layout/forbidden/layer-scan）由真实产物驱动，非 NOT_RUN 分支。

## NO SCOPE EXPANSION — PASS

- 范围恰好 2 个 allowlist 文件、+82/-8、diff SHA 与契约一致（见 FIXER_RANGE）。
- 无 product 文件、fixture、review 报告被触碰。
- 本 Rereviewer 工作树未发生任何 commit/amend/push；fixer 工作树历史仅 `bb86a5e8aa` 一个
  fixer commit（受审对象本身），无额外未授权写入。

## FULL FOCUSED VERIFICATION — 全部通过

| Command | Exit | Result |
| --- | ---: | --- |
| `bash -n scripts/ci/check-enterprise-offline.sh scripts/ci/check-enterprise-offline-tests.sh` | 0 | SYNTAX_OK ×2 |
| `scripts/ci/check-enterprise-offline-tests.sh` | 0 | **21/21 PASS** |
| `git diff --check 93ab820b48..HEAD` | 0 | clean |
| `git diff --check`（worktree） | 0 | clean |
| `git status --porcelain=v1` | 0 | empty |
| `git status --short --branch` | 0 | `## ctyun/replay-116-b7-rereviewer` |
| `git rev-parse HEAD` | 0 | `bb86a5e8aa85ca6fedbbf42004fd232074ae9ba3` |
| `git diff --binary 93ab820b48..HEAD \| sha256sum` | 0 | `0bba9bc67d5d672a7407ad9134625583ca09682f2d39bf18f181b716f7330f84` |

`scripts/ci/check-enterprise-offline-tests.sh` 输出 21 个 `ok -`：reuse 门禁缺失/不匹配/匹配、save
无 build/pull、images==config `--images | sort -u` + required 断言、manifest schema、-CheckOnly
禁 build/pull/save + 写 images/manifest + 不写 bundle、config 包缺依赖失败、config 包内容 37 env
示例 + 无被禁条目 + 无 1.15-only、clean 产物 check 通过、bundle-positive 三段正例 + 4 marker、
canary 负例（真实 .env、dev-default 无 WARNING、docker/volumes、空 images 文件）。总计
`all 21 enterprise offline tests passed`，exit 0。

## 独立 S-8 行为检查（真实 bundle fixture）

在 `/tmp`（工作树外）用 `git clone --shared` + fake-docker/fake-git shim 构造真实产物：
`build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse`（exit 0）→
`build-enterprise-config-package.sh`（exit 0），得真实
`dify-enterprise-offline-1.16.0-enterprise.tar` 与 config tar.gz。

| Case | Command | Exit | Key output |
| --- | --- | ---: | --- |
| 无匹配 pattern | check + `-SecretsPattern`（内容 `THIS_PATTERN_DOES_NOT_EXIST_ANYWHERE`） | **0** | `PASS: real-secret pattern scan (S-8) clean for images, manifest, config archive members, and image bundle layers` |
| config 成员命中 | pattern=`MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY`（dev-default，存在于 config 成员） | **1** | `FAIL: real-secret pattern scan (S-8) found secrets in packaged content` |
| bundle layer 命中 | pattern=`placeholder-layer-content`（存在于 layer.tar 内 layer.txt） | **1** | `FAIL: image bundle layer ab12cd34/layer.tar member layer.txt contains a real secret pattern` + S-8 FAIL |

真实扫描证据：layer `tar xzf` 提取成功、逐文件命中打印 member 名；S-8 FAIL 由 `config_members_hit`/
`layer_scan_hits` 驱动，非 mock。命中 case 均 exit 1，未误报 PASS。

## REMAINING FINDINGS / REGRESSION

- B7R-03（dev-default WARNING「同文件」非「相邻」）、B7R-04（check 脚本硬编码
  `1.16.0-enterprise`）、B7R-05（ps1 UTF-8 BOM）、B7R-06（`forbidden_path` 不拦裸
  `docker/volumes`）保持为**已承认的已知限制（P3）**，范围未触碰，不作本轮阻塞。
- **无新 P0/P1/P2**。
- 既往 PASS 项全部复验通过（21/21 套件内）：reuse 门禁、`-CheckOnly` 禁 build/pull/save、
  required-image 断言、manifest schema、config 包文件集/排除、dev-default WARNING 负例、forbidden
  路径负例、images==config 断言。无回归。

## FINDINGS (Rereview)

| ID | Severity | Finding |
| --- | --- | --- |
| B7RR-01 | INFO | `scan_content_secrets` 内新增的 WARNING 豁免（`check-enterprise-offline.sh:171-184`）在无 `-SecretsPattern` 时不影响行为；它防止 config 合法 dev-default 成员被误 FAIL，被 21/21 套件负例（dev-default 无 WARNING 拒绝）与正例（clean artifacts PASS）双向覆盖。 |
| B7RR-02 | INFO | S-8 三态在「bundle 缺失」场景下（config 扫描过、无可列 layer）返回 NOT_RUN 而非 PASS——符合「PASS 仅在实际扫描 config 成员 + 可列 layer 后」的契约语义，诚实。 |

## VERDICT

**PASS** —— B7R-01（S-8 覆盖 config 成员 + 可列 bundle layer，PASS/FAIL/NOT_RUN 三态如实）与
B7R-02（真实 `-Mode reuse` bundle fixture 正例 + 4 marker 断言）均已关闭；无新 P0/P1/P2；范围精确
（2 文件 / +82/-8 / diff SHA 与契约一致）；无未授权写入；21/21 fixture PASS exit 0；独立 S-8
clean(exit 0)/hit(exit 1) 行为验证通过；既往 PASS 项无回归；B7R-03..06 保持已承认 P3 限制。

## NOT_RUN（如实声明）

| Area | Status |
| --- | --- |
| 真实两层 Compose `config --images` 与 live `docker/.env` 展开比对 | NOT_RUN（无 `docker/.env`/daemon；由构造 + fixture shim 保证） |
| 真实 `docker save` 产物由真实 Docker daemon 生成 | NOT_RUN（使用 fake-docker shim，行为契约经 fixture 断言） |
| 真实受保护环境 pattern 文件 | NOT_RUN（无受保护环境；用等价 pattern 文件独立验证三态） |
| `.ps1` 运行时 | NOT_RUN（无 Windows/PowerShell） |
| Phase F/G/H（compose build/up、`docker load`、`--pull never` smoke、五 runtime image ID 断言） | NOT_RUN（另授权） |
| `docker/volumes/**` 访问或复制 | NOT_RUN（禁止） |

## VERIFICATION COMMAND LOG（命令层面汇总）

Pass/Fail/NOT_RUN：**11 PASS / 0 FAIL / 6 NOT_RUN**（含独立 S-8 三态：2 exit-1 命中属预期负向，
非失败）。Finding 层面：2×INFO，无开放 P0/P1/P2。

`git diff --check` result: **clean (exit 0)** for the fixer range and the worktree.

Current `git status`: clean（`## ctyun/replay-116-b7-rereviewer`，porcelain 空）。

## DECLARATION

- 未执行 commit、amend、push、merge、rebase、reset、checkout 或 cherry-pick；未创建 PR。
- 唯一写入文件为本报告 `docs/enterprise/replay-1.16.0/B7_REREVIEW.md`；未修改任何 product 文件、
  fixture、denylist 文件、`docker/volumes/**` 或真实 `.env`；未访问/复制 volume、未启动 Docker
  服务、未触碰外部系统/数据库/远程。
- fixer 范围无 commit/amend/push 之外的历史动作；本 Rereview 未产生任何 commit。
