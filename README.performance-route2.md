# Dify 路线二性能治理说明

这份文档用于说明当前仓库采用的性能治理策略，以及后续开发如何沿用。

用途：

- 让新的 Codex 线程、AI IDE 或接手工程师快速理解这轮性能优化不是零散 patch，而是有取舍的工程路线
- 记录已经验证有效的前端 / 后端性能规则
- 帮助以后同步官方代码时快速判断哪些改动值得保留、哪些文件需要重点复查

相关文档：

- 企业维护规则见 [README.enterprise-maintenance.md](/D:/CodexSpace/dify/README.enterprise-maintenance.md)
- 企业重大改动与时间序列记录见 [CHANGELOG.enterprise.md](/D:/CodexSpace/dify/CHANGELOG.enterprise.md)
- Docker 企业 overlay 见 [docker/README.enterprise.md](/D:/CodexSpace/dify/docker/README.enterprise.md)

---

## 为什么选择路线二

性能分析阶段曾考虑三条路线：

- 路线一：热点驱动，哪里慢就修哪里
- 路线二：建立统一性能规范，中等投入，逐步治理
- 路线三：结构性重构，显式查询层与序列化层全面重做

最终选择路线二，原因是：

- 路线一见效快，但容易反复踩同类坑，长期维护成本高
- 路线三最彻底，但改动面太大，短期内会显著增加与官方上游合并的成本
- 路线二可以保留现有架构和开发效率，只给高频路径加边界与规则，收益稳定、风险可控，更适合企业长期分支

一句话概括：

- 不推翻现有架构
- 不继续默认放任隐式性能债增长
- 用规则、示范改造和小步验证持续把高频路径收紧

---

## 这轮治理解决了什么

前端和后端都存在一些“对快速迭代友好、但规模上来后容易放大”的模式。

好的部分：

- 现有写法业务表达自然，开发效率高，功能迭代速度快
- 默认宽刷新和零缓存偏保守，早期更容易保证正确性
- 很多问题在小规模数据下并不明显

要约束的部分：

- 后端模型属性里隐式查库，容易形成列表接口 N+1
- 前端高频 query 默认零缓存，容易在切页、切 tab、开弹窗时反复补请求
- mutation 宽失效会把不相关的数据也一起抖起来
- 常驻 header、context、导航、弹层容易把次级页面的重查询提前带出来

本轮治理的目标不是“让所有请求都消失”，而是：

- 让请求只在真正需要时发生
- 让缓存有层级
- 让列表接口尽量显式批量取数
- 让失效范围与用户动作匹配

---

## 已完成的示范改造

后端示范：

- `Platform Admin` 工作区列表去掉 `2N+1`
- `Enterprise Marketplace` 列表去掉多重 `N+1`
- `apps list` 与 `installed-apps` 走批量预取
- `datasets` 列表链路走批量预取与属性兜底

前端示范：

- 企业空间管理和智慧广场把 query 失效改为精准范围
- 智慧广场与平台管理员页按 section / tab 挂载
- 模型供应商、插件状态、知识库相关高频 query 做缓存分层
- 插件任务轮询只在 `/plugins` 页面活跃
- 主导航中的重页面默认关闭 Next 路由预取
- 顶部知识库导航只在知识库路由激活时拉知识库列表
- “只为了拿 refetch/mutate 就先挂 query” 这种模式已被替换为直接 invalidation

这些改造都经过了 Windows 11 + Docker Desktop + 浏览器点击 + 容器日志的本地联调验证。

---

## 前端规则

### 查询规则

- 高稳定配置数据必须分层缓存，不再默认 `staleTime: 0`
- 隐藏 `tab`、`modal`、secondary panel 默认 `enabled: false`
- 常驻导航、header、context 不得默认拉次级页面的重列表
- 不要为了拿 `mutate` 或 `refetch` 去订阅 query
- 非实时数据默认关闭 `refetchOnWindowFocus` 和 `refetchOnReconnect`

### 失效规则

- mutation 后优先做精准 invalidation，不要整组 namespace 一起刷新
- 只失效当前动作真实影响的数据
- 优先 invalidation，少做主动 refetch

### 组件规则

- 常驻组件不能隐式绑定重查询
- 主导航中的重页面链接默认 `prefetch={false}`
- query 的启用条件要尽量贴近调用处，便于后续排查

### hook 规则

- 高复用 query hook 应支持 `enabled`
- 公共 context 只放真正全局需要的数据
- 如果 hook 的唯一目的只是刷新缓存，优先直接依赖 `queryClient.invalidateQueries`

---

## 后端规则

- 列表接口不要依赖会隐式查库的模型属性
- 列表接口需要的关联数据，统一在 service 层批量预取或聚合
- serializer 优先消费显式预取结果，而不是逐条查库
- 新增列表接口时，默认先检查是否存在 N+1 风险

---

## 踩坑与经验

- 只看“页面上显示了什么”不够，要同时看网关日志，很多重请求来自常驻组件而不是当前页面主体
- 很多问题不是单个页面写坏了，而是公共 hook、公共 context 或导航默认行为叠加出来的
- 有些“看起来只是想拿刷新函数”的 hook，实际上会把整组 query 提前挂活
- 这类治理非常适合“小步改动 + Docker 本地验证 + 日志比对”，不适合一次性大重构

---

## 合并官方代码时怎么判断影响

路线二相对大重构更容易和上游合并，但仍有一些高频冲突区需要重点复查：

- [web/service/use-common.ts](/D:/CodexSpace/dify/web/service/use-common.ts)
- [web/service/use-plugins.ts](/D:/CodexSpace/dify/web/service/use-plugins.ts)
- [web/service/knowledge/use-dataset.ts](/D:/CodexSpace/dify/web/service/knowledge/use-dataset.ts)
- [web/context/provider-context-provider.tsx](/D:/CodexSpace/dify/web/context/provider-context-provider.tsx)
- [web/context/modal-context-provider.tsx](/D:/CodexSpace/dify/web/context/modal-context-provider.tsx)
- [web/app/components/header/](/D:/CodexSpace/dify/web/app/components/header)
- 企业版相关 service 与页面

判断原则：

- 如果上游只是改了 UI 或字段，优先保留这轮“按需启用、精准失效、缓存分层”的策略
- 如果上游重写了 hook 或组件结构，就把规则重新套进去，而不是机械保留旧 patch

---

## 后续开发检查单

新增或修改页面前，至少检查：

1. 这个 query 会不会在隐藏状态触发
2. 这个列表会不会在循环里放大请求
3. 这个 mutation 会不会失效过宽
4. 这个常驻组件会不会把次级页面的查询带出来
5. 这个导航链接是否真的值得预取

如果这五个问题都能回答清楚，后续大部分性能回归都能提前避免。
