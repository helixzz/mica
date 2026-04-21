import { Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Contract } from '@/api'

export function ContractsPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Contract[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.listContracts().then(setRows).finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<Contract> = [
    { title: t('field.contract_number'), dataIndex: 'contract_number' },
    { title: t('field.title'), dataIndex: 'title' },
    { title: t('field.status'), dataIndex: 'status', render: (s) => <Tag>{t(`status.${s}` as 'status.active')}</Tag> },
    { title: t('field.total_amount'), align: 'right', render: (_, r) => `${r.currency} ${r.total_amount}` },
    { title: t('field.signed_date'), dataIndex: 'signed_date' },
    { title: t('field.expiry_date'), dataIndex: 'expiry_date' },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>{t('nav.contracts')}</Typography.Title>
      <Table<Contract> rowKey="id" dataSource={rows} columns={columns} loading={loading} pagination={{ pageSize: 20 }} />
    </Space>
  )
}
