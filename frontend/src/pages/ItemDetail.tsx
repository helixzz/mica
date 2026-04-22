import { Button, Card, Descriptions, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Item } from '@/api'

export default function ItemDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [item, setItem] = useState<Item | null>(null)

  useEffect(() => {
    if (!id) return
    void api.items().then((list) => {
      setItem(list.find((i) => i.id === id) || null)
    })
  }, [id])

  if (!item) return <div>{t('message.loading')}</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{item.name}</Typography.Title>
        <Button onClick={() => navigate('/sku')}>{t('supplier.back_to_sku')}</Button>
      </div>
      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label={t('item.code')}>{item.code}</Descriptions.Item>
          <Descriptions.Item label={t('field.item_name')}>{item.name}</Descriptions.Item>
          <Descriptions.Item label={t('item.category_label')}>{item.category || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.uom')}>{item.uom}</Descriptions.Item>
          <Descriptions.Item label={t('field.specification')} span={2}>{item.specification || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.status')}><Tag color={item.is_active !== false ? 'success' : 'default'}>{item.is_active !== false ? t('item.active') : t('item.inactive')}</Tag></Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  )
}
