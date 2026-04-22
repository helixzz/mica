import { Button, Card, Descriptions, Space, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Supplier } from '@/api'

export default function SupplierDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [supplier, setSupplier] = useState<Supplier | null>(null)

  useEffect(() => {
    if (!id) return
    void api.suppliers().then((list) => {
      setSupplier(list.find((s) => s.id === id) || null)
    })
  }, [id])

  if (!supplier) return <div>{t('message.loading')}</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{supplier.name}</Typography.Title>
        <Button onClick={() => navigate('/suppliers')}>{t('supplier.back_to_list')}</Button>
      </div>
      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label={t('supplier.name')}>{supplier.name}</Descriptions.Item>
          <Descriptions.Item label={t('supplier.code')}>{supplier.code || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.contact_name')}>{supplier.contact_name || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.contact_phone')}>{supplier.contact_phone || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.contact_email')}>{supplier.contact_email || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  )
}
