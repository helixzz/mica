import { Button, Card, Descriptions, Space, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Supplier } from '@/api'

export default function SupplierDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [supplier, setSupplier] = useState<Supplier | null>(null)

  useEffect(() => {
    if (!id) return
    void api.suppliers().then((list) => {
      setSupplier(list.find((s) => s.id === id) || null)
    })
  }, [id])

  if (!supplier) return <div>加载中...</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{supplier.name}</Typography.Title>
        <Button onClick={() => navigate('/suppliers')}>返回列表</Button>
      </div>
      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="名称">{supplier.name}</Descriptions.Item>
          <Descriptions.Item label="编码">{supplier.code || '-'}</Descriptions.Item>
          <Descriptions.Item label="联系人">{supplier.contact_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="电话">{supplier.contact_phone || '-'}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{supplier.contact_email || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  )
}
