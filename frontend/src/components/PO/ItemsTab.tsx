import { Popover, Space, Table, Tag, Tooltip, Typography } from 'antd'
import { useTranslation } from 'react-i18next'

import { type FulfillmentLink, type FulfillmentType, type PurchaseOrder } from '@/api'
import { fmtAmount, fmtQty } from '@/utils/format'

interface ItemsTabProps {
  items: PurchaseOrder['items']
  currency: string
}

const fulfillmentTypeColors: Record<FulfillmentType, string> = {
  equivalent: 'green',
  downgraded: 'orange',
  substitute: 'volcano',
  supplementary: 'blue',
}

function FulfillmentLinksCell({ links }: { links: FulfillmentLink[] }) {
  const { t } = useTranslation()

  if (!links || links.length === 0) {
    return <Typography.Text type="secondary" style={{ fontSize: 12 }}>—</Typography.Text>
  }

  return (
    <Space size={4} wrap>
      {links.map((link) => {
        const label = t(`fulfillment_type.${link.fulfillment_type}` as 'fulfillment_type.equivalent')
        const tag = (
          <Tag color={fulfillmentTypeColors[link.fulfillment_type]} style={{ marginInlineEnd: 0 }}>
            {label} · {fmtQty(link.qty_contribution)}
          </Tag>
        )
        if (link.deviation_note) {
          return (
            <Popover
              key={link.id}
              content={
                <div style={{ maxWidth: 320, whiteSpace: 'pre-wrap' }}>
                  {link.deviation_note}
                </div>
              }
              title={t('fulfillment.deviation_note')}
              trigger={['click', 'hover']}
            >
              <span style={{ cursor: 'help' }}>{tag}</span>
            </Popover>
          )
        }
        return <Tooltip key={link.id} title={label}>{tag}</Tooltip>
      })}
    </Space>
  )
}

export function ItemsTab({ items, currency }: ItemsTabProps) {
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
        { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', width: 110, render: (v: string) => fmtAmount(v, currency) },
        { title: t('field.amount'), dataIndex: 'amount', align: 'right', width: 110, render: (v: string) => fmtAmount(v, currency) },
        {
          title: t('fulfillment.column_title'),
          dataIndex: 'fulfillment_links',
          width: 220,
          render: (links: FulfillmentLink[]) => <FulfillmentLinksCell links={links} />,
        },
      ]}
    />
  )
}
