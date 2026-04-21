import React from 'react';
import { Typography, Space, theme } from 'antd';
import { useTranslation } from 'react-i18next';

const { Title, Text } = Typography;

export type IllustrationName = 'empty' | 'search' | 'welcome' | '404' | 'loading';

export interface EmptyStateProps {
  illustration?: IllustrationName;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
}

/**
 * EmptyState component for displaying when no data is available.
 * Uses custom otter illustrations.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  illustration = 'empty',
  title,
  description,
  action,
}) => {
  const { token } = theme.useToken();
  const { t } = useTranslation();

  // In a real app, we would import the SVGs dynamically or use a sprite map.
  // For now, we'll use an img tag pointing to the public/assets folder.
  // Assuming the build process copies src/assets to the output.
  // A better approach for React is to import them as React components.
  
  // We will use a placeholder div if the image fails to load, but ideally
  // these should be inline SVGs to inherit currentColor.
  
  const getIllustrationPath = () => {
    return `/assets/illustrations/otter-${illustration}.svg`;
  };

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
          color: token.colorTextTertiary, // For inline SVGs using currentColor
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* We use an object tag to allow the SVG to inherit CSS variables if possible, 
            or just an img tag. For best results with currentColor, inline SVG is needed.
            Since we are generating SVGs that use CSS variables, img tag might not work 
            for theming unless the SVG itself contains the CSS or uses currentColor.
            We will assume the SVGs are designed to work as images or we will inline them later. */}
        <img 
          src={getIllustrationPath()} 
          alt={illustration} 
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          onError={(e) => {
            // Fallback if image not found
            (e.target as HTMLImageElement).style.display = 'none';
            (e.target as HTMLImageElement).parentElement!.innerHTML = `<div style="width: 120px; height: 120px; border-radius: 50%; background-color: ${token.colorFillAlter}; display: flex; align-items: center; justify-content: center;"><span style="font-size: 48px;">🦦</span></div>`;
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
