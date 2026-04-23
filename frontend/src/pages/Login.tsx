import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Divider, Form, Input, Space, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { api } from '@/api'
import { LanguageSwitcher } from '@/components/LanguageSwitcher'
import { useAuth } from '@/auth/useAuth'
import { extractError } from '@/api/client'

export function LoginPage() {
  const { t } = useTranslation()
  const { login, loading } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [samlEnabled, setSamlEnabled] = useState(false)
  const [samlLoginUrl, setSamlLoginUrl] = useState<string | null>(null)
  const [showLocalLogin, setShowLocalLogin] = useState(false)

  useEffect(() => {
    let active = true
    void api
      .loginOptions()
      .then((options) => {
        if (!active) return
        setSamlEnabled(options.saml_enabled)
        setSamlLoginUrl(options.saml_login_url)
      })
      .catch(() => {
        if (!active) return
        setSamlEnabled(false)
        setSamlLoginUrl(null)
      })

    return () => {
      active = false
    }
  }, [])

  const onFinish = async (values: { username: string; password: string }) => {
    setError(null)
    try {
      await login(values.username, values.password)
      navigate('/dashboard', { replace: true })
    } catch (e) {
      const err = extractError(e)
      setError(err.detail || t('error.login_failed'))
    }
  }

  const onSsoLogin = () => {
    if (!samlLoginUrl) return
    window.location.assign(samlLoginUrl)
  }

  const ssoAvailable = samlEnabled && !!samlLoginUrl

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #2E5266 0%, #1f3a49 100%)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div style={{ position: 'absolute', top: 24, right: 24 }}>
        <LanguageSwitcher />
      </div>
      <Card style={{ width: 380 }}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Typography.Title level={2} style={{ margin: 0, color: '#2E5266' }}>
              Mica
            </Typography.Title>
            {t('app.tagline') && (
              <Typography.Text type="secondary">{t('app.tagline')}</Typography.Text>
            )}
          </div>
          
          {error && <Alert type="error" message={error} showIcon />}

          {ssoAvailable && !showLocalLogin && (
            <>
              <Button type="primary" size="large" block onClick={onSsoLogin}>
                {t('auth.sign_in_with_sso')}
              </Button>
              <Typography.Link 
                onClick={() => setShowLocalLogin(true)}
                style={{ display: 'block', textAlign: 'center' }}
              >
                {t('auth.use_local_account')}
              </Typography.Link>
            </>
          )}

          {(!ssoAvailable || showLocalLogin) && (
            <>
              {ssoAvailable && (
                <Typography.Link
                  onClick={() => setShowLocalLogin(false)} 
                  style={{ display: 'block', textAlign: 'center' }}
                >
                  {t('auth.back_to_sso')}
                </Typography.Link>
              )}
              <Form layout="vertical" onFinish={onFinish} autoComplete="on">
                <Form.Item
                  label={t('field.username')}
                  name="username"
                  rules={[{ required: true }]}
                >
                  <Input
                    prefix={<UserOutlined />}
                    placeholder={t('placeholder.enter_username')}
                    autoFocus
                  />
                </Form.Item>
                <Form.Item
                  label={t('field.password')}
                  name="password"
                  rules={[{ required: true }]}
                >
                  <Input.Password
                    prefix={<LockOutlined />}
                    placeholder={t('placeholder.enter_password')}
                  />
                </Form.Item>
                <Button type="primary" htmlType="submit" block loading={loading} size="large">
                  {t('button.submit')}
                </Button>
              </Form>
              <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', textAlign: 'center' }}>
                Dev: alice / bob / carol / dave / admin · password: MicaDev2026!
              </Typography.Text>
            </>
          )}
        </Space>
      </Card>
    </div>
  )
}
