import { useTranslation } from 'react-i18next'
import { Button, Card, Descriptions, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type Supplier } from '@/api'

export default function SuppliersPage() {
  const navigate = useNavigate()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  useEffect(() => { void api.suppliers().then(setSuppliers) }, [])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>供应商</Typography.Title>
      <Table dataSource={suppliers} rowKey="id" size="small" columns={[
        { title: '名称', dataIndex: 'name', render: (v: string, r: Supplier) => <Link to={`/suppliers/${r.id}`}>{v}</Link> },
        { title: '编码', dataIndex: 'code', width: 120 },
        { title: '联系人', dataIndex: 'contact_name', render: (v: string | null) => v || '-' },
        { title: '电话', dataIndex: 'contact_phone', render: (v: string | null) => v || '-' },
        { title: '邮箱', dataIndex: 'contact_email', render: (v: string | null) => v || '-' },
      ]} />
    </Space>
  )
}
