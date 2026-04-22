import { Button, Card, Col, DatePicker, Form, Input, Row, Select, Space, Typography, message } from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type Item, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'

interface LineForm { key: number; item_id: string | null; item_name: string; specification: string; qty: number; uom: string }

export default function RFQNewPage() {
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [items, setItems] = useState<Item[]>([])
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
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

  const onSubmit = async (asDraft: boolean) => {
    try {
      const values = await form.validateFields()
      if (lines.length === 0 || !lines.some((l) => l.item_name)) { void message.error('请至少添加一个物料'); return }
      if (selectedSuppliers.length === 0) { void message.error('请至少选择一个供应商'); return }
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
        void message.success('询价单已发出')
      } else {
        void message.success('询价单已保存为草稿')
      }
      navigate(`/rfqs/${rfq.id}`)
    } catch (e) {
      void message.error(extractError(e).detail || '创建失败')
    } finally { setSubmitting(false) }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>{	('rfq.new')}</Typography.Title>
      <Card>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item label="标题" name="title" rules={[{ required: true }]}><Input placeholder="Q3 服务器采购询价" /></Form.Item></Col>
            <Col span={6}><Form.Item label="截止日期" name="deadline"><DatePicker style={{ width: '100%' }} /></Form.Item></Col>
          </Row>
          <Form.Item label="备注" name="notes"><Input.TextArea rows={2} /></Form.Item>
        </Form>

        <Typography.Text strong>询价物料</Typography.Text>
        <div style={{ marginBottom: 8 }} />
        {lines.map((l, idx) => (
          <Row key={l.key} gutter={8} style={{ marginBottom: 8 }}>
            <Col span={10}>
              <Select style={{ width: '100%' }} placeholder="选择物料" value={l.item_id ?? undefined}
                onChange={(v) => updateLine(l.key, 'item_id', v)}
                options={items.map((it) => ({ value: it.id, label: `${it.code} · ${it.name}` }))}
                showSearch optionFilterProp="label" allowClear />
            </Col>
            <Col span={4}><Input value={l.qty.toString()} onChange={(e) => updateLine(l.key, 'qty', Number(e.target.value) || 1)} addonAfter={l.uom} /></Col>
            <Col span={8}><Input value={l.specification} onChange={(e) => updateLine(l.key, 'specification', e.target.value)} placeholder="规格" /></Col>
            <Col span={2}>{lines.length > 1 && <Button danger icon={<DeleteOutlined />} onClick={() => removeLine(l.key)} />}</Col>
          </Row>
        ))}
        <Button type="dashed" icon={<PlusOutlined />} onClick={addLine} block>添加物料</Button>

        <div style={{ marginTop: 16 }}>
          <Typography.Text strong>受邀供应商</Typography.Text>
          <Select mode="multiple" style={{ width: '100%', marginTop: 8 }} placeholder="选择供应商（可多选）"
            value={selectedSuppliers} onChange={setSelectedSuppliers}
            options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
            showSearch optionFilterProp="label" />
        </div>
      </Card>

      <Space>
        <Button onClick={() => navigate('/rfqs')}>取消</Button>
        <Button onClick={() => onSubmit(true)} loading={submitting}>保存草稿</Button>
        <Button type="primary" onClick={() => onSubmit(false)} loading={submitting}>保存并发出</Button>
      </Space>
    </Space>
  )
}
