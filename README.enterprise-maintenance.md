# Dify 企业版维护说明

这份文档用于说明当前仓库的企业版维护方式，面向三类读者：

- 你自己以后换电脑继续开发时
- 其他工程师接手这个仓库时
- 需要快速理解仓库规则的 AI IDE / agent

这不是聊天记录摘要，而是当前仓库的正式维护约定。后续涉及企业版 Git 组织、官方同步、换机、离线发布时，以本文件为准。

摘要：

- 当前企业版基于官方 Dify 仓库长期维护
- 官方上游仓库：`https://github.com/langgenius/dify.git`
- 企业版 fork：`https://github.com/D-S-William-Guo/dify.git`
- `main` 是官方同步基线
- `enterprise/main` 是企业长期维护分支
- 企业功能、仓库规整、升级流程、离线发布规则都以本文档为准，不以内化记忆或聊天记录为准

## 当前企业定制概览

- 企业空间管理：已实现并纳入长期维护
- 平台管理员能力：已实现并纳入长期维护
- 智慧广场：已实现一期，支持提交、审核、展示和复制导入
- 离线打包：已收敛为 `smart / rebuild / reuse`
- 企业镜像命名：已统一为 `官方版本-enterprise`
- 重大改动、坑点与时间序列记录见：
  - [CHANGELOG.enterprise.md](/D:/CodexSpace/dify/CHANGELOG.enterprise.md)
- 路线二性能治理原则、已完成示范与后续开发检查单见：
  - [README.performance-route2.md](/D:/CodexSpace/dify/README.performance-route2.md)

最近一次重要规则收敛：

- 企业打包默认优先复用已验证的正式镜像
- 是否可复用不仅看 tag，还看镜像内部 `COMMIT_SHA`

## 当前仓库定位

- 官方上游仓库：`https://github.com/langgenius/dify.git`
- 企业版 fork：`https://github.com/D-S-William-Guo/dify.git`
- 官方同步基线分支：`main`
- 企业长期维护分支：`enterprise/main`
- 默认同步方式：`merge`

## 当前默认约定

- `origin` 指向企业版 fork
- `upstream` 指向官方仓库
- `main` 只作为官方同步基线使用
- `enterprise/main` 承载所有企业定制功能
- 不要在 `main` 上直接开发企业功能
- 不要把 `origin` 再改回官方仓库
- 企业管理功能在企业分支维护
- 离线部署使用 [docker/docker-compose.enterprise.yaml](/D:/CodexSpace/dify/docker/docker-compose.enterprise.yaml)
- 离线构建使用 [scripts/build-enterprise-offline.ps1](/D:/CodexSpace/dify/scripts/build-enterprise-offline.ps1)
- Docker 相关补充说明见 [docker/README.enterprise.md](/D:/CodexSpace/dify/docker/README.enterprise.md)

## 第一部分：首次规整当前仓库

### 第一次整理当前本地仓库

当前背景：

- 本地仓库最初是从官方 Dify 克隆而来
- 现在已经有企业版 fork：`https://github.com/D-S-William-Guo/dify.git`
- 当前企业改动应保留并落入企业长期分支

按以下顺序执行。

### 1. 把当前官方 `origin` 改名为 `upstream`

```powershell
git remote rename origin upstream
```

完成后应看到：官方仓库不再叫 `origin`。

### 2. 新增企业版 fork 为新的 `origin`

```powershell
git remote add origin https://github.com/D-S-William-Guo/dify.git
```

### 3. 检查远程配置

```powershell
git remote -v
```

完成后应看到：

- `origin` -> `https://github.com/D-S-William-Guo/dify.git`
- `upstream` -> `https://github.com/langgenius/dify.git`

### 4. 从当前状态切出企业长期分支

```powershell
git switch -c enterprise/main
```

### 5. 把当前企业改动提交为企业基线

```powershell
git add .
git commit -m "feat: add enterprise workspace management overlay"
```

完成后应看到：当前企业改动进入 Git 历史，而不是继续停留在未提交状态。

### 6. 推送 `enterprise/main` 到企业版 fork

```powershell
git push -u origin enterprise/main
```

完成后应看到：GitHub fork 上已经存在 `enterprise/main`。

### 7. 回到官方同步基线分支

```powershell
git switch main
```

### 8. 让 `main` 跟踪 `upstream/main`

```powershell
git fetch upstream
git branch --set-upstream-to=upstream/main main
```

### 9. 可选：把干净的 `main` 推到企业版 fork

```powershell
git push -u origin main
```

这个步骤是可选的，但建议保留，方便其他电脑直接从你的 fork 克隆后看到完整结构。

### 整理完成后的检查项

执行：

```powershell
git remote -v
git branch -vv
git status
```

完成后应满足：

- `origin` 是企业版 fork
- `upstream` 是官方仓库
- 本地存在 `main` 和 `enterprise/main`
- 企业改动已经进入 Git 提交
- GitHub fork 上可以看到 `enterprise/main`

## 第二部分：长期维护规则

这一部分是第一次整理完成后的长期稳定规则。以后日常开发、同步官方、换电脑、发布离线版本，都按这里执行。

### 整理完成后的仓库规则

- `main` 只负责跟踪官方 `upstream/main`
- `enterprise/main` 只负责企业版长期维护
- 任何企业功能开发都从 `enterprise/main` 切临时分支
- 功能开发完成后合回 `enterprise/main`
- 不在 `main` 上直接改企业代码
- 不把部署环境变量、离线发布脚本、企业功能规则只留在聊天记录里，统一以本文件和仓库文档为准

### 以后每次同步官方更新的固定流程

#### 1. 拉取官方最新代码

```powershell
git fetch upstream
```

#### 2. 更新本地 `main`

```powershell
git switch main
git merge upstream/main
```

完成后应看到：`main` 已经代表最新官方基线。

#### 3. 切回企业分支

```powershell
git switch enterprise/main
```

#### 4. 把官方更新合并到企业分支

```powershell
git merge main
```

#### 5. 如有冲突，解决后提交

```powershell
git add .
git commit
```

#### 6. 做最小回归验证

至少检查：

- 企业管理页面能打开
- 平台管理员身份识别正常
- 工作区创建、成员邀请、角色修改、成员删除正常
- [docker/docker-compose.enterprise.yaml](/D:/CodexSpace/dify/docker/docker-compose.enterprise.yaml) 仍然符合当前部署方式

#### 7. 推送企业分支

```powershell
git push origin enterprise/main
```

### 换另一台电脑时怎么做

不要再从官方仓库直接克隆。以后换电脑时，一律从企业版 fork 克隆。

#### 1. 克隆企业版 fork

```powershell
git clone https://github.com/D-S-William-Guo/dify.git
cd dify
```

#### 2. 补上官方远程

```powershell
git remote add upstream https://github.com/langgenius/dify.git
```

#### 3. 拉取企业长期分支

```powershell
git fetch origin
git switch -c enterprise/main --track origin/enterprise/main
```

如果本地已经有该分支：

```powershell
git switch enterprise/main
```

#### 4. 检查远程与分支

```powershell
git remote -v
git branch -vv
```

完成后应看到：

- `origin` 是企业版 fork
- `upstream` 是官方仓库
- 当前工作分支是 `enterprise/main`

### 发布和离线部署的固定原则

- 源码和镜像是两层东西：
  - Git 仓库存源码
  - Docker 镜像是发布产物
- 每次企业版发布都从 `enterprise/main` 构建
- 官方 `docker/docker-compose.yaml` 不直接魔改
- 企业版部署通过覆盖文件叠加：
  - 官方主文件：`docker/docker-compose.yaml`
  - 企业覆盖文件：`docker/docker-compose.enterprise.yaml`
- 离线发布前先同步 `.env` 变量：
  - `docker/dify-env-sync.py`
  - 或 `docker/dify-env-sync.sh`
- 离线镜像构建和导出使用：
  - `scripts/build-enterprise-offline.ps1`
  - `scripts/build-enterprise-offline.sh`
- Docker 部署层补充说明见：
  - [docker/README.enterprise.md](/D:/CodexSpace/dify/docker/README.enterprise.md)

### 企业镜像版本命名规则

- `docker/docker-compose.enterprise.yaml` 保持当前参数化结构，不需要每次同步官方后去改写具体版本号
- 企业镜像 tag 统一通过 `DIFY_ENTERPRISE_VERSION` 控制
- 长期维护时，正式对外识别的企业业务镜像名统一为：
  - `dify-api-enterprise:<官方版本-enterprise>`
  - `dify-web-enterprise:<官方版本-enterprise>`
- `worker` 与 `worker_beat` 运行时继续复用 `dify-api-enterprise:<官方版本-enterprise>`
- 如果某次本地排障时给 `worker` 或 `worker_beat` 单独补了 tag，可视为临时识别名，不作为正式交付命名规则
- 正式构建与交付时，企业镜像版本统一采用：
  - `官方版本-enterprise`
- 示例：
  - `1.13.3-enterprise`
  - `1.14.0-enterprise`
- `api`、`web`、`worker`、`worker_beat` 共用同一企业镜像版本
- 本地临时开发与验证可以继续使用：
  - `local`
  - `enterprise-local`

### 每次同步官方后如何确定企业镜像版本

每次同步官方最新代码并合并到 `enterprise/main` 后，按下面顺序处理版本：

1. 确认当前这次同步对应的官方 Dify 版本
2. 按 `官方版本-enterprise` 生成本次企业镜像 tag
3. 构建、导出、交付时统一使用这个版本字符串

示例：

- 如果当前同步到的官方版本是 `1.13.3`
- 那么本次企业镜像版本统一使用 `1.13.3-enterprise`

说明：

- 这里更新的是构建和发布时传入的版本字符串，不是去修改 `docker/docker-compose.enterprise.yaml` 里的固定文本
- compose 文件继续保持参数化写法即可
- 如果只是本地调试，不做正式交付，可以继续使用 `local` 或 `enterprise-local`

典型发布流程：

1. 同步官方更新到 `enterprise/main`
2. 更新 `docker/.env`
3. 确认本次企业镜像版本，例如 `1.13.3-enterprise`
4. 本地构建企业镜像
5. 导出离线镜像包
6. 传到生产机
7. `docker load`
8. 用双 compose 文件启动

如果需要显式指定版本，可在启动或构建前设置：

```powershell
$env:DIFY_ENTERPRISE_VERSION="1.13.3-enterprise"
```

或在离线打包时直接传入：

```powershell
.\scripts\build-enterprise-offline.ps1 -Version 1.13.3-enterprise
```

### 最终打包命令参考

#### Windows 11 + Docker Desktop

```powershell
cd D:\CodexSpace\dify
python docker/dify-env-sync.py --dir docker --no-backup
$env:DIFY_ENTERPRISE_VERSION="1.13.3-enterprise"
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
.\scripts\build-enterprise-offline.ps1 -Version $env:DIFY_ENTERPRISE_VERSION -Mode smart
```

#### GUI Ubuntu 云电脑

```bash
cd ~/dify
python3 docker/dify-env-sync.py --dir docker --no-backup
export DIFY_ENTERPRISE_VERSION=1.13.3-enterprise
docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml config -q
./scripts/build-enterprise-offline.sh -Version $DIFY_ENTERPRISE_VERSION -Mode smart
```

说明：

- 默认推荐 `-Mode smart`：
  - 若正式 tag 已存在，且镜像内部 `COMMIT_SHA` 与版本一致，则直接复用
  - 若镜像缺失，或 `COMMIT_SHA` 不匹配，则自动重建
- 如需无条件重建，可使用 `-Mode rebuild`
- 如需严格只复用不重建，可使用 `-Mode reuse`
- 如果只是本地联调，不导出离线包，可以在 `docker/` 目录直接执行双 compose 启动
- 正式交付时，把上面示例里的 `1.13.3-enterprise` 替换为当次同步对应的真实版本

### 目标机首次部署命令参考

如果目标机是全新环境，拿到 `docker/` 目录、`.env` 和离线包后，可以按下面方式启动：

```bash
cd ~/dify/docker
cp .env.example .env
# 按实际部署环境补齐 .env
docker load -i ../dist/offline/dify-enterprise-offline-1.13.3-enterprise.tar
docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml up -d
```

说明：

- 如果你已经准备好了自己的 `.env`，就不需要再执行 `cp .env.example .env`
- 首次部署前默认不需要手工创建 `volumes/**` 数据目录
- 只要 `docker/` 目录结构完整，Docker Compose 会自动创建需要的空目录与卷

### 新环境重新初始化的部署原则

如果目标机器是全新环境，部署时按“代码目录 + 配置文件 + 离线镜像包”处理，不要把本地运行后的数据状态一起复制过去。

应该带过去的内容：

- `docker/` 目录中的配置、模板、启动脚本
- 已确认好的 `docker/.env`
- 离线镜像包和镜像清单
- 如需 HTTPS，再带证书文件

不要直接复用的内容：

- `docker/volumes/app/storage`
- `docker/volumes/db/data`
- `docker/volumes/redis/data`
- `docker/volumes/plugin_daemon`
- `docker/volumes/weaviate`
- 以及其他 `docker/volumes/**` 下已运行产生的数据目录

说明：

- 配置类挂载跟着仓库目录一起带过去即可
- 数据类挂载在目标机首次 `docker compose up -d` 时自动创建为空目录
- 如果你的目标是“新环境初始化”而不是“旧环境迁移”，就不要复制本机旧数据目录

启动方式示例：

```bash
cd docker
docker compose -f docker-compose.yaml -f docker-compose.enterprise.yaml up -d
```

### 建议的版本管理方式

- 每个可发布版本都打 tag
- 推荐 tag 规范：
  - `enterprise-v1.0.0`
  - `enterprise-v1.0.1`
  - `enterprise-v1.1.0`
- 代码 tag、离线镜像包版本、交付记录尽量保持一致
- 代码版本 tag 与 Docker 镜像 tag 可以并行存在：
  - Git tag 可以继续使用 `enterprise-v1.0.0`
  - Docker 镜像 tag 统一使用 `官方版本-enterprise`

示例：

```powershell
git switch enterprise/main
git tag enterprise-v1.0.0
git push origin enterprise/main
git push origin enterprise-v1.0.0
```

完成后应看到：

- GitHub fork 上存在对应 tag
- 离线交付包版本能和代码版本对得上

## 最后提醒

- 这份文档的目标是“把规则外化出来”
- 如果后续仓库结构、分支策略、发布脚本发生变化，优先更新本文件
- 不要让真实维护方式只存在于聊天记录、个人记忆或某一台电脑里
