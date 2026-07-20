# 从 1.14.2-enterprise 升级到 1.15.0-enterprise

本文档用于将已有的 `1.14.2-enterprise` Docker 部署升级到 `1.15.0-enterprise`。

## 交付物

升级需要使用两个发布产物：

- `dify-enterprise-offline-1.15.0-enterprise.tar`
- `dify-enterprise-config-1.15.0-enterprise.tar.gz`

## 1. 先备份

在现有 `1.14.2-enterprise` 部署目录下执行：

```bash
export BACKUP_DIR=/data/backups/dify-1.14.2-$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"

cp -a docker/.env "$BACKUP_DIR/.env"
cp -a docker/volumes "$BACKUP_DIR/volumes"
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml ps > "$BACKUP_DIR/compose-ps.txt"
```

复制运行数据前，先停止旧版本服务：

```bash
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml down
```

## 2. 准备 1.15.0 部署目录

为 `1.15.0-enterprise` 创建新的部署目录，并在该目录中解压配置包：

```bash
mkdir -p /opt/dify-enterprise-1.15.0
cd /opt/dify-enterprise-1.15.0
tar -xzf /path/to/dify-enterprise-config-1.15.0-enterprise.tar.gz
```

如果是离线部署，加载离线镜像包：

```bash
docker load -i /path/to/dify-enterprise-offline-1.15.0-enterprise.tar
```

## 3. 迁移运行数据

把旧版本的 `.env` 和 `docker/volumes` 复制到新目录：

```bash
cp -a /path/to/dify-enterprise-1.14.2/docker/.env docker/.env
cp -a /path/to/dify-enterprise-1.14.2/docker/volumes docker/volumes
```

如果 PostgreSQL 数据文件因为权限问题无法由当前宿主机用户复制，可使用以 root 用户运行的临时容器复制：

```bash
docker run --rm \
  -v /path/to/dify-enterprise-1.14.2/docker/volumes:/old:ro \
  -v /opt/dify-enterprise-1.15.0/docker/volumes:/new \
  busybox:latest \
  sh -c 'rm -rf /new/db && mkdir -p /new && cp -a /old/db /new/db'
```

编辑 `docker/.env`，更新版本和运行时配置：

```bash
DIFY_ENTERPRISE_VERSION=1.15.0-enterprise
COMPOSE_PROFILES=weaviate,postgresql,collaboration
```

如果插件需要在离线或受限网络环境中安装依赖，请配置 PyPI 镜像：

```bash
PIP_MIRROR_URL=https://pypi.tuna.tsinghua.edu.cn/simple
```

## 4. 启动 1.15.0

在 `/opt/dify-enterprise-1.15.0` 目录下执行：

```bash
export DIFY_ENTERPRISE_VERSION=1.15.0-enterprise
export COMPOSE_PROFILES=weaviate,postgresql,collaboration

docker compose \
  --env-file docker/.env \
  -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml \
  config --images | sort -u
```

镜像列表必须包含：

```text
dify-api-enterprise:1.15.0-enterprise
dify-web-enterprise:1.15.0-enterprise
```

`api`、`web`、`worker`、`api_websocket`、`worker_beat` 等服务不能再显示 `1.14.2-enterprise`。

启动服务：

```bash
docker compose \
  --env-file docker/.env \
  -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml \
  up -d --force-recreate --pull never
```

## 5. 执行必要迁移

执行数据库迁移：

```bash
docker compose \
  --env-file docker/.env \
  -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml \
  exec api flask db upgrade
```

执行官方 `1.15.0` 必需的插件自动升级配置回填：

```bash
docker compose \
  --env-file docker/.env \
  -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml \
  exec api flask backfill-plugin-auto-upgrade
```

## 6. 校验向量索引

这一步用于避免常见问题：PostgreSQL 里的知识库、文档、分段已经迁移成功，但 Weaviate 启动到了空数据卷或挂载错误的数据卷。

```bash
scripts/check-enterprise-vector-indexes.sh
```

如果脚本报告缺失 Weaviate 类（class），只重建缺失的向量索引。重建数据来自现有 PostgreSQL 文档和分段，不重新解析上传文件：

```bash
scripts/check-enterprise-vector-indexes.sh --repair
scripts/check-enterprise-vector-indexes.sh
```

## 7. 验证运行状态

检查服务：

```bash
docker compose \
  --env-file docker/.env \
  -f docker/docker-compose.yaml \
  -f docker/docker-compose.enterprise.yaml \
  ps
```

确认镜像：

```bash
docker inspect docker-api-1 docker-api_websocket-1 docker-worker-1 docker-worker_beat-1 docker-web-1 \
  --format '{{.Name}} {{.Config.Image}}'
```

期望看到：

```text
dify-api-enterprise:1.15.0-enterprise
dify-web-enterprise:1.15.0-enterprise
```

打开 Web 页面并验证：

- 使用已有管理员账号登录
- 空间和用户仍然存在
- 应用和工作流可以打开
- 插件列表可以打开
- 知识库召回测试右侧能返回结果
- 企业智慧广场可以打开

## 回滚

如果升级验证失败：

1. 停止 `1.15.0-enterprise` 服务。
2. 使用已备份的 `.env` 和 `docker/volumes`，回到旧的 `1.14.2-enterprise` 目录启动。
3. 不要把部分迁移过的 `1.15.0` 运行数据当作回滚源。
