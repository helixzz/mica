import { Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type PRListItem, type PurchaseOrder } from '@/api'
import { useAuth } from '@/auth/useAuth'

export function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [prs, setPrs] = useState<PRListItem[]>([])
  const [pos, setPos] = useState<PurchaseOrder[]>([])

  useEffect(() => {
    void api.listPRs().then(setPrs).catch(() => setPrs([]))
    void api.listPOs().then(setPos).catch(() => setPos([]))
  }, [])

  const pendingForMe =
    user?.role === 'dept_manager' || user?.role === 'admin'
      ? prs.filter((p) => p.status === 'submitted')
      : []

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>
        {t('message.welcome', { name: user?.display_name ?? '' })}
      </Typography.Title>
      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic title={t('nav.purchase_requisitions')} value={prs.length} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title={t('nav.purchase_orders')} value={pos.length} />
          </Card>
        </Col>
        {pendingForMe.length > 0 && (
          <Col span={8}>
            <Card style={{ background: '#fff7e6', borderColor: '#ffd591' }}>
              <Statistic
                title={t('status.submitted')}
                value={pendingForMe.length}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
        )}
      </Row>

      {pendingForMe.length > 0 && (
        <Card title={t('status.submitted')} size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            {pendingForMe.slice(0, 5).map((p) => (
              <Link key={p.id} to={`/purchase-requisitions/${p.id}`}>
                <Space>
                  <Tag color="orange">{p.pr_number}</Tag>
                  <span>{p.title}</span>
                  <Typography.Text type="secondary">{p.currency} {p.total_amount}</Typography.Text>
                </Space>
              </Link>
            ))}
          </Space>
        </Card>
      )}
    </Space>
  )
}
