import { Alert, Spin } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'
import { extractError } from '@/api/client'

function parseHash(hash: string): { token: string | null; next: string } {
  const params = new URLSearchParams(hash.startsWith('#') ? hash.slice(1) : hash)
  const token = params.get('token')
  const next = params.get('next') || '/dashboard'
  if (!next.startsWith('/') || next.startsWith('//') || next.includes('://')) {
    return { token, next: '/dashboard' }
  }
  return { token, next }
}

export function SsoCallbackPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { loginWithToken } = useAuth()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const { token, next } = parseHash(window.location.hash)

    if (!token) {
      setError(t('auth.sso_missing_token', 'Missing SSO token'))
      return
    }

    void loginWithToken(token)
      .then(() => {
        if (!active) return
        window.history.replaceState(null, '', '/sso-callback')
        navigate(next, { replace: true })
      })
      .catch((e) => {
        if (!active) return
        const err = extractError(e)
        setError(err.detail || t('auth.sso_login_failed', 'SSO login failed'))
      })

    return () => {
      active = false
    }
  }, [loginWithToken, navigate, t])

  if (error) {
    return (
      <div
        style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
      >
        <Alert type="error" showIcon message={error} />
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Spin size="large" tip={t('auth.signing_in', 'Signing you in...')} />
    </div>
  )
}
