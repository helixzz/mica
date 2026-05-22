import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Card, Col, DatePicker, Form, Input, InputNumber, Row, Select, Space, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Item, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'

interface ItemLine {
  key: number
  id?: string  // existing item ID (for update vs create)
  item_id: string | null
  item_name: string
  specification: string | null
  qty: number
  uom: string
}

export function RFQEditPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [items, setItems] = useState<Item[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [lines, setLines] = useState<ItemLine[]>([])
  const [selectedSuppliers, setSelectedSuppliers] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!id) return
    void Promise.all([
      client.get(`/rfqs/${id}`),
      api.items(),
      api.suppliers(),
    ]).then(([rfqRes, itemList, supList]) => {
      const rfq = rfqRes.data
      form.setFieldsValue({
        title: rfq.title,
        deadline: rfq.deadline ? dayjs(rfq.deadline) : null,
        notes: rfq.notes || '',
      })
      setLines(
        (rfq.items || []).map((item: any, i: number) => ({
          key: Date.now() + i,
          id: item.id,
          item_id: item.item_id,
          item_name: item.item_name,
          specification: item.specification,
          qty: Number(item.qty),
          uom: item.uom || 'EA',
        }))
      )
      setSelectedSuppliers((rfq.suppliers || []).map((s: any) => s.supplier_id))
      setItems(itemList)
      setSuppliers(supList)
      setLoading(false)
    }).catch(() => {
      void message.error(t('error.unexpected'))
      navigate('/rfqs')
    })
  }, [id])

  const addLine = () => {
    setLines(ls => [...ls, { key: Date.now(), item_id: null, item_name: '', specification: null, qty: 1, uom: 'EA' }])
  }

  const removeLine = (key: number) => {
    setLines(ls => ls.filter(l => l.key !== key))
  }

  const updateLine = (key: number, field: keyof ItemLine, value: any) => {
    setLines(ls => ls.map(l => l.key === key ? { ...l, [field]: value } : l))
  }

  const onSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      const payload: any = {
        title: values.title,
        deadline: values.deadline ? values.deadline.format('YYYY-MM-DD') : null,
        notes: values.notes || null,
        items: lines.filter(l => l.item_name.trim()).map(l => ({
          ...(l.id ? { id: l.id } : {}),
          item_id: l.item_id || null,
          item_name: l.item_name,
          specification: l.specification || null,
          qty: l.qty,
          uom: l.uom,
        })),
        supplier_ids: selectedSuppliers,
      }
      await client.patch(`/rfqs/${id}`, payload)
      void message.success(t('message.save_success'))
      navigate(`/rfqs/${id}`)
    } catch (e) {
      void message.error(extractError(e).detail || t('error.unexpected'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div>{t('message.loading')}</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>{t('rfq.edit_title', 'Edit RFQ')}</Typography.Title>

      <Card>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label={t('field.title')} name="title" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('field.deadline')} name="deadline">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label={t('field.supplier')}>
                <Select
                  mode="multiple"
                  value={selectedSuppliers}
                  onChange={setSelectedSuppliers}
                  options={suppliers.map(s => ({ value: s.id, label: s.name }))}
                  showSearch
                  optionFilterProp="label"
                  placeholder={t('placeholder.select_supplier')}
                  popupMatchSelectWidth={false}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t('field.notes')} name="notes">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Card>

      <Card title={t('rfq.items_title', 'Items')} extra={<Button icon={<PlusOutlined />} onClick={addLine}>{t('button.add_line')}</Button>}>
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {lines.map((line, idx) => (
            <Card key={line.key} size="small">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <Typography.Text strong>#{idx + 1}</Typography.Text>
                <Button type="text" danger icon={<DeleteOutlined />} onClick={() => removeLine(line.key)} disabled={lines.length <= 1} />
              </div>
              <Row gutter={[12, 12]}>
                <Col xs={24} md={14}>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.item_name')}</Typography.Text>
                  <Select
                    style={{ width: '100%' }}
                    placeholder={t('placeholder.select_item')}
                    value={line.item_id ?? undefined}
                    onChange={(v) => {
                      const it = items.find(i => i.id === v)
                      if (it) {
                        updateLine(line.key, 'item_id', it.id)
                        updateLine(line.key, 'item_name', it.name)
                        updateLine(line.key, 'specification', it.specification)
                      }
                    }}
                    options={items.map(it => ({ value: it.id, label: `${it.code} · ${it.name}` }))}
                    showSearch
                    optionFilterProp="label"
                    allowClear
                    popupMatchSelectWidth={false}
                  />
                </Col>
                <Col xs={6} md={4}>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.qty')}</Typography.Text>
                  <InputNumber min={0.0001} value={line.qty} onChange={(v) => updateLine(line.key, 'qty', Number(v ?? 1))} style={{ width: '100%' }} />
                </Col>
                <Col xs={4} md={3}>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>{t('field.uom')}</Typography.Text>
                  <Input value={line.uom} onChange={(e) => updateLine(line.key, 'uom', e.target.value)} />
                </Col>
              </Row>
            </Card>
          ))}
        </Space>
      </Card>

      <Space>
        <Button onClick={() => navigate(`/rfqs/${id}`)}>{t('button.cancel')}</Button>
        <Button type="primary" loading={saving} onClick={onSave}>{t('button.save')}</Button>
      </Space>
    </Space>
  )
}
