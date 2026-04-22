import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Col, DatePicker, Form, Input, InputNumber, Row, Select, Space, Table, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type ClassificationItem, flattenCategoryTree, type Item, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'

interface LineForm {
  key: number
  line_no: number
  item_id: string | null
  item_name: string
  specification: string
  supplier_id: string | null
  qty: number
  uom: string
  unit_price: number
}

export function PREditPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const { user } = useAuth()
  const isRequester = user?.role === 'requester'
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [companies, setCompanies] = useState<{ id: string; name_zh: string }[]>([])
  const [costCenters, setCostCenters] = useState<{ id: string; label_zh: string }[]>([])
  const [expenseTypes, setExpenseTypes] = useState<{ id: string; label_zh: string }[]>([])
  const [procCategories, setProcCategories] = useState<ClassificationItem[]>([])
  const [refPrices, setRefPrices] = useState<Record<string, { latest_price: number | null; avg_price: number | null }>>({})
  const [lines, setLines] = useState<LineForm[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    void api.suppliers().then(setSuppliers)
    void api.items().then(setItems)
    void api.companies().then(setCompanies)
    void api.listCostCenters().then(setCostCenters)
    void api.listLookupValues('expense_type').then(setExpenseTypes)
    void api.getCategoryTree().then((tree) => setProcCategories(flattenCategoryTree(tree)))
  }, [])

  useEffect(() => {
    if (!id) return
    void (async () => {
      const pr = await api.getPR(id)
      form.setFieldsValue({
        title: pr.title,
        business_reason: pr.business_reason,
        currency: pr.currency,
        required_date: pr.required_date ? dayjs(pr.required_date) : undefined,
        company_id: pr.company_id,
        cost_center_id: pr.cost_center_id,
        expense_type_id: pr.expense_type_id,
        procurement_category_id: pr.procurement_category_id,
      })
      const loadedLines = (pr.items || []).map((item: any, idx: number) => ({
        key: idx + 1,
        line_no: item.line_no || idx + 1,
        item_id: item.item_id,
        item_name: item.item_name,
        specification: item.specification || '',
        supplier_id: item.supplier_id,
        qty: Number(item.qty),
        uom: item.uom || 'EA',
        unit_price: Number(item.unit_price || 0),
      }))
      setLines(loadedLines)

      const itemIds = loadedLines.map((l: LineForm) => l.item_id).filter(Boolean).join(',')
      if (itemIds) {
        void client
          .get<Record<string, { latest_price: number | null; avg_price: number | null }>>(`/sku/reference-prices?item_ids=${itemIds}`)
          .then((r) => setRefPrices(r.data))
          .catch(() => {})
      }
      setLoaded(true)
    })()
  }, [id, form])

  const addLine = () => {
    setLines((ls) => [
      ...ls,
      { key: Date.now(), line_no: ls.length + 1, item_id: null, item_name: '', specification: '', supplier_id: null, qty: 1, uom: 'EA', unit_price: 0 },
    ])
  }

  const removeLine = (key: number) => {
    setLines((ls) => ls.filter((l) => l.key !== key).map((l, i) => ({ ...l, line_no: i + 1 })))
  }

  const updateLine = <K extends keyof LineForm>(key: number, field: K, value: LineForm[K]) => {
    setLines((ls) =>
      ls.map((l) => {
        if (l.key !== key) return l
        const updated = { ...l, [field]: value }
        if (field === 'item_id' && value) {
          const item = items.find((i) => i.id === value)
          if (item) {
            updated.item_name = item.name
            updated.specification = item.specification || ''
          }
          void client
            .get<Record<string, { latest_price: number | null; avg_price: number | null }>>(`/sku/reference-prices?item_ids=${value}`)
            .then((r) => setRefPrices((prev) => ({ ...prev, ...r.data })))
            .catch(() => {})
        }
        return updated
      }),
    )
  }

  const total = lines.reduce((s, l) => s + l.qty * (l.unit_price || 0), 0)

  const onSave = async () => {
    try {
      const values = await form.validateFields()
      if (lines.length === 0) {
        void message.error('请至少添加一行明细')
        return
      }
      setSubmitting(true)
      await client.patch(`/purchase-requisitions/${id}`, {
        title: values.title,
        business_reason: values.business_reason,
        currency: values.currency || 'CNY',
        required_date: values.required_date?.format('YYYY-MM-DD') ?? null,
        company_id: values.company_id || null,
        cost_center_id: values.cost_center_id || null,
        expense_type_id: values.expense_type_id || null,
        procurement_category_id: values.procurement_category_id || null,
        items: lines.map((l) => ({
          line_no: l.line_no,
          item_id: l.item_id,
          item_name: l.item_name,
          specification: l.specification,
          supplier_id: l.supplier_id,
          qty: l.qty,
          uom: l.uom,
          unit_price: l.unit_price || 0,
        })),
      })
      void message.success('已保存')
      navigate(`/purchase-requisitions/${id}`)
    } catch (e) {
      void message.error(extractError(e).detail || '保存失败')
    } finally {
      setSubmitting(false)
    }
  }

  if (!loaded) return <div>{t('message.loading')}</div>

  const columns = [
    { title: '#', dataIndex: 'line_no', width: 40 },
    {
      title: t('field.item_name'),
      width: 280,
      render: (_: unknown, r: LineForm) => (
        <Space direction="vertical" size={0} style={{ width: '100%' }}>
          <Select
            style={{ width: '100%' }}
            placeholder={isRequester ? '选择物料' : t('placeholder.select_item')}
            value={r.item_id ?? undefined}
            onChange={(v) => updateLine(r.key, 'item_id', v)}
            options={items.map((it) => ({ value: it.id, label: `${it.code} · ${it.name}` }))}
            showSearch optionFilterProp="label" allowClear
          />
          {r.item_id && refPrices[r.item_id] && (
            <Typography.Text type="secondary" style={{ fontSize: 11 }}>
              参考：最近 ¥{refPrices[r.item_id].latest_price?.toLocaleString() ?? '-'}
              {refPrices[r.item_id].avg_price ? ` · 均价 ¥${refPrices[r.item_id].avg_price?.toLocaleString()}` : ''}
            </Typography.Text>
          )}
        </Space>
      ),
    },
    ...(!isRequester ? [{
      title: t('field.supplier'),
      width: 200,
      render: (_: unknown, r: LineForm) => (
        <Select
          style={{ width: '100%' }}
          value={r.supplier_id ?? undefined}
          onChange={(v: string) => updateLine(r.key, 'supplier_id', v)}
          options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
          showSearch optionFilterProp="label" allowClear
        />
      ),
    }] : []),
    {
      title: t('field.qty'), width: 90,
      render: (_: unknown, r: LineForm) => (
        <InputNumber min={0.0001} value={r.qty} onChange={(v) => updateLine(r.key, 'qty', Number(v ?? 0))} style={{ width: '100%' }} />
      ),
    },
    {
      title: t('field.uom'), width: 70,
      render: (_: unknown, r: LineForm) => (
        <Input value={r.uom} onChange={(e) => updateLine(r.key, 'uom', e.target.value)} />
      ),
    },
    {
      title: isRequester ? <span>{t('field.unit_price')}<br /><Typography.Text type="secondary" style={{ fontSize: 10 }}>可选</Typography.Text></span> : t('field.unit_price'),
      width: 130,
      render: (_: unknown, r: LineForm) => (
        <InputNumber min={0} value={r.unit_price || undefined} onChange={(v) => updateLine(r.key, 'unit_price', Number(v ?? 0))} style={{ width: '100%' }} placeholder={isRequester ? '可选' : undefined} />
      ),
    },
    {
      title: t('field.amount'), width: 100, align: 'right' as const,
      render: (_: unknown, r: LineForm) => { const a = r.qty * (r.unit_price || 0); return a > 0 ? `¥${a.toLocaleString()}` : '-' },
    },
    {
      title: '', width: 40,
      render: (_: unknown, r: LineForm) => (
        <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeLine(r.key)} disabled={lines.length <= 1} />
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card title="编辑采购申请（草稿）">
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label={t('field.title')} name="title" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('field.currency')} name="currency">
                <Select options={[{ value: 'CNY' }, { value: 'USD' }, { value: 'EUR' }]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('field.required_date')} name="required_date">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item label="公司主体" name="company_id" rules={[{ required: true }]}>
                <Select options={companies.map((c) => ({ value: c.id, label: c.name_zh }))} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="成本中心" name="cost_center_id" rules={[{ required: true }]}>
                <Select options={costCenters.map((c) => ({ value: c.id, label: c.label_zh }))} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="开支类型" name="expense_type_id" rules={[{ required: true }]}>
                <Select options={expenseTypes.map((e) => ({ value: e.id, label: e.label_zh }))} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="采购种类" name="procurement_category_id">
                <Select allowClear showSearch optionFilterProp="label" options={procCategories.map((c) => ({ value: c.id, label: (c.level ?? 1) === 2 ? `  └ ${c.label_zh}` : c.label_zh }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t('field.business_reason')} name="business_reason">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <Typography.Text strong>采购明细</Typography.Text>
          <Button icon={<PlusOutlined />} onClick={addLine}>添加一行</Button>
        </div>
        <Table dataSource={lines} columns={columns} rowKey="key" size="small" pagination={false} />
        <div style={{ textAlign: 'right', marginTop: 8 }}>
          <Typography.Text strong>合计: {total > 0 ? `¥${total.toLocaleString()}` : '-'}</Typography.Text>
        </div>
      </Card>

      <Space>
        <Button onClick={() => navigate(`/purchase-requisitions/${id}`)}>{t('button.back')}</Button>
        <Button type="primary" onClick={onSave} loading={submitting}>保存修改</Button>
      </Space>
    </Space>
  )
}
