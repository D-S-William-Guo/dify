# 离线生产环境部署检查清单

更新时间：2026-09-29（Asia/Shanghai）

## 目的

确认 Dify Enterprise 1.16.0 离线滚动升级的前置条件。本清单是指导，不构成连接目标主机或执行部署的授权；开发机演练结果也不能替代生产/灰度核验。

本次升级沿用现有有效连接配置；默认密码更换保留为独立加固事项，不再自行作为本次重放的阻塞条件。旧的 [Plan B runbook](PRODUCTION_PLAN_B_RUNBOOK.md) 记录的是另一种并行部署方案，不能当作当前滚动升级指令。

## 当前已检查（本机）

- `docker context ls`：只有 default 本机 daemon，无远程/离线 context
- `~/.ssh/config`：不存在；known_hosts 存在但无可用离线主机别名
- 环境变量：无 `OFFLINE_HOST`/registry/offline 相关配置
- 文件系统：未发现独立 offline/deploy/prod Dify 目录（仅 openclaw/AI-Platform-Square-HB/enterprise-agent-poc）

结论：离线主机不是当前这台开发机的 Docker context；需要提供访问信息或在目标主机上执行下列检查。

## 离线主机必查项

在离线主机上执行并回传输出：

```bash
# 1. 基础
uname -a
docker version --format '{{.Server.Version}}'
docker compose version
df -h /var/lib/docker /tmp
free -h
nproc

# 2. 端口占用
ss -ltn | rg ':(80|443)\b' || echo PORTS_FREE

# 3. 现有 Dify 痕迹（勿删，只记录）
ls -la /opt /srv /home/*/dify 2>/dev/null | head -30
docker ps -a --format '{{.Names}} {{.Image}}' | rg -i 'dify|nginx|postgres|redis|weaviate|plugin|sandbox|agent' || echo NO_EXISTING_DIFY

# 4. 网络隔离
ip route | head -10
getent hosts registry-1.docker.io || echo NO_EXTERNAL_DNS
curl -m 5 -sI https://registry-1.docker.io 2>&1 | head -3 || echo NETWORK_BLOCKED
```

## 满足条件后部署顺序

1. 单独确认目标环境的现有 Compose 项目、实际 bind mount 来源、冷备与回退依据；不要仅凭仓库相对路径推断运行中的挂载位置。取得升级窗口及目标环境的单独授权后，再按已确认的历史挂载复制到新的部署目录。
2. 离线配置包只含白名单模板，**不含**真实 `.env`、`docker/volumes/**` 或 sandbox `config.yaml`。沿用该环境现有有效 `.env` 和连接信息，单独放入新部署目录的 `docker/.env`，限制权限；不得将其打进离线包或提交仓库。默认密码轮换另行规划，不与本次镜像升级合并。
3. 从已核验的该环境历史备份/实际挂载中，单独迁移 sandbox 的配置到新部署目录 `docker/volumes/sandbox/conf/config.yaml`，保留所需目录内容与权限，并在不打印配置值的前提下核对其 `app.key` 与该部署环境的 `SANDBOX_API_KEY` 一致。**文件缺失、来源或 key 无法确认时停止，不启动 Compose。** `docker compose config -q` 不能替代这项文件检查；空目录挂载到 `/conf` 会遮蔽镜像内配置。
4. 不要把仓库的 `config.yaml.example` 直接当作可用生产配置：其 `allowed_syscalls: [1, 2, 3]` 在本机隔离演练的合成 JavaScript 任务中触发 `bad system call`；演练中置空列表只证明该单项任务通过，不是生产修改建议。
5. 在前置条件和产物身份均核对后，按另行批准的操作窗口加载镜像、检查 Compose 展开配置、启动新部署并验证服务健康、历史数据及应用功能；失败时按已确认的回退方案处理，不自动改动旧部署。

## 需要你提供

- 离线主机 IP/SSH 别名，或
- 上述必查项输出

目标信息只能用于另行授权的发布准备；本清单不授权连接、轮换 secret、执行部署或修改现有数据。
