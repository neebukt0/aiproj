import { createContext, useContext, useEffect, useState } from 'react'
import api, { setTokenGetter } from '../api/client'

const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const token = user ? localStorage.getItem('at') : null

  useEffect(() => {
    setTokenGetter(() => localStorage.getItem('at'))
  }, [])

  useEffect(() => {
    const t = localStorage.getItem('at')
    if (!t) {
      setUser(null)
      setLoading(false)
      return
    }
    api
      .get('/api/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem('at')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  async function login(email, password) {
    const res = await api.post('/api/auth/login', { email, password })
    localStorage.setItem('at', res.data.access)
    localStorage.setItem('rt', res.data.refresh)
    const me = await api.get('/api/auth/me')
    setUser(me.data)
    return res.data
  }

  async function register(email, password, role = 'client') {
    const res = await api.post('/api/auth/register', { email, password, role })
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
    } catch (e) {
      // ignore
    }
    localStorage.removeItem('at')
    localStorage.removeItem('rt')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, token, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}