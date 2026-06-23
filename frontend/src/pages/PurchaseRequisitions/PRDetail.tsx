import {
  Button,
  Card,
  Descriptions,
  Modal,
  Popover,
  Progress,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
  theme,
} from 'antd'
import { CopyOutlined, DownloadOutlined, UserAddOutlined } from '@ant-design/icons'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import {
  api,
  type PurchaseRequisition,
  type Supplier,
} from '@/api'
import { extractError, getToken } from '@/api/client'
import { ActivityTimeline } from '@/components/ActivityTimeline'
import { ConvertToPOModal } from '@/components/PR/ConvertToPOModal'
import { AddSupplementaryFromPRModal } from '@/components/PR/AddSupplementaryFromPRModal'
import { fmtAmount, fmtAmountNode, fmtQty, fmtQtyNode } from '@/utils/format'
import { MonoId } from '@/components/ui/Mono'
import { useAuth } from '@/auth/useAuth'

const statusColors: Record<string, string> = {
  draft: 'default',
  submitted: 'processing',
  approved: 'success',
  rejected: 'error',
  returned: 'warning',
  cancelled: 'default',
  converted: 'cyan',
}

export function PRDetailPage() {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [pr, setPr] = useState<PurchaseRequisition | null>(null)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [busy, setBusy] = useState(false)
  const [activeTab, setActiveTab] = useState('details')
  const [downstream, setDownstream] = useState<{
    purchase_orders: {
      id: string
      po_number: string
      status: string
      total_amount: string
      currency: string
      supplier_name: string | null
    }[]
    contracts: {
      id: string
      contract_number: string
      title: string
      status: string
      total_amount: string
      currency: string
      po_id: string
      supplier_name: string | null
    }[]
  }>({ purchase_orders: [], contracts: [] })
  const [allUsers, setAllUsers] = useState<{ id: string; display_name: string; email: string }[]>([])
  const [convertOpen, setConvertOpen] = useState(false)
  const [suppOpen, setSuppOpen] = useState(false)
  const [suppItem, setSuppItem] = useState<{ id: string; line_no: number; item_name: string; qty: string | number; uom: string } | null>(null)

  const load = async () => {
    if (!id) return
    try {
      const prData = await api.getPR(id)
      setPr(prData)
    } catch {
      setPr(null)
    }
    try {
      const d = await api.getPRDownstream(id)
      setDownstream({
        purchase_orders: d.purchase_orders,
        contracts: d.contracts,
      })
    } catch {
      setDownstream({ purchase_orders: [], contracts: [] })
    }
  }

  useEffect(() => {
    load()
    void api.suppliers().then(setSuppliers)
    void api.listProxyCandidates().then(candidates =>
      setAllUsers(candidates.map(c => ({ id: c.id, display_name: c.display_name, email: c.email })))
    ).catch(() => {})
  }, [id])

  const supplierMap = useMemo(
    () => Object.fromEntries(suppliers.map((s) => [s.id, s.name])),
    [suppliers]
  )

  const unconvertedPRItems = useMemo(() => {
    if (!pr) return []
    return (pr.items || []).filter((item: any) => {
      const filled = Number(item.fulfilled_qty || 0)
      const total = Number(item.qty || 0)
      return filled < total
    })
  }, [pr])

  if (!pr) return <div>{t('message.loading')}</div>

  const isOwnerOrElevated = user?.id === pr.requester_id || user?.role === 'admin' || user?.role === 'procurement_mgr' || user?.role === 'it_buyer'
  const canSubmit = (pr.status === 'draft' || pr.status === 'returned') && isOwnerOrElevated
  const canEdit = (pr.status === 'draft' || pr.status === 'returned') && isOwnerOrElevated
  const canDelete =
    ['draft', 'returned', 'rejected', 'cancelled'].includes(pr.status) && isOwnerOrElevated
  const canDecide =
    pr.status === 'submitted' && (user?.role === 'dept_manager' || user?.role === 'admin')
  const isBuyer = user?.role === 'it_buyer' || user?.role === 'procurement_mgr' || user?.role === 'admin'
  const canSupplementQuote = pr.status === 'approved' && isBuyer
  const hasIncompleteItems = (pr.items || []).some((item: any) => !item.unit_price || Number(item.unit_price) === 0 || !item.supplier_id)
  const canConvert =
    (pr.status === 'approved' || pr.status === 'partially_converted') &&
    isBuyer &&
    !hasIncompleteItems

  const runDecision = (action: 'approve' | 'reject' | 'return') => {
    Modal.confirm({
      title: t(`message.confirm_${action}` as 'message.confirm_approve'),
      onOk: async () => {
        setBusy(true)
        try {
          await api.decidePR(pr.id, action)
          void message.success(t(`message.${action}_success` as 'message.approve_success'))
          load()
        } catch (e) {
          const err = extractError(e)
          void message.error(err.detail || t('error.unexpected'))
        } finally {
          setBusy(false)
        }
      },
    })
  }

  const runSubmit = () => {
    Modal.confirm({
      title: t('message.confirm_submit'),
      onOk: async () => {
        setBusy(true)
        try {
          await api.submitPR(pr.id)
          void message.success(t('message.submit_success'))
          load()
        } catch (e) {
          const err = extractError(e)
          void message.error(err.detail || t('error.unexpected'))
        } finally {
          setBusy(false)
        }
      },
    })
  }

  const runDelete = () => {
    Modal.confirm({
      title: t('pr.confirm_delete_title'),
      content: t('pr.confirm_delete_body'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deletePR(pr.id)
          void message.success(t('message.deleted'))
          navigate('/purchase-requisitions')
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  const openConvertModal = () => {
    setConvertOpen(true)
  }

  const handleConvertSuccess = (createdPOs: { id: string }[]) => {
    setConvertOpen(false)
    if (createdPOs.length > 0) {
      navigate(`/purchase-orders/${createdPOs[0].id}`)
    } else {
      void load()
    }
  }

  const tabItems = [
    {
      key: 'details',
      label: t('details', '详情'),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label={t('field.title')}>{pr.title}</Descriptions.Item>
              <Descriptions.Item label={t('field.requester')}>
                {pr.requester_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.company')}>
                {pr.company_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.department')}>
                {pr.department_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.cost_center')}>
                {pr.cost_center_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.total_amount')}>
                {fmtAmount(pr.total_amount, pr.currency)}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.required_date')}>
                {pr.required_date || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.created_at')}>
                {new Date(pr.created_at).toLocaleString()}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.submitted_at')}>
                {pr.submitted_at ? new Date(pr.submitted_at).toLocaleString() : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.decided_at')}>
                {pr.decided_at ? new Date(pr.decided_at).toLocaleString() : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.currency')}>
                {pr.currency || 'CNY'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {pr.business_reason && (
            <Card size="small" title={t('field.business_reason')}>
              <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, margin: 0, fontSize: 14 }}>
                {pr.business_reason}
              </Typography.Paragraph>
            </Card>
          )}

          {pr.decision_comment && (
            <Card size="small" title={t('field.decision_comment')}>
              <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, margin: 0 }}>
                {pr.decision_comment}
              </Typography.Paragraph>
              {pr.decided_at && (
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {new Date(pr.decided_at).toLocaleString()}
                </Typography.Text>
              )}
            </Card>
          )}

          <Card
            size="small"
            title={t('pr.collaborators', '协作者')}
            extra={
              (pr.requester_id === user?.id || user?.role === 'admin' || user?.role === 'dept_manager') && (
                <Select
                  size="small"
                  showSearch
                  allowClear
                  placeholder={t('pr.collaborator_search_placeholder', '搜索姓名或邮箱添加')}
                  style={{ width: 200 }}
                  optionFilterProp="label"
                  value={undefined}
                  options={allUsers
                    .filter((u) => u.id !== pr.requester_id && !pr.collaborators.some((c) => c.id === u.id))
                    .map((u) => ({ value: u.id, label: `${u.display_name} (${u.email})` }))}
                  onSelect={async (userId) => {
                    if (!userId) return
                    try {
                      await api.addCollaborator(pr.id, userId as string)
                      await load()
                      message.success(t('pr.collaborator_added', '已添加'))
                    } catch (e) {
                      message.error(extractError(e).detail)
                    }
                  }}
                  suffixIcon={<UserAddOutlined />}
                  popupMatchSelectWidth={false}
                  notFoundContent={t('pr.collaborator_not_found', '未找到该用户')}
                />
              )
            }
          >
            {pr.collaborators.length > 0 ? (
              <Space wrap>
                {pr.collaborators.map((c) => (
                  <Tag
                    key={c.id}
                    closable={pr.requester_id === user?.id || user?.role === 'admin' || user?.role === 'dept_manager'}
                    onClose={async (e) => {
                      e.preventDefault()
                      try {
                        await api.removeCollaborator(pr.id, c.id)
                        await load()
                      } catch (err) {
                        message.error(extractError(err).detail)
                      }
                    }}
                  >
                    {c.display_name}
                  </Tag>
                ))}
              </Space>
            ) : (
              <Typography.Text type="secondary">{t('pr.no_collaborators', '暂无协作者')}</Typography.Text>
            )}
          </Card>

          <Card title={t('nav.purchase_requisitions')}>
            <Table
              rowKey="line_no"
              dataSource={pr.items}
              pagination={false}
              scroll={{ x: 720 }}
              columns={[
                { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
                { title: t('field.item_name'), dataIndex: 'item_name' },
                {
                  title: t('field.supplier'),
                  dataIndex: 'supplier_id',
                  render: (v: string | null) => (v ? supplierMap[v] ?? v : '-'),
                },
                { title: t('field.qty'), dataIndex: 'qty', align: 'right', render: (v: string) => fmtQtyNode(v) },
                { title: t('field.uom'), dataIndex: 'uom', width: 80 },
                { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', render: (v: string) => fmtAmountNode(v, pr.currency) },
                { title: t('field.amount'), dataIndex: 'amount', align: 'right', render: (v: string) => fmtAmountNode(v, pr.currency) },
                {
                  title: t('fulfillment.progress'),
                  width: 180,
                  render: (_: unknown, row: any) => {
                    const total = Number(row.qty || 0)
                    const filled = Number(row.fulfilled_qty || 0)
                    if (total === 0) return '-'
                    const percent = Math.min(100, Math.round((filled / total) * 100))
                    const status = row.is_fully_fulfilled
                      ? 'success'
                      : filled > 0
                        ? 'active'
                        : 'normal'
                    const breakdown = (row.fulfillment_breakdown ?? {}) as Record<string, string>
                    const hasBreakdown = Object.values(breakdown).some(
                      (v) => Number(v) > 0,
                    )
                    const bar = (
                      <div>
                        <Progress
                          percent={percent}
                          status={status as any}
                          size="small"
                          format={() => `${fmtQty(String(filled))}/${fmtQty(String(total))}`}
                        />
                      </div>
                    )
                    if (!hasBreakdown) return bar
                    return (
                      <Popover
                        title={t('fulfillment.breakdown_title')}
                        content={
                          <Space direction="vertical" size={4}>
                            {Object.entries(breakdown)
                              .filter(([, v]) => Number(v) > 0)
                              .map(([k, v]) => (
                                <div key={k}>
                                  <Tag>
                                    {t(`fulfillment_type.${k}` as 'fulfillment_type.equivalent')}
                                  </Tag>
                                  {fmtQty(v)}
                                </div>
                              ))}
                          </Space>
                        }
                      >
                        <span style={{ cursor: 'help' }}>{bar}</span>
                      </Popover>
                    )
                  },
                },
                ...(isBuyer && (pr.status === 'approved' || pr.status === 'partially_converted' || pr.status === 'converted')
                  ? [
                      {
                        title: t('field.actions'),
                        key: 'actions',
                        width: 140,
                        render: (_: unknown, row: any) => (
                          <Button
                            type="link"
                            size="small"
                            disabled={!row.id}
                            onClick={() => {
                              setSuppItem({
                                id: row.id,
                                line_no: row.line_no,
                                item_name: row.item_name,
                                qty: row.qty,
                                uom: row.uom,
                              })
                              setSuppOpen(true)
                            }}
                          >
                            {t('fulfillment.add_supp_for_this_row')}
                          </Button>
                        ),
                      },
                    ]
                  : []),
              ]}
            />
          </Card>

          {(downstream.purchase_orders.length > 0 || downstream.contracts.length > 0) && (
            <Card title={t('pr.related_records_title')}>
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {downstream.purchase_orders.length > 0 && (
                  <div>
                    <Typography.Text strong>{t('pr.related_pos_title')}</Typography.Text>
                    <Table
                      size="small"
                      rowKey="id"
                      pagination={false}
                      style={{ marginTop: 8 }}
                      dataSource={downstream.purchase_orders}
                      columns={[
                        {
                          title: t('field.po_number'),
                          dataIndex: 'po_number',
                          render: (v: string, r) => (
                            <a onClick={() => navigate(`/purchase-orders/${r.id}`)}><MonoId>{v}</MonoId></a>
                          ),
                        },
                        {
                          title: t('field.status'),
                          dataIndex: 'status',
                          render: (v: string) => (
                            <Tag>{t(`status.${v}` as 'status.confirmed')}</Tag>
                          ),
                        },
                        {
                          title: t('field.supplier'),
                          dataIndex: 'supplier_name',
                          render: (v: string | null) => v || '-',
                        },
                        {
                          title: t('field.total_amount'),
                          dataIndex: 'total_amount',
                          align: 'right',
                          render: (v: string, r) => fmtAmountNode(v, r.currency),
                        },
                        {
                          title: '',
                          key: 'action',
                          width: 120,
                          render: (_: unknown, r) => (
                            <Button
                              size="small"
                              onClick={() => navigate(`/purchase-orders/${r.id}`)}
                            >
                              {t('pr.open_po')}
                            </Button>
                          ),
                        },
                      ]}
                    />
                  </div>
                )}

                {downstream.contracts.length > 0 && (
                  <div>
                    <Typography.Text strong>{t('pr.related_contracts_title')}</Typography.Text>
                    <Table
                      size="small"
                      rowKey="id"
                      pagination={false}
                      style={{ marginTop: 8 }}
                      dataSource={downstream.contracts}
                      columns={[
                        {
                          title: t('field.contract_number'),
                          dataIndex: 'contract_number',
                          render: (v: string, r) => (
                            <a onClick={() => navigate(`/contracts/${r.id}`)}><MonoId>{v}</MonoId></a>
                          ),
                        },
                        { title: t('field.title'), dataIndex: 'title' },
                        {
                          title: t('field.status'),
                          dataIndex: 'status',
                          render: (v: string) => (
                            <Tag>{t(`status.${v}` as 'status.active')}</Tag>
                          ),
                        },
                        {
                          title: t('field.supplier'),
                          dataIndex: 'supplier_name',
                          render: (v: string | null) => v || '-',
                        },
                        {
                          title: t('field.total_amount'),
                          dataIndex: 'total_amount',
                          align: 'right',
                          render: (v: string, r) => fmtAmountNode(v, r.currency),
                        },
                        {
                          title: '',
                          key: 'action',
                          width: 120,
                          render: (_: unknown, r) => (
                            <Button
                              size="small"
                              onClick={() => navigate(`/contracts/${r.id}`)}
                            >
                              {t('pr.open_contract')}
                            </Button>
                          ),
                        },
                      ]}
                    />
                  </div>
                )}
              </Space>
            </Card>
          )}
        </Space>
      ),
    },
    {
      key: 'activity',
      label: t('activity.title', '活动日志'),
      children: <ActivityTimeline resourceType="purchase_requisition" resourceId={pr.id} />,
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space align="center">
          <Typography.Title level={3} style={{ margin: 0 }}>
            <MonoId>{pr.pr_number}</MonoId>
          </Typography.Title>
          <Tag color={statusColors[pr.status]}>{t(`status.${pr.status}` as 'status.draft')}</Tag>
        </Space>
        <Space>
          <Button onClick={() => navigate('/purchase-requisitions')}>{t('button.back')}</Button>
          <Button icon={<CopyOutlined />} onClick={() => navigate(`/purchase-requisitions/new/${pr.id}`)}>
            {t('pr.copy_button')}
          </Button>
          {canEdit && (
            <Button onClick={() => navigate(`/purchase-requisitions/${pr.id}/edit`)}>
              {t('button.edit') || '编辑'}
            </Button>
          )}
          {canDelete && (
            <Button danger onClick={runDelete}>
              {t('button.delete')}
            </Button>
          )}
          {canSubmit && (
            <Button type="primary" onClick={runSubmit} loading={busy}>
              {t('button.submit_for_approval')}
            </Button>
          )}
          {canDecide && (
            <>
              <Button danger onClick={() => runDecision('reject')} loading={busy}>
                {t('button.reject')}
              </Button>
              <Button onClick={() => runDecision('return')} loading={busy}>
                {t('button.return')}
              </Button>
              <Button type="primary" onClick={() => runDecision('approve')} loading={busy}>
                {t('button.approve')}
              </Button>
            </>
          )}
          {canConvert && (
            <Button type="primary" onClick={openConvertModal} loading={busy}>
              {t('button.convert_to_po')}
            </Button>
          )}
          {pr.items && pr.items.length > 0 && (
            <Button
              icon={<DownloadOutlined />}
              onClick={async () => {
                try {
                  const resp = await fetch(`/api/v1/purchase-requisitions/${pr.id}/export/rfq-sheet`, {
                    headers: { Authorization: `Bearer ${getToken() ?? ''}` },
                  })
                  if (!resp.ok) throw new Error('export failed')
                  const blob = await resp.blob()
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  const disposition = resp.headers.get('content-disposition') ?? ''
                  const match = disposition.match(/filename="?([^"]+)"?/)
                  a.download = match?.[1] ?? `RFQ-${pr.pr_number}.xlsx`
                  document.body.appendChild(a)
                  a.click()
                  a.remove()
                  URL.revokeObjectURL(url)
                } catch {
                  void message.error(t('error.unexpected'))
                }
              }}
            >
              {t('pr.export_rfq_sheet')}
            </Button>
          )}
          {canSupplementQuote && hasIncompleteItems && (
            <>
              <Button type="primary" onClick={() => navigate(`/purchase-requisitions/${pr.id}/edit`)}>{t('pr.supplement_quote')}
              </Button>
              <Typography.Text type="warning" style={{ fontSize: 12 }}>{t('pr.incomplete_items_warning')}
              </Typography.Text>
            </>
          )}
          {canSupplementQuote && !hasIncompleteItems && (
            <Button onClick={() => navigate(`/purchase-requisitions/${pr.id}/edit`)}>{t('pr.modify_quote')}
            </Button>
          )}
        </Space>
      </div>

      <Tabs items={tabItems} activeKey={activeTab} onChange={setActiveTab} />

      {(canDecide || canSubmit || canSupplementQuote) && (
        <div className="mobile-action-bar" style={{
          display: 'none', position: 'fixed', bottom: 0, left: 0, right: 0,
          padding: '12px 16px', background: token.colorBgContainer,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          zIndex: 100, boxShadow: token.boxShadowSecondary,
        }}>
          <Space style={{ width: '100%', justifyContent: 'center' }}>
            {canSubmit && <Button type="primary" onClick={runSubmit} loading={busy} block>{t('button.submit_for_approval')}</Button>}
            {canDecide && (
              <>
                <Button danger onClick={() => runDecision('reject')} loading={busy}>{t('button.reject')}</Button>
                <Button type="primary" onClick={() => runDecision('approve')} loading={busy}>{t('button.approve')}</Button>
              </>
            )}
            {canSupplementQuote && hasIncompleteItems && (
              <Button type="primary" onClick={() => navigate(`/purchase-requisitions/${pr.id}/edit`)} block>
                {t('pr.supplement_quote')}
              </Button>
            )}
          </Space>
        </div>
      )}

      <style>{`
        @media (max-width: 768px) {
          .mobile-action-bar { display: flex !important; }
        }
      `}</style>

      <ConvertToPOModal
        open={convertOpen}
        pr={pr}
        supplierMap={supplierMap}
        suppliers={suppliers}
        onClose={() => setConvertOpen(false)}
        onSuccess={handleConvertSuccess}
      />
      <AddSupplementaryFromPRModal
        open={suppOpen}
        prId={pr.id}
        prItem={suppItem}
        currency={pr.currency}
        suppliers={suppliers}
        onClose={() => {
          setSuppOpen(false)
          setSuppItem(null)
        }}
        onSuccess={() => {
          void load()
        }}
      />
    </Space>
  )
}
