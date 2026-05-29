<template>
  <div class="visit-summary">
    <div class="summary-header">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><rect x="2" y="2" width="14" height="14" rx="2" stroke="currentColor" stroke-width="1.4"/><path d="M5 6h8M5 9h8M5 12h5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
      <span>就诊摘要</span>
      <span class="summary-badge">可出示给兽医</span>
    </div>
    <div class="summary-body" v-html="rendered" />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ content: String })

const rendered = computed(() => {
  if (!props.content) return ''
  return props.content
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
})
</script>

<style scoped>
.visit-summary {
  margin: 12px 0;
  border-radius: var(--radius-lg);
  border: 2px solid var(--green-300);
  background: linear-gradient(135deg, var(--green-100), #f0f7ec);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  animation: slide-up var(--duration-normal) var(--ease-out);
}
@keyframes slide-up {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  background: rgba(93, 138, 91, 0.12);
  font-size: 14px;
  font-weight: 700;
  color: var(--green-700);
}
.summary-badge {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background: var(--green-500);
  color: #fff;
}

.summary-body {
  padding: 18px;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
}
.summary-body :deep(h2) {
  font-family: var(--font-display);
  font-size: 17px;
  color: var(--green-700);
  margin: 12px 0 6px;
}
.summary-body :deep(h3) {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 10px 0 4px;
}
.summary-body :deep(li) {
  list-style: none;
  padding-left: 12px;
  position: relative;
}
.summary-body :deep(li)::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--green-500);
  font-weight: bold;
}
.summary-body :deep(strong) {
  color: var(--green-700);
}
</style>
