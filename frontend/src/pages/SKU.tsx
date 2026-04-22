import { CheckOutlined, LineChartOutlined, PlusOutlined, WarningOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  Form,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
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
  type Item,
  type SKUAnomaly,
  type SKUBenchmark,
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

  const load = () => {
    void api.items().then(setItems)
    void api.suppliers().then(setSuppliers)
    void api.listSKUAnomalies('new').then(setAnomalies)
    void api.listSKUPrices().then(setPrices)
    void api.listProcurementCategories().then(setCategories)
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          SKU 行情库
        </Typography.Title>
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
        />
      </Card>

      <Card title="近期全部报价">
        <Table<SKUPriceRecord>
          rowKey="id"
          dataSource={prices}
          columns={priceCols}
          pagination={{ pageSize: 20 }}
          size="small"
        />
      </Card>

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
}: {
  selectedItems: string[]
  trends: Record<string, SKUTrendPoint[]>
  itemMap: Record<string, Item>
  supplierMap: Record<string, Supplier>
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
        <ChartContent data={chartData} skuNames={skuNames} width={800} height={320} />
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
}: {
  data: { date: string; price: number; sku: string }[]
  skuNames: string[]
  width: number
  height: number
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
    </g>
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
