import React from 'react';
import { theme, Typography, Space, Breadcrumb } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

const { Title, Text } = Typography;

export interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  breadcrumbs?: Array<{ title: React.ReactNode; href?: string }>;
  autoBreadcrumbs?: boolean;
  actions?: React.ReactNode;
}

/**
 * PageHeader component for consistent page titles, breadcrumbs, and actions.
 * Uses AntD tokens for styling to support theme switching.
 */
export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  breadcrumbs,
  autoBreadcrumbs,
  actions,
}) => {
  const { token } = theme.useToken();
  const location = useLocation();
  const { t } = useTranslation();

  const pathToBreadcrumb = (path: string) => {
    const parts = path.split('/').filter(Boolean);
    return [
      { title: <Link to="/dashboard">{t('breadcrumb.home', 'Home')}</Link> },
      ...parts.map((p, i) => {
        const label = p.replace(/-/g, ' ');
        return {
          title: <Link to={'/' + parts.slice(0, i + 1).join('/')}>{label}</Link>,
        };
      }),
    ];
  };

  const finalBreadcrumbs = autoBreadcrumbs ? pathToBreadcrumb(location.pathname) : breadcrumbs;

  return (
    <div
      style={{
        padding: `${token.paddingLG}px ${token.paddingXL}px`,
        backgroundColor: token.colorBgContainer,
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        marginBottom: token.marginLG,
      }}
    >
      {finalBreadcrumbs && finalBreadcrumbs.length > 0 && (
        <Breadcrumb
          items={finalBreadcrumbs}
          style={{ marginBottom: token.marginSM }}
        />
      )}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: token.marginMD,
        }}
      >
        <Space direction="vertical" size={0}>
          <Title level={2} style={{ margin: 0, fontWeight: 600 }}>
            {title}
          </Title>
          {subtitle && (
            <Text type="secondary" style={{ fontSize: token.fontSize }}>
              {subtitle}
            </Text>
          )}
        </Space>
        {actions && <div>{actions}</div>}
      </div>
    </div>
  );
};
