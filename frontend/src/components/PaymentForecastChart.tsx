import { LeftOutlined, RightOutlined, HomeOutlined } from '@ant-design/icons'
import { Button, Card, Col, Empty, Row, Space, Statistic, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PaymentForecast, type PaymentForecastMonth } from '@/api'
import { fmtAmount } from '@/utils/format'

const PLANNED_COLOR = '#B48A6A'
const PAID_COLOR = '#52c41a'
const TODAY_HIGHLIGHT_BG = 'rgba(139, 94, 60, 0.08)'

interface PaymentTrackerProps {
  title?: string
}

function currentMonthStr(): string {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

function shiftMonth(ym: string, delta: number): string {
  const [y, m] = ym.split('-').map(Number)
  const d = new Date(y, m - 1 + delta, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

export function PaymentTracker({ title }: PaymentTrackerProps) {
  const { t } = useTranslation()
  const today = currentMonthStr()
  const [anchor, setAnchor] = useState<string>(today)
  const [data, setData] = useState<PaymentForecast | null>(null)
  const [loading, setLoading] = useState(false)

  const pastMonths = 3
  const futureMonths = 3

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await api.getPaymentForecast({
        months: futureMonths + 1,
        past_months: pastMonths,
        anchor,
      })
      setData(result)
    } finally {
      setLoading(false)
    }
  }, [anchor])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  const maxValue = useMemo(() => {
    if (!data) return 0
    return data.months.reduce(
      (m, r) => Math.max(m, Number(r.planned || 0), Number(r.paid || 0)),
      0,
    )
  }, [data])

  const windowLabel = data
    ? t('dashboard.tracker_window_range', {
        from: data.months[0]?.month ?? '',
        to: data.months[data.months.length - 1]?.month ?? '',
      })
    : ''

  const isCurrentWindow = anchor === today
  const goPrev = () => setAnchor((a) => shiftMonth(a, -(pastMonths + futureMonths + 1)))
  const goNext = () => setAnchor((a) => shiftMonth(a, pastMonths + futureMonths + 1))
  const goToday = () => setAnchor(today)

  const breakdownColumns: ColumnsType<PaymentForecastMonth> = [
    {
      title: t('dashboard.forecast_month_col'),
      dataIndex: 'month',
      width: 120,
      render: (v: string) => (
        <Space>
          <Typography.Text>{v}</Typography.Text>
          {v === today && <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            ({t('dashboard.tracker_today_marker')})
          </Typography.Text>}
        </Space>
      ),
    },
    {
      title: t('dashboard.planned_amount'),
      dataIndex: 'planned',
      align: 'right',
      render: (v: string) => (
        <Typography.Text style={{ color: PLANNED_COLOR }}>
          {fmtAmount(v)}
        </Typography.Text>
      ),
    },
    {
      title: t('dashboard.paid_amount'),
      dataIndex: 'paid',
      align: 'right',
      render: (v: string) => (
        <Typography.Text style={{ color: PAID_COLOR }}>{fmtAmount(v)}</Typography.Text>
      ),
    },
    {
      title: t('dashboard.forecast_remaining_col'),
      dataIndex: 'remaining',
      align: 'right',
      render: (v: string) => fmtAmount(v),
    },
  ]

  return (
    <Card
      title={title ?? t('dashboard.payment_tracker')}
      extra={
        <Space>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {windowLabel}
          </Typography.Text>
          <Button
            size="small"
            icon={<LeftOutlined />}
            onClick={goPrev}
            title={t('dashboard.tracker_prev')}
          />
          <Button
            size="small"
            icon={<HomeOutlined />}
            onClick={goToday}
            disabled={isCurrentWindow}
            title={t('dashboard.tracker_today')}
          >
            {t('dashboard.tracker_today')}
          </Button>
          <Button
            size="small"
            icon={<RightOutlined />}
            onClick={goNext}
            title={t('dashboard.tracker_next')}
          />
        </Space>
      }
      loading={loading}
    >
      {data && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={12} md={6}>
              <Statistic
                title={t('dashboard.paid_to_date')}
                value={Number(data.paid_to_date)}
                prefix="¥"
                precision={2}
                valueStyle={{ color: PAID_COLOR }}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('dashboard.tracker_window_planned')}
                value={Number(data.grand_planned)}
                prefix="¥"
                precision={2}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('dashboard.tracker_window_paid')}
                value={Number(data.grand_paid)}
                prefix="¥"
                precision={2}
                valueStyle={{ color: PAID_COLOR }}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('dashboard.tracker_window_remaining')}
                value={Math.max(0, Number(data.grand_planned) - Number(data.grand_paid))}
                prefix="¥"
                precision={2}
                valueStyle={{ color: '#8B5E3C' }}
              />
            </Col>
          </Row>

          {data.months.length === 0 ||
          data.months.every((m) => Number(m.planned) === 0 && Number(m.paid) === 0) ? (
            <Empty description={t('dashboard.tracker_window_empty')} style={{ margin: '32px 0' }} />
          ) : (
            <>
              <BarChart months={data.months} maxValue={maxValue} todayMonth={today} />
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

          <Table<PaymentForecastMonth>
            style={{ marginTop: 16 }}
            rowKey="month"
            size="small"
            pagination={false}
            columns={breakdownColumns}
            dataSource={data.months}
            rowClassName={(r) => (r.month === today ? 'tracker-row-today' : '')}
            onRow={(r) =>
              r.month === today
                ? { style: { background: TODAY_HIGHLIGHT_BG } }
                : {}
            }
            summary={(rows) => {
              const totalPlanned = rows.reduce((s, r) => s + Number(r.planned || 0), 0)
              const totalPaid = rows.reduce((s, r) => s + Number(r.paid || 0), 0)
              const totalRemaining = Math.max(0, totalPlanned - totalPaid)
              return (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}>
                    <Typography.Text strong>
                      {t('dashboard.forecast_total_row')}
                    </Typography.Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={1} align="right">
                    <Typography.Text strong style={{ color: PLANNED_COLOR }}>
                      {fmtAmount(totalPlanned)}
                    </Typography.Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={2} align="right">
                    <Typography.Text strong style={{ color: PAID_COLOR }}>
                      {fmtAmount(totalPaid)}
                    </Typography.Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={3} align="right">
                    <Typography.Text strong>{fmtAmount(totalRemaining)}</Typography.Text>
                  </Table.Summary.Cell>
                </Table.Summary.Row>
              )
            }}
          />
        </>
      )}
    </Card>
  )
}

export const PaymentForecastChart = PaymentTracker

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
  todayMonth: string
}

function BarChart({ months, maxValue, todayMonth }: BarChartProps) {
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
      aria-label={t('dashboard.payment_tracker')}
    >
      {months.map((m, i) => {
        if (m.month !== todayMonth) return null
        const x = padLeft + groupW * i
        return (
          <rect
            key={`today-${m.month}`}
            x={x}
            y={padTop}
            width={groupW}
            height={innerH}
            fill="rgba(139, 94, 60, 0.08)"
          />
        )
      })}

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
        const isToday = m.month === todayMonth
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
              fill={isToday ? '#8B5E3C' : '#6F6861'}
              fontWeight={isToday ? 600 : 400}
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
