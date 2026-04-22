import { Button, Card, Col, DatePicker, Form, Input, InputNumber, Row, Select, Space, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type ClassificationItem, flattenCategoryTree, type Item, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'

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
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [items, setItems] = useState<Item[]>([])
  const [companies, setCompanies] = useState<{ id: string; name_zh: string }[]>([])
  const [costCenters, setCostCenters] = useState<{ id: string; label_zh: string }[]>([])
  const [expenseTypes, setExpenseTypes] = useState<{ id: string; label_zh: string }[]>([])
  const [procCategories, setProcCategories] = useState<ClassificationItem[]>([])
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
      setLines(
        (pr.items || []).map((item: any, idx: number) => ({
          key: idx + 1,
          line_no: item.line_no || idx + 1,
          item_id: item.item_id,
          item_name: item.item_name,
          specification: item.specification || '',
          supplier_id: item.supplier_id,
          qty: Number(item.qty),
          uom: item.uom || 'EA',
          unit_price: Number(item.unit_price),
        })),
      )
      setLoaded(true)
    })()
  }, [id, form])

  const total = lines.reduce((s, l) => s + l.qty * l.unit_price, 0)

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

  const lineCols: ColumnsType<LineForm> = [
    { title: '#', dataIndex: 'line_no', width: 40 },
    { title: t('field.item_name'), dataIndex: 'item_name' },
    { title: t('field.specification'), dataIndex: 'specification', ellipsis: true },
    { title: t('field.qty'), dataIndex: 'qty', width: 60, align: 'right' },
    { title: t('field.uom'), dataIndex: 'uom', width: 50 },
    { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', render: (v: number) => `¥${v.toLocaleString()}` },
    { title: t('field.amount'), key: 'amount', align: 'right', render: (_, r) => `¥${(r.qty * r.unit_price).toLocaleString()}` },
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
                <Select
                  allowClear showSearch optionFilterProp="label"
                  options={procCategories.map((c) => ({ value: c.id, label: (c.level ?? 1) === 2 ? `  └ ${c.label_zh}` : c.label_zh }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t('field.business_reason')} name="business_reason">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>

        <Typography.Text strong>明细行（只读，如需修改请删除草稿重新创建）</Typography.Text>
        <Table dataSource={lines} columns={lineCols} rowKey="key" size="small" pagination={false} style={{ marginTop: 8 }} />
        <div style={{ textAlign: 'right', marginTop: 8 }}>
          <Typography.Text strong>合计: ¥{total.toLocaleString()}</Typography.Text>
        </div>
      </Card>

      <Space>
        <Button onClick={() => navigate(`/purchase-requisitions/${id}`)}>{t('button.back')}</Button>
        <Button type="primary" onClick={onSave} loading={submitting}>保存修改</Button>
      </Space>
    </Space>
  )
}
