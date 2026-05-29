// Agent 工具轨迹辅助工具 — 营养评估方向

export const TOOL_LABELS = {
  extract_label_nutrition: '解析包装标签',
  lookup_ingredient: '查询食材',
  compute_energy_requirement: '计算能量需求',
  assess_nutrition: '综合营养评估',
  final_answer: '生成最终报告',
}

const ARG_LABELS = {
  species: '物种',
  weight_kg: '体重(kg)',
  age_months: '月龄',
  neutered: '已绝育',
  conditions: '健康状况',
  allergens: '过敏原',
  query: '查询',
  max_results: '最多返回',
  image_path: '图片路径',
  profile: '宠物档案',
  diet_input: '饮食描述',
  message: '消息',
}

export function toolLabel(name) {
  return TOOL_LABELS[name] || name || '未知工具'
}

export function summarizeArgs(args) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return ''

  const entries = Object.entries(args).filter(([, value]) => {
    if (value === undefined || value === null) return false
    if (typeof value === 'string') return value.trim() !== ''
    if (Array.isArray(value)) return value.length > 0
    if (typeof value === 'object') return Object.keys(value).length > 0
    return true
  })

  if (!entries.length) return ''

  const preview = entries
    .slice(0, 3)
    .map(([key, value]) => `${ARG_LABELS[key] || key}: ${compactValue(value)}`)
    .join(' · ')

  return entries.length > 3 ? `${preview} · ...` : preview
}

export function summarizeText(value, maxLength = 140) {
  if (value === undefined || value === null) return ''

  const text = String(value).replace(/\s+/g, ' ').trim()
  if (!text) return ''

  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text
}

function compactValue(value) {
  if (typeof value === 'string') return summarizeText(value, 50)
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)

  if (Array.isArray(value)) {
    const compact = value.slice(0, 3).map(compactValue).join(', ')
    return value.length > 3 ? `${compact}, ...` : compact
  }

  if (typeof value === 'object') {
    const preview = Object.entries(value)
      .slice(0, 2)
      .map(([key, innerValue]) => `${ARG_LABELS[key] || key}: ${compactValue(innerValue)}`)
      .join(', ')
    return Object.keys(value).length > 2 ? `${preview}, ...` : preview
  }

  return summarizeText(value, 50)
}
