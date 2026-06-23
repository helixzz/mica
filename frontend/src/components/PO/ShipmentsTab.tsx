import { PaperClipOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Shipment } from '@/api'
import { ShipmentActions } from '@/components/ShipmentActions'
import { fmtAmount, fmtAmountNode, fmtQty, fmtQtyNode } from '@/utils/format'
import { MonoId } from '@/components/ui/Mono'

interface ShipmentsTabProps {
  shipments: Shipment[]
  currency: string
  loadAll: () => void
  onRecordShipment: () => void
}

interface AttachmentInfo {
  document_id: string
  original_filename: string
  file_size: number
}

export function ShipmentsTab({ shipments, currency, loadAll, onRecordShipment }: ShipmentsTabProps) {
  const { t } = useTranslation()
  const [attachMap, setAttachMap] = useState<Record<string, AttachmentInfo[]>>({})

  useEffect(() => {
    const fetchAttachments = async () => {
      const map: Record<string, AttachmentInfo[]> = {}
      await Promise.all(
        shipments.map(async (s) => {
          try {
            const docs = await api.listShipmentAttachments(s.id)
            map[s.id] = docs as AttachmentInfo[]
          } catch {
            map[s.id] = []
          }
        })
      )
      setAttachMap(map)
    }
    if (shipments.length > 0) void fetchAttachments()
  }, [shipments])

  return (
    <>
      <div style={{ marginBottom: 12, textAlign: 'right' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={onRecordShipment}>
          {t('button.record_shipment')}
        </Button>
      </div>
      <Table
        rowKey="id"
        dataSource={shipments}
        pagination={false}
        columns={[
          {
            title: t('field.shipment_number'),
            dataIndex: 'shipment_number',
            render: (val: string, r) => {
              const files = attachMap[r.id] || []
              return (
                <div>
                  <div><MonoId>{val}</MonoId></div>
                  {files.length > 0 && (
                    <Space size={4} wrap style={{ marginTop: 4 }}>
                      {files.map((f) => (
                        <Tag
                          key={f.document_id}
                          icon={<PaperClipOutlined />}
                          color="default"
                          style={{ fontSize: 11, lineHeight: '18px', margin: 0 }}
                        >
                          {f.original_filename.length > 20
                            ? `${f.original_filename.slice(0, 18)}…`
                            : f.original_filename}
                        </Tag>
                      ))}
                    </Space>
                  )}
                </div>
              )
            },
          },
          { title: t('field.status'), dataIndex: 'status',
            render: (s: string) => <Tag>{t(`status.${s}` as 'status.pending')}</Tag> },
          { title: t('field.carrier'), dataIndex: 'carrier' },
          { title: t('field.tracking_number'), dataIndex: 'tracking_number', render: (v: string | null) => v ? <MonoId>{v}</MonoId> : '-' },
          { title: t('field.expected_date'), dataIndex: 'expected_date' },
          { title: t('field.actual_date'), dataIndex: 'actual_date' },
          {
            title: t('common.actions'),
            width: 140,
            render: (_: unknown, r) => (
              <ShipmentActions shipment={r} onChanged={() => void loadAll()} />
            ),
          },
        ]}
        expandable={{
          expandedRowRender: (r) => (
            <Table
              rowKey="id"
              dataSource={r.items}
              pagination={false}
              size="small"
              columns={[
                { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
                { title: t('field.item_name'), dataIndex: 'item_name' },
                 { title: t('field.qty_shipped'), dataIndex: 'qty_shipped', align: 'right', render: (v: string) => fmtQtyNode(v) },
                 { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right', render: (v: string) => fmtQtyNode(v) },
                 { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', render: (v: string) => fmtAmountNode(v, currency) },
              ]}
            />
          ),
        }}
      />
    </>
  )
}
