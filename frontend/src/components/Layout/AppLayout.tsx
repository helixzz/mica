import {
  ApartmentOutlined,
  AuditOutlined,
  BankOutlined,
  CarOutlined,
  DashboardOutlined,
  DollarOutlined,
  FileTextOutlined,
  LogoutOutlined,
  SettingOutlined,
  SolutionOutlined,
} from '@ant-design/icons'
import { Avatar, Dropdown, Layout, Menu, Space, Tag, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { LanguageSwitcher } from '../LanguageSwitcher'
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
    { key: '/dashboard', icon: <DashboardOutlined />, label: <Link to="/dashboard">{t('nav.dashboard')}</Link> },
    { key: '/approvals', icon: <AuditOutlined />, label: <Link to="/approvals">{t('nav.approvals')}</Link> },
    { key: '/purchase-requisitions', icon: <SolutionOutlined />, label: <Link to="/purchase-requisitions">{t('nav.purchase_requisitions')}</Link> },
    { key: '/purchase-orders', icon: <FileTextOutlined />, label: <Link to="/purchase-orders">{t('nav.purchase_orders')}</Link> },
    { key: '/contracts', icon: <ApartmentOutlined />, label: <Link to="/contracts">{t('nav.contracts')}</Link> },
    { key: '/shipments', icon: <CarOutlined />, label: <Link to="/shipments">{t('nav.shipments')}</Link> },
    { key: '/payments', icon: <BankOutlined />, label: <Link to="/payments">{t('nav.payments')}</Link> },
    { key: '/invoices', icon: <DollarOutlined />, label: <Link to="/invoices">{t('nav.invoices')}</Link> },
    ...(user?.role === 'admin'
      ? [{ key: '/admin', icon: <SettingOutlined />, label: <Link to="/admin">系统管理</Link> }]
      : []),
  ]

  const roleTag = user ? t(`role.${user.role}` as 'role.admin') : ''
  const currentKey = '/' + (location.pathname.split('/')[1] || 'dashboard')

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
          <Menu mode="inline" selectedKeys={[currentKey]} style={{ height: '100%', borderRight: 0 }} items={menu} />
        </Sider>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
