import { createContext, useContext, useState, useEffect } from 'react'

const TOKEN_KEY = 'lams_token'
const USER_KEY = 'lams_user'

export const authStorage = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getUser: () => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY))
    } catch {
      return null
    }
  },
  set: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  },
}

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(authStorage.getUser())
  const [token, setToken] = useState(authStorage.getToken())
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setUser(authStorage.getUser())
    setToken(authStorage.getToken())
  }, [])

  const login = (tokenData) => {
    const userData = {
      username: tokenData.username,
      fullName: tokenData.full_name,
      role: tokenData.role,
    }
    authStorage.set(tokenData.access_token, userData)
    setToken(tokenData.access_token)
    setUser(userData)
  }

  const logout = () => {
    authStorage.clear()
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
