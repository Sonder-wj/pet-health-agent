const BASE = ''

function getToken() {
  return localStorage.getItem('token')
}

export async function apiPost(path, body) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  // FormData or JSON
  if (body instanceof FormData) {
    const res = await fetch(`${BASE}${path}`, { method: 'POST', headers, body })
    return res
  }
  headers['Content-Type'] = 'application/json'
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  return res
}

export async function apiGet(path) {
  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(`${BASE}${path}`, { headers })
  return res
}

export function streamChat({ query, sessionId, imageFile, signal }) {
  const form = new FormData()
  form.append('query', query)
  if (sessionId) form.append('session_id', sessionId)
  if (imageFile) form.append('image', imageFile)

  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  return fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers,
    body: form,
    signal,
  })
}

export function streamResume({ sessionId, query, signal }) {
  const form = new FormData()
  form.append('query', query)

  const headers = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  return fetch(`${BASE}/api/chat/${sessionId}/resume`, {
    method: 'POST',
    headers,
    body: form,
    signal,
  })
}
