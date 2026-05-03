import { Tabs } from 'antd'
import { useTranslation } from 'react-i18next'

import { type Contract, type InvoiceListRow, type PaymentRecord, type PurchaseOrder, type Shipment } from '@/api'
import { PaymentScheduleTab } from '@/components/PaymentScheduleTab'
import { ContractsTab } from '@/components/PO/ContractsTab'
import { DeliveryPlanTab } from '@/components/PO/DeliveryPlanTab'
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
  handleUnlinkContract: (contract: Contract) => void
}

export function POTabs({
  po,
  shipments,
  payments,
  invoices,
  contracts,
  deliveryPlans,
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
  handleUnlinkContract,
}: POTabsProps) {
  const { t } = useTranslation()

  return (
    <Tabs
      items={[
        {
          key: 'items',
          label: `${t('nav.purchase_orders')} · ${t('field.item_name')}`,
          children: <ItemsTab items={po.items} />,
        },
        {
          key: 'delivery-plan',
          label: t('delivery_plan.title'),
          children: (
            <DeliveryPlanTab
              deliveryPlans={deliveryPlans}
              onNewPlan={() => setDeliveryPlanOpen(true)}
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
            <InvoicesTab
              invoices={invoices}
              onRecordInvoice={() => setInvoiceOpen(true)}
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
          key: 'payment-plan',
          label: t('contract.payment_schedule'),
          children: (
            <PaymentScheduleTab
              poId={po.id}
              currency={po.currency}
              canWrite={canWriteSchedule}
            />
          ),
        },
      ]}
    />
  )
}