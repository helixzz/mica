import { Button, Card, Descriptions, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Item } from '@/api'

export default function ItemDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [item, setItem] = useState<Item | null>(null)

  useEffect(() => {
    if (!id) return
    void api.items().then((list) => {
      setItem(list.find((i) => i.id === id) || null)
    })
  }, [id])

  if (!item) return <div>加载中...</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{item.name}</Typography.Title>
        <Button onClick={() => navigate('/sku')}>返回 SKU 行情库</Button>
      </div>
      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="编码">{item.code}</Descriptions.Item>
          <Descriptions.Item label="名称">{item.name}</Descriptions.Item>
          <Descriptions.Item label="分类">{item.category || '-'}</Descriptions.Item>
          <Descriptions.Item label="单位">{item.uom}</Descriptions.Item>
          <Descriptions.Item label="规格" span={2}>{item.specification || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={item.is_active !== false ? 'success' : 'default'}>{item.is_active !== false ? '启用' : '停用'}</Tag></Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  )
}
