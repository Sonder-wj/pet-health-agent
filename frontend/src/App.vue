<template>
  <router-view v-slot="{ Component }">
    <transition name="page" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
import { onMounted } from 'vue'
import { useChatStore } from './stores/chat'

const chatStore = useChatStore()

onMounted(() => {
  chatStore.loadHistory()
})
</script>
