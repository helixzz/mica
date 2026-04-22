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
      void message.success('已确认')
      load()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const anomalyCols: ColumnsType<SKUAnomaly> = [
    {
      title: '物料',
      dataIndex: 'item_id',
      render: (id: string) => itemMap[id]?.name || id.slice(0, 8),
    },
    {
      title: '基准均价',
      dataIndex: 'baseline_avg_price',
      align: 'right',
    },
    {
      title: '本次价格',
      dataIndex: 'observed_price',
      align: 'right',
    },
    {
      title: '偏离',
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
      title: '严重度',
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
        <Button size="small" icon={<CheckOutlined />} onClick={() => ackAnomaly(r.id)}>
          已知悉
        </Button>
      ),
    },
  ]

  const priceCols: ColumnsType<SKUPriceRecord> = [
    { title: '日期', dataIndex: 'quotation_date' },
    {
      title: '物料',
      dataIndex: 'item_id',
      render: (id: string) => itemMap[id]?.name || id.slice(0, 8),
    },
    {
      title: '供应商',
      dataIndex: 'supplier_id',
      render: (id: string | null) => (id ? supplierMap[id]?.name : '-'),
    },
    {
      title: '价格',
      dataIndex: 'price',
      align: 'right',
      render: (v: string, r) => `${r.currency} ${v}`,
    },
    {
      title: '来源',
      dataIndex: 'source_type',
      render: (v: string) => <Tag>{v}</Tag>,
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        SKU 行情库
      </Typography.Title>

      <Tabs
        defaultActiveKey="market"
        items={[
          {
            key: 'market',
            label: <Space><LineChartOutlined />行情分析</Space>,
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setRecordOpen(true)}>
                    录入报价
                  </Button>
                </div>

      {anomalies.length > 0 && (
        <Alert
          type="warning"
          showIcon
          message={`检测到 ${anomalies.length} 条价格异常待处理`}
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

      <Card title={<Space><LineChartOutlined />选择物料对比价格走势</Space>}>
        <Space style={{ marginBottom: 12 }} wrap>
          <Select
            style={{ width: 200 }}
            allowClear
            placeholder="按分类筛选"
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
            placeholder="选择一个或多个 SKU 进行价格走势对比"
            value={selectedItems}
            onChange={setSelectedItems}
            options={items
              .filter((i) => !categoryFilter || (i as any).category_id === categoryFilter || !((i as any).category_id))
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
                      <Col span={8}><Statistic title="均价" value={bm.avg_price} valueStyle={{ fontSize: 14 }} /></Col>
                      <Col span={8}><Statistic title="最低" value={bm.min_price} valueStyle={{ fontSize: 14 }} /></Col>
                      <Col span={8}><Statistic title="最高" value={bm.max_price} valueStyle={{ fontSize: 14 }} /></Col>
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

      <Card title="近期全部报价">
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
        <Empty description="选择一个或多个 SKU 查看价格走势对比" />
      </div>
    )
  }

  if (chartData.length === 0) {
    return (
      <div style={{ marginTop: 24, textAlign: 'center', padding: '40px 0' }}>
        <Empty description="所选 SKU 暂无历史报价数据" />
      </div>
    )
  }

  const skuNames = [...new Set(chartData.map((d) => d.sku))]

  return (
    <div style={{ marginTop: 24, minHeight: 360 }}>
      <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
        价格走势对比（{skuNames.length} 个 SKU）
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
              <title>{`★ 采购成交\n${pp.po_number}\n${pp.date}: ¥${Number(pp.unit_price).toLocaleString()}\n${pp.supplier_name}`}</title>
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
  const { purchase_stats: ps, market_stats: ms, supplier_comparison: sc, purchase_history: ph } = insights

  const signalMap: Record<string, { color: string; text: string }> = {
    below_avg: { color: '#22C55E', text: '🟢 低于均价（买入时机）' },
    above_avg: { color: '#EF4444', text: '🔴 高于均价（建议观望）' },
    at_avg: { color: '#F59E0B', text: '🟡 接近均价' },
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small" title={`${itemName} — 价格分析`}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic title="采购次数" value={ps.count} suffix="次" />
          </Col>
          <Col span={6}>
            <Statistic title="采购均价" value={ps.avg_price ?? '-'} prefix="¥" precision={0} />
          </Col>
          <Col span={6}>
            <Statistic title="采购中位数" value={ps.median_price ?? '-'} prefix="¥" precision={0} />
          </Col>
          <Col span={6}>
            <Statistic title="采购总额" value={ps.total_amount} prefix="¥" precision={0} />
          </Col>
        </Row>
      </Card>

      {ms && (
        <Card size="small" title="行情信号">
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="当前行情" value={ms.current_price} prefix="¥" precision={0} />
            </Col>
            <Col span={6}>
              <Statistic
                title="vs 均价"
                value={ms.current_vs_avg_pct}
                suffix="%"
                precision={1}
                valueStyle={{ color: ms.current_vs_avg_pct > 0 ? '#EF4444' : '#22C55E' }}
                prefix={ms.current_vs_avg_pct > 0 ? '+' : ''}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="90日波动率"
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
        <Card size="small" title="供应商价格对比">
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
              <Typography.Text strong style={{ width: 100, textAlign: 'right' }}>¥{s.avg_price.toLocaleString()}</Typography.Text>
              <Tag>{s.count}次</Tag>
            </div>
          ))}
        </Card>
      )}

      {ph.length > 0 && (
        <Card size="small" title="采购历史明细">
          <Table
            dataSource={ph}
            rowKey={(r) => `${r.po_number}-${r.date}`}
            size="small"
            pagination={false}
            columns={[
              { title: '日期', dataIndex: 'date', width: 110 },
              { title: '供应商', dataIndex: 'supplier_name' },
              { title: '单价', dataIndex: 'unit_price', align: 'right' as const, render: (v: number) => `¥${v.toLocaleString()}` },
              { title: '数量', dataIndex: 'qty', align: 'right' as const },
              { title: '金额', dataIndex: 'amount', align: 'right' as const, render: (v: number) => `¥${v.toLocaleString()}` },
              { title: 'PO', dataIndex: 'po_number' },
              {
                title: '偏离行情',
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
          `已录入，但检测到价格异常：偏离基准 ${Number(anomaly.deviation_pct).toFixed(2)}%`,
          6
        )
      } else {
        void message.success('价格已录入')
      }
      onDone()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="录入报价" open={open} onCancel={onClose} onOk={submit} confirmLoading={busy} width={560}>
      <Form form={form} layout="vertical">
        <Form.Item name="item_id" label="物料 SKU" rules={[{ required: true }]}>
          <Select
            showSearch
            optionFilterProp="label"
            options={items.map((i) => ({ value: i.id, label: `${i.code} · ${i.name}` }))}
          />
        </Form.Item>
        <Form.Item name="supplier_id" label="供应商">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
          />
        </Form.Item>
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item name="price" label="价格（CNY）" rules={[{ required: true }]}>
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item name="quotation_date" label="报价日期" rules={[{ required: true }]}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item name="source_type" label="来源">
          <Select
            options={[
              { value: 'manual', label: '手工录入' },
              { value: 'quote', label: '供应商报价' },
              { value: 'actual_po', label: '实际订单' },
              { value: 'market_research', label: '市场调研' },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
