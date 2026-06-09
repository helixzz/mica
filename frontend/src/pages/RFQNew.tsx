import { useTranslation } from 'react-i18next'
import { Button, Card, Col, DatePicker, Form, Input, Row, Select, Space, Typography, message } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Item, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'
import { ItemPickerWithCreate } from '@/components/ItemPickerWithCreate'

interface LineForm { key: number; item_id: string | null; item_name: string; specification: string; qty: number; uom: string }

export default function RFQNewPage() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [items, setItems] = useState<Item[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const { t } = useTranslation()
  const [lines, setLines] = useState<LineForm[]>([{ key: 1, item_id: null, item_name: '', specification: '', qty: 1, uom: 'EA' }])
  const [selectedSuppliers, setSelectedSuppliers] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    void api.items().then(setItems)
    void api.suppliers().then(setSuppliers)
  }, [])

  const addLine = () => setLines((ls) => [...ls, { key: Date.now(), item_id: null, item_name: '', specification: '', qty: 1, uom: 'EA' }])
  const removeLine = (key: number) => setLines((ls) => ls.filter((l) => l.key !== key))
  const updateLine = (key: number, field: string, value: any) => {
    setLines((ls) => ls.map((l) => {
      if (l.key !== key) return l
      const updated = { ...l, [field]: value }
      if (field === 'item_id' && value) {
        const it = items.find((i) => i.id === value)
        if (it) { updated.item_name = it.name; updated.specification = it.specification || '' }
      }
      return updated
    }))
  }

  const onItemPicked = (key: number, itemId: string | null, picked?: Item | null) => {
    if (!itemId) {
      updateLine(key, 'item_id', null)
      return
    }
    if (picked && !items.find((i) => i.id === itemId)) {
      setItems((prev) => [...prev, picked])
    }
    setLines((ls) => ls.map((l) => {
      if (l.key !== key) return l
      const it = picked ?? items.find((i) => i.id === itemId)
      if (!it) return { ...l, item_id: itemId }
      return { ...l, item_id: itemId, item_name: it.name, specification: it.specification || '', uom: it.uom || l.uom }
    }))
  }

  const onSubmit = async (asDraft: boolean) => {
    try {
      const values = await form.validateFields()
      if (lines.length === 0 || !lines.some((l) => l.item_name)) { void message.error(t('validation.at_least_one_item')); return }
      if (selectedSuppliers.length === 0) { void message.error(t('validation.at_least_one_supplier')); return }
      setSubmitting(true)
      const { data: rfq } = await client.post('/rfqs', {
        title: values.title,
        deadline: values.deadline?.format('YYYY-MM-DD') ?? null,
        notes: values.notes,
        items: lines.filter((l) => l.item_name).map((l) => ({ item_id: l.item_id, item_name: l.item_name, specification: l.specification, qty: l.qty, uom: l.uom })),
        supplier_ids: selectedSuppliers,
      })
      if (!asDraft) {
        await client.post(`/rfqs/${rfq.id}/send`)
        void message.success(t('message.rfq_sent'))
      } else {
        void message.success(t('message.rfq_saved'))
      }
      navigate(`/rfqs/${rfq.id}`)
    } catch (e) {
      void message.error(extractError(e).detail || t('error.create_failed'))
    } finally { setSubmitting(false) }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>{t('rfq.new')}</Typography.Title>
      <Card>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item label={t('field.title')} name="title" help={t('rfq.title_help')} rules={[{ required: true }]}><Input placeholder={t('rfq.title_placeholder')} /></Form.Item></Col>
            <Col span={6}><Form.Item label={t('field.deadline')} name="deadline" help={t('rfq.deadline_help')}><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item label={t('field.notes')} name="notes" help={t('rfq.notes_help')}><Input.TextArea rows={2} /></Form.Item>
        </Form>

        <Typography.Text strong>{t('rfq.rfq_items')}</Typography.Text>
        <Typography.Text type="secondary" style={{ display: 'block', marginTop: 4, marginBottom: 8 }}>{t('rfq.items_help')}</Typography.Text>
        <div style={{ marginBottom: 8 }} />
        {lines.map((l) => (
          <Row key={l.key} gutter={8} style={{ marginBottom: 8 }}>
            <Col span={10}>
              <ItemPickerWithCreate
                placeholder={t('placeholder.select_item')}
                value={l.item_id ?? undefined}
                onChange={(v, picked) => onItemPicked(l.key, v, picked)}
              />
            </Col>
            <Col span={4}>
              <Input
                value={l.qty.toString()}
                onChange={(e) => updateLine(l.key, 'qty', Number(e.target.value) || 1)}
                suffix={l.uom}
              />
            </Col>
            <Col span={8}><Input value={l.specification} onChange={(e) => updateLine(l.key, 'specification', e.target.value)} placeholder={t('rfq.spec_placeholder')} /></Col>
            <Col span={2}>{lines.length > 1 && <Button danger icon={<DeleteOutlined />} onClick={() => removeLine(l.key)} />}</Col>
          </Row>
        ))}
        <Button type="dashed" icon={<PlusOutlined />} onClick={addLine} block>{t('rfq.add_item')}</Button>

        <div style={{ marginTop: 16 }}>
          <Typography.Text strong>{t('rfq.invited_suppliers')}</Typography.Text>
          <Typography.Text type="secondary" style={{ display: 'block', marginTop: 4 }}>{t('rfq.suppliers_help')}</Typography.Text>
          <Select mode="multiple" style={{ width: '100%', marginTop: 8 }} placeholder={t('rfq.select_suppliers')}
            value={selectedSuppliers} onChange={setSelectedSuppliers}
            options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
            showSearch optionFilterProp="label" />
        </div>
      </Card>

      <Space>
        <Button onClick={() => navigate('/rfqs')}>{t('button.cancel')}</Button>
        <Button onClick={() => onSubmit(true)} loading={submitting}>{t('rfq.save_draft')}</Button>
        <Button type="primary" onClick={() => onSubmit(false)} loading={submitting}>{t('rfq.save_and_send')}</Button>
      </Space>
    </Space>
  )
}
