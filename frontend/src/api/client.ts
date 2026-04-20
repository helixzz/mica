import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

import i18n from '@/i18n'

const TOKEN_KEY = 'mica.token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

export const client: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 20000,
})

client.interceptors.request.use((cfg: InternalAxiosRequestConfig) => {
  const token = getToken()
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  cfg.headers['Accept-Language'] = i18n.language || 'zh-CN'
  return cfg
})

client.interceptors.response.use(
  (r) => r,
  (err: AxiosError<{ detail?: string }>) => {
    if (err.response?.status === 401) {
      clearToken()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export interface ApiError {
  status: number
  detail: string
}

export function extractError(e: unknown): ApiError {
  if (axios.isAxiosError(e)) {
    const status = e.response?.status ?? 0
    const detail =
      (e.response?.data as { detail?: string } | undefined)?.detail ||
      e.message ||
      'unknown_error'
    return { status, detail }
  }
  return { status: 0, detail: String(e) }
}
