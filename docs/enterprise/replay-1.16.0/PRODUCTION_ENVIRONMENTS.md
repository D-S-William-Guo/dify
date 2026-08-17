# Dify Enterprise 生产/灰度环境存档

更新时间：2026-08-17（Asia/Shanghai）
来源：离线主机自检输出（用户提供）

## 生产环境（zhyy-shuju-ai-62-6）

- OS: Linux 4.19.90-2102.2.0.0062.ctl2.x86_64 (ctyun)
- Docker: 25.0.3；Compose: v2.36.2
- 磁盘: 1007G，可用 678G (30%)
- 内存: 125Gi，可用 91Gi；CPU 64
- 端口: 443 已占用（现有 Dify nginx）
- 现有容器: `docker-1161-*`，镜像 `dify-api-enterprise:1.16.1-enterprise`、`dify-web-enterprise:1.16.1-enterprise`、agent/local-sandbox 1.16.1、plugin-daemon 0.6.3-local、sandbox 0.2.15、weaviate 1.27.0、redis 6、nginx、squid；另有 `dify-api-expand:latest`
- 网络: 默认路由 136.142.62.1；docker0/br 内网
- 外网: registry-1.docker.io DNS 可解析，HTTPS 超时（真离线）

## 灰度环境（zhyy-shuju-ai-62-7）

- OS/Docker/Compose 同生产版本
- 磁盘: 1007G，可用 268G (73%)
- 内存: 125Gi，可用 104Gi；CPU 64
- 端口: 443 已占用（现有 Dify nginx）
- 现有容器: 同生产 `docker-1161-*` 1.16.1-enterprise 全栈 + `dify-api-expand:latest`
- 网络: 默认路由 136.142.62.1；不同 docker bridge
- 外网: registry DNS 可解析，HTTPS 超时（真离线）

## 关键结论与风险

1. 两台主机都是**真离线**（无 Docker Hub 连通），适合离线包部署。
2. 两台主机**已在运行 1.16.1-enterprise**；本轮 replay/离线包基线是 **1.16.0-enterprise**，存在版本不一致，发布前必须确认目标版本。
3. 443 已被现有 nginx 占用；升级/替换需停机窗口或端口协调。
4. 存在自定义容器 `dify-api-expand:latest`，不在标准 compose 内，部署时须保留/单独处理。
5. secret 轮换、离线包复扫、registry push 均需以最终确认版本为准。

## 待确认

- 目标版本：沿用现有 1.16.1，还是切到本轮 1.16.0？
- 部署方式：就地替换现有 `docker-1161-*`，还是新 project 并存？
- `dify-api-expand` 是否继续保留？
