import { Table } from 'antd'
import { useTranslation } from 'react-i18next'

import { type PurchaseOrder } from '@/api'
import { fmtAmount, fmtQty } from '@/utils/format'

interface ItemsTabProps {
  items: PurchaseOrder['items']
}

export function ItemsTab({ items }: ItemsTabProps) {
  const { t } = useTranslation()

  return (
    <Table
      rowKey="id"
      dataSource={items}
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
  )
}