import { Card, Modal, Space, Tabs, message } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'

import {
  api,
  type Contract,
  type InvoiceListRow,
  type PaymentRecord,
  type PaymentScheduleItem,
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
import { SupplementaryItemModal } from '@/components/PO/SupplementaryItemModal'

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
  const [attachmentsCount, setAttachmentsCount] = useState(0)
  const [paymentScheduleCount, setPaymentScheduleCount] = useState(0)

  const [shipmentOpen, setShipmentOpen] = useState(false)
  const [paymentOpen, setPaymentOpen] = useState(false)
  const [invoiceOpen, setInvoiceOpen] = useState(false)
  const [contractOpen, setContractOpen] = useState(false)
  const [linkContractOpen, setLinkContractOpen] = useState(false)
  const [deliveryPlanOpen, setDeliveryPlanOpen] = useState(false)
  const [editingPayment, setEditingPayment] = useState<PaymentRecord | null>(null)
  const [editingPlan, setEditingPlan] = useState<any | undefined>(undefined)
  const [busy, setBusy] = useState(false)
  const [paymentPreFill, setPaymentPreFill] = useState<{ contractId?: string; scheduleItemId?: string; amount?: number } | null>(null)
  const [supplementaryOpen, setSupplementaryOpen] = useState(false)
  const [prItemsForSupplementary, setPrItemsForSupplementary] = useState<{ id: string; line_no: number; item_name: string }[]>([])

  const canCreateContract = Boolean(
    user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role),
  )
  const canWriteSchedule = Boolean(
    user && ['admin', 'procurement_mgr', 'finance_auditor', 'it_buyer'].includes(user.role),
  )

  const loadAll = async () => {
    if (!id) return
    const [po0, pr0, sh, pay, inv, ct, dp, docs, sched] = await Promise.all([
      api.getPO(id),
      api.getPOProgress(id).catch(() => null),
      api.listShipments({ po_id: id }).catch(() => []),
      api.listPayments(id).catch(() => []),
      api.listInvoices(id).catch(() => []),
      api.listContracts(id).catch(() => [] as Contract[]),
      api.getPODeliveryPlan(id).catch(() => ({ all_plans: [] })),
      api.listPODocuments(id).catch(() => []),
      api.getPOPaymentSchedule(id).catch(() => ({ items: [] })),
    ])
    setPo(po0)
    setProgress(pr0)
    setShipments(sh)
    setPayments(pay)
    setInvoices(inv)
    setContracts(ct)
    setDeliveryPlans(dp.all_plans)
    setAttachmentsCount(docs.length)
    setPaymentScheduleCount(sched.items ? sched.items.length : 0)
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

  const canDeletePO = Boolean(user && user.role === 'admin')

  const canAddSupplementary = Boolean(
    user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role),
  )

  const openSupplementaryModal = async () => {
    if (!po) return
    try {
      const pr = await api.getPR(po.pr_id)
      setPrItemsForSupplementary(
        (pr.items || [])
          .filter((it: any) => it.id)
          .map((it: any) => ({
            id: it.id as string,
            line_no: it.line_no,
            item_name: it.item_name,
          })),
      )
    } catch {
      setPrItemsForSupplementary([])
    }
    setSupplementaryOpen(true)
  }

  const runDeletePO = () => {
    if (!po) return
    Modal.confirm({
      title: t('po.confirm_delete_title', '确认删除采购订单'),
      content: t('po.confirm_delete_body', {
        number: po.po_number,
        defaultValue: `确认删除采购订单 ${po.po_number}？此操作不可撤销。`,
      }),
      okText: t('button.delete', '删除'),
      okType: 'danger',
      cancelText: t('button.cancel', '取消'),
      onOk: async () => {
        try {
          await api.deletePO(po.id)
          void message.success(t('message.deleted', '已删除'))
          navigate('/purchase-orders')
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  if (!po) return <div>{t('message.loading')}</div>


  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <POHeader
        po={po}
        contractsCount={contracts.length}
        canCreateContract={canCreateContract}
        canDelete={canDeletePO}
        onDelete={runDeletePO}
        onCreateContract={() => setContractOpen(true)}
        canAddSupplementary={canAddSupplementary}
        onAddSupplementary={openSupplementaryModal}
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
                  attachmentsCount={attachmentsCount}
                  paymentScheduleCount={paymentScheduleCount}
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
                  onExecuteSchedulePayment={(item: PaymentScheduleItem) => {
                    setPaymentPreFill({
                      contractId: item.contract_id ?? undefined,
                      scheduleItemId: item.id,
                      amount: Number(item.planned_amount),
                    })
                    setPaymentOpen(true)
                  }}
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
                  paymentPreFill={paymentPreFill}
                  setShipmentOpen={setShipmentOpen}
                  setPaymentOpen={(open) => { setPaymentOpen(open); if (!open) setPaymentPreFill(null) }}
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
      <SupplementaryItemModal
        open={supplementaryOpen}
        po={po}
        prItems={prItemsForSupplementary}
        onClose={() => setSupplementaryOpen(false)}
        onSuccess={() => {
          void loadAll()
        }}
      />
    </Space>
  )
}