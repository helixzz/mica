import { PlusOutlined } from '@ant-design/icons'
import { Button, Table, Tag } from 'antd'
import { useTranslation } from 'react-i18next'

import { type Shipment } from '@/api'
import { ShipmentActions } from '@/components/ShipmentActions'
import { fmtAmount, fmtQty } from '@/utils/format'

interface ShipmentsTabProps {
  shipments: Shipment[]
  loadAll: () => void
  onRecordShipment: () => void
}

export function ShipmentsTab({ shipments, loadAll, onRecordShipment }: ShipmentsTabProps) {
  const { t } = useTranslation()

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
          { title: t('field.shipment_number'), dataIndex: 'shipment_number' },
          { title: t('field.status'), dataIndex: 'status',
            render: (s: string) => <Tag>{t(`status.${s}` as 'status.pending')}</Tag> },
          { title: t('field.carrier'), dataIndex: 'carrier' },
          { title: t('field.tracking_number'), dataIndex: 'tracking_number' },
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
                 { title: t('field.qty_shipped'), dataIndex: 'qty_shipped', align: 'right', render: (v: string) => fmtQty(v) },
                 { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right', render: (v: string) => fmtQty(v) },
                 { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', render: (v: string) => fmtAmount(v) },
              ]}
            />
          ),
        }}
      />
    </>
  )
}