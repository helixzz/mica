import { PlusOutlined } from '@ant-design/icons'
import { Button, Card, Table, Tag } from 'antd'
import dayjs from 'dayjs'
import { useTranslation } from 'react-i18next'

interface DeliveryPlanTabProps {
  deliveryPlans: any[]
  onNewPlan: () => void
}

export function DeliveryPlanTab({ deliveryPlans, onNewPlan }: DeliveryPlanTabProps) {
  const { t } = useTranslation()

  return (
    <Card>
      <div style={{ marginBottom: 12, textAlign: 'right' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={onNewPlan}>
          {t('delivery_plan.new_plan')}
        </Button>
      </div>
      <Table
        rowKey="id"
        dataSource={deliveryPlans}
        pagination={false}
        columns={[
          { title: t('delivery_plan.planned_date'), dataIndex: 'planned_date', render: (v: string) => dayjs(v).format('YYYY-MM-DD') },
          { title: t('nav.items'), dataIndex: 'item_name' },
          { title: t('delivery_plan.plan_name'), dataIndex: 'plan_name' },
          { title: t('delivery_plan.planned_qty'), dataIndex: 'planned_qty', align: 'right' },
          { title: t('delivery_plan.actual_qty'), dataIndex: 'actual_qty', align: 'right' },
          { title: t('delivery_plan.status'), dataIndex: 'status', render: (s: string) => <Tag>{t(`status.${s}`)}</Tag> },
        ]}
      />
    </Card>
  )
}