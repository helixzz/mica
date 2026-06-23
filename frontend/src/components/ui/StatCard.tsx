import React, { useState } from 'react'
import { Card, Typography, Space, theme, Skeleton, Divider } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, MinusOutlined } from '@ant-design/icons'

const { Text, Title } = Typography

export interface StatCardProps {
  label: React.ReactNode
  value: React.ReactNode
  trend?: {
    direction: 'up' | 'down' | 'flat'
    delta: React.ReactNode
  }
  icon?: React.ReactNode
  footer?: React.ReactNode
  loading?: boolean
  variant?: 'default' | 'accent'
  density?: 'comfortable' | 'compact'
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  trend,
  icon,
  footer,
  loading = false,
  variant = 'default',
  density = 'comfortable',
}) => {
  const { token } = theme.useToken()
  const [isHovered, setIsHovered] = useState(false)

  const isAccent = variant === 'accent'
  const isCompact = density === 'compact'
  const isPrimitive = typeof value === 'string' || typeof value === 'number'

  const labelColor = isAccent ? token.colorPrimary : token.colorTextSecondary
  const valueColor = token.colorText
  const iconColor = isAccent ? token.colorPrimary : token.colorTextTertiary
  const iconBg = isAccent ? token.colorPrimaryBg : token.colorFillQuaternary

  const cardPadding = isCompact ? token.paddingSM : token.paddingLG
  const titleLevel: 3 | 4 = isCompact ? 4 : 3
  const iconSize = isCompact ? 32 : 40
  const iconFontSize = isCompact ? token.fontSizeLG : token.fontSizeHeading3
  const labelSize = isCompact ? token.fontSizeSM : token.fontSizeSM
  const stackGap = isCompact ? token.marginXXS : token.marginXS

  const getTrendColor = () => {
    if (!trend) return token.colorTextSecondary
    switch (trend.direction) {
      case 'up':
        return token.colorSuccess
      case 'down':
        return token.colorError
      case 'flat':
        return token.colorTextSecondary
    }
  }

  const getTrendIcon = () => {
    if (!trend) return null
    switch (trend.direction) {
      case 'up':
        return <ArrowUpOutlined />
      case 'down':
        return <ArrowDownOutlined />
      case 'flat':
        return <MinusOutlined />
    }
  }

  return (
    <Card
      bordered={false}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        height: '100%',
        backgroundColor: token.colorBgContainer,
        borderInlineStart: isAccent ? `3px solid ${token.colorPrimary}` : 'none',
        transition: `all ${token.motionDurationMid} ${token.motionEaseInOut}`,
        transform: isHovered ? 'translateY(-2px)' : 'none',
        boxShadow: isHovered ? token.boxShadowSecondary : token.boxShadowTertiary,
      }}
      styles={{ body: { padding: cardPadding } }}
    >
      <Skeleton loading={loading} active paragraph={{ rows: 1 }} title={{ width: '50%' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: isCompact ? 'center' : 'flex-start',
            gap: token.marginSM,
          }}
        >
          <Space
            direction="vertical"
            size={stackGap}
            style={{ minWidth: 0, flex: 1 }}
          >
            <Text
              style={{
                color: labelColor,
                fontSize: labelSize,
                fontWeight: 500,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '100%',
                lineHeight: 1.2,
              }}
            >
              {label}
            </Text>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: token.marginSM, minWidth: 0 }}>
              <Title
                level={titleLevel}
                style={{
                  margin: 0,
                  color: valueColor,
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  fontFamily: isPrimitive ? 'var(--font-mono)' : undefined,
                  fontVariantNumeric: 'tabular-nums',
                  fontFeatureSettings: '"tnum" 1, "zero" 1',
                  lineHeight: isCompact ? 1.2 : 1.15,
                  letterSpacing: isCompact ? 'var(--tracking-heading)' : 'var(--tracking-display)',
                }}
                title={isPrimitive ? String(value) : undefined}
              >
                {value}
              </Title>
              {isCompact && trend && (
                <Space size={token.marginXXS} style={{ color: getTrendColor(), fontSize: token.fontSizeSM, flexShrink: 0 }}>
                  {getTrendIcon()}
                  {typeof trend.delta === 'string' ? (
                    <Text style={{ color: 'inherit', fontWeight: 500 }}>{trend.delta}</Text>
                  ) : (
                    trend.delta
                  )}
                </Space>
              )}
            </div>
            {!isCompact && trend && (
              <Space size={token.marginXXS} style={{ color: getTrendColor(), fontSize: token.fontSizeSM }}>
                {getTrendIcon()}
                {typeof trend.delta === 'string' ? (
                  <Text style={{ color: 'inherit', fontWeight: 500 }}>{trend.delta}</Text>
                ) : (
                  trend.delta
                )}
              </Space>
            )}
          </Space>
          {icon && (
            <div
              aria-hidden
              style={{
                color: iconColor,
                fontSize: iconFontSize,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: iconSize,
                height: iconSize,
                borderRadius: token.borderRadiusLG,
                backgroundColor: iconBg,
                flexShrink: 0,
              }}
            >
              {icon}
            </div>
          )}
        </div>
        {footer && (
          <>
            <Divider style={{ margin: `${isCompact ? token.marginXS : token.marginSM}px 0 0` }} />
            <div style={{ fontSize: token.fontSizeSM, color: token.colorPrimary, textAlign: 'right', paddingTop: token.marginXXS }}>
              {footer}
            </div>
          </>
        )}
      </Skeleton>
    </Card>
  )
}
