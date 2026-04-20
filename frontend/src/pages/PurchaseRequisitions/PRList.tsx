import { PlusOutlined } from '@ant-design/icons'
import { Button, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { api, type PRListItem } from '@/api'

const statusColors: Record<string, string> = {
  draft: 'default',
  submitted: 'processing',
  approved: 'success',
  rejected: 'error',
  returned: 'warning',
  cancelled: 'default',
  converted: 'cyan',
}

export function PRListPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [rows, setRows] = useState<PRListItem[]>([])
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    api
      .listPRs()
      .then(setRows)
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const columns: ColumnsType<PRListItem> = [
    {
      title: t('field.pr_number'),
      dataIndex: 'pr_number',
      render: (v, row) => <Link to={`/purchase-requisitions/${row.id}`}>{v}</Link>,
    },
    { title: t('field.title'), dataIndex: 'title' },
    {
      title: t('field.status'),
      dataIndex: 'status',
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>{t(`status.${s}` as 'status.draft')}</Tag>
      ),
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t('nav.purchase_requisitions')}
        </Typography.Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/purchase-requisitions/new')}
        >
          {t('button.create')}
        </Button>
      </div>
      <Table<PRListItem>
        rowKey="id"
        dataSource={rows}
        columns={columns}
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </Space>
  )
}
