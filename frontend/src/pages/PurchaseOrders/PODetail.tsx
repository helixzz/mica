import { Card, Modal, Space, Tabs, message } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'

import {
  api,
  type Contract,
  type InvoiceListRow,
  type PaymentRecord,
  type POProgress,
  type PurchaseOrder,
  type Shipment,
} from '@/api'
import { extractError } from '@/api/client'
import { ActivityTimeline } from '@/components/ActivityTimeline'
import { useAuth } from '@/auth/useAuth'
import { POHeader } from '@/components/PO/POHeader'
import { POInfoCard } from '@/components/PO/POInfoCard'
import { POModals } from '@/components/PO/POModals'
import { POProgressCard } from '@/components/PO/POProgressCard'
import { POTabs } from '@/components/PO/POTabs'

export function PODetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
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
  const [editingPlan, setEditingPlan] = useState<any | undefined>(undefined)
  const [busy, setBusy] = useState(false)

  const canCreateContract = Boolean(
    user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role),
  )
  const canWriteSchedule = Boolean(
    user && ['admin', 'procurement_mgr', 'finance_auditor'].includes(user.role),
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

  const handleDeleteDeliveryPlan = async (planId: string) => {
    try {
      await api.deleteDeliveryPlan(planId)
      void message.success(t('message.deleted'))
      void loadAll()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  if (!po) return <div>{t('message.loading')}</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <POHeader
        po={po}
        contractsCount={contracts.length}
        canCreateContract={canCreateContract}
        onCreateContract={() => setContractOpen(true)}
      />
      <Tabs
        items={[
          {
            key: 'details',
            label: t('common.details', 'Details'),
            children: (
              <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <POInfoCard po={po} />
                {progress && <POProgressCard progress={progress} />}
                <POTabs
                  po={po}
                  shipments={shipments}
                  payments={payments}
                  invoices={invoices}
                  contracts={contracts}
                  deliveryPlans={deliveryPlans}
                  canCreateContract={canCreateContract}
                  canWriteSchedule={canWriteSchedule}
                  loadAll={loadAll}
                  setShipmentOpen={setShipmentOpen}
                  setPaymentOpen={setPaymentOpen}
                  setInvoiceOpen={setInvoiceOpen}
                  setContractOpen={setContractOpen}
                  setLinkContractOpen={setLinkContractOpen}
                  setDeliveryPlanOpen={setDeliveryPlanOpen}
                  setEditingPayment={setEditingPayment}
                  setEditingPlan={setEditingPlan}
                  handleDeleteDeliveryPlan={handleDeleteDeliveryPlan}
                  handleUnlinkContract={handleUnlinkContract}
                />
                <POModals
                  po={po}
                  shipmentOpen={shipmentOpen}
                  paymentOpen={paymentOpen}
                  invoiceOpen={invoiceOpen}
                  contractOpen={contractOpen}
                  linkContractOpen={linkContractOpen}
                  deliveryPlanOpen={deliveryPlanOpen}
                  editingPayment={editingPayment}
                  editingPlan={editingPlan}
                  busy={busy}
                  contracts={contracts}
                  setShipmentOpen={setShipmentOpen}
                  setPaymentOpen={setPaymentOpen}
                  setInvoiceOpen={setInvoiceOpen}
                  setContractOpen={setContractOpen}
                  setLinkContractOpen={setLinkContractOpen}
                  setDeliveryPlanOpen={setDeliveryPlanOpen}
                  setEditingPayment={setEditingPayment}
                  setEditingPlan={setEditingPlan}
                  setBusy={setBusy}
                  loadAll={loadAll}
                />
              </Space>
            ),
          },
          {
            key: 'activity',
            label: t('activity.title'),
            children: <ActivityTimeline resourceType="purchase_order" resourceId={po.id} />,
          },
        ]}
      />
    </Space>
  )
}