import { DeleteOutlined, EditOutlined, PaperClipOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons'
import { Button, Drawer, Form, Input, Modal, Select, Space, Table, Tag, Typography, Upload, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Shipment } from '@/api'

const STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  in_transit: 'processing',
  arrived: 'cyan',
  accepted: 'success',
  partially_accepted: 'warning',
  rejected: 'error',
  cancelled: 'default',
}

export function ShipmentsPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Shipment[]>([])
  const [loading, setLoading] = useState(false)
  const [editingShipment, setEditingShipment] = useState<Shipment | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [attachDrawer, setAttachDrawer] = useState<Shipment | null>(null)
  const [attachments, setAttachments] = useState<any[]>([])
  const [form] = Form.useForm()

  const load = () => {
    setLoading(true)
    api.listShipments().then(setRows).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const openEdit = (s: Shipment) => {
    setEditingShipment(s)
    form.resetFields()
    form.setFieldsValue({
      status: s.status,
      carrier: s.carrier,
      tracking_number: s.tracking_number,
      expected_date: s.expected_date,
      actual_date: s.actual_date,
      notes: s.notes,
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    if (!editingShipment) return
    try {
      const values = form.getFieldsValue()
      await api.updateShipment(editingShipment.id, values)
      void message.success(t('shipment.updated'))
      setDrawerOpen(false)
      setEditingShipment(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('error.save_failed'))
    }
  }

  const handleDelete = (s: Shipment) => {
    Modal.confirm({
      title: t('shipment.confirm_delete'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteShipment(s.id)
          void message.success(t('shipment.deleted'))
          load()
        } catch (e: any) {
          void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
        }
      },
    })
  }

  const openAttachments = async (s: Shipment) => {
    setAttachDrawer(s)
    try {
      const docs = await api.listShipmentAttachments(s.id)
      setAttachments(docs)
    } catch {
      setAttachments([])
    }
  }

  const handleUpload = async (file: File) => {
    if (!attachDrawer) return false
    try {
      const doc = await api.uploadDocument(file, 'shipment')
      await api.attachShipmentDocument(attachDrawer.id, doc.id)
      void message.success(t('shipment.attachment_added'))
      const docs = await api.listShipmentAttachments(attachDrawer.id)
      setAttachments(docs)
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
    return false
  }

  const handleRemoveAttachment = async (documentId: string) => {
    if (!attachDrawer) return
    try {
      await api.removeShipmentAttachment(attachDrawer.id, documentId)
      void message.success(t('message.deleted'))
      const docs = await api.listShipmentAttachments(attachDrawer.id)
      setAttachments(docs)
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  const columns: ColumnsType<Shipment> = [
    { title: t('field.shipment_number'), dataIndex: 'shipment_number', width: 150 },
    { title: t('field.status'), dataIndex: 'status', width: 120, render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{t(`status.${s}` as 'status.pending')}</Tag> },
    { title: t('field.carrier'), dataIndex: 'carrier', render: (v: string | null) => v || '-' },
    { title: t('field.tracking_number'), dataIndex: 'tracking_number', render: (v: string | null) => v || '-' },
    { title: t('field.expected_date'), dataIndex: 'expected_date', render: (v: string | null) => v || '-' },
    { title: t('field.actual_date'), dataIndex: 'actual_date', render: (v: string | null) => v || '-' },
    { title: t('shipment.items_count'), dataIndex: 'items', width: 80, render: (items: any[]) => items?.length || 0 },
    { title: t('field.created_at'), dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString() },
    {
      title: t('common.actions'), width: 200, render: (_: unknown, r: Shipment) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(r)} />
          <Button size="small" icon={<PaperClipOutlined />} onClick={() => openAttachments(r)} />
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r)} />
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('nav.shipments')}</Typography.Title>
        <Typography.Text type="secondary">{rows.length} {t('shipment.count')}</Typography.Text>
      </div>
      <Table<Shipment>
        rowKey="id"
        dataSource={rows}
        columns={columns}
        loading={loading}
        size="small"
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />

      <Drawer
        title={editingShipment ? t('shipment.edit', { number: editingShipment.shipment_number }) : ''}
        width={420}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setEditingShipment(null) }}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => { setDrawerOpen(false); setEditingShipment(null) }}>{t('button.cancel')}</Button>
            <Button type="primary" onClick={handleSave}>{t('button.save')}</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="status" label={t('field.status')}>
            <Select options={[
              { value: 'pending', label: t('status.pending') },
              { value: 'in_transit', label: t('status.in_transit') },
              { value: 'arrived', label: t('status.arrived') },
              { value: 'accepted', label: t('status.accepted') },
              { value: 'partially_accepted', label: t('status.partially_accepted') },
              { value: 'rejected', label: t('status.rejected') },
              { value: 'cancelled', label: t('status.cancelled') },
            ]} />
          </Form.Item>
          <Form.Item name="carrier" label={t('field.carrier')}>
            <Input />
          </Form.Item>
          <Form.Item name="tracking_number" label={t('field.tracking_number')}>
            <Input />
          </Form.Item>
          <Form.Item name="expected_date" label={t('field.expected_date')}>
            <Input type="date" />
          </Form.Item>
          <Form.Item name="actual_date" label={t('field.actual_date')}>
            <Input type="date" />
          </Form.Item>
          <Form.Item name="notes" label={t('shipment.notes')}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Drawer>

      <Drawer
        title={attachDrawer ? t('shipment.attachments', { number: attachDrawer.shipment_number }) : ''}
        width={480}
        open={!!attachDrawer}
        onClose={() => setAttachDrawer(null)}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Upload
            beforeUpload={handleUpload}
            showUploadList={false}
            multiple
          >
            <Button icon={<UploadOutlined />}>{t('shipment.upload_attachment')}</Button>
          </Upload>
          <Typography.Text type="secondary">{t('shipment.attachment_hint')}</Typography.Text>
          <Table
            dataSource={attachments}
            rowKey="document_id"
            size="small"
            pagination={false}
            columns={[
              { title: t('shipment.filename'), dataIndex: 'original_filename' },
              { title: t('shipment.file_size'), dataIndex: 'file_size', width: 100, render: (v: number) => `${(v / 1024).toFixed(1)} KB` },
              {
                title: t('common.actions'), width: 80, render: (_: unknown, r: any) => (
                  <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleRemoveAttachment(r.document_id)} />
                ),
              },
            ]}
          />
        </Space>
      </Drawer>
    </Space>
  )
}
