import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const clearSession = useCallback(() => {
    localStorage.removeItem('at')
    localStorage.removeItem('rt')
    setUser(null)
  }, [])

  useEffect(() => {
    const t = localStorage.getItem('at')
    if (!t) {
      setLoading(false)
      return
    }
    api
      .get('/api/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => clearSession())
      .finally(() => setLoading(false))
  }, [clearSession])

  // Если обновить токен не удалось, client.js сообщает об этом событием.
  useEffect(() => {
    window.addEventListener('auth:unauthorized', clearSession)
    return () => window.removeEventListener('auth:unauthorized', clearSession)
  }, [clearSession])

  async function login(email, password) {
    const res = await api.post('/api/auth/login', { email, password })
    localStorage.setItem('at', res.data.access)
    localStorage.setItem('rt', res.data.refresh)
    const me = await api.get('/api/auth/me')
    setUser(me.data)
    return res.data
  }

  async function register(email, password) {
    const res = await api.post('/api/auth/register', { email, password })
    localStorage.setItem('at', res.data.access)
    localStorage.setItem('rt', res.data.refresh)
    const me = await api.get('/api/auth/me')
    setUser(me.data)
    return res.data
  }

  async function logout() {
    const rt = localStorage.getItem('rt')
    try {
      await api.post('/api/auth/logout', { refresh: rt })
    } catch {
      // сессия всё равно очищается локально
    }
    clearSession()
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
