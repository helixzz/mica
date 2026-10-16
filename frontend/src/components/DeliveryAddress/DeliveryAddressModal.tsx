import { Form, Input, Modal, Switch, message } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type DeliveryAddress } from '@/api'
import { extractError } from '@/api/client'

interface DeliveryAddressModalProps {
  open: boolean
  /** Receives a newly created or edited entry. */
  onSaved: (address: DeliveryAddress) => void
  onCancel: () => void
  /** Whether this user may create company-wide entries. */
  canMaintainShared?: boolean
}

interface DeliveryAddressFormValues {
  label?: string
  contact_name: string
  contact_phone: string
  detail: string
  is_shared: boolean
}

/**
 * Create a new address book entry.
 *
 * Editing is intentionally not offered here: an entry's text is copied into
 * every requisition that picked it, so the useful editing surface is the
 * requisition itself, not a shared row.
 */
export function DeliveryAddressModal({
  open,
  onSaved,
  onCancel,
  canMaintainShared = false,
}: DeliveryAddressModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm<DeliveryAddressFormValues>()
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!open) return
    form.resetFields()
    form.setFieldsValue({ is_shared: false })
  }, [open, form])

  const submit = async () => {
    let values: DeliveryAddressFormValues
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    setSaving(true)
    try {
      const saved = await api.createDeliveryAddress({
        label: values.label?.trim() || null,
        contact_name: values.contact_name.trim(),
        contact_phone: values.contact_phone.trim(),
        detail: values.detail.trim(),
        is_shared: canMaintainShared && !!values.is_shared,
      })
      void message.success(t('address.create_success'))
      onSaved(saved)
    } catch (e) {
      void message.error(extractError(e).detail || t('error.unexpected'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={t('address.create_title')}
      onCancel={onCancel}
      onOk={() => void submit()}
      confirmLoading={saving}
      okText={t('button.save')}
      cancelText={t('button.cancel')}
      width={520}
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item
          label={t('address.contact_name')}
          name="contact_name"
          rules={[{ required: true, message: t('common.required') }]}
        >
          <Input maxLength={64} placeholder={t('address.contact_name_placeholder')} />
        </Form.Item>
        <Form.Item
          label={t('address.contact_phone')}
          name="contact_phone"
          rules={[{ required: true, message: t('common.required') }]}
        >
          <Input maxLength={32} placeholder={t('address.contact_phone_placeholder')} />
        </Form.Item>
        <Form.Item
          label={t('address.detail')}
          name="detail"
          rules={[{ required: true, message: t('common.required') }]}
        >
          <Input.TextArea rows={2} placeholder={t('address.detail_placeholder')} />
        </Form.Item>
        <Form.Item label={t('address.label')} name="label" extra={t('address.label_help')}>
          <Input maxLength={64} placeholder={t('address.label_placeholder')} />
        </Form.Item>
        {canMaintainShared && (
          <Form.Item
            label={t('address.shared')}
            name="is_shared"
            valuePropName="checked"
            extra={t('address.shared_help')}
          >
            <Switch />
          </Form.Item>
        )}
      </Form>
    </Modal>
  )
}
