# 离线生产环境部署检查清单

更新时间：2026-08-14（Asia/Shanghai）

## 目的

确认离线生产主机是否满足 Dify Enterprise 1.16.0 离线部署条件，以及轮换 secret 后“只改 `.env` 就能起”的假设是否成立。

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

1. 轮换生产/离线 `.env` 全部默认 secret 为随机值（另见轮换 runbook）。
2. 把新 `.env` 放到离线主机 `docker/.env`（权限 600，不进仓库/不打进离线包）。
3. 拷贝离线 tar + config 包到主机。
4. `docker load < dify-enterprise-offline-1.16.0-enterprise.tar`
5. `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q`
6. `docker compose ... up -d --pull never`
7. 验证 nginx/api/web smoke + 真实 secret 复扫。

## 需要你提供

- 离线主机 IP/SSH 别名，或
- 上述必查项输出

拿到后我继续：生成轮换 runbook → 重打离线包 → 指导/执行部署验证。
