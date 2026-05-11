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
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: isAccent ? token.colorPrimaryBg : token.colorBgContainer,
        transition: `all ${token.motionDurationMid} ${token.motionEaseInOut}`,
        transform: isHovered ? 'translateY(-2px)' : 'none',
        boxShadow: isHovered ? token.boxShadowSecondary : token.boxShadowTertiary,
      }}
      styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column' } }}
    >
      <Skeleton loading={loading} active paragraph={{ rows: 1 }} title={{ width: '50%' }}>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Space direction="vertical" size={token.marginXS}>
            <Text
              style={{
                color: isAccent ? token.colorPrimaryText : token.colorTextSecondary,
                fontSize: token.fontSizeSM,
                fontWeight: 500,
              }}
            >
              {label}
            </Text>
            <Title
              level={3}
              style={{
                margin: 0,
                color: isAccent ? token.colorPrimaryTextHover : token.colorText,
                fontWeight: 600,
              }}
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
              style={{
                color: isAccent ? token.colorPrimary : token.colorTextTertiary,
                fontSize: token.fontSizeHeading3,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 48,
                height: 48,
                borderRadius: token.borderRadiusLG,
                backgroundColor: isAccent ? 'rgba(255,255,255,0.6)' : token.colorFillAlter,
              }}
            />
          )}
        </div>
        {footer && (
          <>
            <Divider style={{ margin: `${token.marginSM}px 0 0` }} />
            <div style={{ fontSize: token.fontSizeSM, color: token.colorPrimary, textAlign: 'right' }}>
              {footer}
            </div>
          </>
        )}
      </Skeleton>
    </Card>
  )
}
