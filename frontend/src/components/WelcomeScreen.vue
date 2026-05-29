<template>
  <div class="welcome">
    <div class="welcome-illustration">
      <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <!-- Dog silhouette -->
        <ellipse cx="75" cy="100" rx="45" ry="35" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <circle cx="55" cy="70" r="22" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <ellipse cx="38" cy="48" rx="12" ry="16" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <ellipse cx="72" cy="48" rx="12" ry="16" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <circle cx="49" cy="66" r="2.5" fill="var(--amber-700)"/>
        <circle cx="61" cy="66" r="2.5" fill="var(--amber-700)"/>
        <ellipse cx="55" cy="74" rx="3" ry="2" fill="var(--amber-500)"/>
        <!-- Cat silhouette -->
        <ellipse cx="140" cy="100" rx="35" ry="30" fill="var(--blue-100)" stroke="var(--blue-300)" stroke-width="2"/>
        <circle cx="140" cy="65" r="18" fill="var(--blue-100)" stroke="var(--blue-300)" stroke-width="2"/>
        <path d="M128 50l-8-16M152 50l8-16" stroke="var(--blue-300)" stroke-width="2" stroke-linecap="round"/>
        <circle cx="134" cy="62" r="2" fill="var(--blue-700)"/>
        <circle cx="146" cy="62" r="2" fill="var(--blue-700)"/>
        <ellipse cx="140" cy="68" rx="2.5" ry="1.5" fill="var(--blue-500)"/>
        <!-- Heart between them -->
        <path d="M108 60c-3-4-8-4-10 0s0 8 10 14c10-6 12-10 10-14s-7-4-10 0z" fill="var(--red-300)" opacity="0.6"/>
        <!-- Ground line -->
        <path d="M20 130h160" stroke="var(--border)" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="4 6"/>
      </svg>
    </div>
    <h2 class="welcome-title">你好，我是小宠</h2>
    <p class="welcome-desc">描述宠物的症状或上传照片，我来帮你评估并提供专业建议</p>
    <div class="quick-prompts">
      <button
        v-for="p in prompts"
        :key="p.text"
        class="prompt-chip"
        @click="$emit('sendPrompt', p.text)"
      >
        {{ p.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineEmits(['sendPrompt'])

const prompts = [
  { label: '🐶 狗狗呕吐怎么办', text: '我家狗狗今天吐了两次，精神还好，需要去医院吗？' },
  { label: '🐱 猫咪不太精神', text: '猫咪这两天不太吃东西，总是趴着，是怎么回事？' },
  { label: '💊 宠物用药咨询', text: '宠物药怎么判断剂量？需要注意什么？' },
  { label: '🔍 症状是什么病', text: '我家宠物皮肤上有红斑，还掉毛，可能是什么问题？' },
]
</script>

<style scoped>
.welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  animation: fade-in 600ms var(--ease-out);
}
@keyframes fade-in {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.welcome-illustration svg {
  width: 200px;
  height: 140px;
  display: block;
  margin-bottom: 24px;
  animation: float-slow 5s ease-in-out infinite;
}
@keyframes float-slow {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.welcome-title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}
.welcome-desc {
  font-size: 14px;
  color: var(--text-secondary);
  max-width: 360px;
  text-align: center;
  line-height: 1.6;
}

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 28px;
  max-width: 480px;
  justify-content: center;
}
.prompt-chip {
  padding: 10px 18px;
  border-radius: var(--radius-full);
  background: var(--bg-card);
  border: 1px solid var(--border);
  font-size: 13px;
  color: var(--text-primary);
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
}
.prompt-chip:hover {
  border-color: var(--green-300);
  background: var(--green-100);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
</style>
