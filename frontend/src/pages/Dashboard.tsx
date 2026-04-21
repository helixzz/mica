import { Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type ApprovalTask, type PRListItem, type PurchaseOrder } from '@/api'
import { useAuth } from '@/auth/useAuth'

export function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [prs, setPrs] = useState<PRListItem[]>([])
  const [pos, setPos] = useState<PurchaseOrder[]>([])
  const [pending, setPending] = useState<ApprovalTask[]>([])

  useEffect(() => {
    void api.listPRs().then(setPrs).catch(() => setPrs([]))
    void api.listPOs().then(setPos).catch(() => setPos([]))
    void api.myPendingApprovals().then(setPending).catch(() => setPending([]))
  }, [])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>
        {t('message.welcome', { name: user?.display_name ?? '' })}
      </Typography.Title>

      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title={t('nav.purchase_requisitions')} value={prs.length} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('nav.purchase_orders')} value={pos.length} />
          </Card>
        </Col>
        <Col span={6}>
          <Card style={pending.length > 0 ? { background: '#fff7e6', borderColor: '#ffd591' } : undefined}>
            <Statistic
              title={t('nav.approvals')}
              value={pending.length}
              valueStyle={pending.length > 0 ? { color: '#fa8c16' } : undefined}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('field.total_amount')}
              value={pos.reduce((s, p) => s + Number(p.total_amount || 0), 0).toFixed(2)}
              prefix="¥"
            />
          </Card>
        </Col>
      </Row>

      {pending.length > 0 && (
        <Card title={t('nav.approvals')} size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            {pending.slice(0, 8).map((p) => (
              <div key={p.id}>
                <Space>
                  <Tag color="orange">{p.stage_name}</Tag>
                  <Link to={`/approvals`}>{p.instance_id.slice(0, 8)}</Link>
                  <Typography.Text type="secondary">
                    {new Date(p.assigned_at).toLocaleString()}
                  </Typography.Text>
                </Space>
              </div>
            ))}
          </Space>
        </Card>
      )}
    </Space>
  )
}
