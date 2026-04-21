import React from 'react';
import { theme, Typography, Space, Breadcrumb } from 'antd';

const { Title, Text } = Typography;

export interface PageHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  breadcrumbs?: Array<{ title: React.ReactNode; href?: string }>;
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
  actions,
}) => {
  const { token } = theme.useToken();

  return (
    <div
      style={{
        padding: `${token.paddingLG}px ${token.paddingXL}px`,
        backgroundColor: token.colorBgContainer,
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        marginBottom: token.marginLG,
      }}
    >
      {breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb
          items={breadcrumbs}
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
