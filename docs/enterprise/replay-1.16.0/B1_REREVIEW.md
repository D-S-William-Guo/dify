# B1 Re-Review: Generator Model Mode Normalization

## 1. 关键 Commit ID

| 角色 | Commit | 分支 |
| --- | --- | --- |
| B1 前基线 | `0c2e5736339cca6c9097d9b84acc14c0e30bcc4e` | — |
| Builder | `6e1705ba0161bef7efcd7e01fc8e5c58ecae70dd` | `ctyun/replay-116-b1-builder` |
| 原 Reviewer | `1039167eff800bc59731872fbe8e2f8743ef64f1` | `ctyun/replay-116-b1-reviewer` |
| Fixer | `266d43b0115a83b222b6cfc3ce09a41559996438` | `ctyun/replay-116-b1-fixer` |

## 2. 启动硬门禁结果

```
## ctyun/replay-116-b1-rereviewer
266d43b0115a83b222b6cfc3ce09a41559996438
git status --short: (空，工作区干净)
```

分支、HEAD、工作区清洁度全部符合预期。

## 3. P1-1 逐项关闭证据

原 Reviewer 提出的 P1-1：
> `handleModelChange` 中 `?? model.mode` 偏离 E17 unknown→chat 规则，且无测试覆盖

### 3.1 `?? model.mode` 删除

**automatic** (`web/app/components/app/configuration/config/automatic/get-automatic-res.tsx:227`)：

```typescript
// Builder (含 ?? model.mode, 偏离规则)
mode: (newValue.mode as ModelModeType) ?? model.mode,

// Fixer (完全删除 ?? model.mode)
mode: newValue.mode as ModelModeType,
```

**code-generator** (`web/app/components/app/configuration/config/code-generator/get-code-generator-res.tsx:128`)：

```typescript
// Builder
mode: (newValue.mode as ModelModeType) ?? model.mode,

// Fixer
mode: newValue.mode as ModelModeType,
```

### 3.2 `newValue.mode` 原值传给 `normalizeGeneratorModel`

Fixer 将 `mode: newValue.mode as ModelModeType` 原值传递给 `normalizeGeneratorModel`。`handleModelChange` 的完整代码现为：

```typescript
const newModel = normalizeGeneratorModel({
  ...model,
  provider: newValue.provider,
  name: newValue.modelId,
  mode: newValue.mode as ModelModeType,
})
```

### 3.3 undefined、空值或未知值最终变为 chat

`normalizeGeneratorModel` 实现 (`normalize-generator-model.ts:3-8`)：

```typescript
export const normalizeGeneratorModel = (model: Model): Model => {
  if (model.mode === 'completion')
    return { ...model, mode: 'completion' as ModelModeType }
  return { ...model, mode: 'chat' as ModelModeType }
}
```

- `model.mode === undefined` → `'completion'` 检查不通过 → `'chat'` ✅
- `model.mode === ''` → `'completion'` 检查不通过 → `'chat'` ✅
- `model.mode === 'some-unknown-value'` → `'completion'` 检查不通过 → `'chat'` ✅

### 3.4 completion 明确输入仍保持 completion

`normalizeGeneratorModel` 第一行 `if (model.mode === 'completion')` 保留 completion mode ✅

### 3.5 不会继承旧模型的 completion mode

因 `?? model.mode` 已删除，`newValue.mode === undefined` 时不会回退到旧 `model.mode`。`normalizeGeneratorModel` 接收到 `undefined` 后将转为 `'chat'`。用户从 completion 模型切换到不提供 mode 的新模型后，payload mode 为 `'chat'`。✅

**结论：P1-1 已关闭。**

## 4. Fixer 文件范围

Fixer 仅修改了原 Reviewer 授权路径 `automatic/**` 和 `code-generator/**` 内的 5 个文件，无新增文件：

| 文件 | 变更 |
| --- | --- |
| `automatic/get-automatic-res.tsx` | 1 行：删除 `?? model.mode` |
| `code-generator/get-code-generator-res.tsx` | 1 行：删除 `?? model.mode` |
| `automatic/__tests__/get-automatic-res.spec.tsx` | 新增 mock 按钮 + 1 个集成测试用例 |
| `code-generator/__tests__/get-code-generator-res.spec.tsx` | 新增 mock 按钮 + 1 个集成测试用例 |
| `automatic/__tests__/normalize-generator-model.spec.ts` | 新增 2 个纯函数测试用例 |

未触及 API、Docker、migration、contracts、i18n、依赖、版本、volume 或原 B1_REVIEW.md。

## 5. 新增测试审查

### 5.1 pure function 补充测试 (`normalize-generator-model.spec.ts`)

| 用例 | 覆盖率 | 断言 | 结论 |
| --- | --- | --- | --- |
| `converts undefined to chat` | `mode: undefined` → chat | `result.mode === 'chat'` | PASS |
| `converts unknown string to chat` | `mode: 'some-unknown-mode'` → chat | `result.mode === 'chat'` | PASS |

### 5.2 automatic 集成测试 (`get-automatic-res.spec.tsx`)

**No-mode 模型切换验证**：

```
should normalize no-mode model to chat in basic prompt generation
```

- `render` 使用 `mode={AppModeEnum.COMPLETION}`（从 completion 起步）
- 点击 `change-model-no-mode` → mock 调用 `setModel({ modelId: 'no-mode-model', provider: 'openai' })`（无 mode 字段 → `undefined`）
- 点击 `set-basic-instruction` → 设置 instruction
- 点击 `generate.generate` → 触发生成
- 断言 `mockGenerateBasicAppFirstTimeRule` 被调用，payload 包含 `name: 'no-mode-model', mode: 'chat'` ✅

**Mock 验证**：`ModelParameterModal` mock 的 `setModel` prop 对应真实组件 `setModel={handleModelChange}`（`get-automatic-res.tsx:324`）。Mock 按钮调用 `setModel({ modelId: 'no-mode-model', provider: 'openai' })` 等价于调用 `handleModelChange({ modelId: 'no-mode-model', provider: 'openai' })`，其中 `newValue.mode === undefined` — 精准覆盖 P1-1 缺失路径。

### 5.3 code-generator 集成测试 (`get-code-generator-res.spec.tsx`)

**No-mode 模型切换验证**：

```
should normalize no-mode model to chat in code generation
```

- `render` 使用 `mode={AppModeEnum.COMPLETION}`（从 completion 起步）
- 点击 `change-model-no-mode` → 同上
- 点击 `set-code-instruction` → 设置 instruction
- 点击 `codegen.generate` → 触发生成
- 断言 `mockGenerateRule` payload 包含 `name: 'no-mode-model', mode: 'chat'` ✅

### 5.4 测试质量专项核查

| 检查项 | 结果 |
| --- | --- |
| Mock prop 名 `setModel` 匹配真实组件 | PASS (`get-automatic-res.tsx:324`, `get-code-generator-res.tsx:240`) |
| 测试从 `AppModeEnum.COMPLETION` 开始（非 chat） | PASS (automatic:428, code-gen:342) |
| 切换到不提供 mode 的模型 | PASS (mock 调用无 `mode` 字段) |
| 最终验证真实 API payload，不只是内部 state | PASS (`expect(mockFn).toHaveBeenCalledWith(expect.objectContaining({ model_config: ... }))`) |
| 验证字段包含 `name` + `mode`（确认使用新模型数据） | PASS (`name: 'no-mode-model', mode: 'chat'`) |
| `normalizeGeneratorModel` 未被 mock，运行真实函数 | PASS |
| 纯函数测试覆盖 `undefined` 和任意未知字符串 | PASS |
| 测试无假阳性、调用错 mock 或遗漏必要 instruction | PASS |

## 6. 完整 B1 验收矩阵

| 输入 mode | 预期输出 | 归一化路径 | 测试覆盖 | 结论 |
| --- | --- | --- | --- | --- |
| `completion` | `completion` | `normalizeGeneratorModel` 显式分支 | ✅ pure function + 两组件集成 | PASS |
| `chat` | `chat` | 非 completion fallback | ✅ pure function | PASS |
| `agent-chat` | `chat` | 非 completion fallback | ✅ pure function + 两组件集成 | PASS |
| `agent` | `chat` | 非 completion fallback | ✅ pure function | PASS |
| `advanced-chat` | `chat` | 非 completion fallback | ✅ pure function | PASS |
| `workflow` | `chat` | 非 completion fallback | ✅ pure function | PASS |
| stale localStorage `agent-chat` | `chat` | effect 中 `normalizeGeneratorModel(storedModel)` | ✅ automatic 集成 | PASS |
| `undefined` | `chat` | 非 completion fallback | ✅ pure function + 两组件集成 (no-mode) | PASS |
| `''` (空值) | `chat` | 非 completion fallback | ✅ pure function | PASS |
| 任意未知字符串 | `chat` | 非 completion fallback | ✅ pure function | PASS |

### 回归风险核查

| 检查项 | 结论 |
| --- | --- |
| defaultModel 回填 | PASS — 未被 Fixer 修改 |
| storedModel/localStorage 恢复 | PASS — 未被 Fixer 修改 |
| completion_params | PASS — 未被 Fixer 修改 |
| effect 依赖 (`[defaultModel, storedModel]`) | PASS — 未被 Fixer 修改 |
| provider/name 更新 | PASS — 未被 Fixer 修改 |
| API 调用其他字段 | PASS — 未被 Fixer 修改 |
| 官方 1.16 原有逻辑 | PASS — Fixer 仅在归一化范围内改 1 行 |
| 文件范围越界 | PASS — 严格限制在 B1 授权路径 |

## 7. 实际执行命令与真实结果

```bash
# 启动硬门禁（已执行）
git status --short --branch
## ctyun/replay-116-b1-rereviewer  (工作区干净)

git rev-parse HEAD
266d43b0115a83b222b6cfc3ce09a41559996438

# 审查 diff（已执行）
git diff 0c2e573..266d43b  # 基线与总变化
# 输出: 7 文件（B1_REVIEW.md + 6 实现/测试文件）

git diff 1039167ef..266d43b  # Reviewer 与 Fixer
# 输出: 5 文件，仅 B1 授权路径内的修正

# 静态检查（已执行）
git diff --check 0c2e573..HEAD  # 退出码 0，无空白错误
git diff --check 1039167ef..HEAD  # 退出码 0，无空白错误

# 依赖检查（已执行）
test -d web/node_modules  # MISSING
```

## 8. NOT_RUN 项及原因

| 命令 | 状态 | 原因 |
| --- | --- | --- |
| `pnpm --dir web vitest run app/components/app/configuration/config/automatic app/components/app/configuration/config/code-generator` | NOT_RUN | `web/node_modules` 不存在；按指令不运行 `pnpm install`，不联网下载依赖 |
| `pnpm --dir web type-check` | NOT_RUN | 同上，依赖缺失 |
| 浏览器集成验证 | NOT_RUN | 需要真实浏览器环境，不在自动化工件范围内 |

**未声称测试通过。** 测试结构和 mock 设置已通过静态阅读验证（§5），但实际执行结果待依赖就绪后补充。

## 9. 新 Findings

### P0

无。

### P1

无。P1-1 已被 Fixer 完整关闭。

### P2

无。Fixer 未引入任何新问题。

## 10. 最终结论

**PASS**

- **P1-1 是否关闭**：是。`?? model.mode` 已从两组件删除；`newValue.mode` 原值传入 `normalizeGeneratorModel`；undefined/unknown → chat 通过纯函数和集成测试双重覆盖。
- **新 Findings**：无。
- **测试真实状态**：NOT_RUN（依赖缺失），但通过静态阅读确认 5 个新增用例结构正确、mock 匹配、断言验证真实 API payload、无假阳性风险。
- **复审目标（Fixer）Commit ID**：`266d43b0115a83b222b6cfc3ce09a41559996438`
- **修改文件**（自 Fixer 起）：
  - `web/app/components/app/configuration/config/automatic/get-automatic-res.tsx`
  - `web/app/components/app/configuration/config/code-generator/get-code-generator-res.tsx`
  - `web/app/components/app/configuration/config/automatic/__tests__/get-automatic-res.spec.tsx`
  - `web/app/components/app/configuration/config/code-generator/__tests__/get-code-generator-res.spec.tsx`
  - `web/app/components/app/configuration/config/automatic/__tests__/normalize-generator-model.spec.ts`

### 尚未完成的验证

1. **Vitest 执行**：依赖就绪后运行 `pnpm --dir web vitest run app/components/app/configuration/config/automatic app/components/app/configuration/config/code-generator`，确认全部用例实际通过。
2. **Type-check**：依赖就绪后运行 `pnpm --dir web type-check`，确认无类型错误。
3. **浏览器集成验证**（PATCH_DECISION_MATRIX.md E17 集成验证项）：
   - 创建 text generation（completion）app → prompt generator → 断言 API payload `mode: 'completion'`
   - 创建 chat app → prompt generator → 断言 API payload `mode: 'chat'`
   - 创建传统 agent（agent-chat）app → prompt generator → 断言 API payload `mode: 'chat'`
   - 创建 Agent v2（agent）app → prompt/code generator → 断言 API payload `mode: 'chat'`
   - 浏览器 localStorage 预置 stale `auto-gen-model`（`mode: 'agent-chat'`）→ 断言 payload `mode: 'chat'` 且使用 stored model 的 name/provider
   - 确认 workflow 节点的 code generator payload 同样合法
