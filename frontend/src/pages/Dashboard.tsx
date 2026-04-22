import { Col, Row, Space, Tag, Typography, theme, Button, List, Avatar } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import {
  AppstoreOutlined,
  AuditOutlined,
  BellOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  PlusOutlined,
  SettingOutlined,
  ShoppingCartOutlined,
  WarningOutlined,
  AlertOutlined,
} from '@ant-design/icons'

import {
  api,
  type ApprovalTask,
  type ContractExpiring,
  type DashboardMetrics,
  type PRListItem,
  type PurchaseOrder,
  type SKUAnomaly,
} from '@/api'
import { useAuth } from '@/auth/useAuth'
import { PageHeader, StatCard, Section, EmptyState } from '@/components/ui'

const { Text } = Typography

export function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { token } = theme.useToken()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [prs, setPrs] = useState<PRListItem[]>([])
  const [pos, setPos] = useState<PurchaseOrder[]>([])
  const [pending, setPending] = useState<ApprovalTask[]>([])
  const [contracts, setContracts] = useState<ContractExpiring[]>([])
  const [anomalies, setAnomalies] = useState<SKUAnomaly[]>([])
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [currentTime, setCurrentTime] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.listPRs().catch(() => []),
      api.listPOs().catch(() => []),
      api.myPendingApprovals().catch(() => []),
      api.listExpiringContracts(30).catch(() => []),
      api.listSKUAnomalies('pending').catch(() => []),
      api.getDashboardMetrics('last_month').catch(() => null),
    ]).then(([prsData, posData, pendingData, contractsData, anomaliesData, metricsData]) => {
      setPrs(prsData)
      setPos(posData)
      setPending(pendingData)
      setContracts(contractsData)
      setAnomalies(anomaliesData)
      setMetrics(metricsData)
      setLoading(false)
    })
  }, [])

  const role = user?.role || 'admin'
  const totalAmount = pos.reduce((s, p) => s + Number(p.total_amount || 0), 0).toFixed(2)

  // Role-specific tweaks
  const isItBuyer = role === 'it_buyer'
  const isDeptManager = role === 'dept_manager'
  const isProcurementMgr = role === 'procurement_mgr'
  const isFinanceAuditor = role === 'finance_auditor'
  const isRequester = role === 'requester'

  const prsInProgress = prs.filter((pr) => pr.status === 'submitted' || pr.status === 'approved').length
  const myPrs = prs.filter((pr) => pr.requester_id === user?.id)
  const myDrafts = myPrs.filter((pr) => pr.status === 'draft').length
  const myPending = myPrs.filter((pr) => pr.status === 'submitted').length
  const myApproved = myPrs.filter((pr) => pr.status === 'approved').length

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', paddingBottom: token.paddingXL }}>
      <PageHeader
        title={t('dashboard.greeting', { name: user?.display_name ?? '' })}
        subtitle={
          <Space>
            <Tag color="blue">{t(`role.${role}`)}</Tag>
            <Text type="secondary">
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {currentTime.toLocaleString()}
            </Text>
          </Space>
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            label={t('nav.purchase_requisitions')}
            value={isItBuyer ? prsInProgress : prs.length}
            icon={<FileTextOutlined />}
            loading={loading}
            variant={isItBuyer ? 'accent' : 'default'}
            trend={
              metrics && metrics.pr_count.direction !== 'flat'
                ? {
                    direction: metrics.pr_count.direction,
                    delta: metrics.pr_count.delta_pct,
                  }
                : undefined
            }
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            label={t('nav.purchase_orders')}
            value={pos.length}
            icon={<ShoppingCartOutlined />}
            loading={loading}
            trend={
              metrics && metrics.po_count.direction !== 'flat'
                ? {
                    direction: metrics.po_count.direction,
                    delta: metrics.po_count.delta_pct,
                  }
                : undefined
            }
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            label={t('nav.approvals')}
            value={pending.length}
            icon={<CheckCircleOutlined />}
            loading={loading}
            variant={isDeptManager || (pending.length > 0 && !isItBuyer) ? 'accent' : 'default'}
            trend={
              metrics && metrics.pending_approvals.direction !== 'flat'
                ? {
                    direction: metrics.pending_approvals.direction,
                    delta: metrics.pending_approvals.delta_pct,
                  }
                : undefined
            }
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            label={t('dashboard.total_amount_cny')}
            value={`¥${totalAmount}`}
            icon={<WarningOutlined />}
            loading={loading}
            variant={isFinanceAuditor || isProcurementMgr ? 'accent' : 'default'}
            trend={
              metrics && metrics.po_total_amount.direction !== 'flat'
                ? {
                    direction: metrics.po_total_amount.direction,
                    delta: metrics.po_total_amount.delta_pct,
                  }
                : undefined
            }
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Section
            title={t('dashboard.pending_approvals')}
            extra={<Link to="/approvals">{t('dashboard.view_all')}</Link>}
          >
            {loading ? (
              <div style={{ padding: token.paddingXL, textAlign: 'center' }}>{t('message.loading')}</div>
            ) : pending.length > 0 ? (
              <List
                itemLayout="horizontal"
                dataSource={pending.slice(0, 8)}
                renderItem={(item) => (
                  <List.Item
                    actions={[
                      <Link key="view" to={`/approvals`}>
                        {t('button.approve')}
                      </Link>,
                    ]}
                  >
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          style={{ backgroundColor: token.colorWarningBg, color: token.colorWarning }}
                          icon={<CheckCircleOutlined />}
                        />
                      }
                      title={<Link to={`/approvals`}>{item.instance_id.slice(0, 8)}</Link>}
                      description={
                        <Space>
                          <Tag color="orange">{item.stage_name}</Tag>
                          <Text type="secondary">{new Date(item.assigned_at).toLocaleString()}</Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <EmptyState illustration="welcome" title={t('dashboard.no_pending_approvals')} />
            )}
          </Section>
        </Col>
        <Col xs={24} lg={12}>
          <Section title={t('dashboard.alerts')}>
            {loading ? (
              <div style={{ padding: token.paddingXL, textAlign: 'center' }}>{t('message.loading')}</div>
            ) : contracts.length === 0 && anomalies.length === 0 ? (
              <EmptyState illustration="welcome" title={t('dashboard.no_alerts')} />
            ) : (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {contracts.length > 0 && (
                  <List
                    header={<Text strong>{t('dashboard.expiring_contracts')}</Text>}
                    itemLayout="horizontal"
                    dataSource={contracts.slice(0, 3)}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={
                            <Avatar
                              style={{ backgroundColor: token.colorErrorBg, color: token.colorError }}
                              icon={<AlertOutlined />}
                            />
                          }
                          title={item.title}
                          description={
                            <Space>
                              <Text>{item.contract_number}</Text>
                              <Text type="danger">{item.expiry_date}</Text>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                )}
                {anomalies.length > 0 && (
                  <List
                    header={<Text strong>{t('dashboard.price_anomalies')}</Text>}
                    itemLayout="horizontal"
                    dataSource={anomalies.slice(0, 3)}
                    renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          avatar={
                            <Avatar
                              style={{ backgroundColor: token.colorErrorBg, color: token.colorError }}
                              icon={<WarningOutlined />}
                            />
                          }
                          title={t('dashboard.anomaly_item', { id: item.item_id })}
                          description={
                            <Space>
                              <Text type="danger">{item.deviation_pct}%</Text>
                              <Text type="secondary">{item.observed_price}</Text>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                )}
              </Space>
            )}
          </Section>
        </Col>
      </Row>

      <Section title={t('dashboard.quick_actions')}>
        <Space wrap size="middle">
          {(isRequester || isItBuyer || role === 'admin') && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => navigate('/purchase-requisitions/new')}
            >
              {isRequester ? t('pr.submit_demand') : t('dashboard.new_pr')}
            </Button>
          )}
          {(isItBuyer || isProcurementMgr || role === 'admin') && (
            <Button icon={<PlusOutlined />} onClick={() => navigate('/rfqs/new')}>{t('dashboard.new_rfq')}
            </Button>
          )}
          {isRequester && (
            <Button onClick={() => navigate('/purchase-requisitions')}>{t('pr.my_prs')} {myPrs.length > 0 ? `(${myPrs.length})` : ''}
            </Button>
          )}
          {isDeptManager && (
            <Button type="primary" icon={<AuditOutlined />} onClick={() => navigate('/approvals')}>{t('dashboard.pending_approvals')} ({pending.length})
            </Button>
          )}
          {isFinanceAuditor && (
            <Button onClick={() => navigate('/payments')}>{t('dashboard.payment_mgmt')}
            </Button>
          )}
          <Button icon={<AppstoreOutlined />} onClick={() => navigate('/purchase-orders')}>
            {t('dashboard.view_all_pos')}
          </Button>
          {role === 'admin' && (
            <Button icon={<SettingOutlined />} onClick={() => navigate('/admin')}>
              {t('dashboard.admin_panel')}
            </Button>
          )}
          <Button icon={<BellOutlined />} onClick={() => navigate('/notifications')}>
            {t('dashboard.notifications')}
          </Button>
        </Space>
      </Section>

      {isRequester && myPrs.length > 0 && (
        <Section title={t('pr.my_progress')}>
          <Row gutter={16}>
            <Col span={8}><StatCard label={t('pr.draft_count')} value={myDrafts} variant={myDrafts > 0 ? 'accent' : 'default'} /></Col>
            <Col span={8}><StatCard label={t('pr.pending_count')} value={myPending} /></Col>
            <Col span={8}><StatCard label={t('pr.approved_awaiting')} value={myApproved} variant={myApproved > 0 ? 'accent' : 'default'} /></Col>
          </Row>
        </Section>
      )}
    </Space>
  )
}
