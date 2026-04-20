import { LogoutOutlined } from '@ant-design/icons'
import { Avatar, Button, Dropdown, Layout, Menu, Space, Tag, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { LanguageSwitcher } from './LanguageSwitcher'
import { useAuth } from '@/auth/useAuth'

const { Header, Sider, Content } = Layout

export function AppLayout() {
  const { t } = useTranslation()
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const onLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const menu = [
    { key: '/dashboard', label: <Link to="/dashboard">{t('nav.dashboard')}</Link> },
    {
      key: '/purchase-requisitions',
      label: <Link to="/purchase-requisitions">{t('nav.purchase_requisitions')}</Link>,
    },
    {
      key: '/purchase-orders',
      label: <Link to="/purchase-orders">{t('nav.purchase_orders')}</Link>,
    },
  ]

  const roleTag = user ? t(`role.${user.role}` as 'role.admin') : ''

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          background: '#2E5266',
          padding: '0 24px',
          gap: 24,
        }}
      >
        <Typography.Title level={3} style={{ color: '#E8833A', margin: 0 }}>
          Mica
        </Typography.Title>
        <Typography.Text style={{ color: 'rgba(255,255,255,0.85)' }}>
          {t('app.tagline')}
        </Typography.Text>
        <div style={{ flex: 1 }} />
        <Space size="middle">
          <LanguageSwitcher />
          {user && (
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'logout',
                    icon: <LogoutOutlined />,
                    label: t('nav.logout'),
                    onClick: onLogout,
                  },
                ],
              }}
            >
              <Space style={{ color: '#fff', cursor: 'pointer' }}>
                <Avatar style={{ background: '#E8833A' }}>
                  {user.display_name.slice(0, 1)}
                </Avatar>
                <span>{user.display_name}</span>
                <Tag color="orange">{roleTag}</Tag>
              </Space>
            </Dropdown>
          )}
        </Space>
      </Header>
      <Layout>
        <Sider width={220} theme="light">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            style={{ height: '100%', borderRight: 0 }}
            items={menu}
          />
        </Sider>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

void Button
