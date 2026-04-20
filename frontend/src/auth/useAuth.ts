import { create } from 'zustand'

import { api, type User } from '@/api'
import { clearToken, setToken } from '@/api/client'

interface AuthState {
  user: User | null
  loading: boolean
  initialized: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  loadMe: () => Promise<void>
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  initialized: false,
  login: async (username, password) => {
    set({ loading: true })
    try {
      const tok = await api.login(username, password)
      setToken(tok.access_token)
      const me = await api.me()
      set({ user: me, loading: false, initialized: true })
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },
  logout: () => {
    clearToken()
    set({ user: null, initialized: true })
  },
  loadMe: async () => {
    try {
      const me = await api.me()
      set({ user: me, initialized: true })
    } catch {
      set({ user: null, initialized: true })
    }
  },
}))

void get
