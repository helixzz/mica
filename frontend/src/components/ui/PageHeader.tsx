import React from 'react';
import { theme, Typography, Space, Breadcrumb } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { MonoId } from './Mono';

const { Title, Text } = Typography;

export interface PageHeaderProps {
  title: React.ReactNode;
  /**
   * Optional business identifier (e.g. PR-2026-0017, PO-2026-0019).
   * When provided, renders next to the title in JetBrains Mono.
   * See docs/DESIGN.md §4.2 / §7.8.
   */
  number?: string | null;
  subtitle?: React.ReactNode;
  breadcrumbs?: Array<{ title: React.ReactNode; href?: string }>;
  autoBreadcrumbs?: boolean;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  number,
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
        <Space direction="vertical" size={0} style={{ minWidth: 0 }}>
          <Space size={token.marginSM} align="baseline" wrap>
            <Title
              level={2}
              style={{
                margin: 0,
                fontWeight: 600,
                letterSpacing: 'var(--tracking-heading)',
                lineHeight: 1.2,
              }}
            >
              {title}
            </Title>
            {number && (
              <MonoId style={{ fontSize: token.fontSizeLG, color: token.colorTextSecondary }}>
                {number}
              </MonoId>
            )}
          </Space>
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
