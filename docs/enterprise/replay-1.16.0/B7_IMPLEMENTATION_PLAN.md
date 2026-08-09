# Dify Enterprise 1.16.0 Replay B7 实施计划

## 0. 结论

当前结论：**PLAN_READY**（本文件是供独立 Review 的实施计划，不是 Builder 授权）。

已确认的关键决定：

1. `B7_MODE_REUSE_ONLY`：离线打包只以 `Mode=reuse` 运行。企业镜像
   `dify-api-enterprise:1.16.0-enterprise` / `dify-web-enterprise:1.16.0-enterprise`
   必须已在构建机存在且 `COMMIT_SHA` 等于期望 version tag，脚本才允许复用；缺失或
   不一致必须失败（VALIDATION_PLAN Phase H 第 1 条）。B6R-01 已记录：B6 overlay 的
   `COMMIT_SHA` build arg 携带的是 version tag（`1.16.0-enterprise`）而不是 git hash，
   因此 reuse 门禁比较对象是 tag，不假设 hash。
2. `B7_IMAGES_FROM_B6_CONFIG`：`images-*.txt` 必须等于两层 Compose（官方
   `docker/docker-compose.yaml` + 企业 `docker/docker-compose.enterprise.yaml`）
   `config --images | sort -u` 的展开集合；`COMPOSE_PROFILES` 从部署 `docker/.env`
   的 `VECTOR_STORE`/`DB_TYPE` + `collaboration` 推导，与 B6 验证一致。
3. `B7_MANIFEST_FIELDS`：manifest 必须记录 `version`、`baseline`（官方 tag/commit）、
   `enterprise_commit`（构建机 `git rev-parse HEAD`）、`image_tag`、`generated_at`
   以及每个镜像的 `name`/`id`/`digest`；不写真实 secret。
4. `B7_NO_REAL_ENV_IN_PACKAGE`：image/config archive 一律不含真实 `.env`、secret、
   `docker/volumes/**`、`.git`、cache、`node_modules`、`.venv`、`.next`；
   `DIFY_AGENT_SERVER_SECRET_KEY` 官方开发默认只允许出现在带 WARNING 相邻注释的
   `*.env.example`，绝不进入可运行配置/打包内容；生产 secret 由受保护安装流程生成
   （Phase H 第 6/7 条，B7 只实现扫描门禁，不实现安装器）。
5. `B7_PLUGIN_KNOBS_PASSTHROUGH`：插件离线源与签名只透传官方 knob
   `PIP_MIRROR_AUTO_DETECT`、`PIP_MIRROR_URL`、`FORCE_VERIFYING_SIGNATURE`；
   不建立任何平行 mirror/索引/转发实现（E11/C05）。官方 plugin-daemon
   `.env.example` 确认：显式 `PIP_MIRROR_URL` 优先并禁用自动探测，自动探测是官方默认。
6. `B7_CONFIG_PACKAGE_1_16_SET`：1.16 配置包文件集不再依赖 1.15 专属文件
   （`docker/ENTERPRISE_DEPLOY_STARTUP.md`、`UPGRADE_*.md`、`docker/dify-env-sync.*`、
   `docker/README.enterprise.md`、`scripts/check-enterprise-vector-indexes.sh`）；
   后两者属于 B8，不得前向依赖。
7. `B7_PHASE_FG_NOT_RUN`：Phase F（镜像构建/recreate/`docker inspect` image ID）、
   Phase G（运行验收）与 Phase H 的离线目标 `--pull never` smoke 均归另行授权阶段，
   B7 不启动 Docker 服务、不访问/复制 `docker/volumes/**`。

当前门禁：

```text
B7_BUILDER_NOT_AUTHORIZED
B7_RUNTIME_NOT_AUTHORIZED（Phase F/G/H 需协调者另行批准）
```

## 1. Current-state recovery

### 1.1 强制起点

| 项目 | expected | actual | 结果 |
| --- | --- | --- | --- |
| branch | `ctyun/replay-116-b7-architect` | `ctyun/replay-116-b7-architect` | PASS |
| HEAD | `20672fcef71530dcff1483c17cb2ab3205a75228` | `20672fcef71530dcff1483c17cb2ab3205a75228` | PASS |
| porcelain | empty | empty | PASS |
| B6 overlay 存在 | `git show d218e48f28:docker/docker-compose.enterprise.yaml` 74 行 | 74 行 | PASS |
| B6 Review 为 HEAD | `20672fcef7` 含 B6 overlay `d218e48f28` | `git log` 确认 | PASS |
| 现有离线脚本 | `scripts/build-enterprise-offline.*`、`scripts/*enterprise*config*` | 不存在（`ls` 输出 `no-scripts`） | PASS（B7 待创建） |
| 官方 compose 未变 | `docker/docker-compose.yaml` 与模板一致（B6 已验） | 一致 | PASS |
| env 示例 | `docker/envs/**/*.env.example` 37 个已跟踪 | 37 个 | PASS |

未执行 merge、rebase、reset、checkout、cherry-pick、commit、amend 或 push。

### 1.2 已接受产品事实

- B6 overlay（`d218e48f28`）已合并并通过独立 Review（`20672fcef7`），是 B7 唯一
  读取的 overlay；B7 只读取展开结果，不修改 overlay（ARCHITECT_HANDOFF §5 共享路径
  唯一写入者规则）。
- B6 完成五个企业 runtime 的 image/tag/build 覆盖：
  `api`/`worker`/`worker_beat`/`api_websocket` → `dify-api-enterprise:1.16.0-enterprise`，
  `web` → `dify-web-enterprise:1.16.0-enterprise`；`agent_backend`/`local_sandbox`
  保持官方镜像。
- 官方 1.16 `docker/docker-compose.yaml` 已含 `agent_backend`（官方
  `langgenius/dify-agent-backend:1.16.0`）、`local_sandbox`（官方
  `langgenius/dify-agent-local-sandbox:1.16.0`）、`plugin_daemon`
  （`langgenius/dify-plugin-daemon:0.6.3-local`）、`sandbox`（`0.2.15`）等；离线包
  通过两层 Compose `config --images` 自然包含 Agent 两镜像。
- 官方 plugin daemon 已提供 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL`/
  `FORCE_VERIFYING_SIGNATURE` knob（plugin-daemon `.env.example` 原文核验）；
  官方 compose 的 `plugin_daemon` 服务已把 `PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE`
  作为 interpolation 变量透传。
- 官方 `docker/.env.example` 与 `docker/envs/core-services/dify-agent.env.example`
  已带 `DIFY_AGENT_SERVER_SECRET_KEY` 开发默认值及其 WARNING 相邻注释（Phase H 第 6 条
  前置事实），B7 不新增/不复制该默认值。
- `dist/` 已在根 `.gitignore`；`docker/.gitignore` 忽略 `*.env` 保留 `*.env.example`；
  离线产物（`dist/offline/**`）与临时 `docker/.env` 副本不会污染 diff。

### 1.3 B7 交付物范围依据

ARCHITECT_HANDOFF §5 B7 行 + VALIDATION_PLAN Phase H + PATCH_DECISION_MATRIX
E10/E11/C05：B7 独占离线 image list、manifest、config archive 生成逻辑；只读取
B6 overlay；不得修改 `docker/docker-compose.enterprise.yaml`、业务源码、
`packages/contracts/**`、`docker/volumes/**` 或真实 `.env`/secret。

## 2. Official-first findings

### 2.1 可复用/必须保持的官方 1.16 能力

| 能力 | 官方依据 | B7 用法 |
| --- | --- | --- |
| 两层 Compose image 解析 | `docker/docker-compose.yaml`（auto-generated）+ B6 overlay | 离线脚本用 `docker compose --env-file docker/.env -f docker-compose.yaml -f docker-compose.enterprise.yaml config --images` 解析；`COMPOSE_PROFILES` 来自部署 `.env`（weaviate,postgresql,collaboration） |
| Agent 两镜像 | `agent_backend: langgenius/dify-agent-backend:1.16.0`、`local_sandbox: langgenius/dify-agent-local-sandbox:1.16.0` | 离线 required-image 断言必须包含；企业 tag 不得覆盖 |
| 企业五 runtime 镜像身份 | B6 overlay image/tag 覆盖 | 断言 `api==worker==worker_beat==api_websocket` 同企业 API tag、`web` 企业 Web tag |
| plugin 镜像源/签名 knob | plugin daemon 官方 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE`；官方 compose `plugin_daemon` 已透传 `PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE` | 只在 `docker/envs/core-services/plugin-daemon.env.example` 追加 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL` 官方透传变量；不实现平行 mirror |
| 配置包 env 示例全集 | `docker/envs/**/*.env.example` 37 个 | config 脚本用 `find docker/envs -name '*.env.example'` 全量纳入（含 dify-agent/local-sandbox） |
| 官方 compose/env 文件只读 | 官方 Dockerfile 已支持 `COMMIT_SHA`；`.env.example` 结构稳定 | 配置包把 `docker/docker-compose.yaml`、`docker/docker-compose.enterprise.yaml`、`docker/.env.example`、`docker/nginx/**`、`docker/ssrf_proxy/**` 原样打包 |
| 官方开发默认 key 的 WARNING | `docker/.env.example`、`dify-agent.env.example` 已含开发默认与 WARNING | 扫描门禁校验：含默认值的文件必须相邻 WARNING；默认值绝不进可运行配置 |

### 2.2 企业差距

- 官方无企业离线打包链（旧 `scripts/build-enterprise-offline.*`/config 脚本是 1.15
  fork 维护物）；1.16 必须按新 Compose 服务图重写（E10）。
- 旧 1.15 离线脚本 manifest 只有 `version`/`generated_at`/`images`；Phase H 要求
  manifest 记录版本、基线、企业 commit、image tag、ID/digest —— 需要扩展。
- 旧 config 脚本强依赖 1.15 专属文档/同步脚本和 B8 的 vector checker；B7 移除这些
  前向依赖。
- 官方 env 示例未收录 `PIP_MIRROR_AUTO_DETECT`（plugin daemon 官方默认开启）；B7
  在 plugin-daemon env 示例补透传行。

### 2.3 旧 1.15 离线链需求 disposition（`dify-enterprise-1.15.0` 只读证据）

| 旧元素 | disposition | 1.16 处理 |
| --- | --- | --- |
| `scripts/build-enterprise-offline.sh` / `.ps1` | `REIMPLEMENT_ON_NEW_ARCH` | 重写：两层 Compose `config --images`、`Mode=reuse`、manifest 扩展字段、required-image 断言 |
| `-Version/-OutputDir/-Mode` 参数与 `smart\|rebuild\|reuse` | `KEEP` | 保留；B7 默认发布只授权 `reuse` |
| `get_image_commit_sha`/`is_reusable_image` | `KEEP` | 保留；reuse 门禁：镜像存在且 `COMMIT_SHA`==期望 tag |
| web 构建临时 context（拷贝 package.json/web/packages/sdks 再清理） | `KEEP_MINIMAL_PATCH` | 仅在 `rebuild`/`smart` 路径需要；B7 默认 `reuse` 不进入 |
| manifest 仅 version/generated_at/images | `EXTEND` | 增加 baseline、enterprise_commit、image_tag、逐镜像 id/digest |
| config 脚本打包 1.15 专属文档/dify-env-sync/vector checker | `DROP_FROM_B7` | 只打包 compose+env 示例+nginx/ssrf_proxy+manifest/images；B8 扩展点 |
| `docker/ENTERPRISE_DEPLOY_STARTUP.md`、`README.enterprise.md`、升级文档 | `DROP_FROM_B7` | 1.16 不要求；不新建 docs 于 B7 |
| 离线目标 `--pull never` smoke | `KEEP` | 属于 Phase H 运行门禁，B7 脚本不执行；脚本保证不在离线路径 pull |

## 3. B7 交付物 allowlist / denylist

### 3.1 精确 allowlist（B7 Builder 唯一可写集合）

| 精确文件 | 说明 |
| --- | --- |
| `scripts/build-enterprise-offline.sh` | 主打包脚本（bash；`Mode=reuse` 门禁、image list、manifest、`docker save`） |
| `scripts/build-enterprise-offline.ps1` | PowerShell 行为等价克隆（与旧链 .sh/.ps1 双实现保持一致；仅当 Builder 判断必须维护 Windows 运维路径） |
| `scripts/build-enterprise-config-package.sh` | 配置包脚本（`tar tzf` 生成 `dify-enterprise-config-$VERSION.tar.gz`） |
| `scripts/build-enterprise-config-package.ps1` | 同上 PowerShell 克隆（与旧链一致） |
| `scripts/ci/check-enterprise-offline.sh` | 离线门禁扫描脚本：archive/secret/default-key/volume/image-list/manifest 一致性检查 |
| `scripts/ci/check-enterprise-offline-tests.sh` | fixture/dry-run 测试（docker shim + fixture 工作树） |
| `scripts/ci/check-enterprise-offline-fixtures/**` | 离线测试 fixture（fake docker/git/python、stub compose、canary 文件） |
| `docker/envs/core-services/plugin-daemon.env.example` | **唯一** env 示例修改：追加 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL` 官方透传行（E11/C05） |

说明：

- 默认 product 文件 4 个脚本 + 1 个 env 示例；`-CheckOnly` dry-run 标志内置在
  `build-enterprise-offline.sh`/`.ps1`（供 dry-run 与 fixture 测试）。
- `.ps1` 若 Builder 判断超出成本/收益，必须停下向协调者申请从 allowlist 移除，不得
  默认省掉后声称全链等价；双实现与旧 1.15 链一致是 accepted-style 的默认项。
- 离线输出目录 `dist/offline/**` 是生成产物（gitignored），不在 diff 内，也不是
  allowlist 文件。
- 除上述文件外任何新文件（含新 `.env.example`、新 Dockerfile、新 docs）默认非法；
  Builder 必须停下并请求扩展 allowlist。

### 3.2 只读 reference paths

- `docker/docker-compose.yaml`、`docker/docker-compose-template.yaml`、`docker/.env.example`
- `docker/envs/**/*.env.example`（37 个；除 plugin-daemon 外一律只读）
- `docker/docker-compose.enterprise.yaml`（只读取展开结果，禁止修改）
- `docker/nginx/**`、`docker/ssrf_proxy/**`（配置包只读输入）
- `api/Dockerfile`、`web/Dockerfile`（`COMMIT_SHA` build arg 事实核验）
- 旧 1.15 链 `/home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/scripts/*`（只读证据）
- `docs/enterprise/replay-1.16.0/` 全部（只读 sources of truth）

## 4. 离线契约（Offline contract）

### 4.1 打包模式

- 默认且唯一授权：`-Mode reuse`。`smart`/`rebuild` 属于构建机人工显式选择；B7 验证
  与发布门禁只记录 `Mode=reuse`。
- reuse 门禁（Phase H 第 1 条）：`docker image inspect <enterprise-image>` 必须成功且
  其 `COMMIT_SHA` env 等于 `$DIFY_ENTERPRISE_VERSION`（默认 `1.16.0-enterprise`）；
  缺失或不一致直接退出非零，不得降级为构建/拉取。
- 依赖镜像（postgres/redis/weaviate/sandbox/plugin_daemon/agent 两镜像/nginx/
  ssrf_proxy/init busybox 等）：本地存在则复用；构建机上缺失时允许 `docker pull`
  （联网构建机职责）。离线目标不运行本脚本。
- `-CheckOnly`（dry-run）：解析 image list、执行 reuse 门禁、写 `images-*.txt` 与
  manifest 后退出，禁止任何 `docker build`/`docker pull`/`docker save`。

### 4.2 image list

- 文件名：`images-$VERSION.txt`（默认 `images-1.16.0-enterprise.txt`），每行一个
  镜像名，`sort -u` 去重，与两层 Compose `config --images | sort -u` 完全一致。
- 生成方式：

```bash
docker compose --env-file "$ENV_FILE" \
  -f "$DOCKER_DIR/docker-compose.yaml" \
  -f "$DOCKER_DIR/docker-compose.enterprise.yaml" \
  config --images | sed '/^[[:space:]]*$/d' | sort -u
```

- `ENV_FILE` 默认 `docker/.env`（运维从 `.env.example` 生成，不提交）；`COMPOSE_PROFILES`
  未显式设置时从 `docker/.env` 的 `VECTOR_STORE`/`DB_TYPE` + `collaboration` 推导
  （默认 `weaviate,postgresql,collaboration`）。
- required-image 断言（脚本内强制）：企业 API tag 恰好一个且四个 runtime 解析一致；
  企业 Web tag 恰一个；`langgenius/dify-agent-backend:1.16.0` 与
  `langgenius/dify-agent-local-sandbox:1.16.0` 必须出现；`config --images` 非空。

### 4.3 manifest

- 文件名：`manifest-$VERSION.json`。schema：

```json
{
  "version": "1.16.0-enterprise",
  "baseline": { "tag": "1.16.0", "commit": "5c6372d2f76d240265b92fd27c16bc772ffcb107" },
  "enterprise_commit": "<构建机 git rev-parse HEAD>",
  "image_tag": "1.16.0-enterprise",
  "generated_at": "<ISO-8601 UTC>",
  "images": [
    { "name": "dify-api-enterprise:1.16.0-enterprise",
      "id": "sha256:<Image ID>", "digest": "<RepoDigest 或镜像 digest>" }
  ]
}
```

- `baseline` 固定为官方 `1.16.0` / `5c6372d2f76d240265b92fd27c16bc772ffcb107`
  （sources of truth 一致）。
- `enterprise_commit` 由脚本在构建机 `git rev-parse HEAD` 取当前企业代码 commit，
  与镜像 `COMMIT_SHA`（tag）分开记录；B6R-01 已知限制：tag 不能区分同 tag 两次构建，
  绑定以 `id`/`digest` 为准，Phase F 的 image ID 交叉验证是 B8 门禁。
- 逐镜像 `id` 用 `docker image inspect --format '{{.Id}}'`，`digest` 用
  `--format '{{index .RepoDigests 0}}'`（缺失时如实记录空串，不伪造）。
- manifest 不得含任何真实 secret、`.env` 内容或开发默认 key。

### 4.4 image bundle（离线镜像包）

- 文件名：`dify-enterprise-offline-$VERSION.tar`，由 `docker save -o "$ARCHIVE_PATH" "${IMAGES[@]}"` 生成。
- `docker save` 产物本身无法在打包时做路径排除（由 Docker 全量导出）；排除约束通过
  (a) 脚本不把非镜像文件加入 save 列表、(b) 扫描门禁检查 bundle 顶层结构与逐 layer
  条目、(c) Phase G 运行扫描（另行授权）共同保证。

### 4.5 config package（最小配置包）

- 文件名：`dify-enterprise-config-$VERSION.tar.gz`；依赖同版本 `manifest-*.json` 与
  `images-*.txt` 已存在，否则失败。
- 打包内容（显式文件清单 + `find docker/envs -name '*.env.example'` 全量 + 两个目录）：

```text
docker/docker-compose.yaml
docker/docker-compose.enterprise.yaml
docker/.env.example
docker/envs/**/*.env.example（37 个，含 dify-agent/local-sandbox/plugin-daemon）
docker/nginx/**
docker/ssrf_proxy/**
dist/offline/manifest-$VERSION.json
dist/offline/images-$VERSION.txt
```

- tar 显式 `--exclude`：`*.env`（非 example）、`docker/volumes/**`、`.git`、cache、
  `node_modules`、`.venv`、`.next`、`dist/` 之外的任何业务源码/产物；打包后再由
  `check-enterprise-offline.sh` 全量扫描。
- 配置包不得包含：真实 `.env`、真实 secret、开发默认 key（可运行配置中）、
  `docker/volumes/**`、旧 1.15 专属文档/dify-env-sync/vector checker。

### 4.6 Agent server secret 规则

- 开发默认 `DIFY_AGENT_SERVER_SECRET_KEY=MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY`
  只允许出现在 `docker/.env.example` 与 `docker/envs/core-services/dify-agent.env.example`
  （均已带 WARNING 相邻注释）；B7 不新增出现点。
- 扫描门禁：任何含该默认值的文件必须相邻
  `WARNING`/`Replace this development default in production` 注释，且该默认值不得出现
  在 manifest、images 文件、可运行配置（非 example）或任何非 example 路径中；命中即阻断。
- 生产安装生成全新随机 secret 属于 Phase H 第 7 条受保护安装流程（NOT_RUN for B7）。

### 4.7 `--pull never` 规则

- 离线目标 smoke 固定为：`docker load < bundle` → `docker compose up -d --pull never`
  （operator/Phase H 门禁；NOT_RUN for B7）。
- 打包脚本运行在联网构建机；reuse 模式只在镜像缺失/不匹配时失败或（依赖镜像）在
  构建机 pull，绝不把 pull 行为引入离线目标的启动命令。

## 5. Env 变量矩阵

### 5.1 B7 修改的 env 示例（唯一一处）

| 变量 | 文件 | 值 | 依据 |
| --- | --- | --- | --- |
| `PIP_MIRROR_AUTO_DETECT` | `docker/envs/core-services/plugin-daemon.env.example` | `true`（注释说明：官方默认开启；显式 `PIP_MIRROR_URL` 优先并禁用自动探测） | 官方 plugin-daemon `.env.example`；E11/C05 |
| `PIP_MIRROR_URL` | 同上 | 空（注释示例：`https://pypi.tuna.tsinghua.edu.cn/simple`） | 官方 knob；与官方 compose `plugin_daemon` interpolation 同名透传 |
| `FORCE_VERIFYING_SIGNATURE` | 同上 | `true`（已存在，保留不动） | 官方签名门禁；默认保持 true |

不在 B7 修改（保持官方现状）：

| 变量 | 现状 | B7 约束 |
| --- | --- | --- |
| `DIFY_AGENT_SERVER_SECRET_KEY` | `docker/.env.example`、`dify-agent.env.example` 开发默认 + WARNING | 不新增出现点；扫描门禁见 §4.6 |
| `PIP_MIRROR_URL` | `docker/.env.example`、`sandbox.env.example` 已有 | 只读；不重复定义 |
| `DIFY_ENTERPRISE_API_IMAGE`/`DIFY_ENTERPRISE_WEB_IMAGE`/`DIFY_ENTERPRISE_VERSION`/`ENTERPRISE_ENABLED`/`PLATFORM_ADMIN_EMAILS`/`ALLOW_REGISTER`/`ALLOW_CREATE_WORKSPACE` | B6 overlay `:-default` 展开 | B7 不新增 env 示例（overlay 默认足够）；打包运行时由构建机 `docker/.env`/脚本参数提供 |
| 全部其他 `docker/envs/**/*.env.example` | 官方 | 配置包只读纳入 |

### 5.2 打包运行 env（非提交，构建机本地）

```text
DIFY_ENTERPRISE_VERSION=1.16.0-enterprise
DIFY_ENTERPRISE_API_IMAGE=dify-api-enterprise
DIFY_ENTERPRISE_WEB_IMAGE=dify-web-enterprise
MODE=reuse
COMPOSE_PROFILES=<来自 docker/.env：VECTOR_STORE,DB_TYPE,collaboration>
```

## 6. 安全 / 身份矩阵

| # | 约束 | 断言方式（B7 静态门禁） |
| --- | --- | --- |
| S-1 | `images-*.txt` == 两层 Compose `config --images \| sort -u` | 脚本生成后 `diff` 空 |
| S-2 | 企业 API tag 唯一且四个 runtime 一致；Web tag 唯一；Agent 两镜像必须在列 | required-image 断言，失败退出 |
| S-3 | reuse 门禁：企业镜像缺失或 `COMMIT_SHA` 不匹配即失败 | `docker image inspect` 校验 |
| S-4 | manifest 字段完整（version/baseline/enterprise_commit/image_tag/images[]name,id,digest） | JSON schema 断言 |
| S-5 | 配置包不含 `.env`/secret/`docker/volumes/**`/`.git`/cache/`node_modules`/`.venv`/`.next` | `tar tzf` 精确路径扫描 |
| S-6 | image bundle 顶层结构正确且无被禁条目；逐 layer 条目扫描 | `tar tf` 顶层 + 0700 临时目录逐 layer `tar tzf`（见 §6 note） |
| S-7 | 开发默认 `DIFY_AGENT_SERVER_SECRET_KEY` 仅存在于带 WARNING 的 example；不进 manifest/可运行配置 | 全路径内容扫描 + WARNING 相邻校验 |
| S-8 | 真实 secret 不进入任何打包内容 | pattern 文件从受保护环境构造，0600/0700 临时文件，扫描只输出目标+命中布尔，之后清理（FIX-09） |
| S-9 | 脚本不触碰 `docker/volumes/**`、不读取/复制真实 `.env` 值进产物 | 脚本源码审查 + fixture 负向测试 |
| S-10 | `--pull never` 语义保持 | 离线目标启动命令只记录为 operator/Phase H 门禁；脚本无 `up`/`--pull never` 路径 |

note（S-6 已知上限，`ponytail:` 语义）：image bundle 的 layer blob 是 gzip tar；
`check-enterprise-offline.sh` 在 `0700` 临时目录对每个 layer 做 `tar tzf` 条目扫描，
任一 layer 无法列出则如实记 `NOT_RUN`（不冒充 PASS）；无法在不动容器的前提下探测 layer
内部 secret，Phase G 运行扫描（另行授权）才是权威门禁。

## 7. B7 Builder 验证计划

### 7.1 起点与范围（必跑）

```bash
git branch --show-current
git rev-parse HEAD
git status --short --branch
git merge-base --is-ancestor d218e48f282fee2f9c662d187be0f3508912396e HEAD
git diff --check
git diff --name-status <B7 起始 base SHA>...HEAD   # 期望仅 §3.1 allowlist 文件
git diff <base>...HEAD -- docker/docker-compose.enterprise.yaml   # 期望空
git status --porcelain=v1
```

### 7.2 离线 dry-run / fixture 测试（必跑）

```bash
scripts/ci/check-enterprise-offline-tests.sh
scripts/build-enterprise-offline.sh -CheckOnly -Version 1.16.0-enterprise -Mode reuse   # 构建机真实 docker 或 fixture docker shim
scripts/build-enterprise-config-package.sh -Version 1.16.0-enterprise                   # 依赖 7.3 产物
```

fixture 测试断言（fake `docker`/`git`/`python3` shim + fixture 工作树）：

| 用例 | 期望 |
| --- | --- |
| reuse 门禁：企业镜像缺失 | 退出非零，报 `not reusable` |
| reuse 门禁：`COMMIT_SHA` 不匹配 | 退出非零，报期望/实际 |
| reuse 门禁：`COMMIT_SHA` 匹配 | 通过并复用它 |
| image list 解析 | `images-*.txt` 与 shim 输出的 `config --images` 一致；含 Agent 两镜像与企业 tag |
| `-CheckOnly` | 不调用 `docker build/pull/save`（shim 断言）；写出 images/manifest |
| manifest schema | 字段完整；`baseline` 固定；`enterprise_commit` 来自 shim `git rev-parse HEAD`；逐镜像 id/digest 存在 |
| config 包依赖 | 缺 manifest/images 时失败 |
| config 包内容 | 含 37 个 env 示例 + compose + nginx/ssrf_proxy；无被禁条目 |
| secret/默认 key 扫描 | 植入 canary `.env`/开发默认 key 时失败；干净 fixture 通过 |
| 负向：真实 `.env`/volume 被拒 | 脚本/扫描拒绝 |

### 7.3 archive / secret / default-key / volume 扫描（必跑）

```bash
scripts/ci/check-enterprise-offline.sh \
  -Archive "dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar" \
  -ConfigArchive "dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz" \
  -Manifest "dist/offline/manifest-1.16.0-enterprise.json" \
  -Images "dist/offline/images-1.16.0-enterprise.txt"
```

覆盖 §6 S-5…S-8：config tar 精确路径扫描、image bundle 顶层/逐 layer 扫描、manifest
secret 扫描、开发默认 key 的 WARNING 相邻校验、环境示例全集逐文件扫描。

### 7.4 Phase F/G/H 运行——NOT_RUN，另行授权

- `docker compose build`、`docker compose up`、`docker inspect .Image` 五 runtime
  image ID 相等断言（FIX-10）
- Phase G 运行验收（含 secret 运行扫描）
- 离线目标 `docker load` + `up --pull never` + 最小 smoke（Phase H 第 9 条）

`NOT_RUN` 必须在 B7 报告如实声明；静态 manifest/tag 结果不替代运行 image ID 证据。

## 8. Exact file ownership matrix

| Exact file | Owner | 依赖（只读） | 共享冲突 | Merge order |
| --- | --- | --- | --- | --- |
| `scripts/build-enterprise-offline.sh` / `.ps1` | B7 独占 | B6 overlay 展开结果、官方 compose、旧 1.15 脚本（证据） | 无 | B6 之后 |
| `scripts/build-enterprise-config-package.sh` / `.ps1` | B7 独占 | 离线脚本产物、`docker/envs/**`、`docker/nginx/**`、`docker/ssrf_proxy/**` | 无 | 同 B7 |
| `scripts/ci/check-enterprise-offline.sh` / `-tests.sh` / `-fixtures/**` | B7 独占 | §3.2 全部 reference paths | `scripts/ci/` 目录 B0 已存在（`check-enterprise-replay-scope*`），B7 只新增独立文件，不修改 B0 文件 | 同 B7 |
| `docker/envs/core-services/plugin-daemon.env.example` | B7 独占（唯一 env 示例修改） | 官方 plugin-daemon `.env.example`、官方 compose plugin_daemon 段 | B6 denylist 了 `docker/envs/**`；B7 是本文件唯一写者 | 同 B7 |
| `docs/enterprise/replay-1.16.0/B7_IMPLEMENTATION_PLAN.md` | 本 Architect | 全部 sources of truth | 唯一 writer=本计划 | 随 B7 计划门禁 |
| `dist/offline/**` | B7 生成产物 | — | gitignored，不入 diff | 不提交 |

共享路径唯一所有者重申：`docker/docker-compose.enterprise.yaml` 唯一写者 = B6，
B7 只读展开结果；`docker/envs/**.env.example` 中 plugin-daemon 文件 B7 独占，其余 36 个
只读。

## 9. Global denylist

所有 B7 Builder 禁止：

- `docker/docker-compose.enterprise.yaml`、`docker/docker-compose.yaml`、
  `docker/docker-compose-template.yaml`（逐字节不变）
- `docker/volumes/**`（禁止访问、复制、修改）
- `docker/.env`、真实 `.env`（任何层级非 example）、`docker/envs/**/*.env`（非 example）
- `docker/envs/**` 除 `core-services/plugin-daemon.env.example` 一个文件
- `api/**`、`web/**`、`dify-agent/**`、`packages/**`、`docs/**`（除本计划）、
  `scripts/**` 除 §3.1 allowlist
- `**/pnpm-lock.yaml`、`**/yarn.lock`、`**/package-lock.json`、`**/package.json`、
  `**/uv.lock`
- 旧 1.15 源码/Dockerfile/Compose/lockfile/版本文档恢复
- 数据库、Redis、vector、container、volume、外部服务写操作；`docker pull` 之外任何
  联网副作用只在构建机、只在依赖镜像路径

若需要 denylist 内文件才能实现，Builder 必须停止并报告，不得扩 scope。

## 10. Builder topology and serial gates

```text
B7 Architect（本计划）
→ 独立 Plan Reviewer
→ CHANGES_REQUIRED: finding-scoped Plan Fixer → 独立 Plan Rereviewer
→ B7 Builder（只写 §3.1 allowlist；Phase E 静态 compose + §7 dry-run/fixture/扫描）
→ Code Reviewer（Docker/Offline Reviewer 视角，逐文件核对 §3–§6）
→ Fixer? → Rereviewer
→ 协调者检查 dirty diff 后另行授权 commit
→ fast-forward 到候选分支，记录精确 SHA
→ B8 最终验证（必须等待 B7；含 Phase F/G/H 与离线目标 smoke）
```

- B7 不并行启动其他 Builder；B8 必须等待 B7。
- Phase F/G/H 授权只能由协调者另行发出；未授权时 B7 结束于静态/干跑验证。

## 11. Risks, decisions and stop conditions

### 11.1 Known limitations

- `COMMIT_SHA` 携带 version tag（B6R-01），tag 相同不能区分同 tag 两次构建；镜像与
  commit 的绑定依赖 manifest `id`/`digest` + Phase F 运行交叉验证（B8）。
- image bundle 逐 layer 扫描有不可列出 layer 的已知上限，按 §6 note 如实记 NOT_RUN。
- `config --images` 依赖部署 `docker/.env` 的 profile/变量展开；不同部署 `.env` 会
  得到不同镜像集合，构建机必须使用目标部署的 `.env`（文档化操作约束）。
- 配置包扫描是静态精确路径扫描；镜像 layer 内部 secret 必须由 Phase G 运行扫描兜底。
- `.ps1` 克隆只在维护 Windows 运维路径时保留；未维护则如实声明，不冒充等价。

### 11.2 RECORDED_DECISION

1. `B7_MODE_REUSE_ONLY`：发布打包只用 `Mode=reuse`；reuse 门禁 = 镜像存在 + COMMIT_SHA==tag。
2. `B7_IMAGES_FROM_B6_CONFIG`：images-*.txt == 两层 compose `config --images | sort -u`。
3. `B7_MANIFEST_FIELDS`：version/baseline/enterprise_commit/image_tag/generated_at/images[]name,id,digest。
4. `B7_NO_REAL_ENV_IN_PACKAGE`：包内无真实 env/secret/volume/cache；开发默认 key 仅限带 WARNING 的 example。
5. `B7_PLUGIN_KNOBS_PASSTHROUGH`：只透传官方 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE`，无平行实现。
6. `B7_CONFIG_PACKAGE_1_16_SET`：移除 1.15 专属文件与 B8 前向依赖。
7. `B7_PHASE_FG_NOT_RUN`：Phase F/G/H 运行默认 NOT_RUN，需协调者另行授权。

### 11.3 Stop conditions

- exact branch/SHA/clean/B6 overlay 起点不符；
- 修改了 `docker/docker-compose.enterprise.yaml`、`docker/volumes/**`、任何 denylist
  文件，或需要 §3.1 之外新文件而未获批准；
- reuse 门禁误通过（缺失/COMMIT_SHA 不匹配被接受）或离线路径出现 pull；
- `images-*.txt` != `config --images`，或 required-image 断言失败（Agent 两镜像/五 runtime 身份）；
- manifest 字段缺失、image list 与 manifest 不一致、含 secret/开发默认 key；
- archive/config 扫描发现被禁条目（`.env`/secret/volume/cache/`.git`/`node_modules`/`.venv`/`.next`）；
- 开发默认 key 出现在非 example 或缺少 WARNING 相邻注释；
- Phase F/G/H 被擅自执行；`docker/volumes/**` 被访问/复制；
- 出现 P0/P1 security、secret、signature 或 volume 泄漏。

## 12. Architect validation record and NOT_RUN

### 12.1 实际执行的只读命令

| Command | exit | Result |
| --- | ---: | --- |
| `git branch --show-current` | 0 | `ctyun/replay-116-b7-architect` |
| `git rev-parse HEAD` | 0 | `20672fcef71530dcff1483c17cb2ab3205a75228` |
| `git status --short --branch` | 0 | clean |
| `git status --porcelain=v1` | 0 | empty |
| `git diff --check` | 0 | clean |
| `git log --oneline -5` | 0 | HEAD 为 B6 Review `20672fcef7`，含 overlay `d218e48f28` |
| `git show --stat d218e48f28` | 0 | `docker/docker-compose.enterprise.yaml` 74 行，唯一文件 |
| `ls scripts/build-enterprise-offline.* scripts/*enterprise*config*` | 1 | `no-scripts`（B7 待创建） |
| `git show d218e48f28:docker/docker-compose.enterprise.yaml \| wc -l` | 0 | 74 |
| 读取 sources of truth 六份 + compose/env 示例 + 旧 1.15 四脚本 | — | 全部读取 |
| 官方 plugin-daemon `.env.example` 核验 | — | 确认 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE` 官方 knob |

### 12.2 NOT_RUN

| Area | Status |
| --- | --- |
| `docker compose config`（两层） | NOT_RUN（B7 无 `docker/.env`，未生成临时副本；B6 已验） |
| `docker compose build` / `docker save` | NOT_RUN（B7 Builder 阶段） |
| `docker compose up` / `docker load` / `--pull never` smoke | NOT_RUN（Phase H，另行授权） |
| `docker inspect .Image` 五 runtime image ID 断言 | NOT_RUN（Phase F） |
| browser/E2E / Phase G 运行验收 | NOT_RUN |
| Phase D 数据库/migration 运行 | NOT_RUN（B2–B4 范围） |
| `docker/volumes/**` 访问或复制 | NOT_RUN（禁止） |

## 13. Exact final validation commands

Architect 交付必须执行：

```bash
git diff --name-status
git diff -- docs/enterprise/replay-1.16.0/B7_IMPLEMENTATION_PLAN.md
git diff --check
git status --short --branch
git status --porcelain=v1
```

后续 B7 Builder 必须执行（§7）；最终 B7 Reviewer 在所有 Builder 合并后执行：

```bash
git diff --name-status <accepted-b7-plan-sha>...HEAD
git diff --check
# §7.2 fixture/dry-run、§7.3 archive/secret/default-key/volume 扫描、image list 一致性、manifest 检查
```

不得把 `docker compose build`、容器运行或离线目标 smoke 作为 B7 validation；Phase
F/G/H 属于另行授权阶段。

## 14. Plan Reviewer checklist

- [ ] 强制起点与 B6 overlay 事实真实（§1.1）：branch/HEAD/clean、`d218e48f28` 在 HEAD、74 行、现有脚本不存在。
- [ ] allowlist 精确（§3.1）：4 个脚本 + fixtures + 唯一 env 示例修改；无新文件默认非法。
- [ ] `Mode=reuse` 契约与 reuse 门禁（镜像存在 + COMMIT_SHA==tag，缺失/不一致失败）明确。
- [ ] `images-*.txt` == 两层 Compose `config --images | sort -u`；required-image 断言含 Agent 两镜像与企业五 runtime 身份。
- [ ] manifest 字段（version/baseline/enterprise_commit/image_tag/generated_at/images[]name,id,digest）与 baseline 固定值明确。
- [ ] config package 文件集为 1.16 定义，无 1.15 专属文件/B8 前向依赖；含全部 `docker/envs/**/*.env.example`（agent/local-sandbox）。
- [ ] tar 排除（.env/secret/docker/volumes/.git/cache/node_modules/.venv/.next）与扫描门禁（§6 S-5…S-8）覆盖。
- [ ] Agent server secret：开发默认仅限带 WARNING 的 example；生产生成新 secret 归 Phase H（NOT_RUN）。
- [ ] 插件 mirror/signature 只透传官方 `PIP_MIRROR_AUTO_DETECT`/`PIP_MIRROR_URL`/`FORCE_VERIFYING_SIGNATURE`，无平行实现。
- [ ] `--pull never` smoke 归 Phase H；B7 脚本不在离线路径 pull。
- [ ] dry-run/fixture 测试用例与断言覆盖 reuse 门禁、image list、manifest、config 依赖、secret/volume 扫描负向。
- [ ] Phase F/G/H NOT_RUN 如实声明；无静态结果冒充运行证据。
- [ ] denylist 覆盖 overlay、volumes、envs（非 plugin-daemon）、业务源码、lockfile。
- [ ] 风险、决定、stop conditions 完整；无未声明的文件所有权。

## 15. Gate

```text
Architect dirty plan
→ coordinator inspects real diff
→ separately authorizes plan commit
→ fast-forward plan commit into candidate
→ independent Plan Reviewer from exact new SHA
→ CHANGES_REQUIRED: finding-scoped Fixer
→ independent Rereviewer
→ only then coordinator may authorize B7 Builder（只写 §3.1 allowlist，静态 compose + dry-run/fixture/扫描）
→ Code Reviewer → Fixer? → Rereviewer
→ B7 fast-forward 并记录精确 SHA → B8
```

`RECORDED_DECISION`：`B7_MODE_REUSE_ONLY`、`B7_IMAGES_FROM_B6_CONFIG`、
`B7_MANIFEST_FIELDS`、`B7_NO_REAL_ENV_IN_PACKAGE`、
`B7_PLUGIN_KNOBS_PASSTHROUGH`、`B7_CONFIG_PACKAGE_1_16_SET`、`B7_PHASE_FG_NOT_RUN`。

当前门禁：**PLAN_READY**；`B7_BUILDER_NOT_AUTHORIZED`；Phase F/G/H 需协调者另行授权。
