import type { Model } from '@/types/app'
import { normalizeGeneratorModel } from '../normalize-generator-model'

const baseModel: Model = {
  name: 'gpt-4',
  provider: 'openai',
  mode: 'chat',
  completion_params: { temperature: 0.7 } as Model['completion_params'],
}

describe('normalizeGeneratorModel', () => {
  it('preserves completion mode', () => {
    const model: Model = { ...baseModel, mode: 'completion' }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('completion')
    expect(result.name).toBe('gpt-4')
    expect(result.provider).toBe('openai')
    expect(result.completion_params).toEqual(baseModel.completion_params)
  })

  it('preserves chat mode', () => {
    const model: Model = { ...baseModel, mode: 'chat' }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
  })

  it('converts agent-chat to chat', () => {
    const model: Model = { ...baseModel, mode: 'agent-chat' as Model['mode'] }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
  })

  it('converts agent to chat', () => {
    const model: Model = { ...baseModel, mode: 'agent' as Model['mode'] }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
  })

  it('converts advanced-chat to chat', () => {
    const model: Model = { ...baseModel, mode: 'advanced-chat' as Model['mode'] }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
  })

  it('converts workflow to chat', () => {
    const model: Model = { ...baseModel, mode: 'workflow' as Model['mode'] }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
  })

  it('converts empty string to chat', () => {
    const model: Model = { ...baseModel, mode: '' }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
  })

  it('preserves other model fields', () => {
    const model: Model = {
      name: 'claude-sonnet',
      provider: 'anthropic',
      mode: 'agent-chat' as Model['mode'],
      completion_params: {
        temperature: 0.3,
        max_tokens: 1000,
      } as Model['completion_params'],
    }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
    expect(result.name).toBe('claude-sonnet')
    expect(result.provider).toBe('anthropic')
    expect(result.completion_params).toEqual({
      temperature: 0.3,
      max_tokens: 1000,
    })
  })

  it('converts undefined to chat', () => {
    const model: Model = { ...baseModel, mode: undefined as unknown as Model['mode'] }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
  })

  it('converts unknown string to chat', () => {
    const model: Model = { ...baseModel, mode: 'some-unknown-mode' as Model['mode'] }
    const result = normalizeGeneratorModel(model)

    expect(result.mode).toBe('chat')
  })

  it('returns a new object without mutating input', () => {
    const model: Model = { ...baseModel, mode: 'agent-chat' as Model['mode'] }
    const result = normalizeGeneratorModel(model)

    expect(result).not.toBe(model)
    expect(model.mode).toBe('agent-chat')
  })
})
