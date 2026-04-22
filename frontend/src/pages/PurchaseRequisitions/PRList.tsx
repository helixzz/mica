import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Input, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'

import { api, type PRListItem } from '@/api'
import { fmtAmount } from '@/utils/format'

const statusColors: Record<string, string> = {
  draft: 'default',
  submitted: 'processing',
  approved: 'success',
  rejected: 'error',
  returned: 'warning',
  cancelled: 'default',
  converted: 'cyan',
}

const STATUS_OPTIONS = ['draft', 'submitted', 'approved', 'rejected', 'returned', 'converted']

export function PRListPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [rows, setRows] = useState<PRListItem[]>([])
  const [loading, setLoading] = useState(false)
  const searchInput = useRef<any>(null)

  const load = () => {
    setLoading(true)
    api.listPRs().then(setRows).finally(() => setLoading(false))
  }

  useEffect(load, [])

  const getColumnSearchProps = (dataIndex: string) => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }: any) => (
      <div style={{ padding: 8 }}>
        <Input
          ref={searchInput}
          placeholder={t('button.search')}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => confirm()}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button type="primary" onClick={() => confirm()} icon={<SearchOutlined />} size="small">{t('button.search')}</Button>
          <Button onClick={() => { clearFilters?.(); confirm() }} size="small">{t('button.reset')}</Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => <SearchOutlined style={{ color: filtered ? '#8B5E3C' : undefined }} />,
    onFilter: (value: any, record: any) =>
      record[dataIndex]?.toString().toLowerCase().includes(value.toLowerCase()),
  })

  const columns: ColumnsType<PRListItem> = [
    {
      title: t('field.pr_number'),
      dataIndex: 'pr_number',
      render: (v, row) => <Link to={`/purchase-requisitions/${row.id}`}>{v}</Link>,
      ...getColumnSearchProps('pr_number'),
    },
    {
      title: t('field.title'),
      dataIndex: 'title',
      ...getColumnSearchProps('title'),
    },
    {
      title: t('field.status'),
      dataIndex: 'status',
      filters: STATUS_OPTIONS.map((s) => ({ text: t(`status.${s}` as 'status.draft'), value: s })),
      onFilter: (value, record) => record.status === value,
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>{t(`status.${s}` as 'status.draft')}</Tag>
      ),
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t('nav.purchase_requisitions')}
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/purchase-requisitions/new')}>
          {t('button.create')}
        </Button>
      </div>
      <Table<PRListItem>
        rowKey="id"
        dataSource={rows}
        columns={columns}
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => t('item.total_count', { total }) }}
        size="small"
      />
    </Space>
  )
}
