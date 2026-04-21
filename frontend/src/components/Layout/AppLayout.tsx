import React, { useState } from 'react';
import {
  ApartmentOutlined,
  AuditOutlined,
  BankOutlined,
  BarChartOutlined,
  CarOutlined,
  DashboardOutlined,
  DollarOutlined,
  FileTextOutlined,
  LogoutOutlined,
  SettingOutlined,
  SolutionOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import { Avatar, Dropdown, Layout, Menu, Space, Tag, Typography, theme, Button, Drawer } from 'antd';
import { useTranslation } from 'react-i18next';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { LanguageSwitcher } from '../LanguageSwitcher';
import { useAuth } from '@/auth/useAuth';
import { useTheme } from '@/theme/ThemeProvider';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

// Slot components for downstream agents to fill
import { GlobalSearch } from '@/components/GlobalSearch';

import { NotificationBell } from '@/components/NotificationBell';

export const SearchSlot: React.FC = () => <GlobalSearch />;
export const NotificationSlot: React.FC = () => <NotificationBell />;

export function AppLayout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { mode, setMode } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const onLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const toggleTheme = () => {
    if (mode === 'light') setMode('dark');
    else if (mode === 'dark') setMode('system');
    else setMode('light');
  };

  const getThemeIcon = () => {
    if (mode === 'light') return '☀️';
    if (mode === 'dark') return '🌙';
    return '💻';
  };

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: <Link to="/dashboard" onClick={() => setMobileMenuOpen(false)}>{t('nav.dashboard')}</Link> },
    { key: '/approvals', icon: <AuditOutlined />, label: <Link to="/approvals" onClick={() => setMobileMenuOpen(false)}>{t('nav.approvals')}</Link> },
    { key: '/purchase-requisitions', icon: <SolutionOutlined />, label: <Link to="/purchase-requisitions" onClick={() => setMobileMenuOpen(false)}>{t('nav.purchase_requisitions')}</Link> },
    { key: '/purchase-orders', icon: <FileTextOutlined />, label: <Link to="/purchase-orders" onClick={() => setMobileMenuOpen(false)}>{t('nav.purchase_orders')}</Link> },
    { key: '/contracts', icon: <ApartmentOutlined />, label: <Link to="/contracts" onClick={() => setMobileMenuOpen(false)}>{t('nav.contracts')}</Link> },
    { key: '/shipments', icon: <CarOutlined />, label: <Link to="/shipments" onClick={() => setMobileMenuOpen(false)}>{t('nav.shipments')}</Link> },
    { key: '/payments', icon: <BankOutlined />, label: <Link to="/payments" onClick={() => setMobileMenuOpen(false)}>{t('nav.payments')}</Link> },
    { key: '/invoices', icon: <DollarOutlined />, label: <Link to="/invoices" onClick={() => setMobileMenuOpen(false)}>{t('nav.invoices')}</Link> },
    { key: '/sku', icon: <BarChartOutlined />, label: <Link to="/sku" onClick={() => setMobileMenuOpen(false)}>{t('nav.sku')}</Link> },
    ...(user?.role === 'admin'
      ? [{ key: '/admin', icon: <SettingOutlined />, label: <Link to="/admin" onClick={() => setMobileMenuOpen(false)}>系统管理</Link> }]
      : []),
  ];

  const roleTag = user ? t(`role.${user.role}` as 'role.admin') : '';
  const currentKey = '/' + (location.pathname.split('/')[1] || 'dashboard');

  const Logo = () => (
    <Space size="small" style={{ display: 'flex', alignItems: 'center' }}>
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: token.borderRadiusSM,
          backgroundColor: token.colorPrimary,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: token.colorTextLightSolid,
          fontWeight: 'bold',
          fontSize: 18,
        }}
      >
        M
      </div>
      <Text
        style={{
          fontSize: 20,
          fontWeight: 700,
          color: token.colorText,
          letterSpacing: '-0.02em',
        }}
      >
        Mica
      </Text>
    </Space>
  );

  return (
    <Layout style={{ minHeight: '100vh', background: token.colorBgLayout }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          background: token.colorBgContainer,
          padding: `0 ${token.paddingLG}px`,
          height: 56,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          position: 'sticky',
          top: 0,
          zIndex: token.zIndexPopupBase,
          boxShadow: token.boxShadowTertiary,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', width: 220, flexShrink: 0 }}>
          <Logo />
        </div>

        <Button
          type="text"
          icon={<MenuOutlined />}
          onClick={() => setMobileMenuOpen(true)}
          style={{ display: 'none' }}
          className="mobile-menu-toggle"
          title={t('layout.menu_toggle')}
        />

        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', maxWidth: 480, margin: '0 24px' }}>
          <SearchSlot />
        </div>

        <Space size="middle" style={{ marginLeft: 'auto' }}>
          <NotificationSlot />
          <LanguageSwitcher />
          <Button
            type="text"
            onClick={toggleTheme}
            title={t('theme.toggle')}
            style={{ fontSize: 16, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          >
            {getThemeIcon()}
          </Button>
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
              placement="bottomRight"
            >
              <Space style={{ cursor: 'pointer', padding: '4px 8px', borderRadius: token.borderRadiusSM, transition: 'background 0.2s' }} className="user-dropdown">
                <Avatar size="small" style={{ backgroundColor: token.colorPrimary }}>
                  {user.display_name.slice(0, 1).toUpperCase()}
                </Avatar>
                <span className="user-name" style={{ color: token.colorText, fontWeight: 500 }}>{user.display_name}</span>
                <Tag color="processing" style={{ margin: 0, border: 'none' }}>{roleTag}</Tag>
              </Space>
            </Dropdown>
          )}
        </Space>
      </Header>

      <Layout>
        {/* Desktop Sider */}
        <Sider
          width={220}
          style={{
            background: token.colorBgContainer,
            borderRight: `1px solid ${token.colorBorderSecondary}`,
            display: 'block',
          }}
          className="desktop-sider"
          breakpoint="lg"
          collapsedWidth="0"
          trigger={null}
        >
          <Menu
            mode="inline"
            selectedKeys={[currentKey]}
            style={{ height: '100%', borderRight: 0, padding: `${token.paddingSM}px 0` }}
            items={menuItems}
          />
        </Sider>

        {/* Mobile Drawer */}
        <Drawer
          title={<Logo />}
          placement="left"
          onClose={() => setMobileMenuOpen(false)}
          open={mobileMenuOpen}
          bodyStyle={{ padding: 0 }}
          width={240}
        >
          <Menu
            mode="inline"
            selectedKeys={[currentKey]}
            style={{ borderRight: 0, padding: `${token.paddingSM}px 0` }}
            items={menuItems}
          />
        </Drawer>

        <Content
          style={{
            padding: `${token.paddingLG}px`,
            maxWidth: 1440,
            margin: '0 auto',
            width: '100%',
          }}
        >
          <Outlet />
        </Content>
      </Layout>

      <style>{`
        @media (max-width: 992px) {
          .desktop-sider {
            display: none !important;
          }
          .mobile-menu-toggle {
            display: inline-flex !important;
            margin-right: 16px;
          }
          .user-name {
            display: none;
          }
        }
        .user-dropdown:hover {
          background-color: ${token.colorFillAlter};
        }
        .ant-menu-item-selected {
          border-left: 3px solid ${token.colorPrimary};
        }
      `}</style>
    </Layout>
  );
}
