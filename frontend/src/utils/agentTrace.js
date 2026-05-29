export const TOOL_LABELS = {
  emergency_triage: '紧急分诊评估',
  collect_symptoms: '采集症状信息',
  analyze_pet_image: '分析宠物图片',
  search_pet_knowledge: '检索知识库',
  medication_guide: '用药建议',
  generate_visit_summary: '生成就诊摘要',
  final_answer: '整理最终答复',
  track_symptoms: '查询症状历史',
}

const TRIAGE_LEVEL_LABELS = {
  er_now: '需要立即就医',
  schedule_visit: '建议尽快预约就诊',
  home_care: '可先居家观察',
}

const ARG_LABELS = {
  species: '物种',
  symptoms: '症状',
  query: '问题',
  additional_info: '补充信息',
  current_symptoms: '当前症状',
  pet_profile: '宠物资料',
  image_path: '图片路径',
}

export function toolLabel(name) {
  return TOOL_LABELS[name] || name || '未知工具'
}

export function triageLevelLabel(level) {
  return TRIAGE_LEVEL_LABELS[level] || level || '未判定'
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

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }

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
