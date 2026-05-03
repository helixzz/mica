import { CheckOutlined, DatabaseOutlined, EditOutlined, DeleteOutlined, LineChartOutlined, PlusOutlined, WarningOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  api,
  type ClassificationItem,
  flattenCategoryTree,
  type Item,
  type SKUAnomaly,
  type SKUBenchmark,
  type SKUInsights,
  type SKUPriceRecord,
  type SKUTrendPoint,
  type Supplier,
} from '@/api'
import { extractError } from '@/api/client'
import { fmtAmount, fmtQty } from '@/utils/format'

export function SKUPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [anomalies, setAnomalies] = useState<SKUAnomaly[]>([])
  const [prices, setPrices] = useState<SKUPriceRecord[]>([])
  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [benchmarks, setBenchmarks] = useState<Record<string, SKUBenchmark>>({})
  const [trends, setTrends] = useState<Record<string, SKUTrendPoint[]>>({})
  const [recordOpen, setRecordOpen] = useState(false)
  const [categories, setCategories] = useState<ClassificationItem[]>([])
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [insights, setInsights] = useState<SKUInsights | null>(null)

  const load = () => {
    void api.items().then(setItems)
    void api.suppliers().then(setSuppliers)
    void api.listSKUAnomalies('new').then(setAnomalies)
    void api.listSKUPrices().then(setPrices)
    void api.getCategoryTree().then((tree) => setCategories(flattenCategoryTree(tree)))
  }

  useEffect(load, [])

  useEffect(() => {
    if (selectedItems.length === 0) {
      setBenchmarks({})
      setTrends({})
      return
    }
    const newBenchmarks: Record<string, SKUBenchmark> = {}
    const newTrends: Record<string, SKUTrendPoint[]> = {}
    Promise.all(
      selectedItems.map(async (itemId) => {
        const [bm, tr] = await Promise.all([
          api.getSKUBenchmark(itemId).catch(() => null),
          api.getSKUTrend(itemId).catch(() => []),
        ])
        if (bm) newBenchmarks[itemId] = bm
        newTrends[itemId] = tr
      }),
    ).then(() => {
      setBenchmarks(newBenchmarks)
      setTrends(newTrends)
    })

    if (selectedItems.length === 1) {
      void api.getSKUInsights(selectedItems[0]).then(setInsights).catch(() => setInsights(null))
    } else {
      setInsights(null)
    }
  }, [selectedItems])

  const itemMap = Object.fromEntries(items.map((i) => [i.id, i]))
  const supplierMap = Object.fromEntries(suppliers.map((s) => [s.id, s]))

  const ackAnomaly = async (id: string) => {
    try {
      await api.acknowledgeAnomaly(id)
      void message.success(t('sku.confirmed'))
      load()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const anomalyCols: ColumnsType<SKUAnomaly> = [
    {
      title: t('sku.item_col'),
      dataIndex: 'item_id',
      render: (id: string) => itemMap[id]?.name || id.slice(0, 8),
    },
    {
      title: t('sku.benchmark_avg'),
      dataIndex: 'baseline_avg_price',
      align: 'right',
      render: (v: string) => fmtAmount(v),
    },
    {
      title: t('sku.this_price'),
      dataIndex: 'observed_price',
      align: 'right',
      render: (v: string) => fmtAmount(v),
    },
    {
      title: t('sku.deviation'),
      dataIndex: 'deviation_pct',
      render: (v: string) => {
        const n = Number(v)
        return (
          <Tag color={n > 0 ? 'red' : 'blue'}>
            {n > 0 ? '+' : ''}
            {n.toFixed(2)}%
          </Tag>
        )
      },
    },
    {
      title: t('sku.severity'),
      dataIndex: 'severity',
      render: (v: string) => (
        <Tag color={v === 'critical' ? 'error' : 'warning'} icon={<WarningOutlined />}>
          {v}
        </Tag>
      ),
    },
    {
      title: '',
      render: (_, r) => (
        <Button size="small" icon={<CheckOutlined />} onClick={() => ackAnomaly(r.id)}>{t('sku.acknowledged')}
        </Button>
      ),
    },
  ]

  const priceCols: ColumnsType<SKUPriceRecord> = [
    { title: t('sku.date_col'), dataIndex: 'quotation_date' },
    {
      title: t('sku.item_col'),
      dataIndex: 'item_id',
      render: (id: string) => itemMap[id]?.name || id.slice(0, 8),
    },
    {
      title: t('sku.supplier_col'),
      dataIndex: 'supplier_id',
      render: (id: string | null) => (id ? supplierMap[id]?.name : '-'),
    },
    {
      title: t('sku.price_col'),
      dataIndex: 'price',
      align: 'right',
      render: (v: string) => fmtAmount(v),
    },
    {
      title: t('sku.source_col'),
      dataIndex: 'source_type',
      render: (v: string) => <Tag>{v}</Tag>,
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>{t('sku.title')}
      </Typography.Title>

      <Tabs
        defaultActiveKey="market"
        items={[
          {
            key: 'market',
            label: <Space><LineChartOutlined />{t('sku.market_analysis_tab')}</Space>,
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setRecordOpen(true)}>{t('sku.record_price')}
                  </Button>
                </div>

      {anomalies.length > 0 && (
        <Alert
          type="warning"
          showIcon
          message={t('sku.anomaly_alert', { count: anomalies.length })}
          description={
            <Table<SKUAnomaly>
              rowKey="id"
              dataSource={anomalies}
              columns={anomalyCols}
              pagination={false}
              size="small"
              style={{ marginTop: 8 }}
            />
          }
        />
      )}

      <Card title={<Space><LineChartOutlined />{t('sku.select_to_compare')}</Space>}>
        <Space style={{ marginBottom: 12 }} wrap>
          <Select
            style={{ width: 200 }}
            allowClear
            placeholder={t('sku.filter_by_category')}
            value={categoryFilter}
            onChange={setCategoryFilter}
            options={categories.map((c) => ({
              value: c.id,
              label: c.level === 2 ? `  └ ${c.label_zh}` : c.label_zh,
            }))}
          />
          <Select
            mode="multiple"
            style={{ width: 520 }}
            placeholder={t('sku.select_sku_placeholder')}
            value={selectedItems}
            onChange={setSelectedItems}
            options={items
              .filter((i) => !categoryFilter || i.category_id === categoryFilter || !i.category_id)
              .map((i) => ({ value: i.id, label: `${i.code} · ${i.name}` }))}
            showSearch
            optionFilterProp="label"
            allowClear
            maxTagCount={6}
          />
        </Space>

        {selectedItems.length > 0 && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            {selectedItems.map((itemId) => {
              const bm = benchmarks[itemId]
              const name = itemMap[itemId]?.name || itemId.slice(0, 8)
              if (!bm) return null
              return (
                <Col key={itemId} xs={24} md={12} lg={8} style={{ marginBottom: 12 }}>
                  <Card size="small" title={name} type="inner">
                    <Row gutter={8}>
                      <Col span={8}><Statistic title={t('sku.avg')} value={bm.avg_price} prefix="¥" precision={2} valueStyle={{ fontSize: 14 }} /></Col>
                      <Col span={8}><Statistic title={t('sku.min')} value={bm.min_price} prefix="¥" precision={2} valueStyle={{ fontSize: 14 }} /></Col>
                      <Col span={8}><Statistic title={t('sku.max')} value={bm.max_price} prefix="¥" precision={2} valueStyle={{ fontSize: 14 }} /></Col>
                    </Row>
                  </Card>
                </Col>
              )
            })}
          </Row>
        )}

        <PriceTrendChart
          selectedItems={selectedItems}
          trends={trends}
          itemMap={itemMap}
          supplierMap={supplierMap}
          purchasePoints={insights?.purchase_history || []}
        />
      </Card>

      {insights && selectedItems.length === 1 && (
        <InsightsPanel insights={insights} itemName={itemMap[selectedItems[0]]?.name || ''} />
      )}

      <Card title={t('sku.recent_prices')}>
        <Table<SKUPriceRecord>
          rowKey="id"
          dataSource={prices}
          columns={priceCols}
          pagination={{ pageSize: 20 }}
          size="small"
        />
      </Card>

              </Space>
            ),
          },
        ]}
      />

      <RecordPriceModal
        open={recordOpen}
        items={items}
        suppliers={suppliers}
        onClose={() => setRecordOpen(false)}
        onDone={() => {
          setRecordOpen(false)
          load()
          selectedItems.forEach((itemId) => {
            void api.getSKUBenchmark(itemId).then((bm) => {
              if (bm) setBenchmarks((prev) => ({ ...prev, [itemId]: bm }))
            })
            void api.getSKUTrend(itemId).then((tr) =>
              setTrends((prev) => ({ ...prev, [itemId]: tr })),
            )
          })
        }}
      />
    </Space>
  )
}

const CHART_COLORS = [
  '#8B5E3C', '#3B82F6', '#22C55E', '#F59E0B', '#EF4444',
  '#8B5CF6', '#06B6D4', '#EC4899', '#84CC16', '#F97316',
]

function PriceTrendChart({
  selectedItems,
  trends,
  itemMap,
  supplierMap,
  purchasePoints,
}: {
  selectedItems: string[]
  trends: Record<string, SKUTrendPoint[]>
  itemMap: Record<string, Item>
  supplierMap: Record<string, Supplier>
  purchasePoints: { date: string; unit_price: number; po_number: string; supplier_name: string }[]
}) {
  const { t } = useTranslation()
  const chartData = useMemo(() => {
    const rows: { date: string; price: number; sku: string }[] = []
    selectedItems.forEach((itemId) => {
      const points = trends[itemId] || []
      const name = itemMap[itemId]?.name || itemId.slice(0, 8)
      points.forEach((p) => {
        rows.push({ date: p.date, price: Number(p.price), sku: name })
      })
    })
    rows.sort((a, b) => a.date.localeCompare(b.date))
    return rows
  }, [selectedItems, trends, itemMap])

  if (selectedItems.length === 0) {
    return (
      <div style={{ marginTop: 24, textAlign: 'center', padding: '40px 0' }}>
        <Empty description={t('sku.trend_empty')} />
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div style={{ marginTop: 24, textAlign: 'center', padding: '40px 0' }}>
        <Empty description={t('sku.no_price_data')} />
      </div>
    )
  }

  const skuNames = [...new Set(chartData.map((d) => d.sku))]

  return (
    <div style={{ marginTop: 24, minHeight: 360 }}>
      <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
        {t('sku.trend_title', { count: skuNames.length })}
      </Typography.Text>
      <svg viewBox={`0 0 800 320`} style={{ width: '100%', maxHeight: 400, border: '1px solid var(--color-border-default, #ddd)', borderRadius: 8, background: 'var(--color-bg-subtle, #fafafa)' }}>
        <ChartContent data={chartData} skuNames={skuNames} width={800} height={320} purchasePoints={purchasePoints} />
      </svg>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 8 }}>
        {skuNames.map((name, i) => (
          <Space key={name} size={4}>
            <div style={{ width: 12, height: 12, borderRadius: 2, background: CHART_COLORS[i % CHART_COLORS.length] }} />
            <Typography.Text style={{ fontSize: 12 }}>{name}</Typography.Text>
          </Space>
        ))}
      </div>
    </div>
  )
}

function ChartContent({
  data,
  skuNames,
  width,
  height,
  purchasePoints,
}: {
  data: { date: string; price: number; sku: string }[]
  skuNames: string[]
  width: number
  height: number
  purchasePoints: { date: string; unit_price: number; po_number: string; supplier_name: string }[]
}) {
  const { t } = useTranslation()
  const padding = { top: 20, right: 20, bottom: 40, left: 60 }
  const plotW = width - padding.left - padding.right
  const plotH = height - padding.top - padding.bottom

  const allDates = [...new Set(data.map((d) => d.date))].sort()
  const allPrices = data.map((d) => d.price)
  const minPrice = Math.min(...allPrices) * 0.95
  const maxPrice = Math.max(...allPrices) * 1.05
  const priceRange = maxPrice - minPrice || 1

  const xScale = (date: string) => {
    const idx = allDates.indexOf(date)
    return padding.left + (idx / Math.max(allDates.length - 1, 1)) * plotW
  }
  const yScale = (price: number) =>
    padding.top + plotH - ((price - minPrice) / priceRange) * plotH

  const yTicks = 5
  const yStep = priceRange / yTicks

  return (
    <g>
      {Array.from({ length: yTicks + 1 }, (_, i) => {
        const val = minPrice + i * yStep
        const y = yScale(val)
        return (
          <g key={i}>
            <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#e5e5e5" strokeWidth={0.5} />
            <text x={padding.left - 8} y={y + 4} textAnchor="end" fontSize={10} fill="#999">
              {val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val.toFixed(0)}
            </text>
          </g>
        )
      })}

      {allDates.map((date, i) => {
        if (allDates.length > 15 && i % Math.ceil(allDates.length / 10) !== 0) return null
        const x = xScale(date)
        return (
          <text key={date} x={x} y={height - 8} textAnchor="middle" fontSize={10} fill="#999">
            {date.slice(5)}
          </text>
        )
      })}

      {skuNames.map((sku, si) => {
        const points = data.filter((d) => d.sku === sku).sort((a, b) => a.date.localeCompare(b.date))
        if (points.length === 0) return null
        const color = CHART_COLORS[si % CHART_COLORS.length]
        const pathD = points
          .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(p.date).toFixed(1)} ${yScale(p.price).toFixed(1)}`)
          .join(' ')
        return (
          <g key={sku}>
            <path d={pathD} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
            {points.map((p, i) => (
              <circle key={i} cx={xScale(p.date)} cy={yScale(p.price)} r={3} fill={color} stroke="white" strokeWidth={1}>
                <title>{`${sku}\n${p.date}: ¥${p.price.toLocaleString()}`}</title>
              </circle>
            ))}
          </g>
        )
      })}

      {purchasePoints.map((pp, i) => {
        const dateStr = pp.date
        if (!allDates.includes(dateStr)) return null
        const x = xScale(dateStr)
        const y = yScale(Number(pp.unit_price))
        return (
          <g key={`purchase-${i}`}>
            <circle cx={x} cy={y} r={7} fill="#3B82F6" stroke="white" strokeWidth={2} opacity={0.9}>
              <title>{`★ PO ${pp.po_number}\n${pp.date}: ¥${Number(pp.unit_price).toLocaleString()}\n${pp.supplier_name}`}</title>
            </circle>
            <text x={x} y={y - 12} textAnchor="middle" fontSize={9} fill="#3B82F6" fontWeight={600}>
              ★
            </text>
          </g>
        )
      })}
    </g>
  )
}

function InsightsPanel({ insights, itemName }: { insights: SKUInsights; itemName: string }) {
  const { t } = useTranslation()
  const { purchase_stats: ps, market_stats: ms, supplier_comparison: sc, purchase_history: ph } = insights

  const signalMap: Record<string, { color: string; text: string }> = {
    below_avg: { color: '#22C55E', text: t('sku.buy_signal_below') },
    above_avg: { color: '#EF4444', text: t('sku.buy_signal_above') },
    at_avg: { color: '#F59E0B', text: t('sku.buy_signal_at') },
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small" title={`${itemName} — ${t('sku.price_analysis')}`}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic title={t('sku.purchase_count')} value={ps.count} suffix={t('sku.times')} />
          </Col>
          <Col span={6}>
            <Statistic title={t('sku.purchase_avg')} value={ps.avg_price ?? '-'} prefix="¥" precision={2} />
          </Col>
          <Col span={6}>
            <Statistic title={t('sku.purchase_median')} value={ps.median_price ?? '-'} prefix="¥" precision={2} />
          </Col>
          <Col span={6}>
            <Statistic title={t('sku.purchase_total')} value={ps.total_amount} prefix="¥" precision={2} />
          </Col>
        </Row>
      </Card>

      {ms && (
        <Card size="small" title={t('sku.market_signal')}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title={t('sku.current_price')} value={ms.current_price} prefix="¥" precision={2} />
            </Col>
            <Col span={6}>
              <Statistic
                title={t('sku.vs_avg')}
                value={ms.current_vs_avg_pct}
                suffix="%"
                precision={1}
                valueStyle={{ color: ms.current_vs_avg_pct > 0 ? '#EF4444' : '#22C55E' }}
                prefix={ms.current_vs_avg_pct > 0 ? '+' : ''}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title={t('sku.volatility')}
                value={ms.volatility_pct}
                suffix="%"
                valueStyle={ms.volatility_pct > 15 ? { color: '#EF4444' } : undefined}
              />
            </Col>
            <Col span={6}>
              <div style={{ marginTop: 8 }}>
                <Tag color={signalMap[ms.signal]?.color || 'default'} style={{ fontSize: 14, padding: '4px 12px' }}>
                  {signalMap[ms.signal]?.text || ms.signal}
                </Tag>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {sc.length > 0 && (
        <Card size="small" title={t('sku.supplier_comparison')}>
          {sc.map((s) => (
            <div key={s.supplier_name} style={{ display: 'flex', alignItems: 'center', marginBottom: 8, gap: 12 }}>
              <Typography.Text style={{ width: 180, flexShrink: 0 }}>{s.supplier_name}</Typography.Text>
              <div style={{ flex: 1, background: '#f0f0f0', borderRadius: 4, height: 20, position: 'relative' }}>
                <div
                  style={{
                    width: `${Math.min(100, (s.avg_price / Math.max(...sc.map((x) => x.avg_price))) * 100)}%`,
                    background: '#8B5E3C',
                    borderRadius: 4,
                    height: '100%',
                  }}
                />
              </div>
               <Typography.Text strong style={{ width: 100, textAlign: 'right' }}>{fmtAmount(s.avg_price)}</Typography.Text>
              <Tag>{s.count} {t('sku.times')}</Tag>
            </div>
          ))}
        </Card>
      )}

      {ph.length > 0 && (
        <Card size="small" title={t('sku.purchase_history')}>
          <Table
            dataSource={ph}
            rowKey={(r) => `${r.po_number}-${r.date}`}
            size="small"
            pagination={false}
            columns={[
              { title: t('sku.date_col'), dataIndex: 'date', width: 110 },
              { title: t('sku.supplier_col'), dataIndex: 'supplier_name' },
               { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right' as const, render: (v: number) => fmtAmount(v) },
               { title: t('field.qty'), dataIndex: 'qty', align: 'right' as const, render: (v: string) => fmtQty(v) },
               { title: t('field.amount'), dataIndex: 'amount', align: 'right' as const, render: (v: number) => fmtAmount(v) },
              { title: 'PO', dataIndex: 'po_number' },
              {
                title: t('sku.deviation'),
                dataIndex: 'deviation_pct',
                align: 'right' as const,
                render: (v: number | null) =>
                  v !== null ? (
                    <Tag color={v > 0 ? 'red' : v < -5 ? 'green' : 'default'}>
                      {v > 0 ? '+' : ''}{v.toFixed(1)}%
                    </Tag>
                  ) : '-',
              },
            ]}
          />
        </Card>
      )}
    </Space>
  )
}

function RecordPriceModal({
  open,
  items,
  suppliers,
  onClose,
  onDone,
}: {
  open: boolean
  items: Item[]
  suppliers: Supplier[]
  onClose: () => void
  onDone: () => void
}) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      form.resetFields()
      form.setFieldsValue({ quotation_date: dayjs(), source_type: 'manual' })
    }
  }, [open, form])

  const submit = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const { anomaly } = await api.recordSKUPrice({
        item_id: values.item_id,
        price: Number(values.price),
        quotation_date: values.quotation_date.format('YYYY-MM-DD'),
        supplier_id: values.supplier_id || null,
        source_type: values.source_type,
        notes: values.notes || null,
      })
      if (anomaly) {
        void message.warning(
          t('sku.anomaly_warning', { pct: Number(anomaly.deviation_pct).toFixed(2) }),
          6
        )
      } else {
        void message.success(t('sku.price_recorded'))
      }
      onDone()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={t('sku.record_price_title')} open={open} onCancel={onClose} onOk={submit} confirmLoading={busy} width={560}>
      <Form form={form} layout="vertical">
        <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          {t('sku.record_price_form_help')}
        </Typography.Text>
        <Form.Item name="item_id" label={t('sku.item_sku_label')} help={t('sku.item_help')} rules={[{ required: true }]}>
          <Select
            showSearch
            optionFilterProp="label"
            options={items.map((i) => ({ value: i.id, label: `${i.code} · ${i.name}` }))}
          />
        </Form.Item>
        <Form.Item name="supplier_id" label={t('field.supplier')} help={t('sku.supplier_help')}>
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
          />
        </Form.Item>
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="price" label={t('sku.price_cny')} help={t('sku.price_help')} rules={[{ required: true }]}> 
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="quotation_date" label={t('sku.quotation_date')} help={t('sku.quotation_date_help')} rules={[{ required: true }]}> 
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="source_type" label={t('sku.source_type')} help={t('sku.source_type_help')}>
          <Select
            options={[
              { value: 'manual', label: t('sku.source_manual') },
              { value: 'quote', label: t('sku.source_quote') },
              { value: 'actual_po', label: t('sku.source_actual_po') },
              { value: 'market_research', label: t('sku.source_market') },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
