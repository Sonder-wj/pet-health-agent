<template>
  <div v-if="message" :class="['message-row', message.sender]">
    <div :class="['bubble', message.sender, { streaming: isStreaming }]">
      <div class="bubble-avatar">
        <template v-if="message.sender === 'user'">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="7" r="4" stroke="currentColor" stroke-width="1.5" />
            <path
              d="M3 18c0-4 3.1-7 7-7s7 3 7 7"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
            />
          </svg>
        </template>
        <template v-else>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="7" r="4.5" fill="var(--amber-100)" stroke="var(--amber-500)" stroke-width="1.3" />
            <circle cx="7.5" cy="5.5" r="0.8" fill="var(--amber-700)" />
            <circle cx="12.5" cy="5.5" r="0.8" fill="var(--amber-700)" />
            <ellipse cx="10" cy="8" rx="1.2" ry="0.7" fill="var(--amber-700)" />
          </svg>
        </template>
      </div>

      <div class="bubble-content">
        <div
          v-if="message.type === 'text' || message._placeholder"
          class="bubble-text"
          v-html="renderContent(message.content)"
        />
        <div v-else-if="message.type === 'image'" class="bubble-image">
          <img :src="message.content" alt="上传的图片" loading="lazy" />
        </div>

        <span v-if="!isStreaming" class="bubble-time">{{ formatTime(message.time) }}</span>
        <span v-if="isStreaming" class="cursor-blink">|</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  message: Object,
  isStreaming: { type: Boolean, default: false },
})

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function renderContent(text) {
  if (!text) return ''

  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .split('\n')
    .map(line => {
      const trimmedLine = line.trim()
      const formattedLine = trimmedLine.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

      if (!trimmedLine) return '<div class="md-space"></div>'
      if (/^###\s/.test(formattedLine)) return `<h3 class="md-h3">${formattedLine.slice(4)}</h3>`
      if (/^-\s/.test(formattedLine)) return `<div class="md-li">${formattedLine.slice(2)}</div>`
      return `<p class="md-p">${formattedLine}</p>`
    })
    .join('')
}
</script>

<style scoped>
.message-row {
  display: flex;
  width: 100%;
  margin-bottom: 6px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-row.assistant {
  justify-content: flex-start;
}

.bubble {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  max-width: min(78%, 840px);
  animation: msg-in var(--duration-normal) var(--ease-out);
}

@keyframes msg-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.bubble-avatar {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: #f7f1e4;
  border: 1px solid rgba(84, 70, 48, 0.08);
  color: var(--text-secondary);
  order: 0;
}

.message-row.user .bubble-avatar {
  order: 1;
  background: #d8f0cb;
  color: #426438;
}

.bubble-content {
  position: relative;
  padding: 12px 16px 10px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.58;
  word-break: break-word;
}

.message-row.user .bubble-content {
  background: #95ec69;
  border: 1px solid rgba(76, 130, 55, 0.12);
  border-bottom-right-radius: 6px;
  color: #24311d;
}

.message-row.assistant .bubble-content {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(84, 70, 48, 0.08);
  box-shadow: var(--shadow-sm);
  border-bottom-left-radius: 6px;
}

.bubble-image img {
  display: block;
  max-width: min(320px, 100%);
  border-radius: 14px;
}

.bubble-text {
  white-space: normal;
}

.bubble-text :deep(.md-p) {
  margin: 0;
}

.bubble-text :deep(.md-p + .md-p) {
  margin-top: 4px;
}

.bubble-text :deep(.md-space) {
  height: 8px;
}

.bubble-text :deep(.md-h3) {
  margin: 2px 0 4px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.bubble-text :deep(.md-li) {
  position: relative;
  margin: 2px 0;
  padding-left: 14px;
}

.bubble-text :deep(.md-li)::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--green-500);
}

.bubble-time {
  display: block;
  margin-top: 6px;
  font-size: 10px;
  color: var(--text-secondary);
  opacity: 0.6;
  text-align: right;
}

.cursor-blink {
  animation: blink 0.8s step-end infinite;
  color: var(--green-500);
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0;
  }
}

.streaming .bubble-content {
  border-color: var(--green-300);
}

@media (max-width: 768px) {
  .bubble {
    max-width: 88%;
  }
}
</style>
