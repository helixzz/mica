import React, { useState } from 'react';
import {
  ApartmentOutlined,
  AuditOutlined,
  BankOutlined,
  BarChartOutlined,
  CarOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  DollarOutlined,
  FileTextOutlined,
  LogoutOutlined,
  MoonOutlined,
  SettingOutlined,
  SolutionOutlined,
  SunOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import { Avatar, Dropdown, Layout, Menu, Space, Tag, Typography, theme, Button, Drawer } from 'antd';
import { useTranslation } from 'react-i18next';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';

import { LanguageSwitcher } from '../LanguageSwitcher';
import { useAuth } from '@/auth/useAuth';
import { useTheme } from '@/theme/ThemeProvider';

const { Header, Sider, Content, Footer } = Layout;
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
    if (mode === 'light') return <SunOutlined />;
    if (mode === 'dark') return <MoonOutlined />;
    return <DesktopOutlined />;
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
    { key: '/items', icon: <DatabaseOutlined />, label: <Link to="/items" onClick={() => setMobileMenuOpen(false)}>物料管理</Link> },
    { key: '/rfqs', icon: <SolutionOutlined />, label: <Link to="/rfqs" onClick={() => setMobileMenuOpen(false)}>{t('nav.rfqs')}</Link> },
    { key: '/suppliers', icon: <BankOutlined />, label: <Link to="/suppliers" onClick={() => setMobileMenuOpen(false)}>{t('nav.suppliers')}</Link> },
    ...(user?.role === 'admin'
      ? [{ key: '/admin', icon: <SettingOutlined />, label: <Link to="/admin" onClick={() => setMobileMenuOpen(false)}>系统管理</Link> }]
      : []),
  ];

  const roleTag = user ? t(`role.${user.role}` as 'role.admin') : '';
  const currentKey = '/' + (location.pathname.split('/')[1] || 'dashboard');

  const Logo = () => (
    <Link to="/dashboard" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center' }}>
      <Space size="small" style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
        <svg width="32" height="32" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style={{ display: 'block' }}>
          {/* Otter face */}
          <circle cx="32" cy="34" r="24" fill={token.colorPrimary} />
          {/* Ears */}
          <circle cx="12" cy="16" r="6" fill={token.colorPrimary} />
          <circle cx="52" cy="16" r="6" fill={token.colorPrimary} />
          <circle cx="12" cy="16" r="3.5" fill={token.colorPrimaryBg} />
          <circle cx="52" cy="16" r="3.5" fill={token.colorPrimaryBg} />
          {/* Face patch */}
          <ellipse cx="32" cy="40" rx="16" ry="12" fill={token.colorPrimaryBg} />
          {/* Nose */}
          <ellipse cx="32" cy="36" rx="4" ry="2.5" fill={token.colorPrimaryActive} />
          {/* Eyes */}
          <circle cx="22" cy="30" r="3.5" fill={token.colorPrimaryActive} />
          <circle cx="42" cy="30" r="3.5" fill={token.colorPrimaryActive} />
          <circle cx="23" cy="29" r="1.2" fill="white" />
          <circle cx="43" cy="29" r="1.2" fill="white" />
          {/* Whisker dots */}
          <circle cx="20" cy="40" r="1" fill={token.colorPrimaryActive} opacity="0.5" />
          <circle cx="44" cy="40" r="1" fill={token.colorPrimaryActive} opacity="0.5" />
          {/* Smile */}
          <path d="M27,44 Q32,48 37,44" fill="none" stroke={token.colorPrimaryActive} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <Text
          className="logo-text"
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
    </Link>
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
        <div className="header-logo" style={{ display: 'flex', alignItems: 'center', width: 220, flexShrink: 0 }}>
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

        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', maxWidth: 480, margin: '0 12px', minWidth: 0 }} className="header-search">
          <SearchSlot />
        </div>

        <Space size="middle" style={{ marginLeft: 'auto' }}>
          <NotificationSlot />
          <LanguageSwitcher />
          <Button
            type="text"
            onClick={toggleTheme}
            title={t('theme.toggle')}
            icon={getThemeIcon()}
          />
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

      <Footer
        style={{
          textAlign: 'center',
          padding: '12px 24px',
          fontSize: 12,
          color: token.colorTextTertiary,
          background: token.colorBgLayout,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        Mica v{__APP_VERSION__} · Built {__BUILD_DATE__}
      </Footer>

      <style>{`
        @media (max-width: 992px) {
          .desktop-sider {
            display: none !important;
          }
          .mobile-menu-toggle {
            display: inline-flex !important;
            margin-right: 8px;
          }
          .user-name {
            display: none;
          }
          .header-search {
            max-width: 240px !important;
            margin: 0 8px !important;
          }
        }
        @media (max-width: 768px) {
          .header-search {
            display: none !important;
          }
          .logo-text {
            display: none;
          }
          .header-logo {
            width: auto !important;
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
