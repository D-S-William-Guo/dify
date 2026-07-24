import type { Model, ModelModeType } from '@/types/app'

export const normalizeGeneratorModel = (model: Model): Model => {
  if (model.mode === 'completion')
    return { ...model, mode: 'completion' as ModelModeType }

  return { ...model, mode: 'chat' as ModelModeType }
}
