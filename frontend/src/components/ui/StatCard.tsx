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
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  trend,
  icon,
  footer,
  loading = false,
  variant = 'default',
}) => {
  const { token } = theme.useToken()
  const [isHovered, setIsHovered] = useState(false)

  const isAccent = variant === 'accent'

  const labelColor = isAccent ? token.colorPrimary : token.colorTextSecondary
  const valueColor = token.colorText
  const iconColor = isAccent ? token.colorPrimary : token.colorTextTertiary
  const iconBg = isAccent ? token.colorPrimaryBg : token.colorFillQuaternary

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
      styles={{ body: { padding: token.paddingLG } }}
    >
      <Skeleton loading={loading} active paragraph={{ rows: 1 }} title={{ width: '50%' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            gap: token.marginSM,
          }}
        >
          <Space
            direction="vertical"
            size={token.marginXS}
            style={{ minWidth: 0, flex: 1 }}
          >
            <Text
              style={{
                color: labelColor,
                fontSize: token.fontSizeSM,
                fontWeight: 500,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '100%',
              }}
            >
              {label}
            </Text>
            <Title
              level={3}
              style={{
                margin: 0,
                color: valueColor,
                fontWeight: 600,
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                maxWidth: '100%',
                fontVariantNumeric: 'tabular-nums',
              }}
              title={typeof value === 'string' || typeof value === 'number' ? String(value) : undefined}
            >
              {value}
            </Title>
            {trend && (
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
                fontSize: token.fontSizeHeading3,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 40,
                height: 40,
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
            <Divider style={{ margin: `${token.marginSM}px 0 0` }} />
            <div style={{ fontSize: token.fontSizeSM, color: token.colorPrimary, textAlign: 'right', paddingTop: token.marginXS }}>
              {footer}
            </div>
          </>
        )}
      </Skeleton>
    </Card>
  )
}
