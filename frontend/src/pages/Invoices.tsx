import { CheckCircleTwoTone, WarningTwoTone } from '@ant-design/icons'
import { Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type InvoiceListRow } from '@/api'
import { fmtAmount } from '@/utils/format'

export function InvoicesPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<InvoiceListRow[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.listInvoices().then(setRows).finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<InvoiceListRow> = [
    {
      title: t('field.internal_number'),
      dataIndex: 'internal_number',
      render: (v, r) => <Link to={`/invoices/${r.id}`}>{v}</Link>,
    },
    { title: t('field.invoice_number'), dataIndex: 'invoice_number' },
    { title: t('field.invoice_date'), dataIndex: 'invoice_date' },
    { title: t('field.subtotal'), dataIndex: 'subtotal', align: 'right' },
    { title: t('field.tax_amount'), dataIndex: 'tax_amount', align: 'right' },
    { title: t('field.total_amount'), dataIndex: 'total_amount', align: 'right' },
    {
      title: 'Match',
      dataIndex: 'is_fully_matched',
      width: 80,
      render: (v: boolean) =>
        v ? <CheckCircleTwoTone twoToneColor="#52c41a" /> : <WarningTwoTone twoToneColor="#faad14" />,
    },
    { title: t('field.status'), dataIndex: 'status',
      filters: [{text:'draft',value:'draft'},{text:'pending_match',value:'pending_match'},{text:'matched',value:'matched'},{text:'approved',value:'approved'},{text:'paid',value:'paid'},{text:'cancelled',value:'cancelled'}],
      onFilter: (value: any, record: any) => record.status === value, render: (s) => <Tag>{t(`status.${s}` as 'status.draft')}</Tag> },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>{t('nav.invoices')}</Typography.Title>
      <Table<InvoiceListRow> rowKey="id" dataSource={rows} columns={columns} loading={loading} pagination={{ pageSize: 20 }} />
    </Space>
  )
}
