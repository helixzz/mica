import { Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type PurchaseOrder } from '@/api'
import { fmtAmount } from '@/utils/format'

const PO_STATUSES = ['draft', 'confirmed', 'partially_received', 'fully_received', 'closed']

export function POListPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<PurchaseOrder[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.listPOs().then(setRows).finally(() => setLoading(false))
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
      filters: PO_STATUSES.map((s) => ({ text: t(`status.${s}` as 'status.confirmed'), value: s })),
      onFilter: (value, record) => record.status === value,
      render: (s) => <Tag color="success">{t(`status.${s}` as 'status.confirmed')}</Tag>,
    },
    {
      title: t('field.total_amount'),
      render: (_, r) => fmtAmount(r.total_amount, r.currency),
      align: 'right',
      sorter: (a, b) => Number(a.total_amount) - Number(b.total_amount),
    },
    {
      title: t('field.created_at'),
      dataIndex: 'created_at',
      render: (v: string) => new Date(v).toLocaleString(),
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      defaultSortOrder: 'descend',
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
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
        size="small"
      />
    </Space>
  )
}
