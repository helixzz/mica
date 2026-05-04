import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Card, Col, DatePicker, Form, Input, InputNumber, Row, Select, Space, Table, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type ClassificationItem, flattenCategoryTree, type Item, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { AutosaveBanner, AutosaveUnavailableBanner } from '@/components/AutosaveBanner'
import { PRQuoteConfirmModal } from '@/components/PRQuoteConfirmModal'
import { useAutosave } from '@/hooks/useAutosave'

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
  const [quoteModalOpen, setQuoteModalOpen] = useState(false)
  const autosave = useAutosave(`pr-edit-${id || 'unknown'}`)
  const [autosaveDismissed, setAutosaveDismissed] = useState(false)

  useEffect(() => {
    void api.suppliers().then(setSuppliers)
    void api.items().then(setItems)
    void api.companies().then(setCompanies)
    void api.listCostCenters().then(setCostCenters)
    void api.listLookupValues('expense_type').then(setExpenseTypes)
    void api.getCategoryTree().then((tree) => setProcCategories(flattenCategoryTree(tree)))
  }, [])

  useEffect(() => {
    const formValues = form.getFieldsValue()
    autosave.save({ ...formValues, items: lines })
  })

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
      autosave.clear()
      void message.success(t('message.saved'))
      setQuoteModalOpen(true)
    } catch (e) {
      void message.error(extractError(e).detail || t('error.save_failed'))
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
            placeholder={isRequester ? t('placeholder.select_item') : t('placeholder.select_item')}
            value={r.item_id ?? undefined}
            onChange={(v) => updateLine(r.key, 'item_id', v)}
            options={items.map((it) => ({ value: it.id, label: `${it.code} · ${it.name}` }))}
            showSearch optionFilterProp="label" allowClear
          />
          {r.item_id && refPrices[r.item_id] && (
            <Typography.Text type="secondary" style={{ fontSize: 11 }}>
              {t('sku.ref_latest')}: ¥{refPrices[r.item_id].latest_price?.toLocaleString() ?? '-'}
              {refPrices[r.item_id].avg_price ? ` · ${t('sku.ref_avg')}: ¥${refPrices[r.item_id].avg_price?.toLocaleString()}` : ''}
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
      title: isRequester ? <span>{t('field.unit_price')}<br /><Typography.Text type="secondary" style={{ fontSize: 10 }}>{t('pr.unit_price_optional')}</Typography.Text></span> : t('field.unit_price'),
      width: 130,
      render: (_: unknown, r: LineForm) => (
        <InputNumber min={0} value={r.unit_price || undefined} onChange={(v) => updateLine(r.key, 'unit_price', Number(v ?? 0))} style={{ width: '100%' }} placeholder={isRequester ? t('pr.optional_label') : undefined} />
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
      {!autosaveDismissed && autosave.hasAutosave && autosave.savedAt && (
        <AutosaveBanner
          savedAt={autosave.savedAt}
          onRestore={() => {
            const vals = autosave.restore()
            if (vals) {
              const items = vals.items as LineForm[] | undefined
              if (items) {
                setLines(items)
                form.setFieldsValue({ ...vals, items: undefined })
              } else {
                form.setFieldsValue(vals as Record<string, unknown>)
              }
            }
          }}
          onDismiss={() => setAutosaveDismissed(true)}
        />
      )}
      {!autosave.storageAvailable && <AutosaveUnavailableBanner />}

      <Card title={t('pr.edit_draft')}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label={t('field.title')} name="title" help={t('pr.title_help')} rules={[{ required: true }]}>
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
              <Form.Item label={t('pr.company_label')} name="company_id" help={t('pr.company_help')} rules={[{ required: true }]}>
                <Select options={companies.map((c) => ({ value: c.id, label: c.name_zh }))} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.cost_center_label')} name="cost_center_id" help={t('pr.cost_center_help')} rules={[{ required: true }]}>
                <Select options={costCenters.map((c) => ({ value: c.id, label: c.label_zh }))} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.expense_type_label')} name="expense_type_id" help={t('pr.expense_type_help')} rules={[{ required: true }]}>
                <Select options={expenseTypes.map((e) => ({ value: e.id, label: e.label_zh }))} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.category_label')} name="procurement_category_id" help={t('pr.category_help')}>
                <Select allowClear showSearch optionFilterProp="label" options={procCategories.map((c) => ({ value: c.id, label: (c.level ?? 1) === 2 ? `  └ ${c.label_zh}` : c.label_zh }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t('field.business_reason')} name="business_reason" help={t('pr.business_reason_help')}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>

        <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          {t('pr.line_items_help')}
        </Typography.Text>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <Typography.Text strong>{t('pr.line_items')}</Typography.Text>
          <Button icon={<PlusOutlined />} onClick={addLine}>{t('pr.add_line')}</Button>
        </div>
        <Table dataSource={lines} columns={columns} rowKey="key" size="small" pagination={false} />
        <div style={{ textAlign: 'right', marginTop: 8 }}>
          <Typography.Text strong>{t('pr.total_label')}: {total > 0 ? `¥${total.toLocaleString()}` : '-'}</Typography.Text>
        </div>
      </Card>

      <Space>
        <Button onClick={() => navigate(`/purchase-requisitions/${id}`)}>{t('button.back')}</Button>
        <Button type="primary" onClick={onSave} loading={submitting}>{t('pr.save_changes')}</Button>
      </Space>

      {id && (
        <PRQuoteConfirmModal
          prId={id}
          open={quoteModalOpen}
          onClose={() => {
            setQuoteModalOpen(false)
            navigate(`/purchase-requisitions/${id}`)
          }}
        />
      )}
    </Space>
  )
}
