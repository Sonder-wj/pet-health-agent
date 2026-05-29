<template>
  <div class="login-page">
    <!-- Decorative botanical elements -->
    <div class="deco deco-1" />
    <div class="deco deco-2" />
    <div class="deco deco-3" />

    <div class="login-card">
      <div class="card-header">
        <div class="logo-mark">
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="32" cy="28" r="18" fill="var(--amber-100)" stroke="var(--amber-500)" stroke-width="2"/>
            <circle cx="24" cy="22" r="2.5" fill="var(--amber-700)"/>
            <circle cx="40" cy="22" r="2.5" fill="var(--amber-700)"/>
            <ellipse cx="32" cy="30" rx="3" ry="2" fill="var(--amber-700)"/>
            <path d="M32 46c-4 0-8-2-10-4" stroke="var(--amber-500)" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M20 12c-3-1-6 0-7 3s1 6 4 7" stroke="var(--green-500)" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M44 12c3-1 6 0 7 3s-1 6-4 7" stroke="var(--green-500)" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <h1>小宠</h1>
        <p class="subtitle">AI 宠物健康助手</p>
      </div>

      <div class="tabs">
        <button
          :class="['tab', { active: mode === 'login' }]"
          @click="mode = 'login'"
        >登录</button>
        <button
          :class="['tab', { active: mode === 'register' }]"
          @click="mode = 'register'"
        >注册</button>
      </div>

      <form @submit.prevent="handleSubmit" class="form">
        <div class="field">
          <label>用户名</label>
          <input
            v-model="username"
            type="text"
            placeholder="请输入用户名"
            required
            minlength="2"
            autocomplete="username"
          />
        </div>

        <div v-if="mode === 'register'" class="field">
          <label>邮箱</label>
          <input
            v-model="email"
            type="email"
            placeholder="请输入邮箱"
            required
            autocomplete="email"
          />
        </div>

        <div class="field">
          <label>密码</label>
          <input
            v-model="password"
            type="password"
            placeholder="请输入密码"
            required
            minlength="6"
            autocomplete="current-password"
          />
        </div>

        <p v-if="errMsg" class="error-msg">{{ errMsg }}</p>

        <button type="submit" class="btn-submit" :disabled="loading">
          <span v-if="!loading">{{ mode === 'login' ? '登录' : '注册' }}</span>
          <span v-else class="spinner" />
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { apiPost } from '../api/client'

const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const username = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)
const errMsg = ref('')

async function handleSubmit() {
  errMsg.value = ''
  loading.value = true
  try {
    const endpoint = mode.value === 'login' ? '/api/auth/login' : '/api/auth/register'
    const body = new FormData()
    body.append('username', username.value)
    body.append('password', password.value)
    if (mode.value === 'register') body.append('email', email.value)

    const res = await apiPost(endpoint, body)
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || '请求失败')
    }
    const data = await res.json()
    auth.setAuth(data.token, data.user)
    router.push('/')
  } catch (e) {
    errMsg.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

/* Decorative organic blobs */
.deco {
  position: absolute;
  border-radius: 50%;
  opacity: 0.15;
  z-index: 0;
}
.deco-1 {
  width: 420px; height: 420px;
  background: radial-gradient(circle, var(--green-300), transparent 70%);
  top: -120px; left: -100px;
  animation: float 8s ease-in-out infinite;
}
.deco-2 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, var(--amber-300), transparent 70%);
  bottom: -80px; right: -60px;
  animation: float 10s ease-in-out infinite reverse;
}
.deco-3 {
  width: 200px; height: 200px;
  background: radial-gradient(circle, var(--blue-300), transparent 70%);
  top: 50%; left: 60%;
  animation: float 7s ease-in-out infinite 2s;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

.login-card {
  position: relative;
  z-index: 1;
  width: 400px;
  background: var(--bg-card);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg), 0 0 0 1px var(--border-light);
  padding: 40px 36px 36px;
}

.card-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-mark svg {
  width: 64px;
  height: 64px;
  display: block;
  margin: 0 auto 8px;
}

h1 {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}
.subtitle {
  font-size: 14px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.tabs {
  display: flex;
  gap: 4px;
  background: var(--bg-app);
  border-radius: var(--radius-md);
  padding: 4px;
  margin-bottom: 24px;
}
.tab {
  flex: 1;
  padding: 10px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  background: transparent;
  transition: all var(--duration-fast) var(--ease-out);
}
.tab.active {
  color: var(--text-primary);
  background: var(--bg-card);
  box-shadow: var(--shadow-sm);
}

.field {
  margin-bottom: 16px;
}
.field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.field input {
  width: 100%;
  padding: 12px 16px;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 15px;
  background: var(--bg-input);
  transition: border-color var(--duration-fast);
}
.field input:focus {
  border-color: var(--green-500);
}
.field input::placeholder {
  color: #c5bfad;
}

.error-msg {
  font-size: 13px;
  color: var(--red-500);
  margin-bottom: 8px;
}

.btn-submit {
  width: 100%;
  padding: 13px;
  border-radius: var(--radius-md);
  background: var(--green-500);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  margin-top: 8px;
  transition: background var(--duration-fast), transform var(--duration-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
}
.btn-submit:hover:not(:disabled) {
  background: var(--green-700);
  transform: translateY(-1px);
}
.btn-submit:active:not(:disabled) {
  transform: translateY(0);
}
.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  width: 20px; height: 20px;
  border: 2.5px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
