import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Table,
  Typography,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { api, type ClassificationItem, flattenCategoryTree, type Item, type PRItem, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { AIStreamButton } from '@/components/AIStreamButton'
import { PRQuoteConfirmModal } from '@/components/PRQuoteConfirmModal'

interface LineForm {
  key: number
  line_no: number
  item_id: string | null
  item_name: string
  specification: string | null
  supplier_id: string | null
  qty: number
  uom: string
  unit_price: number
}

export function PRNewPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [form] = Form.useForm<{
    title: string
    business_reason?: string
    required_date?: dayjs.Dayjs
    currency: string
    cost_center_id?: string
    expense_type_id?: string
    procurement_category_id?: string
    company_id?: string
  }>()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [companies, setCompanies] = useState<{ id: string; name_zh: string }[]>([])
  const [costCenters, setCostCenters] = useState<{ id: string; label_zh: string }[]>([])
  const [expenseTypes, setExpenseTypes] = useState<{ id: string; label_zh: string }[]>([])
  const [procCategories, setProcCategories] = useState<ClassificationItem[]>([])
  const [aiFeatures, setAiFeatures] = useState<Record<string, boolean>>({})
  const [lines, setLines] = useState<LineForm[]>([
    { key: 1, line_no: 1, item_id: null, item_name: '', specification: '', supplier_id: null, qty: 1, uom: 'EA', unit_price: 0 },
  ])
  const [submitting, setSubmitting] = useState(false)
  const [savedPRId, setSavedPRId] = useState<string | null>(null)
  const { user } = useAuth()
  const isRequester = user?.role === 'requester'
  const [refPrices, setRefPrices] = useState<Record<string, { latest_price: number | null; avg_price: number | null }>>({})

  useEffect(() => {
    void api.suppliers().then(setSuppliers)
    void api.items().then(setItems)
    void api.companies().then(setCompanies)
    void api.listCostCenters().then(setCostCenters)
    void api.listLookupValues('expense_type').then(setExpenseTypes)
    void api.getCategoryTree().then((tree) => setProcCategories(flattenCategoryTree(tree)))
    void client.get<Record<string, boolean>>('/ai/features-available').then((r) => setAiFeatures(r.data)).catch(() => {})
  }, [])

  const addLine = () => {
    setLines((ls) => [
      ...ls,
      {
        key: Date.now(),
        line_no: ls.length + 1,
        item_id: null,
        item_name: '',
        specification: '',
        supplier_id: null,
        qty: 1,
        uom: 'EA',
        unit_price: 0,
      },
    ])
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
            .get<Record<string, { latest_price: number | null; avg_price: number | null }>>(
              `/sku/reference-prices?item_ids=${value}`,
            )
            .then((r) => setRefPrices((prev) => ({ ...prev, ...r.data })))
            .catch(() => {})
        }
        return updated
      }),
    )
  }

  const onItemSelect = (key: number, itemId: string | null) => {
    if (!itemId) {
      updateLine(key, 'item_id', null)
      return
    }
    const it = items.find((i) => i.id === itemId)
    if (!it) return
    setLines((ls) =>
      ls.map((l) =>
        l.key === key
          ? { ...l, item_id: it.id, item_name: it.name, specification: it.specification, uom: it.uom }
          : l
      )
    )
    void client
      .get<Record<string, { latest_price: number | null; avg_price: number | null }>>(
        `/sku/reference-prices?item_ids=${itemId}`,
      )
      .then((r) => setRefPrices((prev) => ({ ...prev, ...r.data })))
      .catch(() => {})
  }

  const removeLine = (key: number) => {
    setLines((ls) => ls.filter((l) => l.key !== key).map((l, i) => ({ ...l, line_no: i + 1 })))
  }

  const total = lines.reduce((s, l) => s + l.qty * l.unit_price, 0)

  const onFinish = async (saveOnly: boolean) => {
    try {
      const values = await form.validateFields()
      const validLines = lines.filter((l) => l.item_name.trim())
      if (!saveOnly && validLines.length === 0) {
        void message.error(t('pr.items_required'))
        return
      }
      setSubmitting(true)
      const payload = {
        title: values.title,
        business_reason: values.business_reason,
        currency: values.currency || 'CNY',
        required_date: values.required_date ? values.required_date.format('YYYY-MM-DD') : null,
        company_id: values.company_id || null,
        cost_center_id: values.cost_center_id || null,
        expense_type_id: values.expense_type_id || null,
        procurement_category_id: values.procurement_category_id || null,
        items: validLines.map<PRItem>((l) => ({
          line_no: l.line_no,
          item_id: l.item_id,
          item_name: l.item_name,
          specification: l.specification,
          supplier_id: l.supplier_id,
          qty: l.qty,
          uom: l.uom,
          unit_price: l.unit_price,
        })),
      }
      const pr = await api.createPR(payload)
      if (!saveOnly) {
        await api.submitPR(pr.id)
        void message.success(t('message.submit_success'))
        navigate(`/purchase-requisitions/${pr.id}`)
      } else {
        void message.success(t('message.save_success'))
        setSavedPRId(pr.id)
      }
    } catch (e) {
      const err = extractError(e)
      void message.error(err.detail || t('error.unexpected'))
    } finally {
      setSubmitting(false)
    }
  }

  const columns = [
    { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
    {
      title: t('field.item_name'),
      width: 280,
      render: (_: unknown, r: LineForm) => (
        <Space direction="vertical" size={0} style={{ width: '100%' }}>
          <Select
            style={{ width: '100%' }}
            placeholder={isRequester ? t('pr.select_item_requester') : t('placeholder.select_item')}
            value={r.item_id ?? undefined}
            onChange={(v) => onItemSelect(r.key, v)}
            options={items.map((it) => ({ value: it.id, label: `${it.code} · ${it.name}` }))}
            showSearch
            optionFilterProp="label"
            allowClear
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
    ...(!isRequester
      ? [
          {
            title: t('field.supplier'),
            width: 220,
            render: (_: unknown, r: LineForm) => (
              <Select
                style={{ width: '100%' }}
                placeholder={t('placeholder.select_supplier')}
                value={r.supplier_id ?? undefined}
                onChange={(v: string) => updateLine(r.key, 'supplier_id', v)}
                options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
                showSearch
                optionFilterProp="label"
                allowClear
              />
            ),
          },
        ]
      : []),
    {
      title: t('field.qty'),
      width: 110,
      render: (_: unknown, r: LineForm) => (
        <InputNumber
          min={0.0001}
          value={r.qty}
          onChange={(v) => updateLine(r.key, 'qty', Number(v ?? 0))}
          style={{ width: '100%' }}
        />
      ),
    },
    {
      title: t('field.uom'),
      width: 80,
      render: (_: unknown, r: LineForm) => (
        <Input
          value={r.uom}
          onChange={(e) => updateLine(r.key, 'uom', e.target.value)}
        />
      ),
    },
    {
      title: isRequester ? (
        <Space direction="vertical" size={0}>
          <span>{t('field.unit_price')}</span>
          <Typography.Text type="secondary" style={{ fontSize: 10, fontWeight: 'normal' }}>{t('pr.price_optional')}</Typography.Text>
        </Space>
      ) : (
        t('field.unit_price')
      ),
      width: 160,
      render: (_: unknown, r: LineForm) => (
        <InputNumber
          min={0}
          value={r.unit_price || undefined}
          onChange={(v) => updateLine(r.key, 'unit_price', Number(v ?? 0))}
          style={{ width: '100%' }}
          placeholder={isRequester ? t('pr.price_placeholder') : undefined}
        />
      ),
    },
    {
      title: t('field.amount'),
      width: 120,
      align: 'right' as const,
      render: (_: unknown, r: LineForm) => {
        const amt = r.qty * (r.unit_price || 0)
        return amt > 0 ? `¥${amt.toLocaleString()}` : '-'
      },
    },
    {
      title: '',
      width: 50,
      render: (_: unknown, r: LineForm) => (
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => removeLine(r.key)}
        />
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>
        {t('button.create')} · {t('nav.purchase_requisitions')}
      </Typography.Title>

      {isRequester && (
        <Alert
          type="info"
          showIcon
          message={t('pr.guide_title')}
          description={
            <ul style={{ margin: '4px 0 0', paddingLeft: 20, fontSize: 13 }}>
              <li>{t('pr.guide_title_field')}</li>
              <li>{t('pr.guide_required_fields')}</li>
              <li>{t('pr.guide_items')}</li>
              <li>{t('pr.guide_price')}</li>
              <li>{t('pr.guide_reason')}</li>
            </ul>
          }
        />
      )}

      <Card>
        <Form form={form} layout="vertical" initialValues={{ currency: 'CNY' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label={t('field.title')}
                name="title"
                help={t('pr.title_help')}
                rules={[{ required: true }]}
              >
                <Input placeholder={t('placeholder.enter_title')} />
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
              <Form.Item label={t('pr.company_label')} name="company_id" help={t('pr.company_help')} rules={[{ required: true, message: t('validation.select_company') }]}>
                <Select
                  placeholder={t('pr.select_company')}
                  options={companies.map((c) => ({ value: c.id, label: c.name_zh }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.cost_center_label')} name="cost_center_id" help={t('pr.cost_center_help')} rules={[{ required: true, message: t('validation.select_cost_center') }]}>
                <Select
                  placeholder={t('pr.select_cost_center')}
                  options={costCenters.map((c) => ({ value: c.id, label: c.label_zh }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.expense_type_label')} name="expense_type_id" help={t('pr.expense_type_help')} rules={[{ required: true, message: t('validation.select_expense_type') }]}>
                <Select
                  placeholder="CapEx / OpEx"
                  options={expenseTypes.map((e) => ({ value: e.id, label: e.label_zh }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('pr.category_label')} name="procurement_category_id" help={t('pr.category_help')}>
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder={t('pr.select_category')}
                  options={procCategories.map((c) => ({
                    value: c.id,
                    label: (c.level ?? 1) === 2 ? `  └ ${c.label_zh}` : c.label_zh,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t('field.business_reason')} name="business_reason" help={t('pr.business_reason_help')}>
            <Input.TextArea rows={3} placeholder={t('placeholder.enter_reason')} />
          </Form.Item>
          <Space>
            <AIStreamButton
              feature="pr_description_polish"
              body={{ draft: Form.useWatch('business_reason', form) || '' }}
              onChunk={(chunk) => {
                const current = form.getFieldValue('business_reason') || ''
                form.setFieldValue('business_reason', current + chunk)
              }}
              disabled={!Form.useWatch('business_reason', form)}
              available={aiFeatures['pr_description_polish'] === true}
              label={t('button.ai_polish')}
            />
          </Space>
        </Form>
      </Card>

      <Card
        title={t('nav.purchase_requisitions')}
        extra={
          <Button icon={<PlusOutlined />} onClick={addLine}>
            {t('button.add_line')}
          </Button>
        }
      >
        <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          {t('pr.line_items_help')}
        </Typography.Text>
        <Table
          rowKey="key"
          dataSource={lines}
          columns={columns}
          pagination={false}
          summary={() => (
            <Table.Summary.Row>
              <Table.Summary.Cell index={0} colSpan={6} align="right">
                <strong>{t('field.total_amount')}</strong>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={1} align="right">
                <strong>{total > 0 ? `¥${total.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : '-'}</strong>
              </Table.Summary.Cell>
              <Table.Summary.Cell index={2} />
            </Table.Summary.Row>
          )}
        />
      </Card>

      <Space>
        <Button onClick={() => navigate(-1)}>{t('button.cancel')}</Button>
        <Button loading={submitting} onClick={() => onFinish(true)}>
          {t('button.save')}
        </Button>
        <Button type="primary" loading={submitting} onClick={() => onFinish(false)}>
          {t('button.submit_for_approval')}
        </Button>
      </Space>

      {savedPRId && (
        <PRQuoteConfirmModal
          prId={savedPRId}
          open={!!savedPRId}
          onClose={() => {
            const id = savedPRId
            setSavedPRId(null)
            navigate(`/purchase-requisitions/${id}`)
          }}
        />
      )}
    </Space>
  )
}
