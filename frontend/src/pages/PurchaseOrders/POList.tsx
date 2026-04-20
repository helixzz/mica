import { Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type PurchaseOrder } from '@/api'

export function POListPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<PurchaseOrder[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api
      .listPOs()
      .then(setRows)
      .finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<PurchaseOrder> = [
    {
      title: t('field.po_number'),
      dataIndex: 'po_number',
      render: (v, r) => <Link to={`/purchase-orders/${r.id}`}>{v}</Link>,
    },
    {
      title: t('field.status'),
      dataIndex: 'status',
      render: (s) => <Tag color="success">{t(`status.${s}` as 'status.confirmed')}</Tag>,
    },
    {
      title: t('field.total_amount'),
      render: (_, r) => `${r.currency} ${r.total_amount}`,
      align: 'right',
    },
    {
      title: t('field.created_at'),
      dataIndex: 'created_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        {t('nav.purchase_orders')}
      </Typography.Title>
      <Table<PurchaseOrder>
        rowKey="id"
        dataSource={rows}
        columns={columns}
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </Space>
  )
}
