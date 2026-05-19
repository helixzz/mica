import { useNavigate } from 'react-router-dom'

import { type Contract, type DeliveryPlan, type PaymentRecord, type PurchaseOrder } from '@/api'
import { ContractFormModal } from '@/components/ContractFormModal'
import { DeliveryPlanModal } from '@/components/DeliveryPlanModal'
import { InvoiceModal } from '@/components/PO/InvoiceModal'
import { LinkContractModal } from '@/components/PO/LinkContractModal'
import { PaymentEditModal } from '@/components/PO/PaymentEditModal'
import { PaymentModal } from '@/components/PO/PaymentModal'
import { ShipmentModal } from '@/components/PO/ShipmentModal'

interface POModalsProps {
  po: PurchaseOrder
  shipmentOpen: boolean
  paymentOpen: boolean
  invoiceOpen: boolean
  contractOpen: boolean
  linkContractOpen: boolean
  deliveryPlanOpen: boolean
  editingPayment: PaymentRecord | null
  editingPlan: DeliveryPlan | undefined
  busy: boolean
  contracts: Contract[]
  paymentPreFill?: { contractId?: string; scheduleItemId?: string; amount?: number } | null
  setShipmentOpen: (open: boolean) => void
  setPaymentOpen: (open: boolean) => void
  setInvoiceOpen: (open: boolean) => void
  setContractOpen: (open: boolean) => void
  setLinkContractOpen: (open: boolean) => void
  setDeliveryPlanOpen: (open: boolean) => void
  setEditingPayment: (payment: PaymentRecord | null) => void
  setEditingPlan: (plan: DeliveryPlan | undefined) => void
  setBusy: (busy: boolean) => void
  loadAll: () => void
}

export function POModals({
  po,
  shipmentOpen,
  paymentOpen,
  invoiceOpen,
  contractOpen,
  linkContractOpen,
  deliveryPlanOpen,
  editingPayment,
  editingPlan,
  busy,
  contracts,
  setShipmentOpen,
  setPaymentOpen,
  setInvoiceOpen,
  setContractOpen,
  setLinkContractOpen,
  setDeliveryPlanOpen,
  setEditingPayment,
  setEditingPlan,
  setBusy,
  loadAll,
  paymentPreFill,
}: POModalsProps) {
  const navigate = useNavigate()

  return (
    <>
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
        initialContractId={paymentPreFill?.contractId}
        initialScheduleItemId={paymentPreFill?.scheduleItemId}
        initialAmount={paymentPreFill?.amount}
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
        open={deliveryPlanOpen || editingPlan !== undefined}
        onClose={() => { setDeliveryPlanOpen(false); setEditingPlan(undefined) }}
        onSuccess={() => {
          setDeliveryPlanOpen(false)
          setEditingPlan(undefined)
          void loadAll()
        }}
        poId={editingPlan ? undefined : po.id}
        plan={editingPlan}
      />
    </>
  )
}