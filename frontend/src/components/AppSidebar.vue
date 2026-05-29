<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-logo">
        <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="20" cy="17" r="11" fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.25)" stroke-width="1.5"/>
          <circle cx="15" cy="13" r="1.6" fill="var(--text-sidebar)"/>
          <circle cx="25" cy="13" r="1.6" fill="var(--text-sidebar)"/>
          <ellipse cx="20" cy="19" rx="2" ry="1.2" fill="var(--text-sidebar)"/>
          <path d="M20 29c-3 0-5-1.5-6.5-3" stroke="rgba(255,255,255,0.3)" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="sidebar-brand-wrap">
        <span class="sidebar-brand">小宠营养师</span>
        <span class="sidebar-tagline">AI 宠物营养评估</span>
      </div>
    </div>

    <button class="btn-new-chat" @click="$emit('newChat')">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M9 3v12M3 9h12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      新对话
    </button>

    <div class="sidebar-section">
      <span class="section-label">对话记录</span>
      <div class="conversation-list">
        <button
          v-for="conv in conversations"
          :key="conv.thread_id"
          :class="['conv-item', { active: conv.thread_id === activeThreadId }]"
          @click="$emit('select', conv.thread_id)"
        >
          <span class="conv-icon">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M2 2h10v8H4L2 12V2z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/></svg>
          </span>
          <span class="conv-title">{{ conv.title }}</span>
          <span class="conv-time">{{ formatDate(conv.updated_at || conv.created_at) }}</span>
        </button>
        <p v-if="conversations.length === 0" class="empty-hint">暂无对话记录</p>
      </div>
    </div>

    <div class="sidebar-footer">
      <a href="/login" class="footer-link" @click.prevent="handleLogout">退出登录</a>
    </div>
  </aside>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const props = defineProps({
  conversations: Array,
  activeThreadId: String,
})

defineEmits(['newChat', 'select'])

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now - d
  if (diff < 86400000) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.sidebar {
  width: 260px;
  height: 100%;
  background: var(--bg-sidebar);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  color: var(--text-sidebar);
}
@media (max-width: 768px) {
  .sidebar { width: 100%; }
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 18px 12px;
}
.sidebar-logo svg {
  width: 36px; height: 36px;
  display: block;
}
.sidebar-brand-wrap {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.sidebar-brand {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 500;
  color: #e0dbcc;
}
.sidebar-tagline {
  font-size: 10px;
  color: var(--text-sidebar-muted);
  letter-spacing: 0.04em;
}

.btn-new-chat {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 14px;
  padding: 10px 16px;
  background: rgba(255,255,255,0.08);
  color: var(--text-sidebar);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  border: 1px solid rgba(255,255,255,0.08);
  transition: all var(--duration-fast) var(--ease-out);
}
.btn-new-chat:hover {
  background: rgba(255,255,255,0.14);
  color: #fff;
}

.sidebar-section {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.section-label {
  display: block;
  padding: 8px 18px 6px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-sidebar-muted);
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.conv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 18px;
  background: transparent;
  color: var(--text-sidebar);
  font-size: 13px;
  text-align: left;
  border-radius: 0;
  transition: background var(--duration-fast);
}
.conv-item:hover { background: var(--bg-sidebar-hover); }
.conv-item.active { background: var(--bg-sidebar-hover); color: #e8e3d4; }
.conv-icon {
  flex-shrink: 0;
  opacity: 0.5;
}
.conv-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conv-time {
  font-size: 11px;
  color: var(--text-sidebar-muted);
  flex-shrink: 0;
}
.empty-hint {
  padding: 16px 18px;
  font-size: 12px;
  color: var(--text-sidebar-muted);
}

.sidebar-footer {
  padding: 12px 18px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.footer-link {
  font-size: 12px;
  color: var(--text-sidebar-muted);
  cursor: pointer;
}
.footer-link:hover { color: var(--text-sidebar); }
</style>
