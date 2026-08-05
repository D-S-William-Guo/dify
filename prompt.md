你现在参与的是 Dify 企业版（灵枢智能体平台）的企业 fork 维护工作。

## 仓库与分支

企业 fork：

https://github.com/D-S-William-Guo/dify.git

官方 upstream：

https://github.com/langgenius/dify.git

当前企业候选分支：

`codex/enterprise-candidate-1.16.1-20260728`

当前企业版本目标：

`1.16.1-enterprise`

官方稳定底座：

官方 tag/tree `1.16.1`

重要原则：

- 企业发布底座必须是官方稳定 tag/tree，不允许直接基于 `upstream/main` 做企业发布。
- 严禁向官方 `langgenius/dify` 提交、推送或开 PR。
- 如需推送或开 PR，只能在企业 fork `D-S-William-Guo/dify` 内部进行，并且必须先确认 base/head repository。
- 旧企业分支只能作为补丁参考，不能整树复制。
- 不要带入 `docker/volumes/**`、`docker/volume_backups/**`、`docker/.build/**`、`node_modules/**`、`web/.next/**`、`api/.venv/**`、`.env`、缓存或本机运行产物。

## 进入仓库后必须先读

请优先阅读这些文件，并把它们作为当前事实来源：

- `AGENTS.md`
- `README.enterprise-maintenance.md`
- `ENTERPRISE_REPLAY_PLAN.md`
- `docker/README.enterprise.md`
- `docker/ENTERPRISE_DEPLOY_STARTUP.md`
- `CLAUDE.md`
- `.agents/skills/enterprise-docker-workflow/SKILL.md`

不要依赖旧聊天记录、旧工作区、旧 `enterprise/main`、`upstream/main` 或本地记忆作为权威来源。

## 当前进度概况

当前候选已从官方 `1.16.1` tag/tree 创建，并在本地重放企业功能补丁。当前源码基线必须继续保留：

- 企业多空间管理。
- 平台管理员。
- 平台管理员重置成员密码。
- 智慧广场提交、审核、展示、复制导入。
- Docker enterprise overlay。
- 离线镜像包与最小配置包规则。
- 插件本地/离线安装相关修复。
- 知识库 hit testing / dataset 相关已验证修复。
- Agent 大模型生成提示词 mode 修复。
- webapp stale conversation `404 Conversation Not Exists` 清理修复。
- 移动端 `loro-crdt` WebAssembly 渲染兼容修复。
- web 镜像 Corepack/pnpm 缓存与 `NPM_REGISTRY` 构建参数修复。

当前企业 Alembic head：

`a7b8c9d0e1f2`

这个空 merge revision 合并官方 `1.16.1` migration head 与既有 `1.16.0-enterprise` migration head，避免升级时出现 multiple heads 或找不到企业 revision。

## Docker / 部署 SOP

开发和验证时必须确保新的工作区代码、新的 Docker Compose 环境、新的镜像版本一致。

核心规则：

1. Docker Compose 启动必须使用当前工作区的 compose 文件：
   - `docker/docker-compose.yaml`
   - `docker/docker-compose.enterprise.yaml`
2. `.env` 中版本号必须更新：
   - `DIFY_ENTERPRISE_VERSION=1.16.1-enterprise`
3. 常规本机验证建议启用：
   - `COMPOSE_PROFILES=weaviate,postgresql,collaboration`
4. 启动前先看解析结果：

   ```bash
   docker compose --env-file docker/.env \
     -f docker/docker-compose.yaml \
     -f docker/docker-compose.enterprise.yaml \
     config --images
   ```

5. 解析结果中不能出现旧企业版本。
6. `api`、`api_websocket`、`worker`、`worker_beat` 必须使用：
   - `dify-api-enterprise:1.16.1-enterprise`
7. `web` 必须使用：
   - `dify-web-enterprise:1.16.1-enterprise`
8. 官方 Dify Agent 服务应保持官方镜像：
   - `langgenius/dify-agent-backend:1.16.1`
   - `langgenius/dify-agent-local-sandbox:1.16.1`
9. 如果涉及 Docker 验证，必须 rebuild enterprise 镜像，并 force recreate 对应服务。
10. 如果只是部署启动脚本或文档修复，不一定需要重新打镜像，但需要重新生成配置包或确认配置包内容。

## 数据平移 SOP

为了节省重复初始化账号、空间、工作流、插件和知识库的时间，新版本开发环境可尽量复用上一稳定企业环境数据，除非官方升级有破坏性变更或用户明确要求重置。

推荐做法：

- 复制旧环境 `docker/.env` 到新工作区后，必须按新版 `.env.example` 补齐新增配置，并更新 `DIFY_ENTERPRISE_VERSION`。
- 复制旧环境 `docker/volumes/**` 到新工作区前，先停止相关 compose 服务。
- PostgreSQL `pgdata` 权限无法由普通用户复制时，可使用临时 root 容器复制；旧目录必须只读挂载。
- 启动后检查账户、空间、应用、知识库、插件、智慧广场资产，以及 `alembic_version` 是否到达 `a7b8c9d0e1f2`。
- 使用 Weaviate 时，运行 `scripts/check-enterprise-vector-indexes.sh`；缺失 class 时再运行 `--repair` 并复查。

## 离线包 SOP

最终离线打包必须使用 `Mode=reuse`。

含义：

- 只能导出已经点击验证过的同一批 Docker image ID。
- 不能重新 build 一批未经验证的镜像后直接打包。
- 配置包必须包含 compose、env 示例、nginx/ssrf 配置、manifest/images 清单、部署启动说明和升级说明。
- 配置包不得包含 `docker/.env`、`docker/volumes/**`、`volume_backups/**`、`node_modules/**`、`web/.next/**`、`api/.venv/**`、`.git/**`、本机缓存或运行数据。

## 开发协作要求

修改代码前：

- 先读相关文档。
- 先确认当前分支。
- 先确认 remote，避免推到官方 upstream。
- 先确认工作区状态，避免覆盖用户或其他协作者改动。

提交前：

- 检查 `git status`。
- 不提交本地运行产物。
- 不提交 `.env`、`volumes`、缓存、截图产物。
- 运行必要的 lint/type-check/test，或至少说明未运行原因。
- Docker 相关变更至少跑 compose config 校验。

推送前：

- 确认目标是企业 fork：`origin D-S-William-Guo/dify`。
- 严禁推送到官方：`upstream langgenius/dify`。

## 建议 AI IDE 启动提示词

请你作为本仓库的企业版维护协作者工作。

当前任务背景：

我们正在维护 Dify 企业版 `1.16.1-enterprise`。企业 fork 是 `D-S-William-Guo/dify`，官方 upstream 是 `langgenius/dify`。当前候选分支是 `codex/enterprise-candidate-1.16.1-20260728`，必须基于官方稳定 tag/tree `1.16.1`，不能基于 `upstream/main` 做企业发布。

进入仓库后，请先阅读并遵守：

- `AGENTS.md`
- `README.enterprise-maintenance.md`
- `ENTERPRISE_REPLAY_PLAN.md`
- `docker/README.enterprise.md`
- `docker/ENTERPRISE_DEPLOY_STARTUP.md`
- `CLAUDE.md`
- `.agents/skills/enterprise-docker-workflow/SKILL.md`

工作规则：

1. 严禁向官方 `langgenius/dify` 提交、推送或开 PR。
2. 如需推送或开 PR，只能使用企业 fork `D-S-William-Guo/dify`。
3. 旧企业分支只能作为补丁参考，不能整树复制。
4. 不要提交 `docker/volumes/**`、`docker/volume_backups/**`、`docker/.build/**`、`node_modules/**`、`web/.next/**`、`api/.venv/**`、`.env`、`.git/**`、缓存或本机运行产物。
5. Docker 验证必须确保所有服务来自当前 `1.16.1-enterprise` 环境，不允许混入旧企业版本残留。
6. 平移旧环境 `.env` 和 volumes 时，必须检查并替换版本号，尤其是 `DIFY_ENTERPRISE_VERSION`。
7. 当前 Compose profiles 应包含 `collaboration`，确保 `api_websocket` 被启动。
8. `api`、`api_websocket`、`worker`、`worker_beat` 应使用 `dify-api-enterprise:1.16.1-enterprise`。
9. `web` 应使用 `dify-web-enterprise:1.16.1-enterprise`。
10. 离线包最终必须使用 `Mode=reuse`，导出已经点击验证过的同一批镜像。

如果要做改动，请先说明你将检查哪些文件和风险点，然后按最小变更完成，并在结束时给出：

- 修改文件列表
- 验证命令和结果
- 是否涉及镜像重建
- 是否涉及配置包/离线包更新
- 是否有未提交或未跟踪的本地产物
