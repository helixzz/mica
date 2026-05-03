import { Card, Descriptions } from 'antd'
import { useTranslation } from 'react-i18next'

import { type PurchaseOrder } from '@/api'
import { fmtAmount } from '@/utils/format'

interface POInfoCardProps {
  po: PurchaseOrder
}

export function POInfoCard({ po }: POInfoCardProps) {
  const { t } = useTranslation()

  return (
    <Card>
      <Descriptions bordered size="small" column={3}>
        <Descriptions.Item label={t('field.total_amount')}>
          {fmtAmount(po.total_amount, po.currency)}
        </Descriptions.Item>
        <Descriptions.Item label={t('field.amount_invoiced')}>
          {fmtAmount(po.amount_invoiced, po.currency)}
        </Descriptions.Item>
        <Descriptions.Item label={t('field.amount_paid')}>
          {fmtAmount(po.amount_paid, po.currency)}
        </Descriptions.Item>
        <Descriptions.Item label={t('field.created_at')} span={3}>
          {new Date(po.created_at).toLocaleString()}
        </Descriptions.Item>
      </Descriptions>
    </Card>
  )
}