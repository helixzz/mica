import React from 'react';
import { Typography, Space, theme } from 'antd';
import { useTranslation } from 'react-i18next';

import otterEmpty from '@/assets/illustrations/otter-empty.svg';
import otterSearch from '@/assets/illustrations/otter-search.svg';
import otterWelcome from '@/assets/illustrations/otter-welcome.svg';

const { Title, Text } = Typography;

const ILLUSTRATIONS: Record<string, string> = {
  empty: otterEmpty,
  search: otterSearch,
  welcome: otterWelcome,
};

export type IllustrationName = 'empty' | 'search' | 'welcome' | '404' | 'loading';

export interface EmptyStateProps {
  illustration?: IllustrationName;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  illustration = 'empty',
  title,
  description,
  action,
}) => {
  const { token } = theme.useToken();
  const { t } = useTranslation();

  const src = ILLUSTRATIONS[illustration] || ILLUSTRATIONS.empty;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: `${token.paddingXL * 2}px ${token.paddingLG}px`,
        textAlign: 'center',
        backgroundColor: token.colorBgContainer,
        borderRadius: token.borderRadiusLG,
        border: `1px dashed ${token.colorBorderSecondary}`,
      }}
    >
      <div
        style={{
          width: 240,
          height: 240,
          marginBottom: token.marginLG,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <img
          src={src}
          alt={illustration}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      </div>
      <Space direction="vertical" size={token.marginSM} style={{ maxWidth: 400 }}>
        <Title level={4} style={{ margin: 0, color: token.colorText }}>
          {title || t('empty.default')}
        </Title>
        {description && (
          <Text type="secondary" style={{ fontSize: token.fontSize }}>
            {description}
          </Text>
        )}
        {action && <div style={{ marginTop: token.marginMD }}>{action}</div>}
      </Space>
    </div>
  );
};
