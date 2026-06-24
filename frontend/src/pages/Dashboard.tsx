import { Col, Row, Space, Tag, Typography, theme, Button, Dropdown, Grid, List, Avatar, Progress, Card, Tabs, Table, Drawer, Switch } from 'antd'
import { memo, useEffect, useMemo, useState } from 'react'
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
  MenuOutlined,
  MoreOutlined,
} from '@ant-design/icons'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

import {
  api,
  type AgingApproval,
  type AnalyticsData,
  type ApprovalTask,
  type BudgetSummary,
  type ContractExpiring,
  type DashboardMetrics,
  type DeviationRate,
  type PRListItem,
  type PurchaseOrderListItem,
  type SKUAnomaly,
  type DeliveryPlanOverview,
  type InvoiceMatchSummary,
  type PaymentCalendarItem,
} from '@/api'
import { useAuth } from '@/auth/useAuth'
import { StatCard, Section, EmptyState } from '@/components/ui'
import { PaymentTracker } from '@/components/PaymentForecastChart'
import { InvoiceTracker } from '@/components/InvoiceTrackerChart'
import { fmtAmount, fmtAmountNode } from '@/utils/format'
import { MonoId } from '@/components/ui/Mono'

const { Text } = Typography

interface SortableItemProps {
  id: string
  title: string
  visible: boolean
  onToggle: (id: string, checked: boolean) => void
}

function SortableItem({ id, title, visible, onToggle }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    padding: '12px 16px',
    marginBottom: 8,
    backgroundColor: 'var(--color-bg-container)',
    border: '1px solid var(--color-border)',
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <Space>
        <div {...listeners} style={{ cursor: 'grab', padding: '0 8px' }}>
          <MenuOutlined style={{ color: 'var(--color-text-secondary)' }} />
        </div>
        <Text>{title}</Text>
      </Space>
      <Switch checked={visible} onChange={(checked) => onToggle(id, checked)} />
    </div>
  )
}

export function DashboardPage() {
  const { t, i18n } = useTranslation()
  const { user } = useAuth()
  const { token } = theme.useToken()
  const screens = Grid.useBreakpoint()
  const isMobile = !screens.md
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
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [invoiceMatch, setInvoiceMatch] = useState<InvoiceMatchSummary[]>([])
  const [paymentCalendar, setPaymentCalendar] = useState<PaymentCalendarItem[]>([])
  const [deviationRate, setDeviationRate] = useState<DeviationRate | null>(null)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [customizeVisible, setCustomizeVisible] = useState(false)
  const [showWelcome, setShowWelcome] = useState(() => !localStorage.getItem('mica.welcome_dismissed'))

  const defaultLayout = [
    { id: 'stats', visible: true },
    { id: 'alerts', visible: true },
    { id: 'payment_tracker', visible: true },
    { id: 'invoice_tracker', visible: true },
    { id: 'analytics', visible: true },
    { id: 'invoice_match', visible: true },
    { id: 'payment_calendar', visible: true },
    { id: 'budget', visible: true },
    { id: 'aging', visible: true },
    { id: 'my_progress', visible: true },
  ]

  const [layout, setLayout] = useState<{ id: string; visible: boolean }[]>(() => {
    try {
      const saved = localStorage.getItem('mica.dashboard_layout')
      if (saved) {
        const parsed = JSON.parse(saved)
        const merged = [...parsed]
        defaultLayout.forEach((def) => {
          if (!merged.find((m) => m.id === def.id)) {
            merged.push(def)
          }
        })
        return merged
      }
    } catch {
    }
    return defaultLayout
  })

  useEffect(() => {
    localStorage.setItem('mica.dashboard_layout', JSON.stringify(layout))
  }, [layout])

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event

    if (over && active.id !== over.id) {
      setLayout((items) => {
        const oldIndex = items.findIndex((item) => item.id === active.id)
        const newIndex = items.findIndex((item) => item.id === over.id)
        return arrayMove(items, oldIndex, newIndex)
      })
    }
  }

  const handleToggleSection = (id: string, checked: boolean) => {
    setLayout((items) => items.map((item) => (item.id === id ? { ...item, visible: checked } : item)))
  }

  const isSectionVisible = (id: string) => {
    return layout.find((item) => item.id === id)?.visible ?? true
  }

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
      api.getAnalytics().catch(() => null),
      api.getInvoiceMatchSummary().catch(() => []),
      api.getPaymentCalendar().catch(() => []),
      api.getDeviationRate(30).catch(() => null),
    ]).then(([prsData, posData, pendingData, contractsData, anomaliesData, metricsData, deliveryData, budgetData, agingData, analyticsData, invoiceMatchData, paymentCalendarData, deviationData]) => {
      setPrs(prsData)
      setPos(posData)
      setPending(pendingData)
      setContracts(contractsData)
      setAnomalies(anomaliesData)
      setMetrics(metricsData)
      setDeliveryOverview(deliveryData)
      setBudgetSummary(budgetData)
      setAgingApprovals(agingData)
      setAnalytics(analyticsData)
      setInvoiceMatch(invoiceMatchData)
      setPaymentCalendar(paymentCalendarData)
      setDeviationRate(deviationData)
      setLoading(false)
    }).catch(() => {
      setLoading(false)
    })
  }, [])

  const role = user?.role || 'admin'
  const totalAmount = pos.reduce((s, p) => s + Number(p.total_amount || 0), 0)

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

  const sectionTitles: Record<string, string> = {
    stats: t('dashboard.stats_cards', 'Stats Cards'),
    alerts: t('dashboard.alerts'),
    payment_tracker: t('dashboard.payment_tracker', 'Payment Tracker'),
    invoice_tracker: t('dashboard.invoice_tracker', 'Invoice Tracker'),
    analytics: t('dashboard.analytics'),
    invoice_match: t('dashboard.invoice_match'),
    payment_calendar: t('dashboard.payment_calendar'),
    budget: t('dashboard.budget_overview'),
    aging: t('dashboard.aging_approvals'),
    my_progress: t('pr.my_progress'),
  }

  const renderSection = (id: string) => {
    if (!isSectionVisible(id)) return null

    switch (id) {
      case 'stats':
        return (
          <Row gutter={[12, 12]} key="stats">
            <Col xs={24} sm={12} lg={6}>
              <StatCard
                label={t('nav.purchase_requisitions')}
                value={isItBuyer ? prsInProgress : prs.length}
                icon={<FileTextOutlined />}
                loading={loading}
                density="compact"
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
                density="compact"
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
                density="compact"
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
                value={fmtAmount(totalAmount, 'CNY')}
                icon={<WarningOutlined />}
                loading={loading}
                density="compact"
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
        )
      case 'alerts':
        return (
          <Space direction="vertical" size="middle" style={{ width: '100%' }} key="alerts">
            <Row gutter={[12, 12]}>
              {pending.length > 0 && (
                <Col xs={24} sm={12} lg={6}>
                  <StatCard
                    label={t('dashboard.pending_approvals')}
                    value={pending.length}
                    icon={<CheckCircleOutlined />}
                    loading={loading}
                    variant="accent"
                    density="compact"
                    footer={<Link to="/approvals">{t('dashboard.view_approvals')}</Link>}
                  />
                </Col>
              )}
              {contracts.length > 0 && (
                <Col xs={24} sm={12} lg={6}>
                  <StatCard
                    label={t('dashboard.expiring_contracts')}
                    value={contracts.length}
                    icon={<AlertOutlined />}
                    loading={loading}
                    variant="accent"
                    density="compact"
                    footer={<Link to="/contracts">{t('dashboard.view_contracts')}</Link>}
                  />
                </Col>
              )}
              {deliveryOverview && deliveryOverview.total_planned > 0 && (
                <Col xs={24} sm={12} lg={6}>
                  <StatCard
                    label={t('dashboard.delivery_progress')}
                    value={`${Math.round(deliveryOverview.completion_pct)}%`}
                    icon={<CarOutlined />}
                    loading={loading}
                    variant="accent"
                    density="compact"
                    footer={<Link to="/delivery-plans">{t('dashboard.view_delivery')}</Link>}
                  />
                </Col>
              )}
              {deviationRate && deviationRate.total_links > 0 && (
                <Col xs={24} sm={12} lg={6}>
                  <StatCard
                    label={t('fulfillment.deviation_rate_card_title')}
                    value={`${(deviationRate.deviation_rate * 100).toFixed(1)}%`}
                    icon={<AlertOutlined />}
                    loading={loading}
                    variant="accent"
                    density="compact"
                    footer={
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {deviationRate.deviated_links} / {deviationRate.total_links}
                      </Text>
                    }
                  />
                </Col>
              )}
            </Row>
            <Row gutter={[12, 12]}>
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
          </Space>
        )
      case 'payment_tracker':
        return (isProcurementMgr || isFinanceAuditor || isItBuyer || role === 'admin') ? <PaymentTracker key="payment_tracker" /> : null
      case 'invoice_tracker':
        return (isProcurementMgr || isFinanceAuditor || isItBuyer || role === 'admin') ? <InvoiceTracker key="invoice_tracker" /> : null
      case 'analytics':
        return (isProcurementMgr || isFinanceAuditor || isItBuyer || role === 'admin') && analytics ? (
          <Section title={t('dashboard.analytics')} key="analytics">
            <Tabs
              items={[
                {
                  key: 'spend-trend',
                  label: t('dashboard.spend_trend'),
                  children: analytics.trend.length === 0 ? (
                    <EmptyState illustration="welcome" title={t('dashboard.no_analytics_data')} />
                  ) : (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 200, padding: '20px 0 32px', overflow: 'auto' }}>
                        {analytics.trend.map((point) => {
                          const maxTotal = Math.max(...analytics.trend.map((p) => p.total), 1)
                          const heightPct = (point.total / maxTotal) * 100
                          return (
                            <div
                              key={point.month}
                              style={{
                                flex: 1,
                                minWidth: 40,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                height: '100%',
                              }}
                            >
                              <Text type="secondary" style={{ fontSize: 11, marginBottom: 4 }}>
                                {fmtAmount(point.total / 10000, 'CNY')}w
                              </Text>
                              <div
                                style={{
                                  width: '80%',
                                  height: `${Math.max(heightPct, 2)}%`,
                                  backgroundColor: 'var(--color-primary)',
                                  borderRadius: '4px 4px 0 0',
                                  minWidth: 20,
                                  transition: 'height 0.3s',
                                }}
                              />
                              <Text type="secondary" style={{ fontSize: 10, marginTop: 4, transform: 'rotate(-45deg)', transformOrigin: 'top left', whiteSpace: 'nowrap' }}>
                                {point.month.slice(2)}
                              </Text>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'dept-consumption',
                  label: t('dashboard.dept_consumption'),
                  children: (
                    <Table
                      dataSource={analytics.departments}
                      rowKey="dept"
                      pagination={false}
                      size="small"
                      columns={[
                        { title: t('dashboard.department_col'), dataIndex: 'dept', key: 'dept' },
                        {
                          title: t('dashboard.total_spend_col'),
                          dataIndex: 'total',
                          key: 'total',
                          render: (v: number) => fmtAmountNode(v, 'CNY'),
                        },
                        {
                          title: t('dashboard.pct_of_total'),
                          dataIndex: 'pct',
                          key: 'pct',
                          render: (v: number) => (
                            <Progress percent={v} size="small" style={{ minWidth: 80 }} />
                          ),
                        },
                      ]}
                    />
                  ),
                },
                {
                  key: 'supplier-performance',
                  label: t('dashboard.supplier_performance'),
                  children: (
                    <Table
                      dataSource={analytics.suppliers}
                      rowKey="supplier"
                      pagination={false}
                      size="small"
                      columns={[
                        { title: t('dashboard.supplier_col'), dataIndex: 'supplier', key: 'supplier' },
                        {
                          title: t('dashboard.total_shipments_col'),
                          dataIndex: 'total_shipments',
                          key: 'total_shipments',
                        },
                        {
                          title: t('dashboard.avg_delivery_days_col'),
                          dataIndex: 'avg_delivery_days',
                          key: 'avg_delivery_days',
                          render: (v: number) => (
                            <Tag color={v <= 7 ? 'green' : v <= 14 ? 'orange' : 'red'}>
                              {t('dashboard.days_unit', { days: v })}
                            </Tag>
                          ),
                        },
                      ]}
                    />
                  ),
                },
              ]}
            />
          </Section>
        ) : null
      case 'invoice_match':
        return (isProcurementMgr || isFinanceAuditor || isItBuyer || role === 'admin') && invoiceMatch.length > 0 ? (
          <Section title={t('dashboard.invoice_match')} key="invoice_match">
            <Table
              dataSource={invoiceMatch}
              rowKey="po_number"
              pagination={false}
              size="small"
              columns={[
                { title: t('field.po_number'), dataIndex: 'po_number', key: 'po_number', render: (v: string) => <MonoId>{v}</MonoId> },
                { title: t('dashboard.qty_ordered'), dataIndex: 'qty_ordered', key: 'qty_ordered' },
                { title: t('dashboard.qty_received'), dataIndex: 'qty_received', key: 'qty_received' },
                { title: t('dashboard.qty_invoiced'), dataIndex: 'qty_invoiced', key: 'qty_invoiced' },
                {
                  title: t('dashboard.match_status'),
                  dataIndex: 'match_status',
                  key: 'match_status',
                  render: (v: string) => (
                    <Tag color={v === 'matched' ? 'green' : v === 'partial' ? 'orange' : 'red'}>
                      {t(`status.${v}`)}
                    </Tag>
                  ),
                },
              ]}
            />
          </Section>
        ) : null
      case 'payment_calendar':
        return (isProcurementMgr || isFinanceAuditor || isItBuyer || role === 'admin') && paymentCalendar.length > 0 ? (
          <Section title={t('dashboard.payment_calendar')} key="payment_calendar">
            <List
              itemLayout="horizontal"
              dataSource={paymentCalendar}
              rowKey="id"
              renderItem={(item) => {
                const dueDate = new Date(item.due_date)
                const today = new Date()
                const diffTime = dueDate.getTime() - today.getTime()
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
                
                let color = 'default'
                if (diffDays <= 0) color = 'red'
                else if (diffDays <= 7) color = 'orange'

                return (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          style={{ backgroundColor: color === 'red' ? token.colorErrorBg : color === 'orange' ? token.colorWarningBg : token.colorBgLayout, color: color === 'red' ? token.colorError : color === 'orange' ? token.colorWarning : token.colorText }}
                          icon={<ClockCircleOutlined />}
                        />
                      }
                      title={
                        <Space>
<Text strong>{fmtAmount(item.amount, 'CNY')}</Text>
<Tag color={color}>{new Date(item.due_date).toLocaleDateString(i18n.language)}</Tag>
                        </Space>
                      }
                      description={
                        <Space>
{item.po_number && <Text type="secondary">{t('dashboard.payment_po_label')}<MonoId>{item.po_number}</MonoId></Text>}
{item.contract_number && <Text type="secondary">{t('dashboard.payment_contract_label')}<MonoId>{item.contract_number}</MonoId></Text>}
<Text type="secondary">{t('dashboard.payment_installment_label')}{item.installment_no}</Text>
                        </Space>
                      }
                    />
                  </List.Item>
                )
              }}
            />
          </Section>
        ) : null
      case 'budget':
        return (isProcurementMgr || isFinanceAuditor || isItBuyer || role === 'admin') && budgetSummary && budgetSummary.items.length > 0 ? (
          <Section title={t('dashboard.budget_overview')} key="budget">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={8}>
                <Card size="small">
                  <StatCard
                    label={t('dashboard.total_budget')}
                    value={fmtAmount(budgetSummary.total_budget, 'CNY')}
                    loading={loading}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card size="small">
                  <StatCard
                    label={t('dashboard.total_spend')}
                    value={fmtAmount(budgetSummary.total_spend, 'CNY')}
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
                      <Text strong><MonoId>{item.code}</MonoId></Text>
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
                        <Text type="secondary">{t('dashboard.budget')}: {fmtAmount(item.annual_budget, 'CNY')}</Text>
                      </Col>
                      <Col>
                        <Text type="secondary">{t('dashboard.actual_spend')}: {fmtAmount(item.actual_spend, 'CNY')}</Text>
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
        ) : null
      case 'aging':
        return agingApprovals.length > 0 ? (
          <Row gutter={[16, 16]} key="aging">
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
                              <MonoId>{item.pr_number}</MonoId>: {item.title}
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
        ) : null
      case 'quick_actions':
        return null
      case 'my_progress':
        return isRequester && myPrs.length > 0 ? (
          <Section title={t('pr.my_progress')} key="my_progress">
            <Row gutter={16}>
              <Col span={8}><StatCard label={t('pr.draft_count')} value={myDrafts} variant={myDrafts > 0 ? 'accent' : 'default'} /></Col>
              <Col span={8}><StatCard label={t('pr.pending_count')} value={myPending} /></Col>
              <Col span={8}><StatCard label={t('pr.approved_awaiting')} value={myApproved} variant={myApproved > 0 ? 'accent' : 'default'} /></Col>
            </Row>
          </Section>
        ) : null
      default:
        return null
    }
  }

  if (showWelcome) {
    return (
      <Space direction="vertical" size="large" style={{ width: '100%', paddingTop: 60, paddingBottom: token.paddingXL }}>
        <Card
          style={{ maxWidth: 600, margin: '0 auto' }}
          title={<Typography.Title level={3} style={{ margin: 0 }}>{t('welcome.title')}</Typography.Title>}
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Text>
              {t('welcome.role_label')}: <Tag color="blue">{t(`role.${role}`)}</Tag>
            </Text>
            <Space wrap>
              <Button type="primary" onClick={() => navigate('/purchase-requisitions/new')}>
                {t('welcome.create_pr')}
              </Button>
              <Button onClick={() => navigate('/dashboard')}>
                {t('welcome.view_dashboard')}
              </Button>
              <Button
                onClick={() => {
                  setShowWelcome(false)
                  localStorage.setItem('mica.welcome_dismissed', '1')
                }}
              >
                {t('welcome.got_it')}
              </Button>
            </Space>
          </Space>
        </Card>
      </Space>
    )
  }

  const { primaryAction, dropdownItems } = useMemo(() => {
    type Action = {
      key: string
      label: string
      icon: React.ReactNode
      to: string
    }
    const all: { primary: Action | null; rest: Action[] } = { primary: null, rest: [] }

    if (isDeptManager) {
      all.primary = {
        key: 'pending',
        label: `${t('dashboard.pending_approvals')} (${pending.length})`,
        icon: <AuditOutlined />,
        to: '/approvals',
      }
    } else if (isRequester) {
      all.primary = {
        key: 'submit',
        label: t('pr.submit_demand'),
        icon: <PlusOutlined />,
        to: '/purchase-requisitions/new',
      }
    } else if (isItBuyer || isProcurementMgr || role === 'admin') {
      all.primary = {
        key: 'new_pr',
        label: t('dashboard.new_pr'),
        icon: <PlusOutlined />,
        to: '/purchase-requisitions/new',
      }
    } else if (isFinanceAuditor) {
      all.primary = {
        key: 'payments',
        label: t('dashboard.payment_mgmt'),
        icon: <FileTextOutlined />,
        to: '/payments',
      }
    }

    if ((isItBuyer || isProcurementMgr || role === 'admin') && all.primary?.key !== 'new_pr') {
      all.rest.push({ key: 'new_pr', label: t('dashboard.new_pr'), icon: <PlusOutlined />, to: '/purchase-requisitions/new' })
    }
    if (isItBuyer || isProcurementMgr || role === 'admin') {
      all.rest.push({ key: 'new_rfq', label: t('dashboard.new_rfq'), icon: <PlusOutlined />, to: '/rfqs/new' })
    }
    if (isRequester) {
      const myCount = myPrs.length
      all.rest.push({
        key: 'my_prs',
        label: myCount > 0 ? `${t('pr.my_prs')} (${myCount})` : t('pr.my_prs'),
        icon: <FileTextOutlined />,
        to: '/purchase-requisitions',
      })
    }
    if (isFinanceAuditor && all.primary?.key !== 'payments') {
      all.rest.push({ key: 'payments', label: t('dashboard.payment_mgmt'), icon: <FileTextOutlined />, to: '/payments' })
    }
    all.rest.push({ key: 'all_pos', label: t('dashboard.view_all_pos'), icon: <AppstoreOutlined />, to: '/purchase-orders' })
    if (role === 'admin') {
      all.rest.push({ key: 'admin', label: t('dashboard.admin_panel'), icon: <SettingOutlined />, to: '/admin' })
    }
    all.rest.push({ key: 'notifications', label: t('dashboard.notifications'), icon: <BellOutlined />, to: '/notifications' })

    return {
      primaryAction: all.primary,
      dropdownItems: all.rest.map((a) => ({
        key: a.key,
        label: a.label,
        icon: a.icon,
        onClick: () => navigate(a.to),
      })),
    }
  }, [role, isRequester, isItBuyer, isProcurementMgr, isFinanceAuditor, isDeptManager, pending.length, myPrs.length, navigate, t])

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%', paddingBottom: token.paddingLG }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: token.marginSM,
          flexWrap: 'wrap',
          paddingBlock: token.paddingXS,
        }}
      >
        <Space size="small" wrap>
          <Typography.Title level={4} style={{ margin: 0, fontWeight: 600 }}>
            {t('nav.dashboard')}
          </Typography.Title>
          {!isMobile && (
            <Text type="secondary" style={{ fontSize: token.fontSizeSM }}>
              <ClockCircleOutlined style={{ marginRight: 4 }} />
              {currentTime.toLocaleString()}
            </Text>
          )}
        </Space>
        <Space size="small" wrap>
          {primaryAction && (
            <Button
              type="primary"
              size="small"
              icon={primaryAction.icon}
              onClick={() => navigate(primaryAction.to)}
            >
              {isMobile ? null : primaryAction.label}
            </Button>
          )}
          {isMobile ? (
            <Dropdown
              menu={{
                items: [
                  ...dropdownItems,
                  { type: 'divider' as const },
                  {
                    key: 'customize',
                    label: t('dashboard.customize', 'Customize'),
                    icon: <SettingOutlined />,
                    onClick: () => setCustomizeVisible(true),
                  },
                ],
              }}
              trigger={['click']}
              placement="bottomRight"
            >
              <Button size="small" icon={<MoreOutlined />} aria-label={t('dashboard.more_actions', '更多操作')} />
            </Dropdown>
          ) : (
            <>
              {dropdownItems.length > 0 && (
                <Dropdown menu={{ items: dropdownItems }} trigger={['click']} placement="bottomRight">
                  <Button size="small" icon={<MoreOutlined />}>
                    {t('dashboard.more_actions', '更多操作')}
                  </Button>
                </Dropdown>
              )}
              <Button size="small" icon={<SettingOutlined />} onClick={() => setCustomizeVisible(true)}>
                {t('dashboard.customize', 'Customize')}
              </Button>
            </>
          )}
        </Space>
      </div>

      {layout.map((item) => renderSection(item.id))}

      <Drawer
        title={t('dashboard.customize_title', 'Customize Dashboard')}
        placement="right"
        onClose={() => setCustomizeVisible(false)}
        open={customizeVisible}
      >
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={layout.map((item) => item.id)}
            strategy={verticalListSortingStrategy}
          >
            {layout.map((item) => (
              <SortableItem
                key={item.id}
                id={item.id}
                title={sectionTitles[item.id] || item.id}
                visible={item.visible}
                onToggle={handleToggleSection}
              />
            ))}
          </SortableContext>
        </DndContext>
      </Drawer>
    </Space>
  )
}
