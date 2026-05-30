const BASE = ''

function getToken() {
  return localStorage.getItem('token')
}

/**
 * 401 = token 过期 / 无效。统一登出 + 跳 /login,避免页面卡在"服务端错误"banner。
 * 动态 import 避免与 router/stores 的循环依赖。
 */
async function handle401(res, path) {
  if (res.status !== 401) return res
  // 登录端点本身的 401 是"用户名密码错",不该触发自动登出
  if (path && path.includes('/auth/')) return res
  try {
    const { useAuthStore } = await import('../stores/auth')
    const router = (await import('../router')).default
    const auth = useAuthStore()
    auth.logout()
    router.push('/login')
  } catch (_) {
    // 极端情况下 store/router 还没装好,静默退化即可
  }
  return res
}

export async function apiPost(path, body) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  // FormData or JSON
  if (body instanceof FormData) {
    const res = await fetch(`${BASE}${path}`, { method: 'POST', headers, body })
    return handle401(res, path)
  }
  headers['Content-Type'] = 'application/json'
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  return handle401(res, path)
}

export async function apiGet(path) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}${path}`, { headers })
  return handle401(res, path)
}

export async function streamChat({ query, sessionId, imageFile, signal }) {
  const form = new FormData()
  form.append('query', query)
  if (sessionId) form.append('session_id', sessionId)
  if (imageFile) form.append('image', imageFile)

  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers,
    body: form,
    signal,
  })
  return handle401(res, '/api/chat')
}

export async function streamResume({ sessionId, query, imageFile, signal }) {
  const form = new FormData()
  form.append('query', query)
  if (imageFile) form.append('image', imageFile)

  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}/api/chat/${sessionId}/resume`, {
    method: 'POST',
    headers,
    body: form,
    signal,
  })
  return handle401(res, '/api/chat/resume')
}
