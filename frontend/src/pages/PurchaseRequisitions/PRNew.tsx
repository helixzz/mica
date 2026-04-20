import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import {
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

import { api, type Item, type PRItem, type Supplier } from '@/api'
import { extractError } from '@/api/client'

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
  }>()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [lines, setLines] = useState<LineForm[]>([
    { key: 1, line_no: 1, item_id: null, item_name: '', specification: '', supplier_id: null, qty: 1, uom: 'EA', unit_price: 0 },
  ])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    void api.suppliers().then(setSuppliers)
    void api.items().then(setItems)
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
    setLines((ls) => ls.map((l) => (l.key === key ? { ...l, [field]: value } : l)))
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
  }

  const removeLine = (key: number) => {
    setLines((ls) => ls.filter((l) => l.key !== key).map((l, i) => ({ ...l, line_no: i + 1 })))
  }

  const total = lines.reduce((s, l) => s + l.qty * l.unit_price, 0)

  const onFinish = async (saveOnly: boolean) => {
    try {
      const values = await form.validateFields()
      if (lines.length === 0 || lines.some((l) => !l.item_name)) {
        void message.error(t('error.unexpected'))
        return
      }
      setSubmitting(true)
      const payload = {
        title: values.title,
        business_reason: values.business_reason,
        currency: values.currency || 'CNY',
        required_date: values.required_date ? values.required_date.format('YYYY-MM-DD') : null,
        items: lines.map<PRItem>((l) => ({
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
      } else {
        void message.success(t('message.save_success'))
      }
      navigate(`/purchase-requisitions/${pr.id}`)
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
        <Select
          style={{ width: '100%' }}
          placeholder={t('placeholder.select_item')}
          value={r.item_id ?? undefined}
          onChange={(v) => onItemSelect(r.key, v)}
          options={items.map((it) => ({ value: it.id, label: `${it.code} · ${it.name}` }))}
          showSearch
          optionFilterProp="label"
          allowClear
        />
      ),
    },
    {
      title: t('field.supplier'),
      width: 220,
      render: (_: unknown, r: LineForm) => (
        <Select
          style={{ width: '100%' }}
          placeholder={t('placeholder.select_supplier')}
          value={r.supplier_id ?? undefined}
          onChange={(v) => updateLine(r.key, 'supplier_id', v)}
          options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
          showSearch
          optionFilterProp="label"
          allowClear
        />
      ),
    },
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
      title: t('field.unit_price'),
      width: 140,
      render: (_: unknown, r: LineForm) => (
        <InputNumber
          min={0}
          value={r.unit_price}
          onChange={(v) => updateLine(r.key, 'unit_price', Number(v ?? 0))}
          style={{ width: '100%' }}
        />
      ),
    },
    {
      title: t('field.amount'),
      width: 120,
      align: 'right' as const,
      render: (_: unknown, r: LineForm) => (r.qty * r.unit_price).toFixed(2),
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

      <Card>
        <Form form={form} layout="vertical" initialValues={{ currency: 'CNY' }}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label={t('field.title')}
                name="title"
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
          <Form.Item label={t('field.business_reason')} name="business_reason">
            <Input.TextArea rows={2} placeholder={t('placeholder.enter_reason')} />
          </Form.Item>
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
                <strong>{total.toFixed(2)}</strong>
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
    </Space>
  )
}
