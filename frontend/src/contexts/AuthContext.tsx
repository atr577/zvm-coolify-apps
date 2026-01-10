import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import api from '@/services/api'

interface User {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  role: string
  can_create_workspace: boolean
  created_at: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  isAuthenticated: boolean
  isAdmin: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string, inviteToken?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('auth_token')
  })
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
      fetchUser()
    } else {
      setIsLoading(false)
    }
  }, [token])

  const fetchUser = async () => {
    try {
      const response = await api.get<User>('/api/auth/me')
      setUser(response.data)
    } catch {
      localStorage.removeItem('auth_token')
      setToken(null)
      delete api.defaults.headers.common['Authorization']
    } finally {
      setIsLoading(false)
    }
  }

  const login = async (email: string, password: string) => {
    const response = await api.post<{ access_token: string; token_type: string }>(
      '/api/auth/login',
      { email, password }
    )
    const newToken = response.data.access_token
    localStorage.setItem('auth_token', newToken)
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
    setToken(newToken)
    await fetchUser()
  }

  const register = async (email: string, password: string, fullName?: string, inviteToken?: string) => {
    await api.post('/api/auth/register', {
      email,
      password,
      full_name: fullName,
      invite_token: inviteToken
    })
    await login(email, password)
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    delete api.defaults.headers.common['Authorization']
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'admin',
        login,
        register,
        logout
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
