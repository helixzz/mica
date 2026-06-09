import { Alert, Form, Input, InputNumber, Modal, Radio, Select, Typography, message } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  api,
  type Item,
  type POItem,
  type PurchaseOrder,
  type Supplier,
} from '@/api'
import { extractError } from '@/api/client'
import { ItemPickerWithCreate } from '@/components/ItemPickerWithCreate'

interface PRItemContext {
  id: string
  line_no: number
  item_name: string
  qty: string | number
  uom: string
}

interface AddSupplementaryFromPRModalProps {
  open: boolean
  prId: string
  prItem: PRItemContext | null
  currency: string
  suppliers: Supplier[]
  onClose: () => void
  onSuccess: () => void
}

export function AddSupplementaryFromPRModal({
  open,
  prId,
  prItem,
  currency,
  suppliers,
  onClose,
  onSuccess,
}: AddSupplementaryFromPRModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [busy, setBusy] = useState(false)
  const [mode, setMode] = useState<'new_po' | 'append_po'>('new_po')
  const [existingPOs, setExistingPOs] = useState<PurchaseOrder[]>([])
  const [pickedSupplierId, setPickedSupplierId] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !prId) return
    setMode('new_po')
    form.resetFields()
    setPickedSupplierId(null)
    void api
      .listPOs()
      .then((rows) => Promise.all(rows.filter((r) => r.pr_id === prId).map((r) => api.getPO(r.id))))
      .then(setExistingPOs)
      .catch(() => setExistingPOs([]))
  }, [open, prId, form])

  const handleItemPicked = (_id: string | null, picked: Item | null) => {
    if (picked) {
      const cur = form.getFieldsValue()
      form.setFieldsValue({
        item_id: picked.id,
        item_name: cur.item_name?.trim() ? cur.item_name : picked.name,
        uom: cur.uom?.trim() ? cur.uom : (picked.uom || 'EA'),
        specification: cur.specification ?? picked.specification ?? undefined,
      })
    } else {
      form.setFieldsValue({ item_id: null })
    }
  }

  const handleSupplierChange = (val: string | null) => {
    setPickedSupplierId(val)
    form.setFieldsValue({ supplier_id: val })
    if (mode === 'append_po') {
      form.setFieldsValue({ target_po_id: undefined })
    }
  }

  const filteredPOs = pickedSupplierId
    ? existingPOs.filter((po) => po.supplier_id === pickedSupplierId)
    : existingPOs

  const handleOk = async () => {
    if (!prItem) return
    try {
      const values = await form.validateFields()
      setBusy(true)
      await api.addSupplementaryForPRItem(prItem.id, {
        item_id: values.item_id ?? null,
        item_name: values.item_name,
        specification: values.specification ?? null,
        qty: values.qty,
        uom: values.uom || 'EA',
        unit_price: values.unit_price,
        supplier_id: values.supplier_id,
        target_po_id: mode === 'append_po' ? (values.target_po_id ?? null) : null,
        deviation_note: values.deviation_note ?? null,
      })
      void message.success(t('message.save_success'))
      form.resetFields()
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
      title={t('fulfillment.supp_from_pr_title')}
      open={open && !!prItem}
      onCancel={() => {
        if (!busy) {
          form.resetFields()
          onClose()
        }
      }}
      onOk={handleOk}
      confirmLoading={busy}
      okText={t('button.confirm')}
      cancelText={t('button.cancel')}
      width={620}
      destroyOnClose
    >
      {prItem && (
        <>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message={t('fulfillment.supp_from_pr_context', {
              line_no: prItem.line_no,
              item_name: prItem.item_name,
            })}
          />
          <Form form={form} layout="vertical">
            <Form.Item label={t('fulfillment.supp_target_mode')}>
              <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)}>
                <Radio value="new_po">{t('fulfillment.supp_mode_new_po')}</Radio>
                <Radio value="append_po">{t('fulfillment.supp_mode_append_po')}</Radio>
              </Radio.Group>
            </Form.Item>
            <Form.Item
              name="supplier_id"
              label={t('field.supplier')}
              rules={[{ required: true }]}
            >
              <Select
                showSearch
                allowClear
                optionFilterProp="label"
                placeholder={t('placeholder.select')}
                options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
                onChange={handleSupplierChange}
              />
            </Form.Item>
            {mode === 'append_po' && (
              <Form.Item
                name="target_po_id"
                label={t('fulfillment.supp_target_po')}
                rules={[{ required: true }]}
                extra={
                  pickedSupplierId && filteredPOs.length === 0
                    ? t('fulfillment.supp_no_existing_po_for_supplier')
                    : undefined
                }
              >
                <Select
                  placeholder={t('placeholder.select')}
                  disabled={!pickedSupplierId || filteredPOs.length === 0}
                  options={filteredPOs.map((po) => ({
                    value: po.id,
                    label: `${po.po_number} · ${po.supplier_name ?? ''}`.trim(),
                  }))}
                />
              </Form.Item>
            )}
            <Form.Item label={t('item.sku_picker_label')} name="item_id">
              <ItemPickerWithCreate
                value={form.getFieldValue('item_id')}
                onChange={handleItemPicked}
                placeholder={t('placeholder.select_item')}
              />
            </Form.Item>
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
            >
              <InputNumber min={0.0001} step={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="uom" label={t('field.uom')} initialValue="EA">
              <Input maxLength={16} />
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
            <Form.Item name="deviation_note" label={t('fulfillment.deviation_note_label')}>
              <Input.TextArea
                rows={2}
                placeholder={t('fulfillment.deviation_note_placeholder')}
              />
            </Form.Item>
          </Form>
        </>
      )}
    </Modal>
  )
}
