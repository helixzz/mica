import { Button, Input, InputNumber, Modal, Space, Table, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PurchaseOrder, type Receipt } from '@/api'
import { extractError } from '@/api/client'
import { MonoNum } from '@/components/ui'
import { useAuth } from '@/auth/useAuth'
import { fmtQtyNode } from '@/utils/format'

// Mirrors the API's `_RECEIPT_WRITE_ROLES`: the requester accepts the goods,
// procurement can record it on their behalf.
const RECEIVING_ROLES = ['requester', 'admin', 'it_buyer', 'procurement_mgr']
// Who may undo someone else's receipt; the recorder may always undo their own.
const RECEIPT_MANAGER_ROLES = ['admin', 'it_buyer', 'procurement_mgr']

interface Props {
  po: PurchaseOrder
  loadAll: () => void
}

interface ReceiptLine {
  po_item_id: string
  item_name: string
  remaining: number
  qty: number
}

export function ReceiptsPanel({ po, loadAll }: Props) {
  const { t } = useTranslation()
  const user = useAuth((state) => state.user)
  const [receipts, setReceipts] = useState<Receipt[]>([])
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [notes, setNotes] = useState('')
  const [lines, setLines] = useState<ReceiptLine[]>([])

  const canReceive = !!user && RECEIVING_ROLES.includes(user.role)
  const itemNameById = new Map(po.items.map((item) => [item.id, item.item_name]))

  const load = useCallback(async () => {
    try {
      setReceipts(await api.listReceipts(po.id))
    } catch {
      setReceipts([])
    }
  }, [po.id])

  useEffect(() => {
    void load()
  }, [load])

  const openModal = () => {
    setNotes('')
    setLines(
      po.items.map((item) => ({
        po_item_id: item.id,
        item_name: item.item_name,
        // What is still outstanding on this line, so the default answer to
        // "how much arrived?" is one click away.
        remaining: Math.max(0, Number(item.qty) - Number(item.qty_received || 0)),
        qty: 0,
      }))
    )
    setOpen(true)
  }

  const fillRemaining = () => {
    setLines((current) => current.map((line) => ({ ...line, qty: line.remaining })))
  }

  const submit = async () => {
    const items = lines
      .filter((line) => line.qty > 0)
      .map((line) => ({ po_item_id: line.po_item_id, qty: line.qty }))
    if (items.length === 0) {
      void message.warning(t('receipt.need_qty'))
      return
    }
    setSaving(true)
    try {
      await api.createReceipts(po.id, { items, notes: notes || null })
      void message.success(t('receipt.recorded'))
      setOpen(false)
      await load()
      loadAll()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setSaving(false)
    }
  }

  const revoke = (receipt: Receipt) => {
    Modal.confirm({
      title: t('receipt.confirm_revoke'),
      onOk: async () => {
        try {
          await api.deleteReceipt(receipt.id)
          void message.success(t('receipt.revoked'))
          await load()
          loadAll()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  const canRevoke = (receipt: Receipt) =>
    !!user &&
    (receipt.received_by_id === user.id || RECEIPT_MANAGER_ROLES.includes(user.role))

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        <Typography.Text type="secondary">{t('receipt.help')}</Typography.Text>
        {canReceive && (
          <Button type="primary" onClick={openModal}>
            {t('button.confirm_receipt')}
          </Button>
        )}
      </Space>

      <Table
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={receipts}
        locale={{ emptyText: t('receipt.empty') }}
        columns={[
          {
            title: t('field.date'),
            dataIndex: 'received_at',
            width: 170,
            render: (value: string) => <MonoNum>{dayjs(value).format('YYYY-MM-DD HH:mm')}</MonoNum>,
          },
          {
            title: t('field.item_name'),
            dataIndex: 'po_item_id',
            render: (value: string) => itemNameById.get(value) ?? '—',
          },
          {
            title: t('field.qty_recv'),
            dataIndex: 'qty',
            align: 'right',
            width: 110,
            render: (value: string) => fmtQtyNode(value),
          },
          {
            title: t('field.received_by'),
            dataIndex: 'received_by_name',
            width: 140,
            render: (value: string | null) => value ?? '—',
          },
          {
            title: t('field.notes'),
            dataIndex: 'notes',
            render: (value: string | null) => value ?? '—',
          },
          {
            title: '',
            width: 90,
            render: (_: unknown, record: Receipt) =>
              canRevoke(record) ? (
                <Button type="link" danger size="small" onClick={() => revoke(record)}>
                  {t('button.revoke')}
                </Button>
              ) : null,
          },
        ]}
      />

      <Modal
        title={t('receipt.title')}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={submit}
        confirmLoading={saving}
        width={720}
        okText={t('button.confirm_receipt')}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Text type="secondary">{t('receipt.modal_help')}</Typography.Text>
          <Space>
            <Button size="small" onClick={fillRemaining}>
              {t('receipt.fill_remaining')}
            </Button>
          </Space>
          <Table
            rowKey="po_item_id"
            size="small"
            pagination={false}
            dataSource={lines}
            columns={[
              { title: t('field.item_name'), dataIndex: 'item_name' },
              {
                title: t('field.qty_pending'),
                dataIndex: 'remaining',
                align: 'right',
                width: 110,
                render: (value: number) => fmtQtyNode(value),
              },
              {
                title: t('field.qty_recv'),
                width: 150,
                render: (_: unknown, record: ReceiptLine) => (
                  <InputNumber
                    min={0}
                    max={record.remaining}
                    value={record.qty}
                    style={{ width: '100%' }}
                    onChange={(value) =>
                      setLines((current) =>
                        current.map((line) =>
                          line.po_item_id === record.po_item_id
                            ? { ...line, qty: Number(value ?? 0) }
                            : line
                        )
                      )
                    }
                  />
                ),
              },
            ]}
          />
          <Input.TextArea
            rows={2}
            value={notes}
            placeholder={t('field.notes')}
            onChange={(event) => setNotes(event.target.value)}
          />
        </Space>
      </Modal>
    </Space>
  )
}
