import { Card, Descriptions, Space, Typography, Button } from 'antd'
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

  const hasPayeeInfo = Boolean(
    supplier.payee_name || supplier.payee_bank || supplier.payee_bank_account,
  )

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{supplier.name}</Typography.Title>
        <Button onClick={() => navigate('/suppliers')}>{t('supplier.back_to_list')}</Button>
      </div>
      <Card title={t('supplier.basic_info')}>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label={t('supplier.name')}>{supplier.name}</Descriptions.Item>
          <Descriptions.Item label={t('supplier.code')}>{supplier.code || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('supplier.tax_number')}>{supplier.tax_number || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.contact_name')}>{supplier.contact_name || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.contact_phone')}>{supplier.contact_phone || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.contact_email')}>{supplier.contact_email || '-'}</Descriptions.Item>
          {supplier.notes && (
            <Descriptions.Item label={t('supplier.notes')} span={2}>{supplier.notes}</Descriptions.Item>
          )}
        </Descriptions>
      </Card>
      <Card title={t('supplier.payee_section')}>
        {hasPayeeInfo ? (
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label={t('supplier.payee_name')}>
              {supplier.payee_name || <Typography.Text type="secondary">{t('supplier.payee_fallback', { name: supplier.name })}</Typography.Text>}
            </Descriptions.Item>
            <Descriptions.Item label={t('supplier.payee_bank')}>{supplier.payee_bank || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('supplier.payee_bank_account')}>
              <Typography.Text code copyable={!!supplier.payee_bank_account}>
                {supplier.payee_bank_account || '-'}
              </Typography.Text>
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Typography.Text type="secondary">{t('supplier.payee_empty_hint')}</Typography.Text>
        )}
      </Card>
    </Space>
  )
}
