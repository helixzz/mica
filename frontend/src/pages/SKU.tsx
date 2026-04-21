import { CheckOutlined, PlusOutlined, WarningOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
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
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  api,
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
  const [selectedItem, setSelectedItem] = useState<string | null>(null)
  const [benchmark, setBenchmark] = useState<SKUBenchmark | null>(null)
  const [trend, setTrend] = useState<SKUTrendPoint[]>([])
  const [recordOpen, setRecordOpen] = useState(false)

  const load = () => {
    void api.items().then(setItems)
    void api.suppliers().then(setSuppliers)
    void api.listSKUAnomalies('new').then(setAnomalies)
    void api.listSKUPrices().then(setPrices)
  }

  useEffect(load, [])

  useEffect(() => {
    if (!selectedItem) {
      setBenchmark(null)
      setTrend([])
      return
    }
    void api.getSKUBenchmark(selectedItem).then(setBenchmark)
    void api.getSKUTrend(selectedItem).then(setTrend)
  }, [selectedItem])

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

      <Card title="选择物料查看价格基准与趋势">
        <Select
          style={{ width: 360 }}
          placeholder="选择 SKU"
          value={selectedItem || undefined}
          onChange={setSelectedItem}
          options={items.map((i) => ({ value: i.id, label: `${i.code} · ${i.name}` }))}
          showSearch
          optionFilterProp="label"
          allowClear
        />
        {benchmark && (
          <Row gutter={16} style={{ marginTop: 16 }}>
            <Col span={4}>
              <Statistic title="样本数" value={benchmark.sample_size} suffix={`条`} />
            </Col>
            <Col span={5}>
              <Statistic title={`${benchmark.window_days} 日均价`} value={benchmark.avg_price} />
            </Col>
            <Col span={5}>
              <Statistic title="中位数" value={benchmark.median_price} />
            </Col>
            <Col span={5}>
              <Statistic title="最低" value={benchmark.min_price} />
            </Col>
            <Col span={5}>
              <Statistic title="最高" value={benchmark.max_price} />
            </Col>
          </Row>
        )}
        {selectedItem && !benchmark && (
          <Typography.Text type="secondary" style={{ marginLeft: 16 }}>
            尚无历史报价
          </Typography.Text>
        )}
        {trend.length > 0 && (
          <Table
            rowKey={(r) => `${r.date}-${r.supplier_id || 'no'}-${r.price}`}
            style={{ marginTop: 16 }}
            size="small"
            dataSource={trend}
            pagination={false}
            columns={[
              { title: '日期', dataIndex: 'date', width: 140 },
              { title: '价格', dataIndex: 'price', align: 'right' },
              {
                title: '供应商',
                dataIndex: 'supplier_id',
                render: (id: string | null) => (id ? supplierMap[id]?.name : '-'),
              },
              { title: '来源', dataIndex: 'source_type' },
            ]}
          />
        )}
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
          if (selectedItem) {
            void api.getSKUBenchmark(selectedItem).then(setBenchmark)
            void api.getSKUTrend(selectedItem).then(setTrend)
          }
        }}
      />
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
