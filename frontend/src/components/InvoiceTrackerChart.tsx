import { LeftOutlined, RightOutlined, HomeOutlined } from '@ant-design/icons'
import { Button, Card, Col, Empty, Row, Space, Statistic, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type InvoiceForecast, type InvoiceForecastMonth } from '@/api'
import { fmtAmount } from '@/utils/format'

const INVOICEABLE_COLOR = '#B48A6A'
const INVOICED_COLOR = '#1677ff'
const PENDING_COLOR = '#d4380d'
const TODAY_HIGHLIGHT_BG = 'rgba(139, 94, 60, 0.08)'

interface InvoiceTrackerProps {
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

export function InvoiceTracker({ title }: InvoiceTrackerProps) {
  const { t } = useTranslation()
  const today = currentMonthStr()
  const [anchor, setAnchor] = useState<string>(today)
  const [data, setData] = useState<InvoiceForecast | null>(null)
  const [loading, setLoading] = useState(false)

  const pastMonths = 3
  const futureMonths = 3

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await api.getInvoiceForecast({
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
      (m, r) => Math.max(m, Number(r.invoiceable || 0), Number(r.invoiced || 0)),
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

  const breakdownColumns: ColumnsType<InvoiceForecastMonth> = [
    {
      title: t('dashboard.forecast_month_col'),
      dataIndex: 'month',
      width: 120,
      render: (v: string) => (
        <Space>
          <Typography.Text>{v}</Typography.Text>
          {v === today && (
            <Typography.Text type="secondary" style={{ fontSize: 11 }}>
              ({t('dashboard.tracker_today_marker')})
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: t('dashboard.invoiceable_amount'),
      dataIndex: 'invoiceable',
      align: 'right',
      render: (v: string) => (
        <Typography.Text style={{ color: INVOICEABLE_COLOR }}>{fmtAmount(v)}</Typography.Text>
      ),
    },
    {
      title: t('dashboard.invoiced_amount'),
      dataIndex: 'invoiced',
      align: 'right',
      render: (v: string) => (
        <Typography.Text style={{ color: INVOICED_COLOR }}>{fmtAmount(v)}</Typography.Text>
      ),
    },
    {
      title: t('dashboard.pending_to_invoice'),
      dataIndex: 'pending',
      align: 'right',
      render: (v: string) => (
        <Typography.Text style={{ color: PENDING_COLOR }}>{fmtAmount(v)}</Typography.Text>
      ),
    },
  ]

  return (
    <Card
      title={title ?? t('dashboard.invoice_tracker')}
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
                title={t('dashboard.invoiceable_to_date')}
                value={Number(data.grand_invoiceable_to_date)}
                prefix="¥"
                precision={2}
                valueStyle={{ color: INVOICEABLE_COLOR }}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('dashboard.invoiced_to_date')}
                value={Number(data.grand_invoiced_to_date)}
                prefix="¥"
                precision={2}
                valueStyle={{ color: INVOICED_COLOR }}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('dashboard.pending_to_invoice_to_date')}
                value={Number(data.grand_pending_to_date)}
                prefix="¥"
                precision={2}
                valueStyle={{ color: PENDING_COLOR }}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('dashboard.tracker_window_invoiced')}
                value={Number(data.window_invoiced)}
                prefix="¥"
                precision={2}
                valueStyle={{ color: INVOICED_COLOR }}
              />
            </Col>
          </Row>

          {data.months.length === 0 ||
          data.months.every((m) => Number(m.invoiceable) === 0 && Number(m.invoiced) === 0) ? (
            <Empty
              description={t('dashboard.invoice_tracker_empty')}
              style={{ margin: '32px 0' }}
            />
          ) : (
            <>
              <BarChart months={data.months} maxValue={maxValue} todayMonth={today} />
              <Row style={{ marginTop: 12 }} gutter={16} align="middle">
                <Col>
                  <LegendDot
                    color={INVOICEABLE_COLOR}
                    label={t('dashboard.invoiceable_amount')}
                  />
                </Col>
                <Col>
                  <LegendDot color={INVOICED_COLOR} label={t('dashboard.invoiced_amount')} />
                </Col>
              </Row>
            </>
          )}

          <Table<InvoiceForecastMonth>
            style={{ marginTop: 16 }}
            rowKey="month"
            size="small"
            pagination={false}
            columns={breakdownColumns}
            dataSource={data.months}
            rowClassName={(r) => (r.month === today ? 'tracker-row-today' : '')}
            onRow={(r) => (r.month === today ? { style: { background: TODAY_HIGHLIGHT_BG } } : {})}
            summary={(rows) => {
              const totalInvoiceable = rows.reduce((s, r) => s + Number(r.invoiceable || 0), 0)
              const totalInvoiced = rows.reduce((s, r) => s + Number(r.invoiced || 0), 0)
              const totalPending = rows.reduce((s, r) => s + Number(r.pending || 0), 0)
              return (
                <Table.Summary.Row>
                  <Table.Summary.Cell index={0}>
                    <Typography.Text strong>{t('dashboard.forecast_total_row')}</Typography.Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={1} align="right">
                    <Typography.Text strong style={{ color: INVOICEABLE_COLOR }}>
                      {fmtAmount(totalInvoiceable)}
                    </Typography.Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={2} align="right">
                    <Typography.Text strong style={{ color: INVOICED_COLOR }}>
                      {fmtAmount(totalInvoiced)}
                    </Typography.Text>
                  </Table.Summary.Cell>
                  <Table.Summary.Cell index={3} align="right">
                    <Typography.Text strong style={{ color: PENDING_COLOR }}>
                      {fmtAmount(totalPending)}
                    </Typography.Text>
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
  months: InvoiceForecastMonth[]
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
      aria-label={t('dashboard.invoice_tracker')}
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
            <text x={padLeft - 6} y={y + 4} fontSize={11} textAnchor="end" fill="#6F6861">
              {formatCompact(v)}
            </text>
          </g>
        )
      })}

      {months.map((m, i) => {
        const cx = padLeft + groupW * i + groupW / 2
        const invoiceableH = Number(m.invoiceable) * scale
        const invoicedH = Number(m.invoiced) * scale
        const isToday = m.month === todayMonth
        return (
          <g key={m.month}>
            <title>
              {m.month} · {t('dashboard.invoiceable_amount')}: {fmtAmount(m.invoiceable)} ·{' '}
              {t('dashboard.invoiced_amount')}: {fmtAmount(m.invoiced)}
            </title>
            <rect
              x={cx - barW - 2}
              y={padTop + innerH - invoiceableH}
              width={barW}
              height={invoiceableH}
              fill={INVOICEABLE_COLOR}
              rx={2}
            />
            <rect
              x={cx + 2}
              y={padTop + innerH - invoicedH}
              width={barW}
              height={invoicedH}
              fill={INVOICED_COLOR}
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
