<template>
  <section v-if="steps.length" class="trace-panel">
    <div class="trace-header">
      <div>
        <p class="trace-kicker">Agent 处理过程</p>
        <h3 class="trace-title">像工具代理一样展示这次推理链路</h3>
      </div>
      <span class="trace-badge">{{ runningCount > 0 ? `进行中 ${runningCount}` : '已完成' }}</span>
    </div>

    <div class="trace-list">
      <article
        v-for="step in steps"
        :key="step.id"
        :class="['trace-item', `trace-${step.kind}`, `status-${step.status || 'done'}`]"
      >
        <div class="trace-rail">
          <span class="trace-dot" />
          <span class="trace-line" />
        </div>

        <div class="trace-card">
          <div class="trace-meta">
            <span class="trace-kind">{{ kindLabel(step.kind) }}</span>
            <span v-if="step.status === 'running'" class="trace-status running">执行中</span>
            <span v-else-if="step.status === 'done'" class="trace-status done">已完成</span>
            <span v-else class="trace-status">{{ step.status }}</span>
          </div>

          <h4 class="trace-item-title">{{ step.title }}</h4>
          <p v-if="step.summary" class="trace-summary">{{ step.summary }}</p>

          <div v-if="step.argsPreview" class="trace-block">
            <span class="trace-label">输入</span>
            <p>{{ step.argsPreview }}</p>
          </div>

          <div v-if="step.resultPreview" class="trace-block">
            <span class="trace-label">输出</span>
            <p>{{ step.resultPreview }}</p>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  steps: {
    type: Array,
    default: () => [],
  },
})

const runningCount = computed(() => props.steps.filter(step => step.status === 'running').length)

function kindLabel(kind) {
  const labels = {
    thinking: '思考',
    triage: '分诊',
    tool: '工具调用',
  }
  return labels[kind] || '步骤'
}
</script>

<style scoped>
.trace-panel {
  width: min(820px, 100%);
  margin: 6px 0 18px;
  padding: 18px 20px;
  border-radius: 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(250, 246, 236, 0.9));
  border: 1px solid rgba(84, 70, 48, 0.08);
  box-shadow: 0 18px 40px rgba(88, 69, 38, 0.08);
  align-self: flex-start;
}

.trace-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.trace-kicker {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #8d7a58;
}

.trace-title {
  margin-top: 4px;
  font-size: 18px;
  line-height: 1.35;
  color: #2f2618;
}

.trace-badge {
  flex-shrink: 0;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(149, 236, 105, 0.22);
  color: #355226;
  font-size: 12px;
  font-weight: 700;
}

.trace-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trace-item {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 12px;
}

.trace-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.trace-dot {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  margin-top: 4px;
  background: #d6c6a5;
  border: 2px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 3px rgba(214, 198, 165, 0.28);
}

.trace-line {
  flex: 1;
  width: 2px;
  margin-top: 6px;
  background: linear-gradient(180deg, rgba(214, 198, 165, 0.7), rgba(214, 198, 165, 0));
}

.trace-item:last-child .trace-line {
  opacity: 0;
}

.trace-card {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  border: 1px solid rgba(84, 70, 48, 0.08);
}

.trace-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.trace-kind {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8d7a58;
}

.trace-status {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(141, 122, 88, 0.12);
  color: #705f46;
}

.trace-status.running {
  background: rgba(241, 181, 71, 0.18);
  color: #926517;
}

.trace-status.done {
  background: rgba(149, 236, 105, 0.18);
  color: #355226;
}

.trace-item-title {
  font-size: 15px;
  color: #302719;
  line-height: 1.45;
}

.trace-summary {
  margin-top: 6px;
  color: #5f513d;
  font-size: 13px;
  line-height: 1.6;
}

.trace-block {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(247, 241, 228, 0.78);
}

.trace-label {
  display: inline-block;
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8d7a58;
}

.trace-block p {
  font-size: 13px;
  line-height: 1.6;
  color: #514432;
}

.trace-thinking .trace-dot {
  background: #cdb68d;
  box-shadow: 0 0 0 3px rgba(205, 182, 141, 0.24);
}

.trace-triage .trace-dot {
  background: #87b7df;
  box-shadow: 0 0 0 3px rgba(135, 183, 223, 0.22);
}

.trace-tool .trace-dot {
  background: #95ec69;
  box-shadow: 0 0 0 3px rgba(149, 236, 105, 0.2);
}

.status-running .trace-card {
  border-color: rgba(241, 181, 71, 0.24);
  box-shadow: 0 12px 24px rgba(223, 168, 63, 0.08);
}

@media (max-width: 768px) {
  .trace-panel {
    width: 100%;
    padding: 16px;
    border-radius: 20px;
  }

  .trace-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
