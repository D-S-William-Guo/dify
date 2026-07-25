# B2 Inventory 独立复核报告

## 1. 复审身份与基线

- 复审类型：B2 Inventory 独立 Reviewer（非 Inventory 采集者，非 B2 Builder）
- 复审分支：`ctyun/replay-116-b2-inventory-reviewer`
- 复审 HEAD：`6f61419aa18c9fda6c48a3ed58b30feaaa968dac`
- Inventory 提交：`6f61419aa18c9fda6c48a3ed58b30feaaa968dac`，subject `docs: record B2 read-only upgrade inventory`
- Inventory 候选基线：`bfc122e98e21d03e02a0c197b9b5facceecfc073`
- 工作区：复审前干净，仅读取，未修改任何非本报告文件

## 2. 实际执行的只读复核命令（脱敏）

```bash
git status --short --branch
git rev-parse HEAD
git diff --name-status bfc122e98e21d03e02a0c197b9b5facceecfc073..HEAD

docker exec -e PGOPTIONS='-c default_transaction_read_only=on' docker-db_postgres-1 \
  psql -X -v ON_ERROR_STOP=1 -U postgres -d dify -c '<read-only query>'

docker exec docker-weaviate-1 wget -qO- http://127.0.0.1:8080/v1/{meta,schema,.well-known/live,.well-known/ready}

docker exec docker-api-1 python -c '<process-internal authenticated GET /v1/schema; hashed summary only>'

docker compose ls --format json
docker inspect --format '<selected fields>' <container>
docker inspect --format '{{json .Mounts}}' docker-ssrf_proxy-1

diff /home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/docker/ssrf_proxy/{docker-entrypoint.sh,squid.conf.template} \
     /home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/docker/ssrf_proxy/{docker-entrypoint.sh,squid.conf.template}

docker compose -f <1.14.2 compose files> config --no-path-resolution | extract weaviate/sandbox
docker compose -f <1.15.0 compose files> config --no-path-resolution | extract weaviate/sandbox
diff <1.14.2_compose_services> <1.15.0_compose_services>
```

未执行写入、DDL、migration、Alembic、Compose up/down、容器启停、volume 访问、pg_dump、`.env` 读取。

## 3. 文件范围与脱敏检查

### 3.1 文件范围

`git diff --name-status bfc122e98e21..HEAD` 仅输出：

```
A  docs/enterprise/replay-1.16.0/B2_INVENTORY.md
```

确认仅新增 Inventory 文件，无其他文件修改。

### 3.2 脱敏检查

B2_INVENTORY.md 全文扫描结果：

- 无密码、token、secret、API key 明文
- 无 Authorization header 值
- 无数据库/Redis 连接串
- 无用户邮箱、姓名
- 无 app/dataset/document 原始 ID、名称或正文
- 无 Weaviate class 原名（仅输出 SHA-256 短别名前 12 位 hex）
- Image ID、RepoDigest、脱敏 class hash 和 mount 路径已记录，允许

结论：**脱敏检查通过**。

## 4. PostgreSQL 复核结果

所有查询均设置 `PGOPTIONS='-c default_transaction_read_only=on'`。

| 检查项 | 预期（Inventory） | 实际（独立复核） | 结论 |
| --- | --- | --- | --- |
| PostgreSQL version | 15.17 | 15.17 | 一致 |
| alembic_version head | e2f0a9b7c6d5 | e2f0a9b7c6d5 | 一致 |
| enterprise_marketplace_assets 存在 | t | t | 一致 |
| 列数 | 16 | 16 | 一致 |
| 主键 | enterprise_marketplace_asset_pkey (id) | enterprise_marketplace_asset_pkey (id) | 一致 |
| 唯一约束 | unique_enterprise_marketplace_source_app (source_app_id) | unique_enterprise_marketplace_source_app (source_app_id) | 一致 |
| 索引 1 (主键) | enterprise_marketplace_asset_pkey | enterprise_marketplace_asset_pkey | 一致 |
| 索引 2 (唯一) | unique_enterprise_marketplace_source_app | unique_enterprise_marketplace_source_app | 一致 |
| 索引 3 | enterprise_marketplace_asset_source_tenant_id_idx | enterprise_marketplace_asset_source_tenant_id_idx | 一致 |
| 索引 4 | enterprise_marketplace_asset_status_idx (status, updated_at) | enterprise_marketplace_asset_status_idx (status, updated_at) | 一致 |
| 外键 | 无 | 无 | 一致 |

### 4.1 Marketplace 聚合

| metric | 预期 | 实际 | 结论 |
| --- | ---: | ---: | --- |
| 总行数 | 1 | 1 | 一致 |
| status = approved | 1 | 1 | 一致 |
| source_app_id IS NULL | 0 | 0 | 一致 |
| source_app_id IS NOT NULL | 1 | 1 | 一致 |
| 来源 app 存在且 status = normal | 1 | 1 | 一致 |
| 来源 app 缺失 | 0 | 0 | 一致 |
| 来源 app 异常状态 | 0 | 0 | 一致 |
| apps 全部 status 聚合 | normal = 6 | normal = 6 | 一致 |

### 4.2 核心对象计数

| table | 预期 | 实际 | 结论 |
| --- | ---: | ---: | --- |
| accounts | 3 | 3 | 一致 |
| tenants | 5 | 5 | 一致 |
| tenant_account_joins | 6 | 6 | 一致 |
| apps | 6 | 6 | 一致 |
| workflows | 9 | 9 | 一致 |
| datasets | 4 | 4 | 一致 |
| documents | 2 | 2 | 一致 |
| document_segments | 63 | 63 | 一致 |
| conversations | 2407 | 2407 | 一致 |

### 4.3 Plugin 相关表

| table | 预期 | 实际 | 结论 |
| --- | ---: | ---: | --- |
| account_plugin_permissions | 0 | 0 | 一致 |
| pipeline_recommended_plugins | 0 | 0 | 一致 |
| tenant_plugin_auto_upgrade_strategies | 30 | 30 | 一致 |
| workflow_plugin_triggers | 0 | 0 | 一致 |

### 4.4 Dataset/Document 与 Vector Class

| 检查项 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- |
| high_quality + index_struct present | 1 | 1 | 一致 |
| economy + index_struct absent | 2 | 2 | 一致 |
| NULL technique + index_struct absent | 1 | 1 | 一致 |
| index_struct.type | weaviate | weaviate | 一致 |
| class_prefix SHA-256 前 12 位 | 61372cc983f1 | 61372cc983f1 | 一致 |
| completed documents | 2 | 2 | 一致 |

PostgreSQL 复核结论：**全部一致**。所有聚合数与脱敏散列值均与 Inventory 记录完全匹配。

## 5. Weaviate 复核结果

所有请求在 `docker-api-1` 进程内部完成；endpoint/key 未打印，仅输出摘要。

### 5.1 基本健康与版本

| 检查项 | 结果 |
| --- | --- |
| GET /v1/meta version | 1.27.0 |
| GET /v1/.well-known/live | 成功（无输出，exit 0） |
| GET /v1/.well-known/ready | 成功（无输出，exit 0） |
| Weaviate 容器内匿名 GET /v1/schema | HTTP 403 |

### 5.2 认证 Schema

| 检查项 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- |
| HTTP status | 200 | 200 | 一致 |
| class_count | 1 | 1 | 一致 |
| class hash (SHA-256 前 12 hex) | 61372cc983f1 | 61372cc983f1 | 一致 |
| property_count | 9 | 9 | 一致 |
| vectorIndexType | UNKNOWN | UNKNOWN | 一致 |
| vectorizer | UNKNOWN | UNKNOWN | 一致 |
| vectorIndexConfig | UNKNOWN | UNKNOWN | 一致 |

API 响应未显式返回 `vectorIndexType`、`vectorizer`、`vectorIndexConfig`。Inventory 正确记录为 `UNKNOWN`，未猜测为 HNSW 或解释为没有索引。

### 5.3 PostgreSQL/Weaviate Class 集合对应

| metric | 预期 | 实际 | 结论 |
| --- | ---: | ---: | --- |
| expected (PG class_prefix hash) | 1 | 1 | 一致 |
| actual (Weaviate schema class hash) | 1 | 1 | 一致 |
| matched | 1 | 1 | 一致 |
| missing | 0 | 0 | 一致 |
| extra | 0 | 0 | 一致 |

Weaviate 复核结论：**全部一致**。

## 6. Compose/SSRF 复核结果

### 6.1 核心应用版本

| 容器 | image | config_files provenance | 结论 |
| --- | --- | --- | --- |
| api | dify-api-enterprise:1.15.0-enterprise | 1.15.0 | Enterprise 1.15.0 |
| web | dify-web-enterprise:1.15.0-enterprise | 1.15.0 | Enterprise 1.15.0 |
| worker | dify-api-enterprise:1.15.0-enterprise | 1.15.0 | Enterprise 1.15.0 |
| worker_beat | dify-api-enterprise:1.15.0-enterprise | 1.15.0 | Enterprise 1.15.0 |
| api_websocket | dify-api-enterprise:1.15.0-enterprise | 1.15.0 | Enterprise 1.15.0 |

核心 Dify 业务应用确实运行 **Enterprise 1.15.0**。

### 6.2 Weaviate/Sandbox 定义相同性

对 `docker/docker-compose.yaml` + `docker/docker-compose.enterprise.yaml` 两层展开后的 weaviate 和 sandbox service 定义逐字段比较，1.14.2 与 1.15.0 版本：

- **Weaviate 完整 service 定义：完全相同（diff 为空）**
- **Sandbox 完整 service 定义：完全相同（diff 为空）**

两版使用相同 image (`semitechnologies/weaviate:1.27.0`、`langgenius/dify-sandbox:0.2.15`)、相同 mounts、相同 networks、相同非敏感配置结构。

### 6.3 Weaviate/Sandbox 实际 Mount Provenance

| 容器 | mount source | provenance |
| --- | --- | --- |
| weaviate | `/home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/docker/volumes/weaviate` | 1.14.2 |
| sandbox | `/home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/docker/volumes/sandbox/conf` | 1.14.2 |
| sandbox | `/home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/docker/volumes/sandbox/dependencies` | 1.14.2 |

虽然 service 定义与 1.15 相同，但实际数据挂载路径仍来自 1.14.2，这是 provenance/数据所有权/备份来源问题。

### 6.4 SSRF Proxy Security Finding

#### 6.4.1 当前挂载

| mount | source (1.14.2) |
| --- | --- |
| docker-entrypoint.sh | `/home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/docker/ssrf_proxy/docker-entrypoint.sh` |
| squid.conf.template | `/home/ctyun/BigData/GitHub/dify-enterprise-1.14.2/docker/ssrf_proxy/squid.conf.template` |

#### 6.4.2 1.14.2 vs 1.15.0 安全差异（diff 验证）

| 安全特性 | 1.14.2 | 1.15.0 |
| --- | --- | --- |
| ACL 命名 | `acl localnet` (源允许) | `acl client_localnet` (源允许) |
| private destination ACL | 不存在 | `acl to_private_networks dst <14 段>` |
| private destination default deny | 不存在 | `http_access deny to_private_networks` |
| private IP allowlist 机制 | 不存在 | `write_optional_private_allowlist` 生成 `/etc/squid/dify_allow_private.conf` |
| private domain allowlist 机制 | 不存在 | `write_optional_private_allowlist` 生成 `/etc/squid/dify_allow_private.conf` |
| sandbox proxy 配置生成 | 硬编码 `cache_peer` 反向代理段 | 可选 `SSRF_SANDBOX_PROXY_PORT`/`SSRF_SANDBOX_PROXY_HOST` 动态生成 `/etc/squid/dify_sandbox_proxy.conf` |
| sandbox proxy 访问控制 | `acl src_all src all; http_access allow src_all` | 新 `dify_sandbox_proxy_port` ACL |
| entrypoint 中 private/sandbox 配置生成 | 不存在 | 存在（29 行新增） |
| template include | 无 | `include /etc/squid/dify_sandbox_proxy.conf`、`include /etc/squid/dify_allow_private.conf` |

#### 6.4.3 SSRF Compose Service 定义

两版 SSRF Proxy Compose service 定义中 image、volumes（bind mount 目标位置）、entrypoint 和 networks **相同**。

但 **environment contract 不同**：

| environment 变量 | 1.14.2 | 1.15.0 |
| --- | --- | --- |
| `HTTP_PORT` | 存在 | 存在 |
| `COREDUMP_DIR` | 存在 | 存在 |
| `REVERSE_PROXY_PORT` | 存在 | **不存在** |
| `SANDBOX_HOST` | 存在 | **不存在** |
| `SANDBOX_PORT` | 存在 | **不存在** |
| `SSRF_PROXY_ALLOW_PRIVATE_IPS` | **不存在** | 存在 |
| `SSRF_PROXY_ALLOW_PRIVATE_DOMAINS` | **不存在** | 存在 |

1.14.2 通过三个 sandbox 专用变量直接驱动旧 squid.conf.template 中硬编码的反向代理段；1.15.0 将其替换为两个 allowlist 变量，交由新的 docker-entrypoint.sh 生成 private/sandbox 配置。

当前容器既沿用了 1.14.2 的 environment contract，也挂载了 1.14.2 的 entrypoint/template，因此：

**当前 SSRF Proxy 没有执行 1.15.0 新增的 private destination 默认拒绝、private IP/domain allowlist 和新的 sandbox proxy 配置生成逻辑。**

这是一项**独立的安全配置漂移 finding**，Inventory 正确区分了：
- 旧 provenance（容器创建来源为 1.14.2）
- 部分相同基础设施（image、bind mount 目标、entrypoint 文本、networks）
- environment contract 差异（sandbox proxy 变量替换为 allowlist 变量）
- 真实安全配置漂移（挂载文件内容存在安全差异）

### 6.5 Weaviate/Sandbox 版本结论核实

Inventory 的表述准确：Weaviate/Sandbox 的 Compose service 定义和软件 image 与 1.15.0 完全相同，不能笼统声称这两个服务的"软件版本是 Dify 1.14.2"。准确结论是**容器创建来源和数据挂载 provenance 属于 1.14.2 路径**。

Compose/SSRF 复核结论：**核心应用版本、Weaviate/Sandbox 定义、SSRF mount provenance 及安全配置漂移 finding 均经独立确认成立**。

## 7. 门禁判断

### A. B2 migration 代码门禁 — 通过

| 前置条件 | 证据 | 状态 |
| --- | --- | --- |
| 当前 Alembic head 为旧企业 e2f0a9b7c6d5 | 独立查询确认 | 通过 |
| 三个旧企业 revision 可被历史图引用 | e2f0a9b7c6d5 的 ancestry 依赖 f1a14e1e9b41 和 c8f3d9d4a1be | 通过 |
| marketplace schema 与 c8f3d9d4a1be 一致 | 16 列、约束、索引独立确认与 Inventory 记录一致 | 通过 |
| 预期 Weaviate class 与实际完全匹配 | expected=1, actual=1, matched=1, missing=0, extra=0 | 通过 |

现有只读证据**足够支持**未来 Builder 仅执行：
- 原样恢复三个历史 revision（c8f3d9d4a1be、f1a14e1e9b41、e2f0a9b7c6d5）
- 新增无业务 DDL 的 1.16 空 merge（a71e16c0de01）
- migration graph tests

### B. 运行环境升级门禁 — 未授权

以下事项**仍未获授权**：

- 当前环境原地 migration
- Volume 移动、复制或重挂
- SSRF 修复或容器重建
- Weaviate repair
- 生产升级
- 业务验证通过声明

### B2_GO_WITH_CONDITIONS 判断

**Inventory 的 `B2_GO_WITH_CONDITIONS` 建议准确。**

该建议仅表示 B2 migration 代码门禁的 inventory 证据已足够，并非启动 B2 Builder 的授权。当前运行环境仍有独立条件（Weaviate/Sandbox provenance、SSRF 配置漂移），必须先经过本独立复核和人工门禁批准。

## 8. P0/P1/P2 Findings

### P0 — 无

### P1

| ID | 描述 | 类型 |
| --- | --- | --- |
| P1-01 | SSRF Proxy 当前挂载 1.14.2 entrypoint/template，未采用 1.15 新增的 private destination 默认拒绝和 allowlist 安全配置。这是独立的安全配置漂移，本 Review 不修复。 | 安全 |

### P2

| ID | 描述 | 类型 |
| --- | --- | --- |
| P2-01 | Weaviate/Sandbox 实际数据挂载 provenance 属于 1.14.2 路径。虽然 service 定义和软件 image 与 1.15.0 相同，但备份和隔离升级副本必须按这些实际路径建立。 | 运维 |
| P2-02 | Weaviate API 未显式返回 vectorIndexType/vectorizer/vectorIndexConfig，保持 UNKNOWN。升级演练必须独立验证向量索引能否正常工作（hit testing），不能依赖 schema 元数据。 | 验证 |

## 9. 最终结论

- **复核结论：PASS**
- **是否接受 B2_GO_WITH_CONDITIONS：接受**
- **PostgreSQL head：e2f0a9b7c6d5**
- **Weaviate class/hash 对应：expected=1, actual=1, matched=1, missing=0, extra=0，hash = sha256:61372cc983f1**
- **SSRF finding 成立：当前 SSRF Proxy 运行 1.14.2 配置，未采用 1.15 安全增强**
- **P0: 0, P1: 1 (SSRF), P2: 2 (Weaviate provenance, vectorIndexType UNKNOWN)**

## 10. 仍然禁止和仍然 UNKNOWN 的事项

### 仍然禁止

- 执行任何 SQL 写入、DDL 或 migration
- 执行 Alembic upgrade/downgrade/stamp
- 执行 docker compose up/down/restart/build/pull
- 停止、重启或重建容器
- 访问或复制 docker/volumes/** 内容
- 当前环境原地升级、volume 移动/复制/重挂
- SSRF 修复或容器重建
- Weaviate repair
- 生产升级
- Push、merge、rebase
- 启动 B2 Builder

### 仍然 UNKNOWN

- Weaviate vectorIndexType/vectorizer/vectorIndexConfig（API 未返回）
- Weaviate 对象/向量数量、document segment 完整性
- Hit testing 能否成功
- Plugin daemon 持久化数据完整性
- 备份可恢复性
- 1.16 migration 可执行性
- 已安装 plugin 总数（无规范化安装清单表）

### PASS 不等于自动授权 B2 Builder

本独立复核 PASS 仅确认 Inventory 证据准确、B2_GO_WITH_CONDITIONS 建议正确。B2 Builder 启动仍需独立的人工门禁明确批准。

## 11. 运行环境未修改声明

本次独立复核未执行任何写入操作。数据库、Weaviate、容器、volume、Compose 和运行状态均保持复审启动前的精确状态。未修改 B2_INVENTORY.md 或任何其他文件。本报告的创建是唯一的新增文件。
