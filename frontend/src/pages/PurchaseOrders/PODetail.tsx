import {
  DownloadOutlined,
  FileTextOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import {
  Button,
  Card,
  Col,
  Descriptions,
  Modal,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import {
  api,
  type Contract,
  type InvoiceListRow,
  type PaymentRecord,
  type POProgress,
  type PurchaseOrder,
  type Shipment,
} from '@/api'
import { extractError, getToken } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { ContractFormModal } from '@/components/ContractFormModal'
import { DeliveryPlanModal } from '@/components/DeliveryPlanModal'
import { PaymentScheduleTab } from '@/components/PaymentScheduleTab'
import { ContractsTab } from '@/components/PO/ContractsTab'
import { InvoiceModal } from '@/components/PO/InvoiceModal'
import { LinkContractModal } from '@/components/PO/LinkContractModal'
import { PaymentEditModal } from '@/components/PO/PaymentEditModal'
import { PaymentModal } from '@/components/PO/PaymentModal'
import { PaymentsTab } from '@/components/PO/PaymentsTab'
import { ShipmentModal } from '@/components/PO/ShipmentModal'
import { ShipmentsTab } from '@/components/PO/ShipmentsTab'
import { fmtAmount, fmtQty } from '@/utils/format'

function statusTag(s: string): string {
  return s
}

export function PODetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const user = useAuth((s) => s.user)

  const [po, setPo] = useState<PurchaseOrder | null>(null)
  const [progress, setProgress] = useState<POProgress | null>(null)
  const [shipments, setShipments] = useState<Shipment[]>([])
  const [payments, setPayments] = useState<PaymentRecord[]>([])
  const [invoices, setInvoices] = useState<InvoiceListRow[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [deliveryPlans, setDeliveryPlans] = useState<any[]>([])

  const [shipmentOpen, setShipmentOpen] = useState(false)
  const [paymentOpen, setPaymentOpen] = useState(false)
  const [invoiceOpen, setInvoiceOpen] = useState(false)
  const [contractOpen, setContractOpen] = useState(false)
  const [linkContractOpen, setLinkContractOpen] = useState(false)
  const [deliveryPlanOpen, setDeliveryPlanOpen] = useState(false)
  const [editingPayment, setEditingPayment] = useState<PaymentRecord | null>(null)
  const [busy, setBusy] = useState(false)

  const canCreateContract = Boolean(
    user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role),
  )

  const loadAll = async () => {
    if (!id) return
    const [po0, pr0, sh, pay, inv, ct, dp] = await Promise.all([
      api.getPO(id),
      api.getPOProgress(id).catch(() => null),
      api.listShipments({ po_id: id }).catch(() => []),
      api.listPayments(id).catch(() => []),
      api.listInvoices(id).catch(() => []),
      api.listContracts(id).catch(() => [] as Contract[]),
      api.getPODeliveryPlan(id).catch(() => ({ all_plans: [] })),
    ])
    setPo(po0)
    setProgress(pr0)
    setShipments(sh)
    setPayments(pay)
    setInvoices(inv)
    setContracts(ct)
    setDeliveryPlans(dp.all_plans)
  }

  useEffect(() => {
    void loadAll()
  }, [id])

  const handleUnlinkContract = (contract: Contract) => {
    if (!po) return
    Modal.confirm({
      title: t('po.unlink_contract_title', { number: contract.contract_number }),
      content: t('po.unlink_contract_body'),
      okText: t('po.unlink'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.unlinkPoContract(po.id, contract.id)
          void message.success(t('po.unlink_success'))
          void loadAll()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  if (!po) return <div>{t('message.loading')}</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space align="center">
          <Typography.Title level={3} style={{ margin: 0 }}>
            {po.po_number}
          </Typography.Title>
          <Tag color="success">{t(`status.${statusTag(po.status)}` as 'status.confirmed')}</Tag>
        </Space>
        <Space>
          {canCreateContract && (
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              className="no-print"
              onClick={() => setContractOpen(true)}
              disabled={po.status === 'draft' || po.status === 'cancelled'}
            >
              {contracts.length > 0
                ? t('contract.add_another')
                : t('contract.create_btn')}
            </Button>
          )}
          <Button
            icon={<DownloadOutlined />}
            className="no-print"
            onClick={async () => {
              const resp = await fetch(`/api/v1/purchase-orders/${po.id}/export/pdf`, {
                headers: { Authorization: `Bearer ${getToken() ?? ''}` },
              })
              if (!resp.ok) return
              const blob = await resp.blob()
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `${po.po_number}.pdf`
              document.body.appendChild(a)
              a.click()
              a.remove()
              URL.revokeObjectURL(url)
            }}
          >
            {t('button.export_pdf')}
          </Button>
          <Button className="no-print" onClick={() => window.print()}>{t('button.print')}</Button>
          <Button onClick={() => navigate('/purchase-orders')}>{t('button.back')}</Button>
        </Space>
      </div>

      <Card>
        <Descriptions bordered size="small" column={3}>
          <Descriptions.Item label={t('field.total_amount')}>
            {fmtAmount(po.total_amount, po.currency)}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.amount_invoiced')}>
            {fmtAmount(po.amount_invoiced, po.currency)}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.amount_paid')}>
            {fmtAmount(po.amount_paid, po.currency)}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.created_at')} span={3}>
            {new Date(po.created_at).toLocaleString()}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {progress && (
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
      )}

      <Tabs
        items={[
          {
            key: 'items',
            label: `${t('nav.purchase_orders')} · ${t('field.item_name')}`,
            children: (
              <Table
                rowKey="id"
                dataSource={po.items}
                pagination={false}
                columns={[
                  { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
                  { title: t('field.item_name'), dataIndex: 'item_name' },
                  { title: t('field.qty'), dataIndex: 'qty', align: 'right', width: 90, render: (v: string) => fmtQty(v) },
                  { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right', width: 110, render: (v: string) => fmtQty(v) },
                  { title: t('field.qty_invoiced'), dataIndex: 'qty_invoiced', align: 'right', width: 110, render: (v: string) => fmtQty(v) },
                  { title: t('field.uom'), dataIndex: 'uom', width: 60 },
                   { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', width: 110, render: (v: string) => fmtAmount(v) },
                   { title: t('field.amount'), dataIndex: 'amount', align: 'right', width: 110, render: (v: string) => fmtAmount(v) },
                ]}
              />
            ),
          },
          {
            key: 'delivery-plan',
            label: t('delivery_plan.title'),
            children: (
              <Card>
                <div style={{ marginBottom: 12, textAlign: 'right' }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setDeliveryPlanOpen(true)}>
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
            ),
          },
          {
            key: 'shipments',
            label: `${t('nav.shipments')} (${shipments.length})`,
            children: (
              <ShipmentsTab
                shipments={shipments}
                loadAll={loadAll}
                onRecordShipment={() => setShipmentOpen(true)}
              />
            ),
          },
          {
            key: 'payments',
            label: `${t('nav.payments')} (${payments.length})`,
            children: (
              <PaymentsTab
                payments={payments}
                loadAll={loadAll}
                onRecordPayment={() => setPaymentOpen(true)}
                onEditPayment={setEditingPayment}
              />
            ),
          },
          {
            key: 'invoices',
            label: `${t('nav.invoices')} (${invoices.length})`,
            children: (
              <>
                <div style={{ marginBottom: 12, textAlign: 'right' }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setInvoiceOpen(true)}>
                    {t('button.record_invoice')}
                  </Button>
                </div>
                <Table
                  rowKey="id"
                  dataSource={invoices}
                  pagination={false}
                  columns={[
                    { title: t('field.internal_number'), dataIndex: 'internal_number' },
                    { title: t('field.invoice_number'), dataIndex: 'invoice_number' },
                    { title: t('field.invoice_date'), dataIndex: 'invoice_date' },
                     { title: t('field.subtotal'), dataIndex: 'subtotal', align: 'right', render: (v: string) => fmtAmount(v) },
                     { title: t('field.tax_amount'), dataIndex: 'tax_amount', align: 'right', render: (v: string) => fmtAmount(v) },
                     { title: t('field.total_amount'), dataIndex: 'total_amount', align: 'right', render: (v: string) => fmtAmount(v) },
                    { title: t('field.status'), dataIndex: 'status',
                      render: (s: string) => <Tag>{t(`status.${s}` as 'status.draft')}</Tag> },
                  ]}
                />
              </>
            ),
          },
          {
            key: 'contracts',
            label: `${t('nav.contracts')} (${contracts.length})`,
            children: (
              <ContractsTab
                contracts={contracts}
                po={po}
                canCreateContract={canCreateContract}
                onCreateContract={() => setContractOpen(true)}
                onLinkContract={() => setLinkContractOpen(true)}
                onUnlinkContract={handleUnlinkContract}
              />
            ),
          },
          {
            key: 'payment-plan',
            label: t('contract.payment_schedule'),
            children: (
              <PaymentScheduleTab
                poId={po.id}
                currency={po.currency}
                canWrite={Boolean(
                  user && ['admin', 'procurement_mgr', 'finance_auditor'].includes(user.role),
                )}
              />
            ),
          },
        ]}
      />

      <ShipmentModal
        open={shipmentOpen}
        po={po}
        onClose={() => setShipmentOpen(false)}
        onDone={() => { setShipmentOpen(false); void loadAll() }}
        busy={busy}
        setBusy={setBusy}
      />
      <PaymentModal
        open={paymentOpen}
        po={po}
        onClose={() => setPaymentOpen(false)}
        onDone={() => { setPaymentOpen(false); void loadAll() }}
        busy={busy}
        setBusy={setBusy}
      />
      <InvoiceModal
        open={invoiceOpen}
        po={po}
        onClose={() => setInvoiceOpen(false)}
        onDone={() => { setInvoiceOpen(false); void loadAll() }}
        busy={busy}
        setBusy={setBusy}
      />
      <ContractFormModal
        open={contractOpen}
        mode="create"
        poId={po.id}
        onClose={() => setContractOpen(false)}
        onSaved={(saved) => {
          setContractOpen(false)
          void loadAll()
          navigate(`/contracts/${saved.id}`)
        }}
      />
      <LinkContractModal
        open={linkContractOpen}
        po={po}
        alreadyLinkedIds={contracts.map((c) => c.id)}
        onClose={() => setLinkContractOpen(false)}
        onLinked={() => {
          setLinkContractOpen(false)
          void loadAll()
        }}
      />
      <PaymentEditModal
        open={editingPayment !== null}
        payment={editingPayment}
        onClose={() => setEditingPayment(null)}
        onSaved={() => {
          setEditingPayment(null)
          void loadAll()
        }}
      />
      <DeliveryPlanModal
        open={deliveryPlanOpen}
        onClose={() => setDeliveryPlanOpen(false)}
        onSuccess={() => {
          setDeliveryPlanOpen(false)
          void loadAll()
        }}
        poId={po.id}
      />
    </Space>
  )
}