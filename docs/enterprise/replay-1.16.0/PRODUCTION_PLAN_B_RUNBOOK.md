# 生产 Plan B 部署 Runbook（1.16.0）

更新时间：2026-08-17（Asia/Shanghai）
基线：1.16.0-enterprise；Plan A（现有 `docker-1161-*` 1.16.1）保留不动。

## 1. Secret 轮换（一次性，生产/灰度各一套）

在各自主机生成，不进仓库、不打进离线包：

```bash
umask 077
openssl rand -hex 32   # SECRET_KEY
openssl rand -base64 48 # 其余服务 key
```

需轮换项：`SECRET_KEY`、`DB_PASSWORD`、`REDIS_PASSWORD`、`PLUGIN_DAEMON_KEY`、`PLUGIN_DIFY_INNER_API_KEY`、`SANDBOX_API_KEY`、`WEAVIATE_API_KEY`、`CODE_EXECUTION_API_KEY`、`INIT_PASSWORD`。

生产与灰度各用不同值，各自保存到 secret store，之后升级复用。

## 2. 离线包生成（1.16.0）

```bash
cp docker/.env.example docker/.env
scripts/build-enterprise-offline.sh -Version 1.16.0-enterprise -Mode reuse
scripts/build-enterprise-config-package.sh -Version 1.16.0-enterprise
scripts/ci/check-enterprise-offline.sh -Archive ... -ConfigArchive ... -Manifest ... -Images ... -SecretsPattern <真实pattern>
```

产物在 `dist/offline/**`。

## 3. Plan B 部署（不碰 Plan A）

目标主机：生产 62-6、灰度 62-7。

```bash
# 拷贝离线包与 config 包到目标主机
scp dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar <host>:/
scp dist/offline/dify-enterprise-config-1.16.0-enterprise.tar.gz <host>:/

# 目标主机
docker load < dify-enterprise-offline-1.16.0-enterprise.tar
mkdir -p /opt/dify-planb && tar xzf dify-enterprise-config-1.16.0-enterprise.tar.gz -C /opt/dify-planb
cp <轮换后.env> /opt/dify-planb/docker/.env   # chmod 600
docker compose -p dify-planb \
  -f /opt/dify-planb/docker/docker-compose.yaml \
  -f /opt/dify-planb/docker/docker-compose.enterprise.yaml \
  config -q
docker compose -p dify-planb \
  -f /opt/dify-planb/docker/docker-compose.yaml \
  -f /opt/dify-planb/docker/docker-compose.enterprise.yaml \
  up -d --pull never
```

端口 443 已被 Plan A 占用：Plan B 先用备用端口（如 8443）验证，确认后再协调停机切换；不得直接抢占。

## 4. 验证

- nginx/api/web smoke
- `docker inspect` 五 runtime image ID 一致
- `alembic_version = e7c0a9d2b8f3`
- 真实 secret 复扫无命中
- Plan A 容器全程未动；`dify-api-expand` 未触碰

## 5. 回退

- Plan A 原样保留，回退 = 恢复 443 给 Plan A 并重启。
- Plan B 数据/卷独立，删除不影响 Plan A。
