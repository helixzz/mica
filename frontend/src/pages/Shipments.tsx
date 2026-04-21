import { Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Shipment } from '@/api'

export function ShipmentsPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Shipment[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.listShipments().then(setRows).finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<Shipment> = [
    { title: t('field.shipment_number'), dataIndex: 'shipment_number' },
    { title: t('field.status'), dataIndex: 'status', render: (s) => <Tag>{t(`status.${s}` as 'status.pending')}</Tag> },
    { title: t('field.carrier'), dataIndex: 'carrier' },
    { title: t('field.tracking_number'), dataIndex: 'tracking_number' },
    { title: t('field.expected_date'), dataIndex: 'expected_date' },
    { title: t('field.actual_date'), dataIndex: 'actual_date' },
    { title: t('field.created_at'), dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString() },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>{t('nav.shipments')}</Typography.Title>
      <Table<Shipment> rowKey="id" dataSource={rows} columns={columns} loading={loading} pagination={{ pageSize: 20 }} />
    </Space>
  )
}
