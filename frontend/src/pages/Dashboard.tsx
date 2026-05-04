import { Col, Row, Space, Tag, Typography, theme, Button, List, Avatar, Progress, Card } from 'antd'
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
  CarOutlined,
} from '@ant-design/icons'

import {
  api,
  type AgingApproval,
  type ApprovalTask,
  type BudgetSummary,
  type ContractExpiring,
  type DashboardMetrics,
  type PRListItem,
  type PurchaseOrderListItem,
  type SKUAnomaly,
  type DeliveryPlanOverview,
} from '@/api'
import { useAuth } from '@/auth/useAuth'
import { PageHeader, StatCard, Section, EmptyState } from '@/components/ui'
import { PaymentTracker } from '@/components/PaymentForecastChart'
import { InvoiceTracker } from '@/components/InvoiceTrackerChart'

const { Text } = Typography

export function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const { token } = theme.useToken()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [prs, setPrs] = useState<PRListItem[]>([])
  const [pos, setPos] = useState<PurchaseOrderListItem[]>([])
  const [pending, setPending] = useState<ApprovalTask[]>([])
  const [contracts, setContracts] = useState<ContractExpiring[]>([])
  const [anomalies, setAnomalies] = useState<SKUAnomaly[]>([])
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [deliveryOverview, setDeliveryOverview] = useState<DeliveryPlanOverview | null>(null)
  const [budgetSummary, setBudgetSummary] = useState<BudgetSummary | null>(null)
  const [agingApprovals, setAgingApprovals] = useState<AgingApproval[]>([])
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
      api.getDeliveryPlansOverview().catch(() => null),
      api.getBudgetSummary().catch(() => null),
      api.getAgingApprovals().catch(() => []),
    ]).then(([prsData, posData, pendingData, contractsData, anomaliesData, metricsData, deliveryData, budgetData, agingData]) => {
      setPrs(prsData)
      setPos(posData)
      setPending(pendingData)
      setContracts(contractsData)
      setAnomalies(anomaliesData)
      setMetrics(metricsData)
      setDeliveryOverview(deliveryData)
      setBudgetSummary(budgetData)
      setAgingApprovals(agingData)
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
        {pending.length > 0 && (
          <Col xs={24} sm={12} lg={8}>
            <StatCard
              label={t('dashboard.pending_approvals')}
              value={pending.length}
              icon={<CheckCircleOutlined />}
              loading={loading}
              variant="accent"
              trend={{
                direction: 'flat',
                delta: <Link to="/approvals">{t('dashboard.view_approvals')}</Link> as any,
              }}
            />
          </Col>
        )}
        {contracts.length > 0 && (
          <Col xs={24} sm={12} lg={8}>
            <StatCard
              label={t('dashboard.expiring_contracts')}
              value={contracts.length}
              icon={<AlertOutlined />}
              loading={loading}
              variant="accent"
              trend={{
                direction: 'flat',
                delta: <Link to="/contracts">{t('dashboard.view_contracts')}</Link> as any,
              }}
            />
          </Col>
        )}
        {deliveryOverview && deliveryOverview.total_planned > 0 && (
          <Col xs={24} sm={12} lg={8}>
            <StatCard
              label={t('dashboard.delivery_progress')}
              value={`${deliveryOverview.completion_pct}%`}
              icon={<CarOutlined />}
              loading={loading}
              trend={{
                direction: 'flat',
                delta: <Link to="/delivery-plans">{t('dashboard.view_delivery')}</Link> as any,
              }}
            />
          </Col>
        )}
      </Row>

      {(isProcurementMgr || isFinanceAuditor || role === 'admin') && (
        <PaymentTracker />
      )}

      {(isProcurementMgr || isFinanceAuditor || role === 'admin') && (
        <InvoiceTracker />
      )}

      {(isProcurementMgr || isFinanceAuditor || role === 'admin') && budgetSummary && budgetSummary.items.length > 0 && (
        <Section title={t('dashboard.budget_overview')}>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card size="small">
                <StatCard
                  label={t('dashboard.total_budget')}
                  value={`¥${budgetSummary.total_budget.toLocaleString()}`}
                  loading={loading}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small">
                <StatCard
                  label={t('dashboard.total_spend')}
                  value={`¥${budgetSummary.total_spend.toLocaleString()}`}
                  loading={loading}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card size="small">
                <StatCard
                  label={t('dashboard.total_utilization')}
                  value={`${budgetSummary.total_utilization_pct}%`}
                  loading={loading}
                  variant={budgetSummary.total_utilization_pct > 90 ? 'accent' : 'default'}
                />
              </Card>
            </Col>
          </Row>
          <div style={{ marginTop: 16 }}>
            {budgetSummary.items.map((item) => (
              <Card
                key={item.cost_center_id}
                size="small"
                style={{ marginBottom: 8 }}
                title={
                  <Space>
                    <Text strong>{item.code}</Text>
                    <Text type="secondary">{item.label_zh}</Text>
                  </Space>
                }
                extra={
                  <Text type={item.utilization_pct > 90 ? 'danger' : 'secondary'}>
                    {item.utilization_pct}%
                  </Text>
                }
              >
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                  <Row justify="space-between">
                    <Col>
                      <Text type="secondary">{t('dashboard.budget')}: ¥{item.annual_budget?.toLocaleString() ?? '-'}</Text>
                    </Col>
                    <Col>
                      <Text type="secondary">{t('dashboard.actual_spend')}: ¥{item.actual_spend.toLocaleString()}</Text>
                    </Col>
                  </Row>
                  <Progress
                    percent={item.utilization_pct}
                    status={item.utilization_pct > 90 ? 'exception' : item.utilization_pct > 70 ? 'active' : 'normal'}
                    size="small"
                  />
                </Space>
              </Card>
            ))}
          </div>
        </Section>
      )}

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
                      <Link key="view" to={`/purchase-requisitions/${item.biz_id}`}>
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
                      title={<Link to={`/purchase-requisitions/${item.biz_id}`}>{item.biz_number || item.instance_id.slice(0, 8)}: {item.biz_title || item.stage_name}</Link>}
                      description={
                        <Space>
                          <Tag color="orange">{item.stage_name}</Tag>
                          {item.submitter_name && <Text type="secondary">{item.submitter_name}</Text>}
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
            ) : contracts.length === 0 && anomalies.length === 0 && (metrics?.invoices_pending_match ?? 0) + (metrics?.invoices_mismatched ?? 0) === 0 ? (
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
                {((metrics?.invoices_pending_match ?? 0) + (metrics?.invoices_mismatched ?? 0)) > 0 && (
                  <List
                    header={<Text strong>{t('dashboard.pending_invoices')}</Text>}
                    itemLayout="horizontal"
                    dataSource={[
                      ...(metrics?.invoices_pending_match
                        ? [{ key: 'match', count: metrics.invoices_pending_match, kind: 'pending_match' as const }]
                        : []),
                      ...(metrics?.invoices_mismatched
                        ? [{ key: 'mismatch', count: metrics.invoices_mismatched, kind: 'mismatched' as const }]
                        : []),
                    ]}
                    renderItem={(item) => (
                      <List.Item
                        actions={[<Link key="v" to="/invoices">{t('dashboard.view_all')}</Link>]}
                      >
                        <List.Item.Meta
                          avatar={
                            <Avatar
                              style={{
                                backgroundColor: item.kind === 'mismatched' ? token.colorErrorBg : token.colorWarningBg,
                                color: item.kind === 'mismatched' ? token.colorError : token.colorWarning,
                              }}
                              icon={<FileTextOutlined />}
                            />
                          }
                          title={t('dashboard.invoice_alert_count', {
                            count: item.count,
                            status: t(`status.${item.kind}` as 'status.pending_match'),
                          })}
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

      {agingApprovals.length > 0 && (
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Section
              title={t('dashboard.aging_approvals')}
              extra={<Link to="/approvals">{t('dashboard.view_all')}</Link>}
            >
              <List
                itemLayout="horizontal"
                dataSource={agingApprovals}
                renderItem={(item) => {
                  const slaColor = item.is_overdue
                    ? token.colorError
                    : item.is_approaching
                      ? token.colorWarning
                      : token.colorSuccess
                  const slaBg = item.is_overdue
                    ? token.colorErrorBg
                    : item.is_approaching
                      ? token.colorWarningBg
                      : token.colorSuccessBg
                  const slaLabel = item.is_overdue
                    ? t('dashboard.overdue')
                    : item.is_approaching
                      ? t('dashboard.approaching_sla')
                      : t('dashboard.within_sla')
                  return (
                    <List.Item
                      actions={[
                        <Link key="view" to={`/purchase-requisitions/${item.pr_id}`}>
                          {t('dashboard.view_all')}
                        </Link>,
                      ]}
                    >
                      <List.Item.Meta
                        avatar={
                          <Avatar
                            style={{ backgroundColor: slaBg, color: slaColor }}
                            icon={<ClockCircleOutlined />}
                          />
                        }
                        title={
                          <Link to={`/purchase-requisitions/${item.pr_id}`}>
                            {item.pr_number}: {item.title}
                          </Link>
                        }
                        description={
                          <Space>
                            <Text type="secondary">
                              {t('dashboard.hours_waiting', { hours: item.hours_since_submission })}
                            </Text>
                            <Tag color={item.is_overdue ? 'red' : item.is_approaching ? 'orange' : 'green'}>
                              {slaLabel}
                            </Tag>
                          </Space>
                        }
                      />
                    </List.Item>
                  )
                }}
              />
            </Section>
          </Col>
        </Row>
      )}

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
