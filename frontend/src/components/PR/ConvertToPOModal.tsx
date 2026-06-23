import { Alert, Button, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, Typography, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  api,
  type FulfillmentType,
  type Item,
  type PRConversionPreviewGroup,
  type PurchaseOrder,
  type PurchaseRequisition,
  type Supplier,
} from '@/api'
import { extractError } from '@/api/client'
import { ItemPickerWithCreate } from '@/components/ItemPickerWithCreate'
import { fmtAmount, fmtAmountNode, fmtQty, fmtQtyNode } from '@/utils/format'

interface ConvertToPOModalProps {
  open: boolean
  pr: PurchaseRequisition
  supplierMap: Record<string, string>
  suppliers: Supplier[]
  onClose: () => void
  onSuccess: (createdPOs: PurchaseOrder[]) => void
}

type SplitRow = {
  key: string
  pr_item_id: string
  line_no: number
  item_name: string
  supplier_id: string | null
  picked_supplier_id: string | null
  total_qty: number
  remaining_qty: number
  uom: string
  unit_price: number
  this_qty: number
  this_unit_price: number
  this_item_name: string
  this_item_id: string | null
  this_specification: string | null
  this_uom: string | null
  fulfillment_type: FulfillmentType
  deviation_note: string
}

const FULFILLMENT_TYPES: { value: FulfillmentType; labelKey: string }[] = [
  { value: 'equivalent', labelKey: 'fulfillment_type.equivalent' },
  { value: 'downgraded', labelKey: 'fulfillment_type.downgraded' },
  { value: 'substitute', labelKey: 'fulfillment_type.substitute' },
  { value: 'supplementary', labelKey: 'fulfillment_type.supplementary' },
]

export function ConvertToPOModal({
  open,
  pr,
  supplierMap,
  suppliers,
  onClose,
  onSuccess,
}: ConvertToPOModalProps) {
  const { t } = useTranslation()

  const [activeTab, setActiveTab] = useState<'all' | 'rows' | 'split'>('all')
  const [busy, setBusy] = useState(false)

  const [preview, setPreview] = useState<PRConversionPreviewGroup[] | null>(null)
  const [rowsSelected, setRowsSelected] = useState<string[]>([])
  const [splitRows, setSplitRows] = useState<SplitRow[]>([])

  const unconvertedItems = useMemo(() => {
    return (pr.items || []).filter((it: any) => {
      const filled = Number(it.fulfilled_qty || 0)
      const total = Number(it.qty || 0)
      return filled < total
    })
  }, [pr])

  const itemRemainingMap = useMemo(() => {
    const m: Record<string, number> = {}
    for (const it of unconvertedItems) {
      const filled = Number((it as any).fulfilled_qty || 0)
      const total = Number(it.qty || 0)
      m[(it as any).id] = total - filled
    }
    return m
  }, [unconvertedItems])

  useEffect(() => {
    if (!open) return
    setActiveTab('all')
    setRowsSelected(unconvertedItems.map((it: any) => it.id).filter(Boolean) as string[])
    setSplitRows(
      unconvertedItems
        .filter((it: any) => it.id)
        .map((it: any) => {
          const remaining = itemRemainingMap[it.id] ?? Number(it.qty)
          return {
            key: it.id,
            pr_item_id: it.id,
            line_no: it.line_no,
            item_name: it.item_name,
            supplier_id: it.supplier_id,
            picked_supplier_id: it.supplier_id,
            total_qty: Number(it.qty),
            remaining_qty: remaining,
            uom: it.uom,
            unit_price: Number(it.unit_price || 0),
            this_qty: remaining,
            this_unit_price: Number(it.unit_price || 0),
            this_item_name: it.item_name,
            this_item_id: it.item_id ?? null,
            this_specification: it.specification ?? null,
            this_uom: it.uom ?? null,
            fulfillment_type: 'equivalent' as FulfillmentType,
            deviation_note: '',
          }
        }),
    )

    if (activeTab === 'all' || preview === null) {
      void api
        .previewPRConversion(pr.id)
        .then(setPreview)
        .catch(() => setPreview([]))
    }
  }, [open, pr.id])

  const updateSplitRow = (key: string, patch: Partial<SplitRow>) => {
    setSplitRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)))
  }

  const submitAll = async () => {
    setBusy(true)
    try {
      const pos = await api.convertToPO(pr.id)
      void message.success(
        pos.length === 1
          ? t('message.convert_success', { po_number: pos[0].po_number })
          : t('message.convert_success_multi', {
              count: pos.length,
              po_numbers: pos.map((p) => p.po_number).join('、'),
            }),
      )
      onSuccess(pos)
      onClose()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  const submitRows = async () => {
    if (rowsSelected.length === 0) {
      void message.error(t('pr.partial_no_items'))
      return
    }
    setBusy(true)
    try {
      const pos = await api.convertToPOPartial(pr.id, rowsSelected)
      void message.success(
        t('message.convert_success_multi', {
          count: pos.length,
          po_numbers: pos.map((p) => p.po_number).join('、'),
        }),
      )
      onSuccess(pos)
      onClose()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  const submitSplit = async () => {
    const enabled = splitRows.filter((r) => r.this_qty > 0)
    if (enabled.length === 0) {
      void message.error(t('pr.partial_no_items'))
      return
    }
    const missingSupplier = enabled.some((r) => !r.picked_supplier_id)
    if (missingSupplier) {
      void message.error(t('pr.items_missing_supplier'))
      return
    }
    const exceeded = enabled.find(
      (r) => r.fulfillment_type !== 'supplementary' && r.this_qty > r.remaining_qty * 1.5,
    )
    if (exceeded) {
      void message.error(t('fulfillment.qty_exceeds_soft_limit'))
      return
    }
    const needsNote = enabled.find(
      (r) =>
        (r.fulfillment_type === 'downgraded' || r.fulfillment_type === 'substitute') &&
        !r.deviation_note.trim(),
    )
    if (needsNote) {
      void message.error(t('fulfillment.deviation_note_required_for_deviation'))
      return
    }
    const supplementaryWithoutName = enabled.find(
      (r) => r.fulfillment_type === 'supplementary' && !r.this_item_name.trim(),
    )
    if (supplementaryWithoutName) {
      void message.error(t('fulfillment.supplementary_name_required'))
      return
    }

    setBusy(true)
    try {
      const pos = await api.convertToPOWithSpecs(
        pr.id,
        enabled.map((r) => {
          const isSupp = r.fulfillment_type === 'supplementary'
          return {
            pr_item_id: r.pr_item_id,
            qty: r.this_qty,
            unit_price: r.this_unit_price,
            fulfillment_type: r.fulfillment_type,
            deviation_note: r.deviation_note.trim() || null,
            supplier_id:
              r.picked_supplier_id !== r.supplier_id ? r.picked_supplier_id : null,
            item_id: isSupp ? r.this_item_id ?? null : null,
            item_name:
              isSupp && r.this_item_name.trim() !== r.item_name
                ? r.this_item_name.trim()
                : null,
            specification: isSupp ? r.this_specification ?? null : null,
            uom: isSupp ? r.this_uom ?? null : null,
          }
        }),
      )
      void message.success(
        t('message.convert_success_multi', {
          count: pos.length,
          po_numbers: pos.map((p) => p.po_number).join('、'),
        }),
      )
      onSuccess(pos)
      onClose()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  const handleOk = () => {
    if (activeTab === 'all') return submitAll()
    if (activeTab === 'rows') return submitRows()
    return submitSplit()
  }

  return (
    <Modal
      title={t('pr.convert_modal_title')}
      open={open}
      onCancel={() => {
        if (!busy) onClose()
      }}
      onOk={handleOk}
      confirmLoading={busy}
      okText={t('pr.convert_modal_confirm')}
      cancelText={t('button.cancel')}
      width={1280}
      destroyOnClose
    >
      <Tabs
        activeKey={activeTab}
        onChange={(k) => setActiveTab(k as any)}
        items={[
          {
            key: 'all',
            label: t('pr.convert_tab_all'),
            children: (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Typography.Paragraph type="secondary">
                  {t('pr.convert_tab_all_hint')}
                </Typography.Paragraph>
                {preview === null ? (
                  <div style={{ textAlign: 'center', padding: 24 }}>
                    {t('message.loading')}
                  </div>
                ) : preview.length === 0 ? (
                  <Alert type="warning" message={t('pr.already_fully_converted')} />
                ) : (
                  <Table
                    size="small"
                    rowKey="supplier_id"
                    pagination={false}
                    dataSource={preview}
                    columns={[
                      {
                        title: t('field.supplier'),
                        dataIndex: 'supplier_name',
                        render: (v: string | null, r) => v || r.supplier_code || r.supplier_id,
                      },
                      {
                        title: t('pr.convert_preview_item_count'),
                        dataIndex: 'item_count',
                        width: 80,
                        align: 'right',
                      },
                      {
                        title: t('pr.convert_preview_subtotal'),
                        dataIndex: 'subtotal',
                        align: 'right',
                        render: (v: string) => fmtAmountNode(v, pr.currency || 'CNY'),
                      },
                    ]}
                  />
                )}
              </Space>
            ),
          },
          {
            key: 'rows',
            label: t('pr.convert_tab_rows'),
            disabled: unconvertedItems.length === 0,
            children: (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Typography.Paragraph type="secondary">
                  {t('pr.convert_tab_rows_hint')}
                </Typography.Paragraph>
                <Table
                  size="small"
                  rowKey="id"
                  pagination={false}
                  dataSource={unconvertedItems as any[]}
                  rowSelection={{
                    selectedRowKeys: rowsSelected,
                    onChange: (keys) => setRowsSelected(keys as string[]),
                    getCheckboxProps: (row: any) => ({ disabled: !row.supplier_id }),
                  }}
                  columns={[
                    { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
                    { title: t('field.item_name'), dataIndex: 'item_name' },
                    {
                      title: t('field.supplier'),
                      dataIndex: 'supplier_id',
                      render: (v: string | null) =>
                        v ? supplierMap[v] ?? v : (
                          <Typography.Text type="warning">
                            {t('pr.items_missing_supplier')}
                          </Typography.Text>
                        ),
                    },
                    { title: t('field.qty'), dataIndex: 'qty', align: 'right', render: (v: string) => fmtQtyNode(v) },
                    { title: t('field.uom'), dataIndex: 'uom', width: 70 },
                  ]}
                />
              </Space>
            ),
          },
          {
            key: 'split',
            label: t('pr.convert_tab_split'),
            disabled: unconvertedItems.length === 0,
            children: (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Alert
                  type="info"
                  showIcon
                  message={t('pr.convert_tab_split_hint_title')}
                  description={t('pr.convert_tab_split_hint_body')}
                />
                <Table
                  size="small"
                  rowKey="key"
                  pagination={false}
                  dataSource={splitRows}
                  scroll={{ x: 1380 }}
                  columns={[
                    { title: t('field.line_no'), dataIndex: 'line_no', width: 56 },
                    {
                      title: t('field.item_name'),
                      key: 'item_name',
                      render: (_: unknown, row: SplitRow) => {
                        if (row.fulfillment_type === 'supplementary') {
                          return (
                            <Space direction="vertical" size={4} style={{ width: '100%' }}>
                              <ItemPickerWithCreate
                                value={row.this_item_id ?? undefined}
                                placeholder={t('placeholder.select_item')}
                                onChange={(itemId, picked: Item | null) => {
                                  if (picked) {
                                    updateSplitRow(row.key, {
                                      this_item_id: itemId,
                                      this_item_name: picked.name,
                                      this_uom: picked.uom || row.this_uom,
                                      this_specification: picked.specification ?? row.this_specification,
                                    })
                                  } else {
                                    updateSplitRow(row.key, { this_item_id: null })
                                  }
                                }}
                              />
                              <Input
                                value={row.this_item_name}
                                placeholder={t('fulfillment.supplementary_name_placeholder')}
                                onChange={(e) => updateSplitRow(row.key, { this_item_name: e.target.value })}
                              />
                              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                                {t('fulfillment.supplementary_for', { name: row.item_name })}
                              </Typography.Text>
                            </Space>
                          )
                        }
                        return <span>{row.item_name}</span>
                      },
                    },
                    {
                      title: t('field.supplier'),
                      key: 'supplier',
                      width: 200,
                      render: (_: unknown, row: SplitRow) => (
                        <Select
                          value={row.picked_supplier_id ?? undefined}
                          onChange={(v) => updateSplitRow(row.key, { picked_supplier_id: v ?? null })}
                          style={{ width: '100%' }}
                          showSearch
                          allowClear
                          optionFilterProp="label"
                          placeholder={t('placeholder.select')}
                          options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
                          disabled={row.this_qty <= 0}
                        />
                      ),
                    },
                    {
                      title: t('pr.convert_split_remaining'),
                      key: 'remaining',
                      width: 110,
                      align: 'right',
                      render: (_: unknown, row: SplitRow) =>
                        row.fulfillment_type === 'supplementary'
                          ? '—'
                          : `${fmtQty(String(row.remaining_qty))} ${row.uom}`,
                    },
                    {
                      title: t('pr.convert_split_this_qty'),
                      key: 'this_qty',
                      width: 130,
                      render: (_: unknown, row: SplitRow) => (
                        <InputNumber
                          min={0}
                          max={row.fulfillment_type === 'supplementary' ? undefined : row.remaining_qty * 1.5}
                          step={1}
                          value={row.this_qty}
                          onChange={(v) => updateSplitRow(row.key, { this_qty: Number(v ?? 0) })}
                          style={{ width: '100%' }}
                          disabled={!row.picked_supplier_id}
                        />
                      ),
                    },
                    {
                      title: t('pr.convert_split_unit_price'),
                      key: 'this_unit_price',
                      width: 140,
                      render: (_: unknown, row: SplitRow) => (
                        <InputNumber
                          min={0}
                          step={0.01}
                          value={row.this_unit_price}
                          onChange={(v) => updateSplitRow(row.key, { this_unit_price: Number(v ?? 0) })}
                          style={{ width: '100%' }}
                          disabled={row.this_qty <= 0}
                          formatter={(v) => (v === undefined || v === null ? '' : `${pr.currency || 'CNY'} ${v}`)}
                          parser={(v) => Number((v || '').toString().replace(/[^\d.]/g, '')) as 0}
                        />
                      ),
                    },
                    {
                      title: t('fulfillment.type_label'),
                      key: 'type',
                      width: 130,
                      render: (_: unknown, row: SplitRow) => (
                        <Select
                          value={row.fulfillment_type}
                          onChange={(v) => updateSplitRow(row.key, { fulfillment_type: v })}
                          style={{ width: '100%' }}
                          options={FULFILLMENT_TYPES.map((opt) => ({
                            value: opt.value,
                            label: t(opt.labelKey as 'fulfillment_type.equivalent'),
                          }))}
                          disabled={row.this_qty <= 0}
                        />
                      ),
                    },
                    {
                      title: t('fulfillment.deviation_note_label'),
                      key: 'note',
                      render: (_: unknown, row: SplitRow) => (
                        <Input
                          value={row.deviation_note}
                          onChange={(e) => updateSplitRow(row.key, { deviation_note: e.target.value })}
                          placeholder={
                            row.fulfillment_type === 'equivalent'
                              ? '-'
                              : t('fulfillment.deviation_note_placeholder')
                          }
                          disabled={row.this_qty <= 0 || row.fulfillment_type === 'equivalent'}
                        />
                      ),
                    },
                    {
                      title: '',
                      key: 'actions',
                      width: 50,
                      fixed: 'right' as const,
                      render: (_: unknown, row: SplitRow) => {
                        const isExtraRow = row.key !== row.pr_item_id
                        if (!isExtraRow) return null
                        return (
                          <Button
                            type="link"
                            danger
                            size="small"
                            onClick={() =>
                              setSplitRows((prev) => prev.filter((r) => r.key !== row.key))
                            }
                          >
                            {t('button.delete')}
                          </Button>
                        )
                      },
                    },
                  ]}
                />
                <div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {t('fulfillment.add_extra_row_hint')}
                  </Typography.Text>
                  <div style={{ marginTop: 8 }}>
                    {(pr.items || [])
                      .filter((it: any) => it.id)
                      .map((it: any) => (
                        <Button
                          key={it.id}
                          size="small"
                          style={{ marginRight: 8, marginBottom: 4 }}
                          onClick={() => {
                            setSplitRows((prev) => [
                              ...prev,
                              {
                                key: `${it.id}-extra-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                                pr_item_id: it.id,
                                line_no: it.line_no,
                                item_name: it.item_name,
                                supplier_id: it.supplier_id,
                                picked_supplier_id: it.supplier_id,
                                total_qty: Number(it.qty),
                                remaining_qty: Number(it.qty),
                                uom: it.uom,
                                unit_price: Number(it.unit_price || 0),
                                this_qty: 1,
                                this_unit_price: 0,
                                this_item_name: '',
                                this_item_id: null,
                                this_specification: null,
                                this_uom: null,
                                fulfillment_type: 'supplementary' as FulfillmentType,
                                deviation_note: '',
                              },
                            ])
                          }}
                        >
                          + L{it.line_no} {t('fulfillment.add_supplementary_for', { name: it.item_name })}
                        </Button>
                      ))}
                  </div>
                </div>
              </Space>
            ),
          },
        ]}
      />
    </Modal>
  )
}
