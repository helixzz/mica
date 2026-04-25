import {
  Button,
  Card,
  Descriptions,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
  message,
  theme,
} from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type PurchaseRequisition, type Supplier } from '@/api'
import { extractError } from '@/api/client'
import { fmtAmount, fmtQty } from '@/utils/format'
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

  const load = () => {
    if (!id) return
    void api.getPR(id).then(setPr)
    void api
      .getPRDownstream(id)
      .then((d) =>
        setDownstream({
          purchase_orders: d.purchase_orders,
          contracts: d.contracts,
        }),
      )
      .catch(() => setDownstream({ purchase_orders: [], contracts: [] }))
  }

  useEffect(() => {
    load()
    void api.suppliers().then(setSuppliers)
  }, [id])

  const supplierMap = useMemo(
    () => Object.fromEntries(suppliers.map((s) => [s.id, s.name])),
    [suppliers]
  )

  if (!pr) return <div>{t('message.loading')}</div>

  const canSubmit = (pr.status === 'draft' || pr.status === 'returned') && user?.id === pr.requester_id
  const canEdit = (pr.status === 'draft' || pr.status === 'returned') && user?.id === pr.requester_id
  const canDecide =
    pr.status === 'submitted' && (user?.role === 'dept_manager' || user?.role === 'admin')
  const isBuyer = user?.role === 'it_buyer' || user?.role === 'procurement_mgr' || user?.role === 'admin'
  const canSupplementQuote = pr.status === 'approved' && isBuyer
  const hasIncompleteItems = (pr.items || []).some((item: any) => !item.unit_price || Number(item.unit_price) === 0 || !item.supplier_id)
  const canConvert =
    pr.status === 'approved' && isBuyer && !hasIncompleteItems

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

  const runConvert = async () => {
    setBusy(true)
    try {
      const po = await api.convertToPO(pr.id)
      void message.success(t('message.convert_success', { po_number: po.po_number }))
      navigate(`/purchase-orders/${po.id}`)
    } catch (e) {
      const err = extractError(e)
      void message.error(err.detail || t('error.unexpected'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space align="center">
          <Typography.Title level={3} style={{ margin: 0 }}>
            {pr.pr_number}
          </Typography.Title>
          <Tag color={statusColors[pr.status]}>{t(`status.${pr.status}` as 'status.draft')}</Tag>
        </Space>
        <Space>
          <Button onClick={() => navigate('/purchase-requisitions')}>{t('button.back')}</Button>
          {canEdit && (
            <Button onClick={() => navigate(`/purchase-requisitions/${pr.id}/edit`)}>
              {t('button.edit') || '编辑'}
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
            <Button type="primary" onClick={runConvert} loading={busy}>
              {t('button.convert_to_po')}
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

      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label={t('field.title')}>{pr.title}</Descriptions.Item>
          <Descriptions.Item label={t('field.total_amount')}>
            {fmtAmount(pr.total_amount, pr.currency)}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.business_reason')} span={2}>
            {pr.business_reason || '-'}
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
          {pr.decision_comment && (
            <Descriptions.Item label={t('field.decision_comment')} span={2}>
              {pr.decision_comment}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title={t('nav.purchase_requisitions')}>
        <Table
          rowKey="line_no"
          dataSource={pr.items}
          pagination={false}
          scroll={{ x: 600 }}
          columns={[
            { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
            { title: t('field.item_name'), dataIndex: 'item_name' },
            {
              title: t('field.supplier'),
              dataIndex: 'supplier_id',
              render: (v: string | null) => (v ? supplierMap[v] ?? v : '-'),
            },
            { title: t('field.qty'), dataIndex: 'qty', align: 'right', render: (v: string) => fmtQty(v) },
            { title: t('field.uom'), dataIndex: 'uom', width: 80 },
            { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', render: (v: string) => fmtAmount(v) },
            { title: t('field.amount'), dataIndex: 'amount', align: 'right', render: (v: string) => fmtAmount(v) },
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
                        <a onClick={() => navigate(`/purchase-orders/${r.id}`)}>{v}</a>
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
                      render: (v: string, r) => fmtAmount(v, r.currency),
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
                        <a onClick={() => navigate(`/contracts/${r.id}`)}>{v}</a>
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
                      render: (v: string, r) => fmtAmount(v, r.currency),
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
    </Space>
  )
}
