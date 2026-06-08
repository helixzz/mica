import { Form, Input, InputNumber, Modal, Select, Typography, message } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PurchaseOrder } from '@/api'
import { extractError } from '@/api/client'

interface SupplementaryItemModalProps {
  open: boolean
  po: PurchaseOrder
  prItems: { id: string; line_no: number; item_name: string }[]
  onClose: () => void
  onSuccess: () => void
}

export function SupplementaryItemModal({
  open,
  po,
  prItems,
  onClose,
  onSuccess,
}: SupplementaryItemModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [busy, setBusy] = useState(false)

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      await api.addSupplementaryPOItem(po.id, {
        item_name: values.item_name,
        specification: values.specification ?? null,
        qty: values.qty,
        uom: values.uom || 'EA',
        unit_price: values.unit_price,
        supplementary_for_pr_item_id: values.supplementary_for_pr_item_id ?? null,
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
      title={t('fulfillment.add_supplementary_title')}
      open={open}
      onCancel={() => {
        form.resetFields()
        onClose()
      }}
      onOk={handleOk}
      confirmLoading={busy}
      okText={t('button.confirm')}
      cancelText={t('button.cancel')}
      width={600}
    >
      <Typography.Paragraph type="secondary">
        {t('fulfillment.add_supplementary_hint')}
      </Typography.Paragraph>
      <Form form={form} layout="vertical">
        <Form.Item
          name="item_name"
          label={t('field.item_name')}
          rules={[{ required: true }]}
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
          <Input />
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
            formatter={(v) => (v === undefined || v === null ? '' : `${po.currency} ${v}`)}
            parser={(v) => Number((v || '').toString().replace(/[^\d.]/g, '')) as 0}
          />
        </Form.Item>
        <Form.Item
          name="supplementary_for_pr_item_id"
          label={t('fulfillment.supplementary_for_pr_item')}
        >
          <Select
            allowClear
            placeholder="-"
            options={prItems.map((it) => ({
              value: it.id,
              label: `L${it.line_no} · ${it.item_name}`,
            }))}
          />
        </Form.Item>
        <Form.Item
          name="deviation_note"
          label={t('fulfillment.deviation_note_label')}
        >
          <Input.TextArea
            rows={2}
            placeholder={t('fulfillment.deviation_note_placeholder')}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}
