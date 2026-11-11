import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

const AUTH_ENDPOINTS = [
  '/api/auth/login',
  '/api/auth/register',
  '/api/auth/refresh',
]

function isAuthEndpoint(url = '') {
  return AUTH_ENDPOINTS.some((path) => url.includes(path))
}

// Запрос токена напрямую из localStorage — без гонки с инициализацией AuthContext.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('at')
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

let refreshPromise = null

// Обновление access-токена по refresh-токену (одна попытка на все параллельные 401).
function refreshAccessToken() {
  const refresh = localStorage.getItem('rt')
  if (!refresh) return Promise.resolve(null)

  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_BASE}/api/auth/refresh`, { refresh })
      .then((res) => {
        localStorage.setItem('at', res.data.access)
        return res.data.access
      })
      .catch(() => {
        localStorage.removeItem('at')
        localStorage.removeItem('rt')
        return null
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const status = error.response?.status

    if (status === 401 && original && !original._retry && !isAuthEndpoint(original.url)) {
      original._retry = true
      const token = await refreshAccessToken()
      if (token) {
        original.headers = original.headers || {}
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      }
      window.dispatchEvent(new Event('auth:unauthorized'))
    }

    return Promise.reject(error)
  },
)

export default api
