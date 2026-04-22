import { useTranslation } from 'react-i18next'
import { Button, Card, Descriptions, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type Supplier } from '@/api'

export default function SuppliersPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  useEffect(() => { void api.suppliers().then(setSuppliers) }, [])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>{t('supplier.title')}</Typography.Title>
      <Table dataSource={suppliers} rowKey="id" size="small" columns={[
        { title: t('supplier.name'), dataIndex: 'name', render: (v: string, r: Supplier) => <Link to={`/suppliers/${r.id}`}>{v}</Link> },
        { title: t('supplier.code'), dataIndex: 'code', width: 120 },
        { title: t('field.contact_name'), dataIndex: 'contact_name', render: (v: string | null) => v || '-' },
        { title: t('field.contact_phone'), dataIndex: 'contact_phone', render: (v: string | null) => v || '-' },
        { title: t('field.contact_email'), dataIndex: 'contact_email', render: (v: string | null) => v || '-' },
      ]} />
    </Space>
  )
}
