import { DeleteOutlined, EditOutlined, PaperClipOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons'
import { Button, Drawer, Form, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography, Upload, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PurchaseOrder, type Shipment } from '@/api'
import { fmtQty } from '@/utils/format'

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

  const [createOpen, setCreateOpen] = useState(false)
  const [poList, setPoList] = useState<PurchaseOrder[]>([])
  const [selectedPO, setSelectedPO] = useState<PurchaseOrder | null>(null)
  const [createLines, setCreateLines] = useState<{ po_item_id: string; qty_shipped: number }[]>([])
  const [createCarrier, setCreateCarrier] = useState('')
  const [createTracking, setCreateTracking] = useState('')
  const [createActualDate, setCreateActualDate] = useState('')
  const [createBusy, setCreateBusy] = useState(false)

  const load = () => {
    setLoading(true)
    api.listShipments().then(setRows).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const openCreate = async () => {
    setSelectedPO(null)
    setCreateLines([])
    setCreateCarrier('')
    setCreateTracking('')
    setCreateActualDate(new Date().toISOString().slice(0, 10))
    try {
      const pos = await api.listPOs()
      setPoList(pos)
    } catch { setPoList([]) }
    setCreateOpen(true)
  }

  const onSelectPO = async (poId: string) => {
    try {
      const po = await api.getPO(poId)
      setSelectedPO(po)
      setCreateLines(po.items.map(i => ({
        po_item_id: i.id,
        qty_shipped: Math.max(0, Number(i.qty) - Number(i.qty_received || 0)),
      })))
    } catch {
      setSelectedPO(null)
      setCreateLines([])
    }
  }

  const handleCreate = async () => {
    if (!selectedPO) return
    setCreateBusy(true)
    try {
      await api.createShipment({
        po_id: selectedPO.id,
        items: createLines.filter(l => l.qty_shipped > 0),
        carrier: createCarrier || null,
        tracking_number: createTracking || null,
        actual_date: createActualDate || null,
      })
      void message.success(t('message.shipment_recorded'))
      setCreateOpen(false)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('error.save_failed'))
    } finally {
      setCreateBusy(false)
    }
  }

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
        <Space>
          <Typography.Text type="secondary">{rows.length} {t('shipment.count')}</Typography.Text>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>{t('shipment.new')}</Button>
        </Space>
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

      <Modal
        title={t('shipment.new')}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        confirmLoading={createBusy}
        okButtonProps={{ disabled: !selectedPO || createLines.every(l => l.qty_shipped <= 0) }}
        width={800}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Select
            placeholder={t('shipment.select_po')}
            style={{ width: '100%' }}
            showSearch
            optionFilterProp="label"
            value={selectedPO?.id}
            onChange={onSelectPO}
            options={poList.map(po => ({ value: po.id, label: `${po.po_number} — ¥${Number(po.total_amount).toFixed(2)}` }))}
          />
          {selectedPO && (
            <>
              <Space>
                <Input placeholder={t('field.carrier')} value={createCarrier} onChange={e => setCreateCarrier(e.target.value)} style={{ width: 200 }} />
                <Input placeholder={t('field.tracking_number')} value={createTracking} onChange={e => setCreateTracking(e.target.value)} style={{ width: 200 }} />
                <Input type="date" value={createActualDate} onChange={e => setCreateActualDate(e.target.value)} style={{ width: 160 }} />
              </Space>
              <Typography.Text type="secondary">{t('po.shipment_help')}</Typography.Text>
              <Table
                rowKey="id"
                size="small"
                pagination={false}
                dataSource={selectedPO.items}
                columns={[
                  { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
                  { title: t('field.item_name'), dataIndex: 'item_name' },
                   { title: t('field.qty'), dataIndex: 'qty', align: 'right' as const, width: 90, render: (v: string) => fmtQty(v) },
                   { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right' as const, width: 100, render: (v: string) => fmtQty(v) },
                  {
                    title: t('field.qty_shipped'), width: 140,
                    render: (_: unknown, r: any, idx: number) => (
                      <InputNumber
                        min={0}
                        value={createLines[idx]?.qty_shipped}
                        onChange={v => setCreateLines(ls => ls.map((x, i) => i === idx ? { ...x, qty_shipped: Number(v ?? 0) } : x))}
                        style={{ width: '100%' }}
                      />
                    ),
                  },
                ]}
              />
            </>
          )}
        </Space>
      </Modal>
    </Space>
  )
}
