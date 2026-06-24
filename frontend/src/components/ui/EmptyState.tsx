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
  size?: 'default' | 'compact' | 'inline';
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  illustration = 'empty',
  title,
  description,
  action,
  size = 'default',
}) => {
  const { token } = theme.useToken();
  const { t } = useTranslation();

  const src = ILLUSTRATIONS[illustration] || ILLUSTRATIONS.empty;
  const isCompact = size === 'compact';
  const isInline = size === 'inline';

  if (isInline) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: token.marginSM,
          padding: `${token.paddingSM}px ${token.paddingMD}px`,
          color: token.colorTextSecondary,
        }}
      >
        <Text type="secondary" style={{ fontSize: token.fontSize }}>
          {title || t('empty.default')}
        </Text>
        {action}
      </div>
    );
  }

  const illustrationSize = isCompact ? 80 : 240;
  const verticalPadding = isCompact ? token.paddingMD : token.paddingXL * 2;
  const horizontalPadding = isCompact ? token.paddingMD : token.paddingLG;
  const titleLevel: 4 | 5 = isCompact ? 5 : 4;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: `${verticalPadding}px ${horizontalPadding}px`,
        textAlign: 'center',
        backgroundColor: 'transparent',
        borderRadius: token.borderRadiusLG,
        border: isCompact ? 'none' : `1px dashed ${token.colorBorderSecondary}`,
      }}
    >
      <div
        style={{
          width: illustrationSize,
          height: illustrationSize,
          marginBottom: isCompact ? token.marginSM : token.marginLG,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: isCompact ? 0.7 : 1,
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
      <Space direction="vertical" size={isCompact ? token.marginXXS : token.marginSM} style={{ maxWidth: 400 }}>
        <Title level={titleLevel} style={{ margin: 0, color: token.colorText, fontWeight: 500 }}>
          {title || t('empty.default')}
        </Title>
        {description && (
          <Text type="secondary" style={{ fontSize: isCompact ? token.fontSizeSM : token.fontSize }}>
            {description}
          </Text>
        )}
        {action && <div style={{ marginTop: isCompact ? token.marginXS : token.marginMD }}>{action}</div>}
      </Space>
    </div>
  );
};
