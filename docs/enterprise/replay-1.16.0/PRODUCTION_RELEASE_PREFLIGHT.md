# Dify Enterprise 1.16.0 生产发布前置状态

更新时间：2026-08-14（Asia/Shanghai）
候选 HEAD：`a53db8122688eb5ba00f9b8dbdb05cc22f31dc67`（origin 一致）

## 已就绪

| 项 | 状态 | 证据 |
| --- | --- | --- |
| 企业 API/Web 镜像 | ✅ `566bdf4c88cf` / `b76919e998`（本地构建，无 RepoDigest） | `evidence/phase-f-rebuild/`、`evidence/phase-h-rerun/` |
| 离线链 smoke | ✅ 同一 daemon `--pull never` 全 PASS | `evidence/phase-h-rerun/` |
| 私有 registry 登录态 | ✅ `~/.docker/config.json` 存在 `yd-srdart.srdcloud.cn` auth | 本地检查 |
| 迁移/运行/离线证据 | ✅ 全部闭环 | `DECISION_RISK_LEDGER.md`、`FINAL_VALIDATION_SUMMARY.md` |

## 阻塞项（需要外部输入，未执行）

| # | 步骤 | 缺失输入 | 无法自动执行的证据 |
| --- | --- | --- | --- |
| 1 | 真实 secret pattern 扫描 | 受保护环境生成的真实 pattern 文件（0600） | 环境无受保护 pattern；之前只用 synthetic |
| 2 | 真离线 Docker host 验证 | 无外网 Docker host 地址/SSH 访问 | `~/.ssh/config` 无 host；无 OFFLINE_HOST 环境变量 |
| 3 | 镜像 push 到私有 registry | 仓库路径（例如 `yd-srdart.srdcloud.cn/<ns>/dify-api-enterprise`）、tag 策略、push 授权 | 本地镜像 RepoDigest 为空；registry 登录态存在但无目标 repo 名 |
| 4 | 镜像签名/审计 | signing key / notary / cosign 配置 | `~/.docker/trust` 不存在；无签名密钥 |
| 5 | 隔离环境部署演练 | 独立主机/Compose/存储/网络配置 | 无独立环境；当前只有 1.15 生产栈和本地 daemon |
| 6 | 生产备份/回滚演练 | 生产运维窗口、备份存储、回滚目标 | 属生产运维操作，未获环境/窗口 |

## 自动化进展（2026-08-14 第二轮）

- 尝试只读查询私有 registry catalog（`https://yd-srdart.srdcloud.cn/v2/_catalog`）：代理/无代理、放宽 TLS 均失败（SSL EOF / timeout），无法自动推断仓库路径。
- 签名工具检查：`cosign`/`notary` 均未安装；`~/.docker/trust` 不存在。
- 离线 Docker host：无 SSH config、无 `OFFLINE_HOST` 环境变量，无法自动连接。
- 真实 secret pattern：环境无受保护 pattern 文件；此前 synthetic 扫描已 PASS。
- 本地可复用镜像：API `566bdf4c88cf`、Web `b76919e998` 存在。

## 待输入就绪后的执行命令（runbook 占位）

### 1. 真实 secret 扫描

```bash
scripts/ci/check-enterprise-offline.sh \
  -Archive <离线tar> -ConfigArchive <config.tar.gz> \
  -Manifest <manifest.json> -Images <images.txt> \
  -SecretsPattern <受保护0600 pattern文件>
```

### 2. 真离线 Docker host

```bash
scp dist/offline/dify-enterprise-offline-1.16.0-enterprise.tar <offline-host>:/
ssh <offline-host> 'docker load -i /dify-enterprise-offline-1.16.0-enterprise.tar && docker compose ... up -d --pull never'
```

### 3. 镜像 push 到 registry（需仓库路径）

```bash
docker tag dify-api-enterprise:1.16.0-enterprise <registry>/<ns>/dify-api-enterprise:1.16.0-enterprise
docker tag dify-web-enterprise:1.16.0-enterprise <registry>/<ns>/dify-web-enterprise:1.16.0-enterprise
docker push <registry>/<ns>/dify-api-enterprise:1.16.0-enterprise
docker push <registry>/<ns>/dify-web-enterprise:1.16.0-enterprise
docker manifest inspect <registry>/<ns>/dify-api-enterprise:1.16.0-enterprise
```

### 4. 签名

```bash
# cosign 或 notary 安装并配置密钥后：
cosign sign <registry>/<ns>/dify-api-enterprise:1.16.0-enterprise
cosign sign <registry>/<ns>/dify-web-enterprise:1.16.0-enterprise
cosign verify ... 
```

### 5. 隔离部署演练

独立主机/Compose/存储上，用 pushed 镜像 + `--pull never` 起栈，重复 Phase H smoke。

### 6. 备份/回滚

生产运维窗口：先全量备份，再演练恢复目标、启动 1.15、核对 inventory。

## 可立即继续的路径

提供以下任一输入后可自动继续：

1. 真实 secret pattern 文件路径（或受保护环境执行命令）。
2. 离线 Docker host 的 SSH 地址/别名。
3. 私有 registry 仓库路径与目标 tag。
4. 签名工具与密钥位置（cosign/notary）。
5. 隔离演练环境的连接信息。
6. 备份/回滚演练窗口。

缺少上述输入前，剩余步骤保持 NOT_RUN，不伪造执行。
