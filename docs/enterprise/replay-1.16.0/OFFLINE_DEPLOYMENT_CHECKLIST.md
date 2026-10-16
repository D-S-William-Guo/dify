# 离线生产环境部署检查清单

更新时间：2026-10-16（Asia/Shanghai）

## 目的

确认 Dify Enterprise 1.16.0 离线滚动升级的前置条件。本清单是指导，不构成连接目标主机或执行部署的授权；开发机演练结果也不能替代生产/灰度核验。

本次升级沿用现有有效连接配置；默认密码更换保留为独立加固事项，不再自行作为本次重放的阻塞条件。旧的 [Plan B runbook](PRODUCTION_PLAN_B_RUNBOOK.md) 记录的是另一种并行部署方案，不能当作当前滚动升级指令。

## 交付内容与使用方式

采用“镜像 tar + docker 部署文件 + 清单与升级指导”交付。配置压缩包解开后提供新的 docker 部署文件，不是可直接覆盖旧环境的整套运行配置。

本次产物位于 `dist/offline/rehearsal-82e50fff`，源码来源固定为 `82e50fff1b29b576d0e153b2e4316dc80d183de2`；四份完整 SHA-256 和本机验证边界见 [CURRENT_STATE](CURRENT_STATE.md)。后续仅修改文档不改变包来源身份。

| 交付文件 | 用途 |
| --- | --- |
| `dify-enterprise-offline-1.16.0-enterprise.tar` | 目标机加载全部镜像，不在线 build 或 pull |
| `dify-enterprise-config-1.16.0-enterprise.tar.gz` | 在独立暂存目录解开，提供 Compose、企业 overlay、nginx/SSRF 模板及 env 示例；包内还含 manifest/images 清单，不要将整个解包目录直接覆盖旧 docker 目录 |
| `manifest-1.16.0-enterprise.json`、`images-1.16.0-enterprise.txt` | 核对来源、镜像名称和精确 image ID；不能只比对可变 tag |
| 本清单及对应 SHA-256 记录 | 交接操作边界、配置合并方法、验收和回退要求 |

真实 `.env`、证书/私钥、运行数据与 sandbox `config.yaml` 不在交付包中；它们由目标环境自己的历史配置和数据提供，不从开发机复制。目标机加载包后须确认所有镜像 ID 与 manifest 一致；本地第一方镜像没有 registry RepoDigest，image ID 绑定不等于 registry 来源签名。

## 历史已检查（本机，2026-09-29）

以下保留当时记录，不代表目标机现状；后续本机镜像与历史数据回归见 CURRENT_STATE，执行前仍须重新核对目标身份。

- `docker context ls`：只有 default 本机 daemon，无远程/离线 context
- `~/.ssh/config`：不存在；known_hosts 存在但无可用离线主机别名
- 环境变量：无 `OFFLINE_HOST`/registry/offline 相关配置
- 文件系统：未发现独立 offline/deploy/prod Dify 目录（仅 openclaw/AI-Platform-Square-HB/enterprise-agent-poc）

结论：离线主机不是当前这台开发机的 Docker context；需要提供访问信息或在目标主机上执行下列检查。

## 离线主机必查项

取得该目标的单独只读授权后，在离线主机上执行并回传脱敏输出，不回传配置或 secret 内容：

```bash
# 1. 基础
uname -a
docker version --format '{{.Server.Version}}'
docker compose version
df -h /var/lib/docker /tmp
free -h
nproc

# 2. 端口占用：另核对该环境自定义入口（例如32401），不能只查默认端口
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

1. **先确认升级路径。** 核对目标实际运行版本、镜像 ID、数据库引擎/版本、Alembic revision、Compose 项目和实际挂载。旧存档记载生产/灰度曾使用定制1.16.1，不能假定今天是1.15.x，也不能未经兼容核验直接切到1.16.0。不同时升级数据库或向量库大版本；`dify-api-expand` 不纳入本轮替换。
2. **核验并准备交付物。** 目标机校验四产物 SHA-256，在独立暂存目录解开配置包；加载镜像并比对 manifest 的逐项 image ID。加载同名 tag 可能改变本地标签，加载前先保留旧精确镜像和回退引用；加载镜像本身不等于已切换服务。
3. **在批准的停机窗口制作一致备份。** 确认旧项目范围后停掉应用写入者及需要冷复制的数据服务；不得直接复制正在写入的数据库目录。记录停机前数据库 revision、关键对象计数和镜像/挂载身份。保留旧部署目录、旧镜像和备份，先确认备份范围、可读性、权限与恢复方式。
4. **完整平移旧目录和实际挂载。** 将该环境旧 docker 目录及实际挂载的数据复制到全新部署目录，保留属主、权限和必要配置；旧目录不覆盖、不删除。仓库目录以外的 bind mount 和 Docker named volume 必须按清单单独处理，不能假定复制 docker 目录就包含全部数据。关系库、Weaviate、文件存储和插件存储须来自一致备份；新旧栈不得同时写同一份数据。
5. **合并新部署文件，不整目录盲目覆盖。** 按下表逐项处理，在新目录完成 Compose 配置核验，确认所有数据挂载指向预定的新副本、端口/网络/项目名无冲突；不得误用旧绝对路径或 /tmp 演练路径，也不把打印出来的完整解析配置放入交付记录。
6. **单独确认数据库迁移。** 根据目标实际 revision 与候选迁移图确认支持的路径、执行主体和迁移步骤，先在该目标备份副本上验证；只由一个已确认的迁移入口执行并检查最终 revision 和关键计数。不得 stamp、跳过未知 revision 或猜测降级。开发机已升级后使用的 `MIGRATION_ENABLED=false` 不是目标环境通用指令；是否启用及何时关闭必须由该目标迁移方案决定，不能让多个 API 服务并发执行。
7. **启动并从真实入口验证。** 使用交付的精确镜像，不在线 build/pull；给服务明确的启动等待窗口，健康检查就绪后再测入口。将 nginx reload/restart 纳入该次批准范围，避免仍指向旧容器 IP；核对真实对外端口和 API/Web 路由，而非只看容器 running。失败保留现场并停止后续操作，不自动重试、回退或清理。
8. **验证历史功能后再交接。** 检查历史账号/工作区/应用/两文档等实际对象，执行受控召回与图片、一个对话流和一个文件工作流，以及该环境实际使用的企业入口；记录镜像 ID、时间及结果，不记录密钥或历史正文。默认不重索引、不改模型；发现模型前置问题按下节单独确认处理。

### 新旧文件合并规则

| 内容 | 如何处理 |
| --- | --- |
| Compose 和企业 overlay | 使用新版本服务结构，逐项保留目标所需的项目、端口、挂载与自定义扩展；保留 Agent 服务和官方安全选项，不能把旧 Compose 整份盖回去 |
| `.env` 及实际启用的分文件 env | 沿用目标环境有效连接、密码、加密密钥、功能开关等；对照新示例补齐必要新增项，检查 Compose 合并优先级，不用示例默认值覆盖旧值 |
| nginx/SSRF 模板、入口配置 | 以新版本结构合并目标自定义端口（如32401）、域名、代理和安全规则；处理实际生成配置与模板的对应关系，不能以为仅更新模板就已生效 |
| 证书、私钥、历史 storage/数据库/向量/插件数据 | 从该环境自己的受控备份迁移到新副本，保持权限；新配置包不得覆盖这些内容 |
| sandbox `volumes/sandbox/conf/config.yaml` | 迁移该环境历史配置，核对 `app.key` 与该环境 `SANDBOX_API_KEY` 一致，不打印值；缺失、来源或对应关系无法确认即停，空目录挂载会遮蔽镜像内配置 |

不要把 `config.yaml.example` 直接当作可用生产配置：其 `allowed_syscalls: [1, 2, 3]` 在本机隔离演练曾触发 `bad system call`；演练置空列表只证明单项合成任务通过，不是生产修改建议。默认密码轮换仍是独立延期加固，不与本次镜像升级合并。

### 历史应用模型绑定

默认模型切换不会重写已有应用/工作流的已发布节点。升级前按应用 ID（不能只按同名标题）核对已发布版的 provider、model 和凭据绑定名称，草稿不代表运行版。优先沿用目标可用模型和凭据；确需迁移时，单独批准该应用的模型修改、保存、发布与一次复测，不把开发机 qwen3.8-flash 或开发凭据直接套到目标。不要通过更换全局密钥掩盖单一旧应用的绑定问题。

### 回退与交付边界

- 切换前保留旧镜像的精确 ID、可用引用、旧 Compose/配置、旧目录和该目标一致备份；开发机旧冷备不能代替目标机备份。
- 未发生数据库/数据格式变化时，是否能只回退应用镜像也须核对兼容性。发生迁移或升级后已有新写入时，不能默认换回旧镜像即可恢复；不得让旧程序直接写未知的新 schema。
- 需要整库回退时，先停写并保留升级后的数据现场，再按另行批准的方案恢复对应关系库、向量和文件数据的一致副本。明确升级后新增数据的损失范围并由用户决定，不自动覆盖或执行降级。
- 本机已完成最终包镜像的历史数据重点回归与最小包检查；没有完成该新 tar 在真正离线目标机的加载/启动验收。未完整验证的功能、会话刷新等限制见 CURRENT_STATE，不将局部 PASS 写成生产全量验收通过。
- 不再笼统补齐所有测试，也不自动新建空数据演练；只补目标实际需要且影响本次升级的项目，接受限制和扩大范围由用户确认。实例清理、生产/灰度部署和 secret 轮换不因本清单完善而获准。

## 需要你提供

- 离线主机 IP/SSH 别名，或
- 上述必查项输出

目标信息只能用于另行授权的发布准备；本清单不授权连接、轮换 secret、执行部署或修改现有数据。
