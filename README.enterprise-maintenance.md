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
- `codex/enterprise-candidate-20260424` 是当前从干净 `upstream/main` 重放企业补丁得到的候选分支
- `enterprise/main` 未来应由验证通过的干净候选分支晋升而来；旧 `enterprise/main` 只作为历史参考
- 企业功能、仓库规整、升级流程、离线发布规则都以本文档为准，不以内化记忆或聊天记录为准

## 当前正确工作模式

本轮维护已经从“在旧 `enterprise/main` 上长周期合并官方 main”切换为“以官方最新源码为底座，重放必要企业能力”。

当前分支定位：

- `main`：官方同步基线，跟踪 `upstream/main`，禁止直接开发企业能力。
- `codex/enterprise-candidate-20260424`：当前最佳企业候选分支，基于 `upstream/main` `da00de668886`，已重放企业空间、平台管理员、智慧广场和企业 Docker/离线部署能力。
- `enterprise/main`：旧企业长期分支曾承载大量历史改动，但当前状态包含长周期同步残留、旧测试漂移、运行态脏数据和未验证调优，不能再直接作为发布源。
- `codex/protect-enterprise-main-20260424-103050`：旧 `enterprise/main` 的保护快照，只用于回溯和挑选必要补丁。

后续开发默认从当前干净候选分支继续。候选分支验证稳定后，再把它晋升为新的 `enterprise/main`。

对 AI IDE / agent 的硬规则：

- 先读 `AGENTS.md`，再读本文档、`ENTERPRISE_REPLAY_PLAN.md` 和 `docker/README.enterprise.md`。
- 不要把旧 `enterprise/main` 的大面积改动视为“应该全部保留”的企业资产。
- 旧分支中的 Markdown、脚本或补丁只有在当前文档收录、补丁清单要求，或重新通过当前源码验证后，才允许带入新候选。
- 旧路线二性能治理和历史 Docker 排障经验属于参考材料，不能压过当前干净候选分支和官方主线基线。

## 当前维护优先级

以后处理企业版仓库时，默认按下面的优先级决策，不要倒置顺序：

1. 先同步官方 Dify 最新代码，保证 `main` 跟上 `upstream/main`，再从官方基线创建干净企业候选分支
2. 再保住并继续维护企业级定制能力，当前核心是企业多空间、平台管理员和智慧广场
3. 最后才处理阶段性的性能治理、局部重构或其他非主线优化

这条顺序的含义是：

- 官方同步永远是第一优先级，因为企业版长期维护必须建立在最新官方基线上
- 企业功能是第二优先级，因为它们构成企业分支存在的核心价值
- 路线二性能治理是第三优先级，它很重要，但本质上属于阶段性治理成果；以后如果进入归档状态，也不能反过来压过官方同步和企业功能维护

如果三者发生冲突，先保官方同步路径，再保企业功能可用，最后再决定哪些性能治理规则继续保留、哪些进入历史记录。

## 当前前端构建基线规则

前端构建相关问题，默认按下面的长期规则处理：

- 前端构建基线始终以 `upstream/main` 当前状态为准
- 同步官方后，如果 `web` 无法构建，先分析企业分支是否偏离了 `upstream/main` 当前的构建方向
- 这里说的“构建方向”不只是一两个依赖名，还包括当前主线使用的 workspace 结构、构建输入、Docker build 输入、样式入口和构建配置
- 处理顺序是：先恢复到与 `upstream/main` 当前主线一致且可构建的状态，再把企业功能差异和阶段性优化重新叠上去
- 不要把某一代具体前端技术方案永久写死在企业文档里；以后官方主线再变化时，仍然按“先分析当前 `upstream/main`，再回到同一大方向”执行

同时要把两个问题分开判断：

- `docker/volumes/**`、`.venv/**`、`node_modules/**`、`.codex/**` 这类内容属于运行时或本机产物，只影响构建上下文清洁度
- 与 `upstream/main` 当前主线保持一致，才属于前端构建基线本身

也就是说，构建上下文治理是环境卫生，前端主线对齐是源码与构建基线；不要把两者混成一个问题。

Windows + Docker Desktop 下还有一条执行规则：

- `web` 的企业镜像重建，如果仓库根或 `web/` 下保留本地 `node_modules`，不要再依赖人工挪目录的临时做法
- 默认通过 [`build-enterprise-web.ps1`](D:\CodexSpace\dify\docker\scripts\build-enterprise-web.ps1) 先准备精简 build context，再调用 compose build
- 这样处理的是 Windows sender 对本地依赖 reparse point 的上下文读取问题，属于“构建上下文治理”，不是前端源码基线本身

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
- 开发点击验证、容器日志验证和离线打包必须基于同一批最新重建并已验证的 enterprise 镜像，不能用旧容器做验证、再用新镜像去上线

## 当前仓库定位

- 官方上游仓库：`https://github.com/langgenius/dify.git`
- 企业版 fork：`https://github.com/D-S-William-Guo/dify.git`
- 官方同步基线分支：`main`
- 当前企业候选分支：`codex/enterprise-candidate-20260424`
- 旧企业分支：`enterprise/main`，当前仅作为历史参考，待候选分支晋升后再重新成为干净长期维护分支
- 旧保护快照：`codex/protect-enterprise-main-20260424-103050`
- 默认同步方式：官方基线重放企业补丁，不再默认使用旧脏树 merge

## 当前默认约定

- `origin` 指向企业版 fork
- `upstream` 指向官方仓库
- `main` 只作为官方同步基线使用
- 当前企业开发和验证以 `codex/enterprise-candidate-20260424` 为准
- `enterprise/main` 在候选分支正式晋升前只用于历史对照
- 不要在 `main` 上直接开发企业功能
- 不要把 `origin` 再改回官方仓库
- 企业管理功能在企业分支维护
- 离线部署使用 [docker/docker-compose.enterprise.yaml](/D:/CodexSpace/dify/docker/docker-compose.enterprise.yaml)
- 离线构建使用 [scripts/build-enterprise-offline.ps1](/D:/CodexSpace/dify/scripts/build-enterprise-offline.ps1)
- Docker 相关补充说明见 [docker/README.enterprise.md](/D:/CodexSpace/dify/docker/README.enterprise.md)

## 第一部分：首次规整当前仓库

本部分是早期建仓历史流程，保留用于理解远程命名和分支来源。当前日常同步和发布不再按本部分重新操作，后续以“第二部分：长期维护规则”的干净候选分支流程为准。

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
- `codex/enterprise-candidate-20260424` 是当前企业功能开发和验证基线
- `enterprise/main` 在候选分支晋升前只作为历史对照；晋升后才重新成为干净企业长期分支
- 任何企业功能开发都从当前干净企业候选或晋升后的干净 `enterprise/main` 切临时分支
- 功能开发完成后合回当前干净企业候选或晋升后的干净 `enterprise/main`
- 不在 `main` 上直接改企业代码
- 不把部署环境变量、离线发布脚本、企业功能规则只留在聊天记录里，统一以本文件和仓库文档为准

### 以后每次同步官方更新的固定流程

执行同步、冲突处理和后续开发时，始终套用上面的维护优先级，不要把阶段性性能 patch 放到官方同步和企业功能之前。

默认采用“官方基线 + 企业补丁重放”模式。只有在小版本更新、差异极小、候选分支已经很干净并且补丁组没有冲突时，才可以考虑直接 merge。

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

#### 3. 从官方基线创建新的企业候选分支

```powershell
git switch -c codex/enterprise-candidate-YYYYMMDD main
```

分支名可以按日期调整，例如 `codex/enterprise-candidate-20260426`。

#### 4. 按补丁清单重放企业能力

按 `ENTERPRISE_REPLAY_PLAN.md` 的顺序重放，不要从旧分支整树复制：

1. 企业多空间与平台管理员
2. 智慧广场提交、审核、展示、复制
3. Docker enterprise overlay 与离线打包
4. 已经被真实运行验证过的安装、登录、公共路由修复
5. DSL 导入和配置 hook 回归保护
6. workflow、plugin、dataset、tool 等广覆盖兼容补丁

#### 5. 每组补丁验证后提交

```powershell
git add .
git commit -m "feat: replay enterprise workspace and marketplace patches"
```

提交信息按实际补丁组调整。不要把运行数据、缓存、`node_modules`、`docker/volumes/**` 或旧测试漂移提交进来。

#### 6. 做候选分支回归验证

至少检查：

- 企业管理页面能打开
- 平台管理员身份识别正常
- 工作区创建、重名保护、成员邀请、角色修改、成员删除、非当前工作区删除正常
- 智慧广场提交、审核、展示、复制到另一个空间正常
- 插件安装、知识库、应用创建、DSL 导入的代表路径正常
- [docker/docker-compose.enterprise.yaml](/D:/CodexSpace/dify/docker/docker-compose.enterprise.yaml) 仍然符合当前部署方式

补充硬规则：

- 本地 `pytest`、`pnpm type-check`、定向前端测试只算第一道门，不算最终运行态验证
- 只要本轮改动涉及运行时代码，必须先重建对应 enterprise 镜像，再用这批新镜像重建 compose 服务后做点击验证
- 点击验证、日志排查、最小联调如果不是基于本轮刚重建出来的容器，默认视为验证无效
- 最终离线打包必须导出这批已经验证通过的同一批镜像，不能用旧容器做验证、再换成另一批镜像上线

#### 7. 晋升新的长期企业分支

候选分支通过后，先保护旧 `enterprise/main`，再晋升新候选。下面的 `reset --hard` 只允许在明确确认“用候选分支替换旧企业分支”时使用：

```powershell
git branch codex/protect-enterprise-main-YYYYMMDD enterprise/main
git switch enterprise/main
git reset --hard codex/enterprise-candidate-YYYYMMDD
git push --force-with-lease origin enterprise/main
```

如果不想改写远端历史，则改用 PR 或 merge commit 合入；但无论哪种方式，发布源必须是验证通过的干净候选内容，而不是旧脏树。

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

#### 3. 拉取企业分支

```powershell
git fetch origin
git switch -c codex/enterprise-candidate-20260424 --track origin/codex/enterprise-candidate-20260424
```

如果当前候选已经晋升为新的 `enterprise/main`，则使用：

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
- 当前工作分支是当前干净企业候选，或已经晋升后的干净 `enterprise/main`

### 发布和离线部署的固定原则

- 源码和镜像是两层东西：
  - Git 仓库存源码
  - Docker 镜像是发布产物
- 每次企业版发布都从当前验证通过的干净企业候选构建；候选晋升后再从新的干净 `enterprise/main` 构建
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

镜像一致性补充规则：

- `worker` 与 `worker_beat` 不只是“逻辑上复用” `dify-api-enterprise:<官方版本-enterprise>`，运行中的容器也必须实际切到当前 tag 对应的同一镜像 ID
- 如果重新 build 了 `dify-api-enterprise:<官方版本-enterprise>`，必须再执行一次双 compose 的服务重建，让 `api`、`worker`、`worker_beat` 一起切到新的镜像
- 否则旧容器会继续引用旧镜像 ID，旧镜像失去 tag 后会变成 dangling `<none>`，造成“tag 是新的、运行还是旧的”这种假对齐状态
- 最低验收动作：
  - `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml up -d --force-recreate api worker worker_beat`
  - 然后检查 `docker compose ... ps`
  - 必要时再用 `docker inspect` 确认三者的 `Config.Image` 与实际 `Image` 已经对齐到当前企业镜像

联动重建补充规则：

- 不把“整套 compose 全量重启”作为默认动作
- 默认按受影响服务做最小联动重建，避免把无关服务和数据面一起扰动
- 如果重建了 `web` 运行镜像，默认同时重建 `nginx`：
  - `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml up -d --force-recreate web nginx`
- 如果重建了 `api` 运行镜像，默认同时重建 `api`、`worker`、`worker_beat`、`nginx`：
  - `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml up -d --force-recreate api worker worker_beat nginx`
- 如果只修改了 Nginx 配置、模板或 HTTPS 相关挂载，单独重建 `nginx`：
  - `docker compose -f docker/docker-compose.yaml -f docker/docker-compose.enterprise.yaml up -d --force-recreate nginx`
- 只有在服务范围不清、依赖状态混乱、网络状态异常，或者需要做一轮完整环境回收时，才考虑更大范围的 compose 重启
- 每次联动重建后，至少检查：
  - `docker compose ... ps`
  - `docker compose ... logs --tail=... nginx web api`
  - 浏览器入口是否已经落到新容器

### 每次同步官方后如何确定企业镜像版本

每次同步官方最新代码并创建干净企业候选后，按下面顺序处理版本：

1. 从同步后的 [api/pyproject.toml](/D:/CodexSpace/dify/api/pyproject.toml) 读取官方后端版本
2. 从同步后的 [web/package.json](/D:/CodexSpace/dify/web/package.json) 读取官方前端版本
3. 确认两者版本完全一致
4. 按 `官方版本-enterprise` 生成本次企业镜像 tag
5. 构建、导出、交付时统一使用这个版本字符串

示例：

- 如果当前同步到的官方版本是 `1.13.3`
- 那么本次企业镜像版本统一使用 `1.13.3-enterprise`

说明：

- 这两处源码文件是当前仓库的官方版本来源，属于企业镜像版本判定的黄金标准，不再依赖人工记忆、聊天记录或手工猜测
- 只有在 [api/pyproject.toml](/D:/CodexSpace/dify/api/pyproject.toml) 与 [web/package.json](/D:/CodexSpace/dify/web/package.json) 的版本一致时，才允许继续生成 `官方版本-enterprise`
- 如果两者版本不一致，视为同步未完成、本地状态漂移或合并后仍有异常；此时必须先解决版本不一致问题，禁止继续本地验证、镜像重建、离线打包和生产交付
- 这里更新的是构建和发布时传入的版本字符串，不是去修改 `docker/docker-compose.enterprise.yaml` 里的固定文本
- compose 文件继续保持参数化写法即可
- 一旦确定了本轮 `官方版本-enterprise`，本地回归验证、compose 重建、浏览器点击验证、离线打包和生产部署都必须沿用同一个 `DIFY_ENTERPRISE_VERSION`
- 不允许在本地验证时使用一个版本值、打包时换成另一个版本值，或让运行中的 compose 容器继续停留在旧 tag
- 如果只是本地调试，不做正式交付，可以继续使用 `local` 或 `enterprise-local`；但这条路径不属于正式验证、离线打包或生产交付的黄金标准流程

典型发布流程：

1. 同步官方更新到 `main`
2. 从 `main` 创建新的干净企业候选并重放企业补丁
3. 更新 `docker/.env`
4. 读取 [api/pyproject.toml](/D:/CodexSpace/dify/api/pyproject.toml) 与 [web/package.json](/D:/CodexSpace/dify/web/package.json) 的版本并确认一致
5. 生成本次企业镜像版本，例如 `1.13.3-enterprise`
6. 将该值设为本轮唯一的 `DIFY_ENTERPRISE_VERSION`
7. 用该值完成本地构建与 compose 验证
8. 导出离线镜像包
9. 传到生产机
10. `docker load`
11. 继续使用同一个版本值通过双 compose 文件启动

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

开发态数据目录保护规则：

- `docker/volumes/**` 里的数据库、存储、Redis、插件、向量库等运行数据目录，不得在日常开发、路线二治理、镜像重建、容器联动重建时擅自删除
- 这些目录一旦被清空，本机环境就可能表现成“全新初始化”，已有用户、应用、提交记录和运行状态都会丢失
- 只有两种情况允许删除：
  - 你明确要求重置环境或删除这些数据目录
  - 我先提出删除建议，并明确说明影响范围，得到你的同意后再执行
- 没有得到你的明确许可时，`docker/volumes/db/data`、`docker/volumes/app/storage`、`docker/volumes/redis/data`、`docker/volumes/plugin_daemon`、`docker/volumes/weaviate` 等目录一律视为需要保留
- “清理工作区残留”默认不包含这些正在使用的运行数据目录

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
