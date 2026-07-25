# B2 只读升级前 Inventory

## 1. 结论

**建议：`B2_GO_WITH_CONDITIONS`。**

PostgreSQL 侧确认当前数据库实际 Alembic head 为旧企业 head
`e2f0a9b7c6d5`，`enterprise_marketplace_assets` 的实际结构与历史
revision `c8f3d9d4a1be` 一致，且现有 marketplace 来源 app 聚合未发现缺失
或异常状态。这支持“恢复三个旧企业 revision，并用空 merge 连接官方
1.16 head”的数据库历史前置假设。

认证的只读 Weaviate schema GET 进一步确认 1 个 class，且其 SHA-256
脱敏别名与 PostgreSQL 中唯一需要向量索引的 high-quality dataset 的
`class_prefix` 完全匹配，缺失和额外 class 均为 0。因此，仅就 B2 migration
代码门禁，证据已足够支持恢复三个历史 revision 和创建空 merge。

`B2_GO_WITH_CONDITIONS` 不是启动 B2 Builder 的授权。当前运行环境仍有独立
条件：Weaviate/Sandbox 的数据挂载 provenance 属于 1.14.2 路径；运行中的
SSRF Proxy 仍挂载 1.14.2 entrypoint/template，未采用 1.15 新增的 private
destination 默认拒绝和 allowlist 安全配置。必须先经过独立 Inventory
Reviewer 和人工门禁批准；本任务不授权 migration、repair、Compose 变更、
SSRF 修复、容器重建或 volume 操作。

## 2. 采集身份与只读边界

- 初次采集时间：`2026-07-25T11:11:45+08:00`
- 整改补采时间：`2026-07-25T11:31:01+08:00`
- 候选 commit：`bfc122e98e21d03e02a0c197b9b5facceecfc073`
- 整改起点提交：`b48622dbc412bc949941920be320d05868f14a5a`
- 分支：`ctyun/replay-116-b2-inventory`
- 启动门禁：分支、HEAD 均符合要求；采集前工作区干净。
- 数据库边界：仅执行 `SHOW`、information schema/系统目录 `SELECT`、
  `COUNT` 和 `GROUP BY`；所有 psql 调用均设置
  `PGOPTIONS='-c default_transaction_read_only=on'`。
- Weaviate 边界：仅执行 HTTP GET；未查询或导出对象正文。一次认证
  `GET /v1/schema` 在 `docker-api-1` 进程内部读取该进程已持有的 endpoint/key；
  endpoint、key 和 Authorization header 均未打印或传回宿主 shell。
- Docker 边界：仅使用 `docker ps`、`docker compose ls` 和精确字段
  `docker inspect`/`docker image inspect`；未通过 inspect 读取 `.Config.Env`。
- volume 边界：只记录 inspect 返回的 mount 类型及源/目标路径；未访问、
  读取、复制或修改任何挂载内容或 `docker/volumes/**` 文件。
- 脱敏边界：未查询或记录具体业务 ID、邮箱、姓名、应用/知识库名称、文档
  内容、DSL、凭据、密码、token、secret、连接串或完整环境变量。

本次没有执行 Compose up/down/restart/build/pull，没有停止或重启容器，没有
执行数据库写入、DDL、VACUUM、migration、Alembic upgrade/downgrade/stamp，
没有调用 Weaviate 写接口，也没有修改数据库、Weaviate、容器、volume 或运行
状态。

## 3. 实际执行命令（脱敏形式）

```bash
git status --short --branch
git rev-parse HEAD

docker compose ls --format json
docker ps --filter label=com.docker.compose.project=docker --format '<selected fields>'
docker inspect --format '<name/service/project/working_dir/config_files/image/state/health/mounts>' <container>
docker image inspect --format '<image ID/tags/repo digests>' <image ID>

docker exec \
  -e PGOPTIONS='-c default_transaction_read_only=on' \
  docker-db_postgres-1 \
  psql -X -v ON_ERROR_STOP=1 -U postgres -d dify \
  -c '<SHOW or SELECT-only inventory query>'

docker exec docker-weaviate-1 \
  wget -qO- http://127.0.0.1:8080/v1/meta
docker exec docker-weaviate-1 \
  wget -qO- http://127.0.0.1:8080/v1/schema
docker exec docker-weaviate-1 \
  wget -qO- http://127.0.0.1:8080/v1/.well-known/{live,ready}
docker exec docker-api-1 \
  python -c '<process-internal authenticated GET /v1/schema; hashed summary only>'
```

没有使用 `pg_dump`，没有读取 `.env`，也没有打印 Docker Env。仅获授权的
容器内脚本从自身进程环境读取 Weaviate endpoint/key 并在容器内完成请求；
命令输出和本报告均不包含认证值。

## 4. Compose 与 runtime 身份

### 4.1 Project 级身份

`docker compose ls` 报告 project `docker` 为 `running(12)`，并同时聚合四个
config 文件：

- `/home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/docker/docker-compose.yaml`
- `/home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/docker/docker-compose.enterprise.yaml`
- `/home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/docker/docker-compose.yaml`
- `/home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/docker/docker-compose.enterprise.yaml`

原因已通过逐容器 labels 独立核实：Docker Compose 按相同 project 名
`docker` 聚合仍在运行的容器。1.15.0 重建了核心应用及多数基础服务，但
Weaviate、sandbox、ssrf_proxy 未重建；后者仍以同一 project 名运行，所以
project 级 `ConfigFiles` 同时出现两代路径。这是容器创建 provenance、数据
所有权和备份来源的混合状态；不能据此笼统声称整个系统仍运行 Dify 1.14.2。

### 4.2 容器、镜像与状态

所有 12 个容器的 project 均为 `docker`，状态均为 `running`。

| service / container | 容器创建 provenance label | image | image ID | health |
| --- | --- | --- | --- | --- |
| `nginx` / `docker-nginx-1` | 1.15.0 | `nginx:latest` | `sha256:6c3a6ea6608c89c79027066654a2ef4f0fe58a7bf2c08cc3894733406e476602` | not configured |
| `web` / `docker-web-1` | 1.15.0 | `dify-web-enterprise:1.15.0-enterprise` | `sha256:ed1b6cc1bbb27ce54052152a06b0aa4b6fd18292704720a228bcb01f4ff93808` | not configured |
| `plugin_daemon` / `docker-plugin_daemon-1` | 1.15.0 | `langgenius/dify-plugin-daemon:0.6.3-local` | `sha256:7837b8d62dea565822b6f87bcf22d12ca5a54fcd4666880b1d8dd2152b3b2cf0` | not configured |
| `worker` / `docker-worker-1` | 1.15.0 | `dify-api-enterprise:1.15.0-enterprise` | `sha256:051f1f1caf97ad8daf13f2785de96e93c7cd24b86944505852fa96275d810166` | not configured |
| `api` / `docker-api-1` | 1.15.0 | `dify-api-enterprise:1.15.0-enterprise` | `sha256:051f1f1caf97ad8daf13f2785de96e93c7cd24b86944505852fa96275d810166` | healthy |
| `worker_beat` / `docker-worker_beat-1` | 1.15.0 | `dify-api-enterprise:1.15.0-enterprise` | `sha256:051f1f1caf97ad8daf13f2785de96e93c7cd24b86944505852fa96275d810166` | not configured |
| `api_websocket` / `docker-api_websocket-1` | 1.15.0 | `dify-api-enterprise:1.15.0-enterprise` | `sha256:051f1f1caf97ad8daf13f2785de96e93c7cd24b86944505852fa96275d810166` | not configured |
| `db_postgres` / `docker-db_postgres-1` | 1.15.0 | `postgres:15-alpine` | `sha256:c1dd58d6cec8e67cb85b2c8fd200fa870697269c5024e59627095326a8254ae2` | healthy |
| `redis` / `docker-redis-1` | 1.15.0 | `redis:6-alpine` | `sha256:474c77ec7e49d73a86e345ccd2c4a53a5f43b485691294d3af63a2a1af4d6170` | healthy |
| `weaviate` / `docker-weaviate-1` | 1.14.2 | `semitechnologies/weaviate:1.27.0` | `sha256:f24b5f0e68e6629024cd525876cd4a1c4cf313ec9295168ab6784ea09ef6d382` | not configured |
| `ssrf_proxy` / `docker-ssrf_proxy-1` | 1.14.2 | `ubuntu/squid:latest` | `sha256:f49c57d208193ab0d5468e8daedf2eb48d78b3a842bd1d9f8849db13d566b024` | not configured |
| `sandbox` / `docker-sandbox-1` | 1.14.2 | `langgenius/dify-sandbox:0.2.15` | `sha256:4782db7ea946f2f4a42ad1016ea32ec764bbe1287dbb584eff8c741d63b953d9` | healthy |

API、worker、worker_beat 与 api_websocket 使用同一不可变 API image ID。企业
API/Web 本地镜像没有 RepoDigest；其他安全可得的主要 RepoDigest 为：

- PostgreSQL:
  `postgres@sha256:09e4f20b14ddb3dfe3a0c825b206032aaf8f28300ba2070c0b60fc1c10c6abc7`
- Weaviate:
  `semitechnologies/weaviate@sha256:53fa576934f8e2c9130dc3a61a0f9b7d9330fe0ff456ccb37db05d03b700abc9`
- sandbox:
  `langgenius/dify-sandbox@sha256:750e1111426ef31a9217b81c98cccfb750f17b182af3221102e420afa9f0928e`
- plugin daemon:
  `langgenius/dify-plugin-daemon@sha256:3c694329357bc580b28bdec59321a981acd3279f8f69d1a3fb59a47cf7f770c3`

### 4.3 核心应用实际版本结论

核心 Dify 业务应用确实运行 1.15.0 企业镜像：

- API、worker、worker_beat、api_websocket：
  `dify-api-enterprise:1.15.0-enterprise`，且不可变 image ID 相同。
- Web：`dify-web-enterprise:1.15.0-enterprise`。

因此本环境的核心业务应用版本结论是 **Dify Enterprise 1.15.0**。下述
1.14.2 provenance 只适用于未重建的基础服务，不能被表述为核心应用仍运行
1.14.2。

### 4.4 Weaviate 与 Sandbox 定义复核

对两份基础 Compose 定义逐字段比较后：

| 项目 | Weaviate 1.14.2 vs 1.15.0 | Sandbox 1.14.2 vs 1.15.0 |
| --- | --- | --- |
| 完整 service 定义 | 相同 | 相同 |
| image | 均为 `semitechnologies/weaviate:1.27.0` | 均为 `langgenius/dify-sandbox:0.2.15` |
| mounts | 均为 `./volumes/weaviate:/var/lib/weaviate` | 均挂载 `./volumes/sandbox/dependencies:/dependencies` 和 `./volumes/sandbox/conf:/conf` |
| healthcheck | 两版均未配置 | 两版均为 GET `localhost:8194/health` |
| network | 两版均未显式声明，使用 project default network | 两版均为 `ssrf_proxy_network` |
| 非敏感配置结构 | environment 名称、值及 service keys 均相同 | env_file、environment 名称/值及 service keys 均相同 |

运行容器使用的 Weaviate/Sandbox image 与 1.15 定义相同，所以不能根据旧
working_dir/config label 声称这两个服务的软件版本是 Dify 1.14.2。准确结论
是：容器创建来源和实际数据挂载仍属于 1.14.2 路径，这是 provenance、数据
所有权和备份来源问题。

隔离升级的备份集合必须使用 inspect 确认的实际 1.14.2 Weaviate/Sandbox
挂载路径。当前环境不得原地移动、重新挂载或把路径切换到 1.15.0。

### 4.5 SSRF Proxy 独立安全 finding

SSRF Proxy 不是“定义相同但 label 较旧”。两版虽使用相同
`ubuntu/squid:latest` image、相同两个 bind target 和相同 networks，但
environment 结构、entrypoint 和 Squid template 存在真实安全漂移。

1.15 新增的安全行为包括：

- 增加 private destination 地址 ACL，默认在通用放行前拒绝 private
  destination；
- 支持通过 `SSRF_PROXY_ALLOW_PRIVATE_IPS` 和
  `SSRF_PROXY_ALLOW_PRIVATE_DOMAINS` 对选定 private IP/network 或 domain
  建立可选 allowlist；
- entrypoint 分别生成 private allowlist 配置和 sandbox proxy 配置；
- sandbox proxy 改为由可选 host/port 配置生成专用 Squid include，而不是
  1.14.2 template 中固定的反向代理段。

当前 `docker-ssrf_proxy-1` 明确挂载 1.14.2 的
`docker-entrypoint.sh` 和 `squid.conf.template`，且容器创建 labels 指向
1.14.2 Compose；本任务未读取 runtime Env。因此无论是否额外注入变量，当前
运行容器都**没有执行上述 1.15 entrypoint/template 安全配置**。这是独立的
运行环境安全 finding；本 inventory 不修复、不重建也不重启 SSRF Proxy。

### 4.6 Mount 路径 inventory

以下仅为 inspect 返回的路径；未读取路径内容。

表中 `1.15.0` 前缀表示
`/home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/`，`1.14.2` 前缀表示
`/home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/`。

| service | type | source → target |
| --- | --- | --- |
| `nginx` | bind | 1.15.0 `docker/nginx/docker-entrypoint.sh` → `/docker-entrypoint-mount.sh` |
| `nginx` | bind | 1.15.0 `docker/nginx/ssl` → `/etc/ssl` |
| `nginx` | bind | 1.15.0 `docker/volumes/certbot/conf/live` → `/etc/letsencrypt/live` |
| `nginx` | bind | 1.15.0 `docker/nginx/https.conf.template` → `/etc/nginx/https.conf.template` |
| `nginx` | bind | 1.15.0 `docker/volumes/certbot/conf` → `/etc/letsencrypt` |
| `nginx` | bind | 1.15.0 `docker/nginx/proxy.conf.template` → `/etc/nginx/proxy.conf.template` |
| `nginx` | bind | 1.15.0 `docker/nginx/conf.d` → `/etc/nginx/conf.d` |
| `nginx` | bind | 1.15.0 `docker/volumes/certbot/www` → `/var/www/html` |
| `nginx` | bind | 1.15.0 `docker/nginx/nginx.conf.template` → `/etc/nginx/nginx.conf.template` |
| `plugin_daemon` | bind | 1.15.0 `docker/volumes/plugin_daemon` → `/app/storage` |
| `api`, `worker` | bind | 1.15.0 `docker/volumes/app/storage` → `/app/api/storage` |
| `db_postgres` | bind | 1.15.0 `docker/volumes/db/data` → `/var/lib/postgresql/data` |
| `redis` | bind | 1.15.0 `docker/volumes/redis/data` → `/data` |
| `weaviate` | bind | 1.14.2 `docker/volumes/weaviate` → `/var/lib/weaviate` |
| `ssrf_proxy` | bind | 1.14.2 `docker/ssrf_proxy/docker-entrypoint.sh` → `/docker-entrypoint-mount.sh` |
| `ssrf_proxy` | bind | 1.14.2 `docker/ssrf_proxy/squid.conf.template` → `/etc/squid/squid.conf.template` |
| `ssrf_proxy` | volume | `/home/ctyun/BigData/docker_root/volumes/6e195fa8776bfcf0770f3f8bfee1b853fd6450491679bcd4c1b473194ac2e230/_data` → `/var/log/squid` |
| `ssrf_proxy` | volume | `/home/ctyun/BigData/docker_root/volumes/ef797a6fee622e3deb6fa6b9b285560dac3c59b48fcb036c0943b9bcc7c0611a/_data` → `/var/spool/squid` |
| `sandbox` | bind | 1.14.2 `docker/volumes/sandbox/conf` → `/conf` |
| `sandbox` | bind | 1.14.2 `docker/volumes/sandbox/dependencies` → `/dependencies` |

`web`、`worker_beat` 和 `api_websocket` 无 mounts。

## 5. PostgreSQL inventory

### 5.1 Server 与 migration identity

- PostgreSQL server version：`15.17`
- `alembic_version` 实际唯一值：`e2f0a9b7c6d5`
- 分类：**旧企业 head**，不是官方 1.16 head `7a1c2d9e4b60`，也不是其他值。

旧企业历史文件显示：

```text
c8f3d9d4a1be
  └─> f1a14e1e9b41 (另一个 parent: a4f2d8c9b731)
        └─> e2f0a9b7c6d5 (另一个 parent: d9e8f7a6b5c4)
```

数据库只在 `alembic_version` 中记录当前 head，但该值按旧历史图逻辑依赖
`f1a14e1e9b41` 和 `c8f3d9d4a1be`。因此三个旧企业 revision 均可能仍被该
数据库历史引用；删除任一历史 revision 会破坏可解析性。

### 5.2 `enterprise_marketplace_assets`

表存在，共 16 列：

| column | type | nullable | default |
| --- | --- | --- | --- |
| `id` | varchar | NO | none |
| `source_tenant_id` | varchar | NO | none |
| `source_app_id` | varchar | NO | none |
| `submitter_account_id` | varchar | NO | none |
| `reviewer_account_id` | varchar | YES | none |
| `status` | varchar | NO | `'pending'` |
| `title` | varchar | NO | none |
| `description` | text | NO | `''` |
| `category` | varchar | NO | `'General'` |
| `tags` | json | NO | none |
| `scenario` | text | NO | `''` |
| `allow_show_workspace_name` | boolean | NO | `false` |
| `review_note` | text | YES | none |
| `created_at` | timestamp without time zone | NO | `CURRENT_TIMESTAMP` |
| `updated_at` | timestamp without time zone | NO | `CURRENT_TIMESTAMP` |
| `reviewed_at` | timestamp without time zone | YES | none |

约束：

- primary key `enterprise_marketplace_asset_pkey`：`(id)`
- unique constraint `unique_enterprise_marketplace_source_app`：
  `(source_app_id)`
- foreign key：**无**

索引：

- unique btree `enterprise_marketplace_asset_pkey (id)`
- unique btree `unique_enterprise_marketplace_source_app (source_app_id)`
- btree `enterprise_marketplace_asset_source_tenant_id_idx (source_tenant_id)`
- btree `enterprise_marketplace_asset_status_idx (status, updated_at)`

与历史 migration `c8f3d9d4a1be` 比对：16 列、nullable/default、主键、唯一
约束和两个附加索引均一致；未观察到非标准 schema 漂移。该历史 schema
不包含 1.16 计划中的不可变快照字段，后者仍属于未来 B4，而不是 B2。

### 5.3 Marketplace 聚合

| metric | count |
| --- | ---: |
| 总行数 | 1 |
| status = `approved` | 1 |
| `source_app_id IS NULL` | 0 |
| `source_app_id IS NOT NULL` | 1 |
| 来源 app 存在、tenant 匹配且 app status = `normal` | 1 |
| 来源 app 缺失 | 0 |
| 来源 app 异常状态 | 0 |
| 来源 app tenant 不匹配 | 0 |

全体 apps 的 status 聚合仅有 `normal = 6`。未输出任何 app ID、名称或业务
内容。

### 5.4 核心对象聚合计数

| table | count |
| --- | ---: |
| `accounts` | 3 |
| `tenants` | 5 |
| `tenant_account_joins` | 6 |
| `apps` | 6 |
| `workflows` | 9 |
| `datasets` | 4 |
| `documents` | 2 |
| `document_segments` | 63 |
| `conversations` | 2407 |

当前 `public` schema 中没有名为 `plugins` 或 `plugin_installations` 的规范化
安装清单表。安全可识别的 plugin 相关表聚合为：

| table | count |
| --- | ---: |
| `account_plugin_permissions` | 0 |
| `pipeline_recommended_plugins` | 0 |
| `tenant_plugin_auto_upgrade_strategies` | 30 |
| `workflow_plugin_triggers` | 0 |

因此“已安装 plugin 总数”是 `UNKNOWN`；上述相关表计数不能替代 plugin
daemon 持久化 inventory。

### 5.5 Dataset/document 与预期 vector class 聚合

`datasets` 按 indexing technique 和 `index_struct` 是否存在聚合：

| indexing technique | index_struct | count |
| --- | --- | ---: |
| `high_quality` | present | 1 |
| `economy` | absent | 2 |
| NULL | absent | 1 |

`documents` schema 没有单独的 `status` 列；按实际存在的
`indexing_status` 聚合为：

| indexing_status | count |
| --- | ---: |
| `completed` | 2 |

本次将 `indexing_technique = 'high_quality'` 定义为实际需要向量索引的
dataset。聚合结果：

- 需要向量索引的 dataset：1
- 其中 `index_struct.vector_store.class_prefix` 存在：1
- 缺失 class_prefix：0
- `index_struct.type`：`weaviate`，1
- PostgreSQL 预期 class 脱敏别名：`sha256:61372cc983f1`

class_prefix 在 PostgreSQL 内使用 SHA-256 计算，仅输出前 12 位 hex；未将
class_prefix 明文、dataset ID 或 dataset 名称传出数据库。

## 6. Weaviate inventory

- 容器 image tag：`semitechnologies/weaviate:1.27.0`
- GET `/v1/meta` 返回 version：`1.27.0`
- GET `/v1/.well-known/live`：成功
- GET `/v1/.well-known/ready`：成功
- Weaviate 容器内匿名 GET `/v1/schema`：HTTP 403
- API 容器内认证 GET `/v1/schema`：HTTP 200
- schema/class 总数：1
- class 脱敏别名：`sha256:61372cc983f1`
- property 数量：9
- `vectorIndexType`：API 响应未显式提供，`UNKNOWN`；不得将缺失解释为没有
  向量索引，也不得猜测为 HNSW。
- `vectorizer`：API 响应未显式提供，`UNKNOWN`。
- `vectorIndexConfig`：API 响应未显式提供，`UNKNOWN`/使用服务默认值待确认。

认证请求只在 `docker-api-1` 内部读取并使用该进程已有的 endpoint/key；只向
宿主输出 HTTP status、数量、SHA-256 短别名和安全字段摘要。没有打印
endpoint、API key、Authorization header 或完整 Env，也没有查询对象列表或
正文。

### 6.1 PostgreSQL/Weaviate class 集合对应

PostgreSQL 预期 `weaviate` class 集合与 Weaviate schema 实际 class 集合使用
相同算法（class/class_prefix UTF-8 字节的 SHA-256，前 12 位 hex）比较：

| metric | count |
| --- | ---: |
| PostgreSQL 预期 Weaviate class | 1 |
| Weaviate 实际 class | 1 |
| 匹配 | 1 |
| 缺失 | 0 |
| 额外 | 0 |

该聚合证明当前唯一 high-quality dataset 的预期 class 在 schema 中存在，且
没有额外 class。它不证明 class 内对象数量、向量内容、document segment
完整性或 hit testing 成功，因为本任务没有查询任何 Weaviate 对象正文或向量。

## 7. B2 风险判定

### 7.1 A. B2 migration 代码门禁

| 问题 | 结论 |
| --- | --- |
| 当前 Alembic head | 旧企业 `e2f0a9b7c6d5` |
| 三个旧企业 revision 是否可能仍被引用 | 是；实际 head 的旧历史 ancestry 依赖 `f1a14e1e9b41` 和 `c8f3d9d4a1be` |
| marketplace 实际 schema 是否与旧 migration 一致 | 是，与 `c8f3d9d4a1be` 一致 |
| B2 恢复历史 revision 的前置假设 | PostgreSQL 证据支持 |
| B2 空 merge 的前置假设 | PostgreSQL 证据支持连接旧企业 head 与官方 `7a1c2d9e4b60`；本任务未运行或验证 migration 图 |
| migration 代码证据结论 | 已有足够只读证据恢复三个历史 revision 并创建无业务 DDL 的空 merge |

### 7.2 B. 运行环境与升级演练门禁

| 项目 | 结论 |
| --- | --- |
| 核心 Dify 应用版本 | API/Web/worker/beat/websocket 确实为 Enterprise 1.15.0 |
| Weaviate/Sandbox provenance | 定义与 1.15 相同、软件 image 相同，但容器创建来源和数据 mount 仍是 1.14.2 路径 |
| SSRF Proxy | 存在真实安全配置漂移；当前容器未采用 1.15 private destination deny/allowlist 与新 sandbox proxy 生成方式 |
| PostgreSQL/Weaviate 对应 | 预期 1、实际 1、匹配 1、缺失 0、额外 0 |
| 备份与隔离副本 | 必须按 inspect 的实际 mount provenance 建立完整备份和隔离副本 |
| 当前运行环境 | 禁止原地升级、移动/重挂 volume、修复或重建 SSRF Proxy |
| 仍需审批 | 独立 Inventory Reviewer 和人工门禁 |

### 7.3 最终建议

**`B2_GO_WITH_CONDITIONS`**：只表示 B2 migration 代码门禁的 inventory 证据
已足够。它不允许修改当前容器或 volume，不允许执行 migration，不允许修复
SSRF，不允许启动 B2 Builder。Builder 启动仍须独立 Inventory Reviewer 和
人工门禁明确批准。

## 8. 已证明、未证明与后续要求

本 inventory 只证明采集时刻：

- 12 个运行容器的 labels、镜像、image ID/digest、mount 路径、状态和 health；
- 核心 Dify 应用实际运行 Enterprise 1.15.0；
- project `docker` 的 Weaviate/Sandbox 数据 provenance 仍指向 1.14.2 路径，
  但两版 service 定义和软件 image 相同；
- SSRF Proxy 当前使用 1.14.2 配置，未采用已核实的 1.15 安全增强；
- PostgreSQL 15.17 的实际旧企业 head、表结构及脱敏聚合计数；
- marketplace 现有行的来源 app 聚合可正常匹配；
- Weaviate 1.27.0 进程 live/ready、schema class 总数和脱敏结构；
- PostgreSQL 预期 class 与 Weaviate schema class 哈希集合完全匹配。

本 inventory **没有证明**：

- 1.16 migration 可执行、单一最终 head 可形成或 rollback 可恢复；
- Weaviate 响应未显式提供的 vector index type/config 默认值；
- Weaviate 对象/向量数量、document segment 完整性或 hit testing 成功；
- plugin daemon 安装数据、storage、Redis 或文件内容完整；
- 业务 smoke、hit testing、智慧广场复制或无 secret DSL 快照行为；
- 备份可恢复、隔离升级副本可用，或当前 volume 可以原地升级。

后续升级必须由运维先创建数据库、storage、Redis、plugin 和 vector store 的
可恢复备份，并建立隔离升级副本。源 volume 必须保持只读，且不得被新
Compose 直接挂载。migration 只能在隔离副本执行；失败时从备份恢复到新的
隔离目标。**不得直接升级当前运行 volume，也不得使用 Alembic stamp 或
downgrade 作为原地升级/回滚手段。**
