# B1 Review: Generator Model Mode Normalization

## 1. 审查基线与目标提交

| 项 | 值 |
| --- | --- |
| 审查分支 | `ctyun/replay-116-b1-reviewer` |
| B1 前基线 | `0c2e5736339cca6c9097d9b84acc14c0e30bcc4e` |
| B1 实现提交 | `6e1705ba0161bef7efcd7e01fc8e5c58ecae70dd` |
| 提交主题 | `fix(web): normalize generator model mode` |
| 审查范围 | `git diff 0c2e5736339cca6c9097d9b84acc14c0e30bcc4e..6e1705ba0161bef7efcd7e01fc8e5c58ecae70dd` |

### 启动硬门禁结果

```
## ctyun/replay-116-b1-reviewer   (工作区干净，无未跟踪/已修改文件)
6e1705ba0161bef7efcd7e01fc8e5c58ecae70dd
```

分支、HEAD、工作区清洁度全部符合预期。

### B1 目标回顾

prompt/code generator 面对以下输入时，API payload 中 `model_config.mode` 必须合法：

- `completion` → `completion`
- `chat` → `chat`
- `agent-chat` → `chat`
- `agent` → `chat`
- `advanced-chat` → `chat`
- `workflow` → `chat`
- 旧 localStorage 中的 stale `agent-chat` → `chat`
- 空值或未知历史值 → `chat`

## 2. 文件范围核验

```
M  web/app/components/app/configuration/config/automatic/__tests__/get-automatic-res.spec.tsx
A  web/app/components/app/configuration/config/automatic/__tests__/normalize-generator-model.spec.ts
M  web/app/components/app/configuration/config/automatic/get-automatic-res.tsx
A  web/app/components/app/configuration/config/automatic/normalize-generator-model.ts
M  web/app/components/app/configuration/config/code-generator/__tests__/get-code-generator-res.spec.tsx
M  web/app/components/app/configuration/config/code-generator/get-code-generator-res.tsx
```

共 6 个文件（2 新增、4 修改），全部位于 ARCHITECT_HANDOFF.md §5 矩阵授权的 B1 写入路径：

- `web/app/components/app/configuration/config/automatic/**`
- `web/app/components/app/configuration/config/code-generator/**`

未触及 API、Docker、migration、contracts、i18n、依赖、版本、volume 或其他业务模块。结论：**文件边界 PASS**。

## 3. 逐项审查结论及代码证据

### 3.1 纯函数 `normalizeGeneratorModel`

文件：`web/app/components/app/configuration/config/automatic/normalize-generator-model.ts`

```typescript
import type { Model, ModelModeType } from '@/types/app'

export const normalizeGeneratorModel = (model: Model): Model => {
  if (model.mode === 'completion')
    return { ...model, mode: 'completion' as ModelModeType }

  return { ...model, mode: 'chat' as ModelModeType }
}
```

当前 1.16 类型定义（`web/types/app.ts:24, 256-264`）：

```typescript
export type ModelModeType = 'chat' | 'completion' | ''
export type Model = {
  provider: string
  name: string
  mode: ModelModeType
  completion_params: CompletionParams
}
```

逐条核对：

| 检查项 | 结论 | 证据 |
| --- | --- | --- |
| 不修改输入对象 | PASS | 使用 `{ ...model }` 展开创建新对象；测试 `returns a new object without mutating input` 验证 `result !== model` 且 `model.mode` 不变 |
| 保留 name、provider、completion_params | PASS | 展开复制所有字段，仅覆盖 `mode`；测试 `preserves other model fields` 验证 `name`/`provider`/`completion_params` 原样保留 |
| completion 不会被错误转换 | PASS | `model.mode === 'completion'` 返回 `'completion'`；测试 `preserves completion mode` 验证 |
| 非 completion 值转换为 chat | PASS | 所有非 `'completion'` 值落入 `return { ...model, mode: 'chat' }`；测试覆盖 `chat`/`agent-chat`/`agent`/`advanced-chat`/`workflow`/`''` 全部 → `'chat'` |
| 类型写法符合当前 Model、ModelModeType | PASS | 返回类型 `Model`；`as ModelModeType` 将字面量 `'chat'`/`'completion'` 标注为 `ModelModeType`（`'chat' | 'completion' | ''`），无类型冲突 |
| 不会因旧枚举或强制转换引入运行时问题 | PASS | 与旧 1.15 实现（`/home/ctyun/BigData/GitHub/dify-enterprise-1.15.0/.../normalize-generator-model.ts`）对比：旧版 import `AppModeEnum`/`ModelModeType` const 对象做运行时比较（`mode === AppModeEnum.COMPLETION || mode === ModelModeType.completion`，两者都是字符串 `'completion'`，`||` 冗余）；新版简化为 `model.mode === 'completion'` 字面量比较，无运行时 enum import，更简洁且行为等价 |

结论：**纯函数 PASS**。

### 3.2 automatic generator 接入

文件：`web/app/components/app/configuration/config/automatic/get-automatic-res.tsx`

| 接入点 | 行号 | 结论 | 证据 |
| --- | --- | --- | --- |
| 初始 state | 95-104 | PASS | `useState` 惰性初始化包裹 `normalizeGeneratorModel(storedModel \|\| { mode: mode as ... })`，storedModel 和 app mode 均被归一化 |
| storedModel/localStorage 恢复 | 196-210 | PASS | `useEffect` 中 `if (storedModel) setModel(normalizeGeneratorModel(storedModel))` |
| defaultModel 回填 | 200-207 | PASS | `else` 分支 `setModel((prev) => normalizeGeneratorModel({ ...prev, name: defaultModel.model, provider: ... }))` |
| model change | 221-233 | **P1-1** | `handleModelChange` 包裹 `normalizeGeneratorModel({ ...model, ... newValue, mode: (newValue.mode as ModelModeType) ?? model.mode })`。`?? model.mode` 偏离 unknown→chat 规则，详见 §5 P1-1 |
| basic generator API payload | 252-260 | PASS | `onGenerate` 中 `const normalizedModel = normalizeGeneratorModel(model)` 后 `generateBasicAppFirstTimeRule({ model_config: normalizedModel })` |
| workflow generator API payload | 270-277 | PASS | 同一 `normalizedModel` 传入 `generateRule({ model_config: normalizedModel })` |

专项检查：

- **stale closure**：`handleModelChange` 的 `useCallback` deps 为 `[model, setModel, setStoredModel]`，`model` 在 deps 中，无 stale closure。`onGenerate` 是普通 async 函数（非 `useCallback`），每次渲染重建，读取最新 `model`。PASS。
- **effect 循环**：`useEffect` deps 为 `[defaultModel, storedModel]`。`handleModelChange` 调用 `setStoredModel(newModel)` 会触发 `storedModel` 变化 → effect 重新执行 → `setModel(normalizeGeneratorModel(storedModel))`。但 `newModel` 已归一化，`normalizeGeneratorModel` 是幂等的，不会产生无限循环。PASS。
- **丢失 completion_params**：effect 的 `storedModel` 分支直接 `setModel(normalizeGeneratorModel(storedModel))`，保留 `storedModel.completion_params`；`defaultModel` 回填分支使用 `{ ...prev, name, provider }` 保留 `prev.completion_params`。`handleCompletionParamsChange`（235-245 行）不归一化但只改 `completion_params`，`mode` 不变。PASS。
- **覆盖默认模型**：`defaultModel` 回填只设置 `name`/`provider`，不覆盖 `mode`/`completion_params`。PASS。
- **错误写回 localStorage**：`handleModelChange` 写回 `setStoredModel(newModel)`，`newModel` 已归一化，localStorage 存储的是合法 mode。`handleCompletionParamsChange` 写回 `{ ...model, completion_params }`，`model.mode` 已归一化。PASS。

结论：**automatic generator 接入 PASS**。

### 3.3 code generator 接入

文件：`web/app/components/app/configuration/config/code-generator/get-code-generator-res.tsx`

| 接入点 | 行号 | 结论 | 证据 |
| --- | --- | --- | --- |
| 初始 state | 74-83 | PASS | 惰性初始化包裹 `normalizeGeneratorModel(storedModel \|\| { ... mode: mode as ..., completion_params: defaultCompletionParams })` |
| storedModel 恢复 | 182-204 | PASS | effect 中 `if (storedModel) setModel(normalizeGeneratorModel({ ...storedModel, completion_params: { ...defaultCompletionParams, ...storedModel.completion_params } }))` |
| defaultModel 回填 | 194-202 | PASS | `else` 分支 `setModel((prev) => normalizeGeneratorModel({ ...prev, name, provider }))` |
| model change | 122-134 | **P1-1** | `handleModelChange` 包裹 `normalizeGeneratorModel`，与 automatic 一致，但同样含 `?? model.mode`，详见 §5 P1-1 |
| API payload | 148-162 | PASS | `onGenerate` 中 `const normalizedModel = normalizeGeneratorModel(model)` 后 `generateRule({ model_config: normalizedModel })` |

专项检查 — **defaultCompletionParams 合并行为**：

基线代码（`0c2e573`）的 code-generator effect 中 storedModel 分支：

```typescript
setModel({
  ...storedModel,
  completion_params: {
    ...defaultCompletionParams,
    ...storedModel.completion_params,
  },
})
```

B1 修改后：

```typescript
setModel(
  normalizeGeneratorModel({
    ...storedModel,
    completion_params: {
      ...defaultCompletionParams,
      ...storedModel.completion_params,
    },
  }),
)
```

合并语义完全保留（`defaultCompletionParams` 作为底，`storedModel.completion_params` 覆盖），`normalizeGeneratorModel` 只追加 `mode` 归一化，不触碰 `completion_params`。**官方 1.16 语义保持 PASS**。

结论：**code generator 接入 PASS**。

### 3.4 测试质量

#### 3.4.1 纯函数测试

文件：`automatic/__tests__/normalize-generator-model.spec.ts`（92 行，9 个用例）

| 用例 | 覆盖目标 | 结论 |
| --- | --- | --- |
| `preserves completion mode` | completion → completion + name/provider/completion_params 保留 | PASS |
| `preserves chat mode` | chat → chat | PASS |
| `converts agent-chat to chat` | agent-chat → chat | PASS |
| `converts agent to chat` | agent → chat | PASS |
| `converts advanced-chat to chat` | advanced-chat → chat | PASS |
| `converts workflow to chat` | workflow → chat | PASS |
| `converts empty string to chat` | 空值 → chat | PASS |
| `preserves other model fields` | name/provider/completion_params 在 agent-chat 输入下保留 | PASS |
| `returns a new object without mutating input` | 不修改输入对象 | PASS |

覆盖 B1 要求的全部 mode 映射 + 字段保留 + 不可变性。测试使用 `as Model['mode']` 模拟非法 mode 值（如 `'agent-chat'`），符合测试 stale localStorage 场景的需求。

#### 3.4.2 automatic generator 集成测试

文件：`automatic/__tests__/get-automatic-res.spec.tsx`（新增 4 个用例，138 行）

| 用例 | 验证内容 | 结论 |
| --- | --- | --- |
| `should normalize agent-chat app mode to chat in basic prompt generation` | `mode={AGENT_CHAT}` + `isBasicMode` → `generateBasicAppFirstTimeRule` payload `mode: 'chat'` | PASS |
| `should normalize agent-chat app mode to chat in workflow generation` | `mode={AGENT_CHAT}` + `isBasicMode={false}` + `currentPrompt` → `generateRule` payload `mode: 'chat'` | PASS |
| `should send mode=completion for completion app mode` | `mode={COMPLETION}` + `isBasicMode` → payload `mode: 'completion'` | PASS |
| `should normalize stale localStorage agent-chat to chat before generation` | localStorage 预置 `mode: 'agent-chat'` + `mode={CHAT}` → payload `name: 'stored-model'`, `mode: 'chat'` | PASS |

stale localStorage 测试在 render 前通过 `localStorage.setItem('auto-gen-model', ...)` 注入 stale 数据，验证 stored model 的 `name` 被使用且 `mode` 被归一化。这真实覆盖了旧 localStorage 场景。

#### 3.4.3 code generator 集成测试

文件：`code-generator/__tests__/get-code-generator-res.spec.tsx`（新增 2 个用例，64 行）

| 用例 | 验证内容 | 结论 |
| --- | --- | --- |
| `should normalize agent-chat app mode to chat in code generation` | `mode={AGENT_CHAT}` → `generateRule` payload `mode: 'chat'` | PASS |
| `should send mode=completion for completion app mode in code generation` | `mode={COMPLETION}` → payload `mode: 'completion'` | PASS |

#### 3.4.4 mock 与查询方式核对

- `vi.mock('@/service/debug', ...)` mock 了 `generateBasicAppFirstTimeRule` 和 `generateRule`，测试通过 `expect(mockFn).toHaveBeenCalledWith(expect.objectContaining({ model_config: expect.objectContaining({ mode: '...' }) }))` 验证实际 API payload 中的 mode。这是对真实调用路径的验证，不是仅验证内部 state。
- `vi.mock('react-i18next', ...)` 在 `vitest.setup.ts` 全局 mock，测试使用 `screen.getByText(/(?:^|\.)generate\.generate(?=$|:)/)` 正则匹配 i18n key 模式，与既有测试一致。
- `beforeEach` 中 `localStorage.clear()` + `sessionStorage.clear()` + 重置 `mockDefaultModel`，测试隔离正确。
- `vitest.setup.ts` 的 `beforeEach` 在测试文件 `beforeEach` 之前执行，创建全新 mock localStorage；测试文件的 `beforeEach` 再 clear；stale localStorage 测试在 test body 中 setItem，时序正确。
- `normalizeGeneratorModel` 未被 mock，测试运行真实函数。

结论：**测试质量部分 PASS，但存在覆盖缺口**。测试真实证明已覆盖路径的 API payload 合法性，mock/查询/异步断言符合当前 Vitest/happy-dom/i18n-mock 结构。但 `handleModelChange` 中 `newValue.mode === undefined` 路径（`?? model.mode`）未被任何测试覆盖，详见 §5 P1-1。

### 3.5 官方优先

| 检查项 | 结论 |
| --- | --- |
| 没有覆盖或回退官方 1.16 已有行为 | PASS — B1 只在原有逻辑外层包裹 `normalizeGeneratorModel`，未删除任何既有功能；`defaultCompletionParams` 合并语义、effect 依赖、`useCallback` deps 均保持原样 |
| 没有直接复制不适配当前架构的 1.15 代码 | PASS — 1.15 版本 import `AppModeEnum`/`ModelModeType` const 对象做运行时比较；1.16 版本简化为字面量 `=== 'completion'`，无运行时 enum import，适配当前 TS/Vite+ 架构 |
| `normalize-generator-model.ts` 放置位置 | PASS — 放在 `automatic/` 目录，`code-generator` 通过 `../automatic/normalize-generator-model` 导入。code-generator 已大量导入 `../automatic/*`（idea-output、instruction-editor、res-placeholder、result、style.module.css、types、use-gen-data），此依赖模式已存在 |

### 3.6 fallback 产品假设一致性

PATCH_DECISION_MATRIX.md E17 记录：

> 实施任务：先写纯函数参数化测试，再在读取、默认值、model change 和 API payload 边界统一调用；未知值选择 chat 的产品假设需记录。

实现中未知值（非 `'completion'`）统一 fallback 到 `'chat'`。该假设通过以下方式记录：

1. 纯函数测试 `converts empty string to chat` / `converts agent-chat to chat` / `converts agent to chat` / `converts advanced-chat to chat` / `converts workflow to chat` 显式验证。
2. PATCH_DECISION_MATRIX.md E17 本身记录了该产品决定。
3. 本审查文档确认一致性。

结论：**fallback 产品假设一致性 FAIL**。纯函数本身正确实现 unknown→chat，但 `handleModelChange` 中的 `?? model.mode` 在 `newValue.mode === undefined` 时绕过该规则，继承旧 `completion`，详见 §5 P1-1。

## 4. 实际执行的命令和真实结果

### 4.1 已执行

```bash
# 启动硬门禁
git status --short --branch
# 输出: ## ctyun/replay-116-b1-reviewer  (无额外行，工作区干净)

git rev-parse HEAD
# 输出: 6e1705ba0161bef7efcd7e01fc8e5c58ecae70dd

# 文件范围
git diff --name-status 0c2e5736339cca6c9097d9b84acc14c0e30bcc4e..6e1705ba0161bef7efcd7e01fc8e5c58ecae70dd
# 输出: 6 个文件 (2A, 4M)，全部在 automatic/** 和 code-generator/** 内

git diff --stat 0c2e5736339cca6c9097d9b84acc14c0e30bcc4e..6e1705ba0161bef7efcd7e01fc8e5c58ecae70dd
# 输出: 357 insertions(+), 41 deletions(-)

# 静态检查
git diff --check 0c2e5736339cca6c9097d9b84acc14c0e30bcc4e..6e1705ba0161bef7efcd7e01fc8e5c58ecae70dd
# 退出码: 0 (无空白错误)

# 依赖检查
test -d web/node_modules
# 输出: MISSING
```

### 4.2 未执行及原因

| 命令 | 状态 | 原因 |
| --- | --- | --- |
| `pnpm --dir web vitest run app/components/app/configuration/config/automatic app/components/app/configuration/config/code-generator` | NOT_RUN | `web/node_modules` 不存在；按指令不执行 `pnpm install`，不联网下载依赖 |
| `pnpm --dir web type-check` | NOT_RUN | 同上，依赖缺失 |

**未声称测试通过。** 测试结构和 mock 设置已通过静态阅读验证（见 §3.4），但实际执行结果待依赖就绪后补充。

## 5. Findings

### P0

无。

### P1

**[P1-1] `handleModelChange` 中 `?? model.mode` 偏离 E17 unknown→chat 规则，且无测试覆盖**

文件：
- `web/app/components/app/configuration/config/automatic/get-automatic-res.tsx:227`
- `web/app/components/app/configuration/config/code-generator/get-code-generator-res.tsx:128`

基线代码：
```typescript
mode: newValue.mode as ModelModeType,
```

B1 修改后：
```typescript
mode: (newValue.mode as ModelModeType) ?? model.mode,
```

#### 根因链

1. `ModelParameterModal` 的 `handleChangeModel`（`web/app/components/header/account-setting/model-provider-page/model-parameter-modal/index.tsx:82-93`）实际调用：
   ```typescript
   const handleChangeModel = ({ provider, model }: DefaultModel) => {
     const targetProvider = activeTextGenerationModelList.find(...)
     const targetModelItem = targetProvider?.models.find(...)
     setModel({
       modelId: model,
       provider,
       mode: targetModelItem?.model_properties.mode as string,
       features: targetModelItem?.features || [],
     })
   }
   ```
   当 `targetModelItem` 缺失（模型不在当前 provider 列表中）或 `model_properties.mode` 缺失时，`mode` 的运行时值为 `undefined`（`as string` 只骗编译器，不改变运行时值）。`setModel` 回调签名中 `mode?: string` 也是可选的。

2. B1 的 `handleModelChange` 接收 `newValue.mode === undefined` 后：
   ```typescript
   mode: (newValue.mode as ModelModeType) ?? model.mode
   ```
   `?? model.mode` 使 `undefined` 回退到 `model.mode`（当前已归一化的旧值）。

3. 若旧状态为 `completion`（用户此前选了一个 completion 模型），用户切换到一个不声明 `model_properties.mode` 的新模型时：
   - **B1 当前实现**：`mode` = `model.mode` = `'completion'` → `normalizeGeneratorModel` 保留 `'completion'` → API payload `mode: 'completion'`。
   - **E17 批准规则**：`newValue.mode === undefined` 属于"空值或未知历史值"，应 fallback 到 `'chat'`。

#### 违规点

- **偏离 PATCH_DECISION_MATRIX.md E17**：E17 明确规定"空值或未知历史值 → chat"。`undefined` 是运行时真实发生的空值场景，`?? model.mode` 使其继承旧 `completion`，违反该规则。
- **无测试证明**：两个组件的 `ModelParameterModal` mock 始终传 `mode: 'chat'`（`get-automatic-res.spec.tsx:57`、`get-code-generator-res.spec.tsx:56`），`newValue.mode === undefined` 路径未被任何测试覆盖。纯函数测试也未覆盖 `undefined` 输入。
- **额外行为变化**：基线代码 `mode: newValue.mode as ModelModeType` 在 `newValue.mode === undefined` 时会设为 `undefined`，经 B1 归一化后变为 `'chat'`。B1 的 `?? model.mode` 改变了这一行为，属于未经批准和未经测试的行为变化。

#### 建议 Fix

删除 `?? model.mode`，将 `newValue.mode` 原值交给 `normalizeGeneratorModel` 归一化。详见 §6 整改清单。

### P2

无。

## 6. 最终结论

**CHANGES_REQUIRED**

B1 实现的主体正确、在授权范围内，但存在 1 个 P1 finding 必须修复后才能合并：

1. 纯函数 `normalizeGeneratorModel` 不修改输入、保留所有字段、正确映射所有 mode（completion 保留，其余 → chat），适配 1.16 类型系统，未复制 1.15 运行时 enum 模式。— PASS
2. automatic 和 code generator 在初始 state、storedModel 恢复、defaultModel 回填、API payload 全部接入归一化；无 stale closure、effect 循环、completion_params 丢失或 localStorage 脏写回。— PASS
3. code generator 的 `defaultCompletionParams` 合并语义完整保留。— PASS
4. 测试覆盖已验证路径的 mode 映射（含 stale localStorage），通过验证实际 API payload 中的 `model_config.mode` 真实证明行为。— PASS（但 P1-1 路径未覆盖）
5. 文件边界严格，仅 6 个文件全部在 `automatic/**` 和 `code-generator/**` 内。— PASS
6. fallback 到 chat 的产品假设在纯函数层面与 E17 一致，但 `handleModelChange` 的 `?? model.mode` 在 `newValue.mode === undefined` 时绕过该规则。— **FAIL（P1-1）**
7. `git diff --check` 通过，无空白错误。— PASS

### 最小 Fixer 整改清单

以下整改不扩大文件范围，不修改 API、Docker、i18n、依赖或其他模块。Fixer 只在 B1 授权路径内修改：

1. **`web/app/components/app/configuration/config/automatic/get-automatic-res.tsx`**：
   删除 `?? model.mode`，将 `newValue.mode` 原值交给 `normalizeGeneratorModel`。
   ```typescript
   // 修改前
   mode: (newValue.mode as ModelModeType) ?? model.mode,
   // 修改后
   mode: newValue.mode as ModelModeType,
   ```

2. **`web/app/components/app/configuration/config/code-generator/get-code-generator-res.tsx`**：
   同样删除 `?? model.mode`。
   ```typescript
   // 修改前
   mode: (newValue.mode as ModelModeType) ?? model.mode,
   // 修改后
   mode: newValue.mode as ModelModeType,
   ```

3. **给两个组件的 `ModelParameterModal` mock 增加"不提供 mode 的模型切换"路径**：
   在 `get-automatic-res.spec.tsx` 和 `get-code-generator-res.spec.tsx` 的 mock 中增加一个不传 `mode`（或 `mode: undefined`）的切换按钮，例如：
   ```tsx
   <button
     onClick={() => setModel({ modelId: 'no-mode-model', provider: 'openai' })}
   >
     change-model-no-mode
   </button>
   ```

4. **从 completion 初始状态切换到不提供 mode 的新模型后，验证最终 API payload 为 chat**：
   新增集成测试用例：`mode={COMPLETION}` 初始化 → 点击"不提供 mode 的模型切换" → 生成 → 断言 `generateBasicAppFirstTimeRule` / `generateRule` payload `model_config.mode === 'chat'`。automatic 和 code-generator 各一个。

5. **纯函数测试补充 `undefined` 和任意未知历史字符串 → chat**：
   在 `normalize-generator-model.spec.ts` 增加用例：
   - `converts undefined to chat`：`mode: undefined as Model['mode']` → `result.mode === 'chat'`
   - `converts unknown string to chat`：`mode: 'some-unknown-mode' as Model['mode']` → `result.mode === 'chat'`

6. **不扩大文件范围**：不修改 API、Docker、i18n、依赖或其他模块。Fixer 只触及上述 B1 授权文件。

## 7. 后续仍需完成的真实浏览器集成验证

以下验证尚未执行，不得冒充已验证：

1. **Vitest 执行**：依赖就绪后运行
   ```bash
   pnpm --dir web vitest run \
     app/components/app/configuration/config/automatic \
     app/components/app/configuration/config/code-generator
   ```
   确认全部用例（含既有 + B1 新增）实际通过。

2. **Type-check**：依赖就绪后运行
   ```bash
   pnpm --dir web type-check
   ```
   确认无类型错误。

3. **浏览器集成验证**（VALIDATION_PLAN.md Phase G / PATCH_DECISION_MATRIX.md E17 集成验证项）：
   - 创建 text generation（completion）app，打开 prompt generator，执行一次生成，确认 API payload `mode: 'completion'`。
   - 创建 chat app，打开 prompt generator，执行一次生成，确认 API payload `mode: 'chat'`。
   - 创建传统 agent（agent-chat）app，打开 prompt generator，执行一次生成，确认 API payload `mode: 'chat'`。
   - 创建 Agent v2（agent）app，打开 prompt/code generator，执行一次生成，确认 API payload `mode: 'chat'`。
   - 在浏览器 localStorage 中预置 stale `auto-gen-model`（`mode: 'agent-chat'`），打开 generator，确认 payload `mode: 'chat'` 且使用 stored model 的 name/provider。
   - 确认 workflow 节点的 code generator payload 同样合法。
