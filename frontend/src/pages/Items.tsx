import { DeleteOutlined, DownloadOutlined, EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Col, Drawer, Form, Input, InputNumber, Modal, Row, Select, Space, Switch, Table, Tag, Typography, message, theme } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type ClassificationItem, flattenCategoryTree, type Item } from '@/api'
import { downloadCSV } from '@/utils/export'

export default function ItemsPage() {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const [data, setData] = useState<Item[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [categories, setCategories] = useState<ClassificationItem[]>([])
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<Item | null>(null)
  const [form] = Form.useForm()

  const categoryMap = Object.fromEntries(categories.map((c) => [c.id, c]))

  const load = async () => {
    setLoading(true)
    try {
      const result = await api.itemsPaginated({
        category_id: categoryFilter,
        search: search || undefined,
        page,
        page_size: pageSize,
      })
      setData(result.items)
      setTotal(result.total)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void api.getCategoryTree().then((tree) => setCategories(flattenCategoryTree(tree)))
  }, [])

  useEffect(() => {
    void load()
  }, [categoryFilter, search, page, pageSize])

  const handleExport = () => {
    const headers = [
      t('item.code'), t('field.item_name'), t('item.category_label'),
      t('field.uom'), t('field.specification'), t('item.status_col'),
    ]
    const rows = data.map((i) => [
      i.code, i.name, categoryMap[i.category_id || '']?.label_zh || t('item.uncategorized'),
      i.uom, i.specification || '',
      i.is_enabled !== false ? t('item.active') : t('item.inactive'),
    ])
    downloadCSV(`mica-items-${new Date().toISOString().slice(0, 10)}.csv`, headers, rows)
  }

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
      void load()
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
          void load()
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
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>{t('button.export_excel')}</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingItem(null); form.resetFields(); setDrawerOpen(true) }}>{t('item.new')}</Button>
        </Space>
      </div>

      <Row gutter={16}>
        <Col xs={24} md={6}>
          <Card size="small" title={t('item.category_label')} styles={{ body: { maxHeight: 400, overflow: 'auto' } }}>
            <div
              onClick={() => setCategoryFilter(undefined)}
              style={{
                padding: '4px 8px', cursor: 'pointer', borderRadius: token.borderRadiusSM,
                background: categoryFilter === undefined ? token.colorPrimaryBg : 'transparent',
                color: categoryFilter === undefined ? token.colorPrimary : token.colorText,
                marginBottom: 4,
              }}
            >
              {t('item.all_categories')} ({total})
            </div>
            {categories.map((c) => (
              <div
                key={c.id}
                onClick={() => setCategoryFilter(c.id)}
                style={{
                  padding: '4px 8px', cursor: 'pointer', borderRadius: token.borderRadiusSM,
                  background: categoryFilter === c.id ? token.colorPrimaryBg : 'transparent',
                  color: categoryFilter === c.id ? token.colorPrimary : token.colorText,
                  paddingLeft: (c.level ?? 1) === 2 ? 24 : 8,
                }}
              >
                {c.label_zh}
              </div>
            ))}
          </Card>
        </Col>
        <Col xs={24} md={18}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Input
              prefix={<SearchOutlined />}
              placeholder={t('item.search_placeholder', 'Search by code, name or specification')}
              allowClear
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              style={{ maxWidth: 400 }}
            />
            <Typography.Text type="secondary">
              {t('item.count', { total })}
            </Typography.Text>
            <Table
              dataSource={data}
              rowKey="id"
              size="small"
              loading={loading}
              pagination={{
                current: page,
                pageSize,
                total,
                showSizeChanger: true,
                pageSizeOptions: ['20', '50', '100'],
                showTotal: (cnt) => cnt === 1 ? t('item.one_result') : t('item.total_results', { total: cnt }),
                onChange: (p, ps) => { setPage(p); setPageSize(ps) },
              }}
              columns={[
                { title: t('item.code'), dataIndex: 'code', width: 140, sorter: (a, b) => a.code.localeCompare(b.code) },
                { title: t('field.item_name'), dataIndex: 'name', sorter: (a, b) => a.name.localeCompare(b.name) },
                {
                  title: t('item.category_label'), dataIndex: 'category_id',
                  render: (v: string | null) => {
                    if (!v) return <Tag>{t('item.uncategorized')}</Tag>
                    const cat = categoryMap[v]
                    return cat ? <Tag color="blue">{cat.label_zh}</Tag> : '-'
                  },
                },
                { title: t('field.uom'), dataIndex: 'uom', width: 60 },
                { title: t('field.specification'), dataIndex: 'specification', ellipsis: true },
                {
                  title: t('item.status_col'), dataIndex: 'is_enabled', width: 70,
                  render: (v: boolean) => <Tag color={v !== false ? 'success' : 'default'}>{v !== false ? t('item.active') : t('item.inactive')}</Tag>,
                },
                {
                  title: t('item.actions_col'), width: 120,
                  render: (_: unknown, r: Item) => (
                    <Space>
                      <Button size="small" icon={<EditOutlined />} onClick={() => { setEditingItem(r); form.setFieldsValue(r); setDrawerOpen(true) }} />
                      <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r.id)} />
                    </Space>
                  ),
                },
              ]}
              onChange={(_pagination, _filters, sorter: any) => {
                if (sorter.order) {
                  // Client-side sort for simplicity; server-side could be added if needed
                  const sorted = [...data].sort((a, b) => {
                    const field = sorter.field as keyof Item
                    const va = String(a[field] ?? '')
                    const vb = String(b[field] ?? '')
                    return sorter.order === 'ascend' ? va.localeCompare(vb) : vb.localeCompare(va)
                  })
                  setData(sorted)
                }
              }}
            />
          </Space>
        </Col>
      </Row>

      <Drawer title={editingItem ? t('item.edit_code', { code: editingItem.code }) : t('item.new')} width={480} open={drawerOpen} onClose={() => { setDrawerOpen(false); setEditingItem(null) }} footer={
        <Space style={{ float: 'right' }}><Button onClick={() => setDrawerOpen(false)}>{t('button.cancel')}</Button><Button type="primary" onClick={handleSave}>{t('button.save')}</Button></Space>
      }>
        <Form form={form} layout="vertical">
          <Form.Item name="code" label={t('item.code')} help={t('item.code_help')} rules={[{ required: !editingItem }]}><Input placeholder="SRV-MEM-96GB" disabled={!!editingItem} /></Form.Item>
          <Form.Item name="name" label={t('field.item_name')} help={t('item.name_help')} rules={[{ required: true }]}><Input placeholder="96GB RDIMM DDR5 6400MT/s" /></Form.Item>
          <Form.Item name="category_id" label={t('item.category_label')} help={t('item.category_help')}><Select allowClear showSearch optionFilterProp="label" placeholder={t('item.select_category')} options={categories.map((c) => ({ value: c.id, label: (c.level ?? 1) === 2 ? `  └ ${c.label_zh}` : c.label_zh }))} /></Form.Item>
          <Form.Item name="uom" label={t('item.uom_label')} help={t('item.uom_help')} initialValue="EA"><Select options={[{ value: 'EA', label: 'EA' }, { value: 'SET', label: 'SET' }, { value: 'PCS', label: 'PCS' }, { value: 'LICENSE', label: 'LICENSE' }, { value: 'HOUR', label: 'HOUR' }]} /></Form.Item>
          <Form.Item name="specification" label={t('item.spec_label')} help={t('item.spec_help')}><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="requires_serial" label={t('item.serial_required')} valuePropName="checked"><Switch /></Form.Item>
          {editingItem && <Form.Item name="is_enabled" label={t('item.active_label')} valuePropName="checked"><Switch /></Form.Item>}
        </Form>
      </Drawer>
    </Space>
  )
}
