import { DeleteOutlined, DownloadOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Divider, Drawer, Form, Input, Modal, Space, Table, Tag, Typography, message } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type Supplier } from '@/api'
import { downloadCSV } from '@/utils/export'
import { showUndoToast } from '@/utils/undo'

export default function SuppliersPage() {
  const { t } = useTranslation()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingSupplier, setEditingSupplier] = useState<Supplier | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    api.suppliers().then(setSuppliers).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const handleExport = () => {
    const headers = [
      t('supplier.code'), t('supplier.name'), t('supplier.tax_number'),
      t('field.contact_name'), t('field.contact_phone'), t('field.contact_email'),
      t('supplier.status'),
    ]
    const data = suppliers.map(s => [
      s.code, s.name, s.tax_number || '',
      s.contact_name || '', s.contact_phone || '', s.contact_email || '',
      s.is_enabled !== false ? t('common.enabled') : t('common.disabled'),
    ])
    downloadCSV(`mica-suppliers-${new Date().toISOString().slice(0, 10)}.csv`, headers, data)
  }

  const handleSave = async () => {
    try {
      const values = form.getFieldsValue()
      if (editingSupplier) {
        await api.updateSupplier(editingSupplier.id, values)
        void message.success(t('supplier.updated'))
      } else {
        await api.createSupplier(values)
        void message.success(t('message.created'))
      }
      form.resetFields()
      setDrawerOpen(false)
      setEditingSupplier(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('error.save_failed'))
    }
  }

  const toggleActive = async (supplier: Supplier) => {
    try {
      await api.updateSupplier(supplier.id, { is_enabled: !supplier.is_enabled })
      void message.success(supplier.is_enabled ? t('admin.deactivated') : t('common.updated'))
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  const handleDelete = (supplier: Supplier) => {
    Modal.confirm({
      title: t('supplier.confirm_delete'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteSupplier(supplier.id)
          showUndoToast(t('undo.deleted', { item: t('nav.suppliers') }), async () => {
            await api.restoreFromRecycleBin('supplier', supplier.id)
            load()
          }, 8000)
          load()
        } catch (e: any) {
          void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
        }
      },
    })
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('supplier.title')}</Typography.Title>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>{t('button.export_excel')}</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingSupplier(null); form.resetFields(); setDrawerOpen(true) }}>
            {t('supplier.new')}
          </Button>
        </Space>
      </div>
      <Typography.Text type="secondary">{suppliers.length} {t('supplier.count')}</Typography.Text>
      <Table
        dataSource={suppliers}
        rowKey="id"
        size="small"
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        columns={[
          { title: t('supplier.code'), dataIndex: 'code', width: 120 },
          { title: t('supplier.name'), dataIndex: 'name', render: (v: string, r: Supplier) => <Link to={`/suppliers/${r.id}`}>{v}</Link> },
          { title: t('supplier.tax_number'), dataIndex: 'tax_number', render: (v: string | null) => v || '-' },
          { title: t('field.contact_name'), dataIndex: 'contact_name', render: (v: string | null) => v || '-' },
          { title: t('field.contact_phone'), dataIndex: 'contact_phone', render: (v: string | null) => v || '-' },
          { title: t('field.contact_email'), dataIndex: 'contact_email', render: (v: string | null) => v || '-' },
          { title: t('supplier.status'), dataIndex: 'is_enabled', width: 70, render: (v: boolean) => <Tag color={v !== false ? 'success' : 'default'}>{v !== false ? t('common.enabled') : t('common.disabled')}</Tag> },
          {
            title: t('common.actions'), width: 200, render: (_: unknown, r: Supplier) => (
              <Space>
                <Button size="small" icon={<EditOutlined />} onClick={() => { setEditingSupplier(r); form.setFieldsValue(r); setDrawerOpen(true) }} />
                <Button size="small" danger={r.is_enabled !== false} onClick={() => toggleActive(r)}>
                  {r.is_enabled !== false ? t('common.disabled') : t('common.enabled')}
                </Button>
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r)} />
              </Space>
            ),
          },
        ]}
      />
      <Drawer
        title={editingSupplier ? t('supplier.edit', { name: editingSupplier.name }) : t('supplier.new')}
        width={420}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setEditingSupplier(null) }}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => { setDrawerOpen(false); setEditingSupplier(null) }}>{t('button.cancel')}</Button>
            <Button type="primary" onClick={handleSave}>{t('button.save')}</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="code" label={t('supplier.code')} rules={[{ required: true }]}>
            <Input disabled={!!editingSupplier} />
          </Form.Item>
          <Form.Item name="name" label={t('supplier.name')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="tax_number" label={t('supplier.tax_number')}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_name" label={t('field.contact_name')}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_phone" label={t('field.contact_phone')}>
            <Input />
          </Form.Item>
          <Form.Item name="contact_email" label={t('field.contact_email')}>
            <Input />
          </Form.Item>
          <Divider orientation="left" plain style={{ fontSize: 13, color: '#8B5E3C' }}>
            {t('supplier.payee_section')}
          </Divider>
          <Form.Item
            name="payee_name"
            label={t('supplier.payee_name')}
            help={t('supplier.payee_name_help')}
          >
            <Input placeholder={editingSupplier?.name ?? ''} />
          </Form.Item>
          <Form.Item name="payee_bank" label={t('supplier.payee_bank')}>
            <Input />
          </Form.Item>
          <Form.Item name="payee_bank_account" label={t('supplier.payee_bank_account')}>
            <Input />
          </Form.Item>
          <Form.Item name="notes" label={t('supplier.notes')}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Drawer>
    </Space>
  )
}
