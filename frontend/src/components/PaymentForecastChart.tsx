import { Card, Col, Empty, Row, Statistic, Typography } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PaymentForecast } from '@/api'
import { fmtAmount } from '@/utils/format'

const PLANNED_COLOR = '#B48A6A'
const PAID_COLOR = '#52c41a'

interface PaymentForecastChartProps {
  months?: number
  title?: string
}

export function PaymentForecastChart({ months = 6, title }: PaymentForecastChartProps) {
  const { t } = useTranslation()
  const [data, setData] = useState<PaymentForecast | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api
      .getPaymentForecast(months)
      .then(setData)
      .finally(() => setLoading(false))
  }, [months])

  const maxValue = useMemo(() => {
    if (!data) return 0
    return data.months.reduce(
      (m, r) => Math.max(m, Number(r.planned || 0), Number(r.paid || 0)),
      0,
    )
  }, [data])

  const hasAny = data && data.months.some((m) => Number(m.planned) > 0 || Number(m.paid) > 0)

  if (!loading && !hasAny) {
    return (
      <Card title={title ?? t('dashboard.payment_forecast')}>
        <Empty description={t('dashboard.payment_forecast_empty')} />
      </Card>
    )
  }

  return (
    <Card title={title ?? t('dashboard.payment_forecast')} loading={loading}>
      {data && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} md={8}>
              <Statistic
                title={t('dashboard.grand_planned')}
                value={Number(data.grand_planned)}
                prefix="¥"
                precision={2}
              />
            </Col>
            <Col xs={12} md={8}>
              <Statistic
                title={t('dashboard.grand_paid')}
                value={Number(data.grand_paid)}
                prefix="¥"
                precision={2}
                valueStyle={{ color: PAID_COLOR }}
              />
            </Col>
            <Col xs={12} md={8}>
              <Statistic
                title={t('dashboard.grand_remaining')}
                value={
                  Math.max(0, Number(data.grand_planned) - Number(data.grand_paid))
                }
                prefix="¥"
                precision={2}
                valueStyle={{ color: '#8B5E3C' }}
              />
            </Col>
          </Row>

          <BarChart months={data.months} maxValue={maxValue} />

          <Row style={{ marginTop: 12 }} gutter={16} align="middle">
            <Col>
              <LegendDot color={PLANNED_COLOR} label={t('dashboard.planned_amount')} />
            </Col>
            <Col>
              <LegendDot color={PAID_COLOR} label={t('dashboard.paid_amount')} />
            </Col>
          </Row>
        </>
      )}
    </Card>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
      <span
        style={{
          width: 12,
          height: 12,
          borderRadius: 2,
          background: color,
          display: 'inline-block',
        }}
      />
      <Typography.Text style={{ fontSize: 12 }}>{label}</Typography.Text>
    </span>
  )
}

interface BarChartProps {
  months: { month: string; planned: string; paid: string; remaining: string }[]
  maxValue: number
}

function BarChart({ months, maxValue }: BarChartProps) {
  const { t } = useTranslation()
  const width = 800
  const height = 260
  const padTop = 20
  const padBottom = 44
  const padLeft = 56
  const padRight = 16
  const innerW = width - padLeft - padRight
  const innerH = height - padTop - padBottom

  const scale = maxValue > 0 ? innerH / maxValue : 0
  const groupW = innerW / Math.max(months.length, 1)
  const barW = Math.min(24, (groupW - 8) / 2)

  const yTicks = 4
  const tickValues = Array.from({ length: yTicks + 1 }, (_, i) => (maxValue * i) / yTicks)

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{
        width: '100%',
        maxHeight: 320,
        border: '1px solid var(--color-border-default, #ddd)',
        borderRadius: 8,
        background: 'var(--color-bg-subtle, #fafafa)',
      }}
      role="img"
      aria-label={t('dashboard.payment_forecast')}
    >
      {tickValues.map((v, i) => {
        const y = padTop + innerH - v * scale
        return (
          <g key={i}>
            <line
              x1={padLeft}
              x2={padLeft + innerW}
              y1={y}
              y2={y}
              stroke="#E5E0DC"
              strokeDasharray={i === 0 ? '' : '3 3'}
            />
            <text
              x={padLeft - 6}
              y={y + 4}
              fontSize={11}
              textAnchor="end"
              fill="#6F6861"
            >
              {formatCompact(v)}
            </text>
          </g>
        )
      })}

      {months.map((m, i) => {
        const cx = padLeft + groupW * i + groupW / 2
        const plannedH = Number(m.planned) * scale
        const paidH = Number(m.paid) * scale
        return (
          <g key={m.month}>
            <title>
              {m.month} · {t('dashboard.planned_amount')}: {fmtAmount(m.planned)} ·{' '}
              {t('dashboard.paid_amount')}: {fmtAmount(m.paid)}
            </title>
            <rect
              x={cx - barW - 2}
              y={padTop + innerH - plannedH}
              width={barW}
              height={plannedH}
              fill={PLANNED_COLOR}
              rx={2}
            />
            <rect
              x={cx + 2}
              y={padTop + innerH - paidH}
              width={barW}
              height={paidH}
              fill={PAID_COLOR}
              rx={2}
            />
            <text
              x={cx}
              y={padTop + innerH + 18}
              fontSize={11}
              textAnchor="middle"
              fill="#6F6861"
            >
              {m.month}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function formatCompact(v: number): string {
  if (v === 0) return '0'
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`
  return v.toFixed(0)
}
