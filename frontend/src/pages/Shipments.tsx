import { DownloadOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Input, InputNumber, Modal, Select, Space, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PurchaseOrder, type PurchaseOrderListItem, type Shipment } from '@/api'
import { ShipmentActions } from '@/components/ShipmentActions'
import { downloadCSV } from '@/utils/export'
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

  const [createOpen, setCreateOpen] = useState(false)
  const [poList, setPoList] = useState<PurchaseOrderListItem[]>([])
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

  const handleExport = () => {
    const headers = [
      t('field.shipment_number'), t('field.status'), t('field.carrier'),
      t('field.tracking_number'), t('field.expected_date'), t('field.actual_date'),
      t('shipment.items_count'), t('field.created_at'),
    ]
    const data = rows.map(r => [
      r.shipment_number, t(`status.${r.status}` as 'status.pending'), r.carrier || '',
      r.tracking_number || '', r.expected_date || '', r.actual_date || '',
      String(r.items?.length || 0), new Date(r.created_at).toLocaleString(),
    ])
    downloadCSV(`mica-shipments-${new Date().toISOString().slice(0, 10)}.csv`, headers, data)
  }

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
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      void message.error(err?.response?.data?.detail || t('error.save_failed'))
    } finally {
      setCreateBusy(false)
    }
  }

  const columns: ColumnsType<Shipment> = [
    { title: t('field.shipment_number'), dataIndex: 'shipment_number', width: 150 },
    { title: t('field.status'), dataIndex: 'status', width: 120, render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{t(`status.${s}` as 'status.pending')}</Tag> },
    { title: t('field.carrier'), dataIndex: 'carrier', render: (v: string | null) => v || '-' },
    { title: t('field.tracking_number'), dataIndex: 'tracking_number', render: (v: string | null) => v || '-' },
    { title: t('field.expected_date'), dataIndex: 'expected_date', render: (v: string | null) => v || '-' },
    { title: t('field.actual_date'), dataIndex: 'actual_date', render: (v: string | null) => v || '-' },
    { title: t('shipment.items_count'), dataIndex: 'items', width: 80, render: (items: Shipment['items']) => items?.length || 0 },
    { title: t('field.created_at'), dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString() },
    {
      title: t('common.actions'),
      width: 140,
      render: (_: unknown, r: Shipment) => (
        <ShipmentActions shipment={r} onChanged={load} />
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('nav.shipments')}</Typography.Title>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>{t('button.export_excel')}</Button>
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
                    render: (_: unknown, _r, idx: number) => (
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
