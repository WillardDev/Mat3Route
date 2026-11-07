// One file of fetch functions for the MatatuPulse API. JWT lives in localStorage.

const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '') + '/api'
const KEY = 'mp_auth'

export class ApiError extends Error {
  constructor(status, data) {
    super((data && data.detail) || `Request failed (${status})`)
    this.status = status
    this.data = data
  }
}

export function getAuth() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || null
  } catch {
    return null
  }
}

export function setAuth(auth) {
  try {
    if (auth) localStorage.setItem(KEY, JSON.stringify(auth))
    else localStorage.removeItem(KEY)
  } catch {
    /* storage unavailable */
  }
  window.dispatchEvent(new Event('mp-auth'))
}

async function refreshAccess() {
  const auth = getAuth()
  if (!auth?.refresh) return false
  const res = await fetch(`${BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: auth.refresh }),
  })
  if (!res.ok) return false
  const data = await res.json()
  setAuth({ ...auth, access: data.access, refresh: data.refresh || auth.refresh })
  return true
}

async function request(path, { method = 'GET', body, auth = true, retry = true } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = auth ? getAuth()?.access : null
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401 && auth && token && retry) {
    if (await refreshAccess()) return request(path, { method, body, auth, retry: false })
    setAuth(null)
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}

// --- auth
export const requestOtp = (phone) => request('/auth/otp/request', { method: 'POST', body: { phone }, auth: false })
export const verifyOtp = (phone, code) => request('/auth/otp/verify', { method: 'POST', body: { phone, code }, auth: false })

// --- routes
export const getRoutes = (search = '') =>
  request(`/routes${search ? `?search=${encodeURIComponent(search)}` : ''}`)
export const getRoute = (id) => request(`/routes/${id}`)
export const toggleSubscribe = (id) => request(`/routes/${id}/subscribe`, { method: 'POST' })

// --- reports + votes
export const createReport = (payload) => request('/reports', { method: 'POST', body: payload })
export const vote = (eventId, kind) => request(`/events/${eventId}/vote`, { method: 'POST', body: { kind } })

// --- signal (public, but sends the token so staff see Replay)
export const getSignal = () => request('/signal', { auth: !!getAuth()?.access })
export const replayDemo = () => request('/demo/replay', { method: 'POST' })
