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
    meta: { requiresAuth: false },
  },
  {
    path: '/chat/:threadId',
    name: 'ChatThread',
    component: () => import('../views/Chat.vue'),
    meta: { requiresAuth: false },
  },
]

const router = createRouter({
  history: createWebHashHistory('/static/'),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return '/login'
  }
})

export default router
