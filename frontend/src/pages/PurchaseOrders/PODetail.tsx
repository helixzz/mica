import { Button, Card, Descriptions, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type PurchaseOrder } from '@/api'

export function PODetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [po, setPo] = useState<PurchaseOrder | null>(null)

  useEffect(() => {
    if (!id) return
    void api.getPO(id).then(setPo)
  }, [id])

  if (!po) return <div>{t('message.loading')}</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Space align="center">
          <Typography.Title level={3} style={{ margin: 0 }}>
            {po.po_number}
          </Typography.Title>
          <Tag color="success">{t(`status.${po.status}` as 'status.confirmed')}</Tag>
        </Space>
        <Button onClick={() => navigate('/purchase-orders')}>{t('button.back')}</Button>
      </div>

      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label={t('field.po_number')}>{po.po_number}</Descriptions.Item>
          <Descriptions.Item label={t('field.total_amount')}>
            {po.currency} {po.total_amount}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.created_at')} span={2}>
            {new Date(po.created_at).toLocaleString()}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card>
        <Table
          rowKey="id"
          dataSource={po.items}
          pagination={false}
          columns={[
            { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
            { title: t('field.item_name'), dataIndex: 'item_name' },
            { title: t('field.qty'), dataIndex: 'qty', align: 'right' },
            { title: t('field.uom'), dataIndex: 'uom', width: 80 },
            { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right' },
            { title: t('field.amount'), dataIndex: 'amount', align: 'right' },
          ]}
        />
      </Card>
    </Space>
  )
}
