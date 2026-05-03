import { Card, Col, Progress, Row, Statistic } from 'antd'
import { useTranslation } from 'react-i18next'

import { type POProgress } from '@/api'

interface POProgressCardProps {
  progress: POProgress
}

export function POProgressCard({ progress }: POProgressCardProps) {
  const { t } = useTranslation()

  return (
    <Card title={t('progress.title')}>
      <Row gutter={24}>
        <Col span={8}>
          <Statistic title={t('progress.received')} value={progress.pct_received} suffix="%" />
          <Progress percent={Math.min(100, progress.pct_received)} status="active" />
        </Col>
        <Col span={8}>
          <Statistic title={t('progress.invoiced')} value={progress.pct_invoiced} suffix="%" />
          <Progress percent={Math.min(100, progress.pct_invoiced)} status="active" strokeColor="#faad14" />
        </Col>
        <Col span={8}>
          <Statistic title={t('progress.paid')} value={progress.pct_paid} suffix="%" />
          <Progress percent={Math.min(100, progress.pct_paid)} status="active" strokeColor="#52c41a" />
        </Col>
      </Row>
    </Card>
  )
}