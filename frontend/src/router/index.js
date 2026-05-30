import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'Chat',
    component: () => import('../views/Chat.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/chat/:threadId',
    name: 'ChatThread',
    component: () => import('../views/Chat.vue'),
    meta: { requiresAuth: true },
  },
]

// dev 走 '/' 根路径,build 走 '/static/'(和 vite.config.js base 一致)
const router = createRouter({
  history: createWebHashHistory(import.meta.env.PROD ? '/static/' : '/'),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return '/login'
  }
})

export default router
