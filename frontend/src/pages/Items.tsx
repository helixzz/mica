import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Drawer, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type ClassificationItem, flattenCategoryTree, type Item } from '@/api'

export default function ItemsPage() {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [categories, setCategories] = useState<ClassificationItem[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<Item | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    void api.items().then(setItems)
    void api.getCategoryTree().then((tree) => setCategories(flattenCategoryTree(tree)))
  }
  useEffect(load, [])

  const categoryMap = Object.fromEntries(categories.map((c) => [c.id, c]))

  const handleSave = async () => {
    try {
      const values = form.getFieldsValue()
      if (editingItem) {
        await api.updateItem(editingItem.id, values)
        void message.success(t('item.updated'))
      } else {
        await api.createItem(values)
        void message.success(t('message.created'))
      }
      form.resetFields()
      setDrawerOpen(false)
      setEditingItem(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('common.operation_failed'))
    }
  }

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: t('item.confirm_delete'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteItem(id)
          void message.success(t('item.deleted'))
          load()
        } catch (e: any) {
          void message.error(e?.response?.data?.detail || t('item.delete_failed'))
        }
      },
    })
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('item.title')}</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingItem(null); form.resetFields(); setDrawerOpen(true) }}>{t('item.new')}</Button>
      </div>
      <Typography.Text type="secondary">{items.length} {t('item.count')}</Typography.Text>
      <Table dataSource={items} rowKey="id" size="small" pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => t('item.total_count', { total }) }} columns={[
        { title: t('item.code'), dataIndex: 'code', width: 140 },
        { title: t('field.item_name'), dataIndex: 'name' },
        { title: t('item.category_label'), dataIndex: 'category_id', render: (v: string | null) => { if (!v) return <Tag>{t('item.uncategorized')}</Tag>; const cat = categoryMap[v]; return cat ? <Tag color="blue">{cat.label_zh}</Tag> : '-' } },
        { title: t('field.uom'), dataIndex: 'uom', width: 60 },
        { title: t('field.specification'), dataIndex: 'specification', ellipsis: true },
        { title: t('item.status_col'), dataIndex: 'is_active', width: 70, render: (v: boolean) => <Tag color={v !== false ? 'success' : 'default'}>{v !== false ? t('item.active') : t('item.inactive')}</Tag> },
        { title: t('item.actions_col'), width: 120, render: (_: unknown, r: Item) => (
          <Space>
            <Button size="small" icon={<EditOutlined />} onClick={() => { setEditingItem(r); form.setFieldsValue(r); setDrawerOpen(true) }} />
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r.id)} />
          </Space>
        )},
      ]} />
      <Drawer title={editingItem ? t('item.edit_code', { code: editingItem.code }) : t('item.new')} width={480} open={drawerOpen} onClose={() => { setDrawerOpen(false); setEditingItem(null) }} footer={
        <Space style={{ float: 'right' }}><Button onClick={() => setDrawerOpen(false)}>{t('button.cancel')}</Button><Button type="primary" onClick={handleSave}>{t('button.save')}</Button></Space>
      }>
        <Form form={form} layout="vertical">
          <Form.Item name="code" label={t('item.code')} rules={[{ required: !editingItem }]}><Input placeholder="SRV-MEM-96GB" disabled={!!editingItem} /></Form.Item>
          <Form.Item name="name" label={t('field.item_name')} rules={[{ required: true }]}><Input placeholder="96GB RDIMM DDR5 6400MT/s" /></Form.Item>
          <Form.Item name="category_id" label={t('item.category_label')}><Select allowClear showSearch optionFilterProp="label" placeholder={t('item.select_category')} options={categories.map((c) => ({ value: c.id, label: (c.level ?? 1) === 2 ? `  └ ${c.label_zh}` : c.label_zh }))} /></Form.Item>
          <Form.Item name="uom" label={t('item.uom_label')} initialValue="EA"><Select options={[{ value: 'EA', label: 'EA' }, { value: 'SET', label: 'SET' }, { value: 'PCS', label: 'PCS' }, { value: 'LICENSE', label: 'LICENSE' }, { value: 'HOUR', label: 'HOUR' }]} /></Form.Item>
          <Form.Item name="specification" label={t('item.spec_label')}><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="requires_serial" label={t('item.serial_required')} valuePropName="checked"><Switch /></Form.Item>
          {editingItem && <Form.Item name="is_active" label={t('item.active_label')} valuePropName="checked"><Switch /></Form.Item>}
        </Form>
      </Drawer>
    </Space>
  )
}
