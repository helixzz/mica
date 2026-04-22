import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Drawer, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, Tag, Typography, message } from 'antd'
import { useEffect, useState } from 'react'

import { api, type ClassificationItem, flattenCategoryTree, type Item } from '@/api'

export default function ItemsPage() {
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
        void message.success('已更新')
      } else {
        await api.createItem(values)
        void message.success('已创建')
      }
      form.resetFields()
      setDrawerOpen(false)
      setEditingItem(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || '操作失败')
    }
  }

  const handleDelete = (id: string) => {
    Modal.confirm({
      title: '确认删除该物料？',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.deleteItem(id)
          void message.success('已删除')
          load()
        } catch (e: any) {
          void message.error(e?.response?.data?.detail || '删除失败')
        }
      },
    })
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>物料管理</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingItem(null); form.resetFields(); setDrawerOpen(true) }}>新增物料</Button>
      </div>
      <Typography.Text type="secondary">{items.length} 个物料</Typography.Text>
      <Table dataSource={items} rowKey="id" size="small" pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }} columns={[
        { title: '编码', dataIndex: 'code', width: 140 },
        { title: '名称', dataIndex: 'name' },
        { title: '采购种类', dataIndex: 'category_id', render: (v: string | null) => { if (!v) return <Tag>未分类</Tag>; const cat = categoryMap[v]; return cat ? <Tag color="blue">{cat.label_zh}</Tag> : '-' } },
        { title: '单位', dataIndex: 'uom', width: 60 },
        { title: '规格', dataIndex: 'specification', ellipsis: true },
        { title: '状态', dataIndex: 'is_active', width: 70, render: (v: boolean) => <Tag color={v !== false ? 'success' : 'default'}>{v !== false ? '启用' : '停用'}</Tag> },
        { title: '操作', width: 120, render: (_: unknown, r: Item) => (
          <Space>
            <Button size="small" icon={<EditOutlined />} onClick={() => { setEditingItem(r); form.setFieldsValue(r); setDrawerOpen(true) }} />
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r.id)} />
          </Space>
        )},
      ]} />
      <Drawer title={editingItem ? `编辑 ${editingItem.code}` : '新增物料'} width={480} open={drawerOpen} onClose={() => { setDrawerOpen(false); setEditingItem(null) }} footer={
        <Space style={{ float: 'right' }}><Button onClick={() => setDrawerOpen(false)}>取消</Button><Button type="primary" onClick={handleSave}>保存</Button></Space>
      }>
        <Form form={form} layout="vertical">
          <Form.Item name="code" label="编码" rules={[{ required: !editingItem }]}><Input placeholder="SRV-MEM-96GB" disabled={!!editingItem} /></Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input placeholder="96GB RDIMM DDR5 6400MT/s" /></Form.Item>
          <Form.Item name="category_id" label="采购种类"><Select allowClear showSearch optionFilterProp="label" placeholder="选择采购种类" options={categories.map((c) => ({ value: c.id, label: (c.level ?? 1) === 2 ? `  └ ${c.label_zh}` : c.label_zh }))} /></Form.Item>
          <Form.Item name="uom" label="计量单位" initialValue="EA"><Select options={[{ value: 'EA', label: 'EA' }, { value: 'SET', label: 'SET' }, { value: 'PCS', label: 'PCS' }, { value: 'LICENSE', label: 'LICENSE' }, { value: 'HOUR', label: 'HOUR' }]} /></Form.Item>
          <Form.Item name="specification" label="规格描述"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="requires_serial" label="需要序列号" valuePropName="checked"><Switch /></Form.Item>
          {editingItem && <Form.Item name="is_active" label="启用状态" valuePropName="checked"><Switch /></Form.Item>}
        </Form>
      </Drawer>
    </Space>
  )
}
