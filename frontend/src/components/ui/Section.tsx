import React from 'react';
import { Card, Typography, Space, theme } from 'antd';

const { Title, Text } = Typography;

export interface SectionProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
  extra?: React.ReactNode;
  density?: 'comfortable' | 'compact';
  children: React.ReactNode;
}

export const Section: React.FC<SectionProps> = ({
  title,
  description,
  extra,
  density = 'comfortable',
  children,
}) => {
  const { token } = theme.useToken();
  const isCompact = density === 'compact';

  return (
    <Card
      bordered={false}
      style={{
        marginBottom: isCompact ? token.marginMD : token.marginLG,
        backgroundColor: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
        boxShadow: token.boxShadowTertiary,
      }}
      bodyStyle={{ padding: isCompact ? token.paddingMD : token.paddingLG }}
    >
      {(title || description || extra) && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            marginBottom: isCompact ? token.marginSM : token.marginLG,
            paddingBottom: isCompact ? token.paddingXS : token.paddingMD,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Space direction="vertical" size={token.marginXXS}>
            {title && (
              <Title level={isCompact ? 5 : 4} style={{ margin: 0, fontWeight: 600 }}>
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
