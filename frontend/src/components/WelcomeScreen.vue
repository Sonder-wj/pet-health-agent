<template>
  <div class="welcome">
    <div class="welcome-illustration">
      <svg viewBox="0 0 200 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <!-- 食盆 -->
        <ellipse cx="100" cy="125" rx="60" ry="12" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <path d="M40 125 Q40 95 100 95 Q160 95 160 125" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <!-- 食物 -->
        <circle cx="80" cy="100" r="6" fill="var(--green-300)"/>
        <circle cx="100" cy="98" r="5" fill="var(--red-300)"/>
        <circle cx="118" cy="100" r="6" fill="var(--amber-500)"/>
        <circle cx="90" cy="106" r="4" fill="var(--blue-300)"/>
        <circle cx="110" cy="106" r="4" fill="var(--green-500)"/>
        <!-- 狗 -->
        <circle cx="55" cy="60" r="20" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <ellipse cx="42" cy="42" rx="10" ry="14" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <ellipse cx="68" cy="42" rx="10" ry="14" fill="var(--amber-100)" stroke="var(--amber-300)" stroke-width="2"/>
        <circle cx="49" cy="58" r="2" fill="var(--amber-700)"/>
        <circle cx="61" cy="58" r="2" fill="var(--amber-700)"/>
        <ellipse cx="55" cy="65" rx="2.5" ry="1.6" fill="var(--amber-500)"/>
        <!-- 猫 -->
        <circle cx="150" cy="60" r="18" fill="var(--blue-100)" stroke="var(--blue-300)" stroke-width="2"/>
        <path d="M138 47l-7-14M162 47l7-14" stroke="var(--blue-300)" stroke-width="2" stroke-linecap="round"/>
        <circle cx="144" cy="58" r="1.8" fill="var(--blue-700)"/>
        <circle cx="156" cy="58" r="1.8" fill="var(--blue-700)"/>
        <ellipse cx="150" cy="64" rx="2" ry="1.3" fill="var(--blue-500)"/>
        <!-- 营养符号 ❤ -->
        <path d="M100 30c-3-4-8-4-10 0s0 8 10 14c10-6 12-10 10-14s-7-4-10 0z" fill="var(--red-300)" opacity="0.6"/>
      </svg>
    </div>
    <h2 class="welcome-title">你好,我是小宠营养师</h2>
    <p class="welcome-desc">告诉我你家宝贝的档案与饮食,我用 USDA + AAFCO 数据给出结构化营养评估</p>
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
  {
    label: '🐶 10kg 拉布拉多自制饮食',
    text: '我家 10kg 拉布拉多,3 岁,已绝育,无疾病。每天喂 300g 鸡胸肉 + 100g 白米饭 + 50g 南瓜,营养够吗?',
  },
  {
    label: '🐱 肾病猫商品粮评估',
    text: '我家 4kg 老猫,8 岁,绝育,确诊慢性肾病。每天吃 60g 某商品粮(粗蛋白 32%、粗脂肪 14%、粗纤维 3%、水分 10%、kcal/kg 4000),适合吗?',
  },
  {
    label: '📷 包装照解析',
    text: '我刚上传了商品粮包装照,帮我看看营养成分。',
  },
  {
    label: '⚠️ 钙磷比检查',
    text: '听说自制肉饭钙不够,怎么补?给狗喂全鸡胸肉会怎样?',
  },
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
  max-width: 380px;
  text-align: center;
  line-height: 1.6;
}

.quick-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 28px;
  max-width: 540px;
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
