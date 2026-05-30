<template>
  <div class="chat-layout">
    <AppSidebar
      :conversations="chatStore.conversations"
      :active-thread-id="chatStore.activeThreadId"
      @new-chat="handleNewChat"
      @select="handleSelectThread"
    />

    <main class="chat-main">
      <header class="chat-topbar">
        <div class="topbar-left">
          <button class="btn-sidebar-toggle" @click="showSidebar = !showSidebar" aria-label="Toggle sidebar">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M3 5h14M3 10h14M3 15h10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </button>
          <h2 class="chat-title">{{ chatStore.currentTitle }}</h2>
        </div>
      </header>

      <div class="chat-messages" ref="messagesEl">
        <PetProfileCard :profile="chatStore.petProfile" />

        <WelcomeScreen
          v-if="!chatStore.activeThreadId && chatStore.messages.length === 0 && !chatStore.isStreaming"
          @send-prompt="text => handleSend({ text, imageFile: null })"
        />

        <template v-for="(msg, index) in chatStore.messages" :key="index">
          <MessageBubble
            :message="msg"
            :is-streaming="Boolean(msg._placeholder && chatStore.isStreaming)"
          />

          <!-- 评估卡 / 报告嵌入到对应的 assistant 消息后面,成为对话历史的一部分 -->
          <AssessmentCard
            v-if="msg.assessment"
            :assessment="msg.assessment"
          />

          <MarkdownReport
            v-if="msg.report"
            :markdown="msg.report"
          />

          <AgentTracePanel
            v-if="shouldRenderTraceAfter(index, msg)"
            :steps="chatStore.agentTrace"
          />
        </template>

        <div v-if="chatStore.error" class="error-banner">
          <span>{{ chatStore.error }}</span>
        </div>

        <ThinkingDots v-if="chatStore.thinking && !chatStore.streamingText && chatStore.agentTrace.length === 0" />
      </div>

      <ChatInput
        ref="chatInputEl"
        :disabled="chatStore.isStreaming"
        @send="handleSend"
      />
    </main>

    <transition name="overlay">
      <div v-if="showSidebar" class="sidebar-overlay" @click="showSidebar = false">
        <div class="sidebar-drawer" @click.stop>
          <AppSidebar
            :conversations="chatStore.conversations"
            :active-thread-id="chatStore.activeThreadId"
            @new-chat="handleNewChat"
            @select="handleSelectThread"
          />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import AppSidebar from '../components/AppSidebar.vue'
import AgentTracePanel from '../components/AgentTracePanel.vue'
import MessageBubble from '../components/MessageBubble.vue'
import ChatInput from '../components/ChatInput.vue'
import WelcomeScreen from '../components/WelcomeScreen.vue'
import ThinkingDots from '../components/ThinkingDots.vue'
import PetProfileCard from '../components/PetProfileCard.vue'
import AssessmentCard from '../components/AssessmentCard.vue'
import MarkdownReport from '../components/MarkdownReport.vue'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()
const messagesEl = ref(null)
const chatInputEl = ref(null)
const showSidebar = ref(false)

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

function shouldRenderTraceAfter(index, msg) {
  const isLatestUserMessage = msg.sender === 'user' && index === chatStore.messages.length - 2
  return isLatestUserMessage && chatStore.agentTrace.length > 0
}

watch(() => chatStore.streamingText, scrollToBottom)
watch(() => chatStore.messages.length, scrollToBottom)
watch(() => chatStore.agentTrace.length, scrollToBottom)

async function handleSend({ text, imageFile }) {
  await chatStore.sendMessage(text, imageFile)
  chatStore.loadHistory()
}

function handleNewChat() {
  chatStore.resetSession()
  router.push('/')
  showSidebar.value = false
}

async function handleSelectThread(threadId) {
  chatStore.resetSession()
  chatStore.activeThreadId = threadId
  await chatStore.loadThread(threadId)
  router.push(`/chat/${threadId}`)
  showSidebar.value = false
}

watch(() => route.params.threadId, async id => {
  if (id && id !== chatStore.activeThreadId) {
    await handleSelectThread(id)
  }
}, { immediate: true })
</script>

<style scoped>
.chat-layout {
  height: 100%;
  display: flex;
  position: relative;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
  z-index: 1;
}

.chat-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: rgba(255, 251, 243, 0.94);
  border-bottom: 1px solid rgba(84, 70, 48, 0.08);
  flex-shrink: 0;
  backdrop-filter: blur(14px);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.btn-sidebar-toggle {
  display: none;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: transparent;
  transition: background var(--duration-fast);
}

.btn-sidebar-toggle:hover {
  background: rgba(0, 0, 0, 0.04);
}

@media (max-width: 768px) {
  .btn-sidebar-toggle {
    display: flex;
  }
}

.chat-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.error-banner {
  width: min(820px, 100%);
  padding: 14px 18px;
  background: var(--red-100);
  border: 1px solid var(--red-300);
  border-radius: 18px;
  color: var(--red-700);
  font-size: 13px;
  margin-top: 6px;
}

.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 100;
  backdrop-filter: blur(2px);
}

@media (max-width: 768px) {
  .sidebar-overlay {
    display: block;
  }
}

.sidebar-drawer {
  width: 280px;
  height: 100%;
}

.overlay-enter-active {
  transition: opacity var(--duration-normal) var(--ease-out);
}

.overlay-leave-active {
  transition: opacity 200ms var(--ease-out);
}

.overlay-enter-from,
.overlay-leave-to {
  opacity: 0;
}
</style>
