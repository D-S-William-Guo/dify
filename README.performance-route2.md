# Dify 路线二性能治理历史参考

本文档保留旧 `enterprise/main` 中路线二性能治理的有效经验，但它不是当前企业候选分支的最高优先级规则。

## 当前状态

- 当前企业发布候选是 `codex/enterprise-candidate-20260424`。
- 旧 `enterprise/main` 中的路线二性能治理属于历史参考，不得直接整批重放。
- 如果路线二改动与 `upstream/main` 当前实现、企业空间、平台管理员、智慧广场或 Docker 发布链路冲突，以当前干净候选分支和官方主线为准。

## 可保留的原则

- 高频查询要有明确缓存层级，不要默认零缓存。
- 隐藏 tab、modal、secondary panel 默认不要预拉重数据。
- mutation 后优先精准 invalidation，避免整组 namespace 抖动。
- 后端列表接口避免隐式 N+1，优先显式批量查询。
- 常驻 header、context、导航不要拉取次级页面重列表。

## 使用边界

- 这些原则只能作为新开发和回归排查时的设计参考。
- 不允许为了恢复旧路线二补丁而偏离当前 `upstream/main` 的构建方式。
- 不允许从旧脏分支整批复制 UI 迁移、测试漂移或本地环境特化改动。
- 只有当某个性能补丁在当前候选分支中重新通过源码检查、测试、镜像构建、浏览器点击和日志验证后，才可以成为当前企业资产。

## Agent 提醒

Codex、Claude Code 或其他 agent 进入仓库后，先读：

- `AGENTS.md`
- `README.enterprise-maintenance.md`
- `ENTERPRISE_REPLAY_PLAN.md`
- `docker/README.enterprise.md`

不要把本文档当作覆盖这些文件的规则源。本文档只说明历史性能治理经验如何被谨慎复用。
