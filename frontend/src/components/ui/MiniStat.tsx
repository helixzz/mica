import type { ReactNode } from 'react'
import { Typography } from 'antd'

export interface MiniStatProps {
  label: ReactNode
  value: ReactNode
  valueColor?: string
}

export function MiniStat({ label, value, valueColor }: MiniStatProps) {
  return (
    <div style={{ minWidth: 140, flex: '1 1 140px' }}>
      <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', lineHeight: 1.4 }}>
        {label}
      </Typography.Text>
      <Typography.Text
        strong
        style={{
          fontSize: 16,
          color: valueColor,
          fontFamily: 'var(--font-mono)',
          fontFeatureSettings: '"tnum" 1, "zero" 1',
          lineHeight: 1.3,
          display: 'block',
        }}
      >
        {value}
      </Typography.Text>
    </div>
  )
}
