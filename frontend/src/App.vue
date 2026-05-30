<template>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import { watch } from 'vue'
import { useChatStore } from './stores/chat'
import { useAuthStore } from './stores/auth'

const chatStore = useChatStore()
const auth = useAuthStore()

// 跟随登录状态切换:
// - 登入(包括首次进入页面就有 token) → 拉取当前账号的会话列表
// - 登出 → 立刻清空侧栏,防止上一个账号的记录漏到下一个账号
watch(
  () => auth.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) {
      chatStore.loadHistory()
    } else {
      chatStore.clearAccountData()
    }
  },
  { immediate: true },
)
</script>
