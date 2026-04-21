import React from 'react';
import { Card, Typography, Space, theme } from 'antd';

const { Title, Text } = Typography;

export interface SectionProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
  extra?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * Section component for grouping related content.
 * Provides consistent spacing and card-like container.
 */
export const Section: React.FC<SectionProps> = ({
  title,
  description,
  extra,
  children,
}) => {
  const { token } = theme.useToken();

  return (
    <Card
      bordered={false}
      style={{
        marginBottom: token.marginLG,
        backgroundColor: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
        boxShadow: token.boxShadowTertiary,
      }}
      bodyStyle={{ padding: token.paddingLG }}
    >
      {(title || description || extra) && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: token.marginLG,
            paddingBottom: token.paddingMD,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Space direction="vertical" size={token.marginXXS}>
            {title && (
              <Title level={4} style={{ margin: 0, fontWeight: 600 }}>
                {title}
              </Title>
            )}
            {description && (
              <Text type="secondary" style={{ fontSize: token.fontSize }}>
                {description}
              </Text>
            )}
          </Space>
          {extra && <div>{extra}</div>}
        </div>
      )}
      <div>{children}</div>
    </Card>
  );
};
