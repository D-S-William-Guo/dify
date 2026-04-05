// Credits:
// https://github.com/tailwindlabs/tailwindcss-intellisense/issues/227

import { readFileSync } from 'node:fs'
import { parse, type AtRule, type Declaration, type Rule } from 'postcss'

type CssDeclarationMap = Record<string, string>
type CssRuleMap = Record<string, CssDeclarationMap>
type LayerName = '@layer utilities' | '@layer components' | '@layer base'
type LayerMap = Partial<Record<LayerName, CssRuleMap>>

type TailwindPluginApi = {
  addUtilities: (utilities: CssRuleMap) => void
  addComponents: (components: CssRuleMap) => void
  addBase: (base: CssRuleMap) => void
}

type PluginCreator = (api: TailwindPluginApi) => void

const LAYER_NAME_SET = new Set<LayerName>(['@layer utilities', '@layer components', '@layer base'])

const collectRuleDeclarations = (rule: Rule): CssDeclarationMap => {
  const declarations: CssDeclarationMap = {}

  rule.nodes?.forEach((node) => {
    if (node.type !== 'decl')
      return

    const declaration = node as Declaration
    declarations[declaration.prop] = declaration.value
  })

  return declarations
}

const objectifyLayerRules = (layerNode: AtRule): CssRuleMap => {
  const rules: CssRuleMap = {}

  layerNode.nodes?.forEach((node) => {
    if (node.type !== 'rule')
      return

    const rule = node as Rule
    rules[rule.selector] = collectRuleDeclarations(rule)
  })

  return rules
}

const parseCssLayers = (cssContent: string): LayerMap => {
  const root = parse(cssContent)
  const layers: LayerMap = {}

  root.walkAtRules('layer', (atRule) => {
    const layerName = `@layer ${atRule.params}` as LayerName
    if (!LAYER_NAME_SET.has(layerName))
      return

    layers[layerName] = {
      ...(layers[layerName] ?? {}),
      ...objectifyLayerRules(atRule),
    }
  })

  return layers
}

export const cssAsPlugin: (cssPath: string[]) => PluginCreator = (cssPath: string[]) => {
  const isTailwindCSSIntelliSenseMode = 'TAILWIND_MODE' in process.env
  if (!isTailwindCSSIntelliSenseMode) {
    return () => {}
  }

  return ({ addUtilities, addComponents, addBase }) => {
    const jssList = cssPath.map(p => parseCssLayers(readFileSync(p, 'utf8')))

    for (const jss of jssList) {
      if (jss['@layer utilities'])
        addUtilities(jss['@layer utilities'])
      if (jss['@layer components'])
        addComponents(jss['@layer components'])
      if (jss['@layer base'])
        addBase(jss['@layer base'])
    }
  }
}
