import { Tabs } from 'antd'
import { useTranslation } from 'react-i18next'

import { type Contract, type InvoiceListRow, type PaymentRecord, type PaymentScheduleItem, type PurchaseOrder, type Shipment } from '@/api'
import { PaymentScheduleTab } from '@/components/PaymentScheduleTab'
import { ContractsTab } from '@/components/PO/ContractsTab'
import { DeliveryPlanTab } from '@/components/PO/DeliveryPlanTab'
import { POAttachmentsTab } from '@/components/PO/POAttachmentsTab'
import { InvoicesTab } from '@/components/PO/InvoicesTab'
import { ItemsTab } from '@/components/PO/ItemsTab'
import { PaymentsTab } from '@/components/PO/PaymentsTab'
import { ShipmentsTab } from '@/components/PO/ShipmentsTab'

interface POTabsProps {
  po: PurchaseOrder
  shipments: Shipment[]
  payments: PaymentRecord[]
  invoices: InvoiceListRow[]
  contracts: Contract[]
  deliveryPlans: any[]
  attachmentsCount: number
  paymentScheduleCount: number
  canCreateContract: boolean
  canWriteSchedule: boolean
  loadAll: () => void
  setShipmentOpen: (open: boolean) => void
  setPaymentOpen: (open: boolean) => void
  setInvoiceOpen: (open: boolean) => void
  setContractOpen: (open: boolean) => void
  setLinkContractOpen: (open: boolean) => void
  setDeliveryPlanOpen: (open: boolean) => void
  setEditingPayment: (payment: PaymentRecord | null) => void
  setEditingPlan: (plan: any) => void
  handleDeleteDeliveryPlan: (id: string) => void
  handleUnlinkContract: (contract: Contract) => void
  onExecuteSchedulePayment?: (item: PaymentScheduleItem) => void
}

export function POTabs({
  po,
  shipments,
  payments,
  invoices,
  contracts,
  deliveryPlans,
  attachmentsCount,
  paymentScheduleCount,
  canCreateContract,
  canWriteSchedule,
  loadAll,
  setShipmentOpen,
  setPaymentOpen,
  setInvoiceOpen,
  setContractOpen,
  setLinkContractOpen,
  setDeliveryPlanOpen,
  setEditingPayment,
  setEditingPlan,
  handleDeleteDeliveryPlan,
  handleUnlinkContract,
  onExecuteSchedulePayment,
}: POTabsProps) {
  const { t } = useTranslation()

  return (
    <Tabs
      items={[
        {
          key: 'items',
          label: `${t('nav.purchase_orders')} · ${t('field.item_name')} (${po.items.length})`,
          children: <ItemsTab items={po.items} currency={po.currency} onChanged={loadAll} />,
        },
        {
          key: 'delivery-plan',
          label: `${t('delivery_plan.title')} (${deliveryPlans.length})`,
          children: (
            <DeliveryPlanTab
              deliveryPlans={deliveryPlans}
              onNewPlan={() => setDeliveryPlanOpen(true)}
              onEdit={(plan) => setEditingPlan(plan)}
              onDelete={handleDeleteDeliveryPlan}
            />
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
              currency={po.currency}
            />
          ),
        },
        {
          key: 'payments',
          label: `${t('nav.payments')} (${payments.length})`,
          children: (
            <PaymentsTab
              payments={payments}
              currency={po.currency}
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
            <InvoicesTab
              invoices={invoices}
              onRecordInvoice={() => setInvoiceOpen(true)}
              onChanged={() => void loadAll()}
            />
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
          key: 'attachments',
          label: `${t('po.attachments', 'Attachments')} (${attachmentsCount})`,
          children: <POAttachmentsTab poId={po.id} />,
        },
        {
          key: 'payment-plan',
          label: `${t('contract.payment_schedule')} (${paymentScheduleCount})`,
          children: (
            <PaymentScheduleTab
              poId={po.id}
              currency={po.currency}
              canWrite={canWriteSchedule}
              onExecutePayment={onExecuteSchedulePayment}
            />
          ),
        },
      ]}
    />
  )
}