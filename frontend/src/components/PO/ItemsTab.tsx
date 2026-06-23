import { DeleteOutlined, EditOutlined } from '@ant-design/icons'
import { Button, Form, Input, InputNumber, Modal, Popover, Space, Table, Tooltip, Typography, message } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type FulfillmentLink, type FulfillmentType, type POItem, type PurchaseOrder } from '@/api'
import { extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { fmtAmount, fmtAmountNode, fmtQty, fmtQtyNode } from '@/utils/format'

interface ItemsTabProps {
  items: PurchaseOrder['items']
  currency: string
  onChanged?: () => void
}

const fulfillmentTypeStateClass: Record<FulfillmentType, string> = {
  equivalent: 'tag-state tag-state--success',
  downgraded: 'tag-state tag-state--warning',
  substitute: 'tag-state tag-state--error',
  supplementary: 'tag-state tag-state--info',
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
          <span className={fulfillmentTypeStateClass[link.fulfillment_type] ?? 'tag-state tag-state--neutral'}>
            {label} · {fmtQty(link.qty_contribution)}
          </span>
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

interface EditPOItemModalProps {
  open: boolean
  poItem: POItem | null
  currency: string
  onClose: () => void
  onSuccess: () => void
}

function EditPOItemModal({ open, poItem, currency, onClose, onSuccess }: EditPOItemModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [busy, setBusy] = useState(false)

  const handleOk = async () => {
    if (!poItem) return
    try {
      const values = await form.validateFields()
      setBusy(true)
      await api.updatePOItem(poItem.id, {
        qty: values.qty,
        unit_price: values.unit_price,
        item_name: values.item_name,
        specification: values.specification ?? null,
      })
      void message.success(t('message.save_success'))
      onSuccess()
      onClose()
    } catch (e: any) {
      if (e?.errorFields) return
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      title={t('po_item.edit_title')}
      open={open && !!poItem}
      onCancel={() => {
        if (!busy) onClose()
      }}
      onOk={handleOk}
      confirmLoading={busy}
      okText={t('button.confirm')}
      cancelText={t('button.cancel')}
      width={560}
      destroyOnClose
    >
      {poItem && (
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            item_name: poItem.item_name,
            specification: poItem.specification,
            qty: Number(poItem.qty),
            unit_price: Number(poItem.unit_price),
          }}
        >
          <Form.Item
            name="item_name"
            label={t('field.item_name')}
            rules={[{ required: true, max: 255 }]}
          >
            <Input maxLength={255} />
          </Form.Item>
          <Form.Item name="specification" label={t('field.specification')}>
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item
            name="qty"
            label={t('field.qty')}
            rules={[{ required: true }, { type: 'number', min: 0.0001 }]}
            extra={
              Number(poItem.qty_received) > 0
                ? t('po_item.qty_received_warning', { qty: poItem.qty_received })
                : undefined
            }
          >
            <InputNumber min={Number(poItem.qty_received) || 0.0001} step={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="unit_price"
            label={t('field.unit_price')}
            rules={[{ required: true }, { type: 'number', min: 0 }]}
          >
            <InputNumber
              min={0}
              step={0.01}
              style={{ width: '100%' }}
              formatter={(v) => (v === undefined || v === null ? '' : `${currency} ${v}`)}
              parser={(v) => Number((v || '').toString().replace(/[^\d.]/g, '')) as 0}
            />
          </Form.Item>
        </Form>
      )}
    </Modal>
  )
}

export function ItemsTab({ items, currency, onChanged }: ItemsTabProps) {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const [editing, setEditing] = useState<POItem | null>(null)
  const [editOpen, setEditOpen] = useState(false)

  const canEdit = Boolean(
    user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role),
  )

  const handleDelete = (item: POItem) => {
    Modal.confirm({
      title: t('po_item.delete_confirm_title'),
      content: t('po_item.delete_confirm_body', { name: item.item_name }),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deletePOItem(item.id)
          void message.success(t('message.deleted'))
          onChanged?.()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  return (
    <>
      <Table
        rowKey="id"
        dataSource={items}
        pagination={false}
        columns={[
          { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
          { title: t('field.item_name'), dataIndex: 'item_name' },
          { title: t('field.qty'), dataIndex: 'qty', align: 'right', width: 90, render: (v: string) => fmtQtyNode(v) },
          { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right', width: 110, render: (v: string) => fmtQtyNode(v) },
          { title: t('field.qty_invoiced'), dataIndex: 'qty_invoiced', align: 'right', width: 110, render: (v: string) => fmtQtyNode(v) },
          { title: t('field.uom'), dataIndex: 'uom', width: 60 },
          { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', width: 110, render: (v: string) => fmtAmountNode(v, currency) },
          { title: t('field.amount'), dataIndex: 'amount', align: 'right', width: 110, render: (v: string) => fmtAmountNode(v, currency) },
          {
            title: t('fulfillment.column_title'),
            dataIndex: 'fulfillment_links',
            width: 220,
            render: (links: FulfillmentLink[]) => <FulfillmentLinksCell links={links} />,
          },
          ...(canEdit
            ? [
                {
                  title: t('field.actions'),
                  key: 'actions',
                  width: 120,
                  fixed: 'right' as const,
                  render: (_: unknown, row: POItem) => (
                    <Space size={4}>
                      <Button
                        size="small"
                        type="link"
                        icon={<EditOutlined />}
                        onClick={() => {
                          setEditing(row)
                          setEditOpen(true)
                        }}
                      />
                      <Button
                        size="small"
                        type="link"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(row)}
                      />
                    </Space>
                  ),
                },
              ]
            : []),
        ]}
        scroll={{ x: 1100 }}
      />
      <EditPOItemModal
        open={editOpen}
        poItem={editing}
        currency={currency}
        onClose={() => {
          setEditOpen(false)
          setEditing(null)
        }}
        onSuccess={() => onChanged?.()}
      />
    </>
  )
}
