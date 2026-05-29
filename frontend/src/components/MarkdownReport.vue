<template>
  <div v-if="markdown" class="report-card">
    <div class="card-header">
      <h3>📝 最终报告</h3>
      <button class="copy-btn" @click="copyMd" :class="{ copied }">
        {{ copied ? '✓ 已复制' : '复制 Markdown' }}
      </button>
    </div>
    <div class="report-body" v-html="rendered"></div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  markdown: { type: String, default: '' },
})

const copied = ref(false)

const rendered = computed(() => {
  if (!props.markdown) return ''
  return marked.parse(props.markdown, { breaks: true, gfm: true })
})

async function copyMd() {
  try {
    await navigator.clipboard.writeText(props.markdown)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    copied.value = false
  }
}
</script>

<style scoped>
.report-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
  margin: 12px 0;
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

.copy-btn {
  padding: 4px 10px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  border-radius: var(--radius-full);
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.copy-btn:hover {
  background: var(--green-100);
  color: var(--green-700);
  border-color: var(--green-300);
}

.copy-btn.copied {
  background: var(--green-300);
  color: #fff;
  border-color: var(--green-500);
}

.report-body {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-primary);
}

.report-body :deep(h1),
.report-body :deep(h2),
.report-body :deep(h3) {
  font-family: var(--font-display);
  margin: 16px 0 8px;
  color: var(--text-primary);
}

.report-body :deep(h1) { font-size: 18px; }
.report-body :deep(h2) { font-size: 16px; }
.report-body :deep(h3) { font-size: 14px; }

.report-body :deep(p) {
  margin: 6px 0;
}

.report-body :deep(ul),
.report-body :deep(ol) {
  margin: 6px 0;
  padding-left: 22px;
}

.report-body :deep(li) {
  margin: 2px 0;
}

.report-body :deep(strong) {
  color: var(--text-primary);
  font-weight: 700;
}

.report-body :deep(code) {
  background: var(--bg-input);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-family: 'Menlo', 'Consolas', monospace;
}

.report-body :deep(blockquote) {
  margin: 8px 0;
  padding: 8px 12px;
  border-left: 3px solid var(--amber-300);
  background: var(--amber-100);
  color: var(--amber-700);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.report-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-light);
  margin: 12px 0;
}
</style>
