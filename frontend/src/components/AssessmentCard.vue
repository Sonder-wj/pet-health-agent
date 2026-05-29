<template>
  <div v-if="assessment" class="assessment-card">
    <div class="card-header">
      <h3>📊 营养评估</h3>
      <span class="finding-badge">{{ assessment.findings?.length || 0 }} 项发现</span>
    </div>

    <!-- 能量平衡 -->
    <section class="block">
      <div class="block-title">能量平衡</div>
      <div class="energy-row">
        <span class="energy-label">摄入</span>
        <strong>{{ format(assessment.energy?.intake_kcal) }}</strong>
        <span class="vs">/</span>
        <span class="energy-label">目标 MER</span>
        <strong>{{ format(assessment.energy?.mer) }}</strong>
        <span class="unit">kcal/day</span>
      </div>
      <div class="bar-wrap">
        <div class="bar-track">
          <div class="bar-fill" :class="energyClass" :style="{ width: energyPct + '%' }"></div>
        </div>
        <span class="balance" :class="energyClass">
          偏差 {{ formatPct(assessment.energy?.balance_pct) }}
        </span>
      </div>
    </section>

    <!-- 营养素 -->
    <section v-if="assessment.nutrients?.length" class="block">
      <div class="block-title">营养素密度 (per 1000 kcal ME)</div>
      <div class="nutrients">
        <div v-for="n in assessment.nutrients" :key="n.nutrient" class="nutrient-row">
          <span class="dot" :class="statusClass(n.status)"></span>
          <span class="n-name">{{ nutrientLabel(n.nutrient) }}</span>
          <span class="n-value">{{ format(n.actual) }} {{ n.unit }}</span>
          <span class="n-target">目标 {{ formatTarget(n) }}</span>
        </div>
      </div>
    </section>

    <!-- Findings -->
    <section v-if="assessment.findings?.length" class="block">
      <div class="block-title">关键发现</div>
      <div class="findings">
        <div v-for="(f, idx) in sortedFindings" :key="idx" class="finding-row" :class="f.severity">
          <span class="severity-tag">{{ severityIcon(f.severity) }} {{ severityLabel(f.severity) }}</span>
          <span class="f-msg">{{ f.message }}</span>
        </div>
      </div>
    </section>

    <p class="footer-note">
      ⚠️ 评估仅供参考,不替代兽医诊断。critical 项尤其涉及疾病时请咨询执业兽医。
    </p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  assessment: { type: Object, default: null },
})

const energyPct = computed(() => {
  const e = props.assessment?.energy
  if (!e || !e.mer) return 0
  const pct = (e.intake_kcal / e.mer) * 100
  return Math.min(150, Math.max(0, pct))
})

const energyClass = computed(() => {
  const b = props.assessment?.energy?.balance_pct
  if (b === undefined || b === null) return 'ok'
  if (b > 50 || b < -50) return 'critical'
  if (b > 20 || b < -20) return 'warning'
  return 'ok'
})

const SEVERITY_ORDER = { critical: 0, warning: 1, info: 2 }

const sortedFindings = computed(() => {
  return [...(props.assessment?.findings || [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3)
  )
})

const NUTRIENT_LABELS = {
  protein: '蛋白质', fat: '脂肪', carb: '碳水', fiber: '纤维',
  calcium: '钙', phosphorus: '磷', taurine: '牛磺酸', sodium: '钠',
}

function nutrientLabel(name) {
  return NUTRIENT_LABELS[name] || name
}

function statusClass(status) {
  if (status === 'low' || status === 'high') return 'warning'
  return 'ok'
}

function severityIcon(s) {
  return { critical: '🔴', warning: '🟡', info: '🟢' }[s] || '⚪'
}

function severityLabel(s) {
  return { critical: '严重', warning: '注意', info: '提示' }[s] || s
}

function format(n) {
  if (n === undefined || n === null) return '—'
  return typeof n === 'number' ? n.toFixed(0) : n
}

function formatPct(n) {
  if (n === undefined || n === null) return '—'
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

function formatTarget(n) {
  const mn = n.target_min
  const mx = n.target_max
  if (mn !== null && mx !== null) return `${mn}–${mx}`
  if (mn !== null) return `≥ ${mn}`
  if (mx !== null) return `≤ ${mx}`
  return '—'
}
</script>

<style scoped>
.assessment-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
  margin: 12px 0;
  font-size: 13px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-light);
}

.card-header h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 16px;
  color: var(--text-primary);
}

.finding-badge {
  background: var(--amber-100);
  color: var(--amber-700);
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 600;
}

.block {
  margin: 12px 0;
}

.block-title {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  font-weight: 600;
}

.energy-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 6px;
}

.energy-label {
  font-size: 11px;
  color: var(--text-secondary);
}

.energy-row strong {
  font-size: 16px;
  color: var(--text-primary);
}

.vs {
  color: var(--text-secondary);
}

.unit {
  font-size: 11px;
  color: var(--text-secondary);
  margin-left: auto;
}

.bar-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-track {
  flex: 1;
  height: 10px;
  background: var(--border-light);
  border-radius: var(--radius-full);
  overflow: hidden;
  position: relative;
}

.bar-track::after {
  content: '';
  position: absolute;
  left: 66.67%;
  top: 0;
  height: 100%;
  width: 2px;
  background: var(--text-secondary);
  opacity: 0.3;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out);
}

.bar-fill.ok      { background: var(--green-500); }
.bar-fill.warning { background: var(--amber-500); }
.bar-fill.critical{ background: var(--red-500); }

.balance {
  font-size: 12px;
  font-weight: 600;
}

.balance.ok      { color: var(--green-700); }
.balance.warning { color: var(--amber-700); }
.balance.critical{ color: var(--red-700); }

.nutrients {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nutrient-row {
  display: grid;
  grid-template-columns: 14px 1fr auto auto;
  gap: 10px;
  align-items: center;
  font-size: 12px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  align-self: center;
  justify-self: center;
}

.dot.ok      { background: var(--green-500); }
.dot.warning { background: var(--amber-500); }
.dot.critical{ background: var(--red-500); }

.n-name { color: var(--text-primary); font-weight: 500; }
.n-value { color: var(--text-primary); font-variant-numeric: tabular-nums; }
.n-target { color: var(--text-secondary); font-size: 11px; }

.findings {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.finding-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.finding-row.critical {
  background: var(--red-100);
  border-left: 3px solid var(--red-500);
}

.finding-row.warning {
  background: var(--amber-100);
  border-left: 3px solid var(--amber-500);
}

.finding-row.info {
  background: var(--green-100);
  border-left: 3px solid var(--green-500);
}

.severity-tag {
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.f-msg {
  flex: 1;
  color: var(--text-primary);
}

.footer-note {
  margin: 12px 0 0;
  padding-top: 10px;
  border-top: 1px solid var(--border-light);
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.5;
}
</style>
