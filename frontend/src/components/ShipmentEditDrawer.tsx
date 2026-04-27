import { Button, Drawer, Form, Input, Select, Space, message } from 'antd'
import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Shipment } from '@/api'

interface Props {
  shipment: Shipment | null
  open: boolean
  onClose: () => void
  onSaved: () => void
}

export function ShipmentEditDrawer({ shipment, open, onClose, onSaved }: Props) {
  const { t } = useTranslation()
  const [form] = Form.useForm()

  useEffect(() => {
    if (open && shipment) {
      form.resetFields()
      form.setFieldsValue({
        status: shipment.status,
        carrier: shipment.carrier,
        tracking_number: shipment.tracking_number,
        expected_date: shipment.expected_date,
        actual_date: shipment.actual_date,
        notes: shipment.notes,
      })
    }
  }, [open, shipment, form])

  const handleSave = async () => {
    if (!shipment) return
    try {
      const values = form.getFieldsValue()
      await api.updateShipment(shipment.id, values)
      void message.success(t('shipment.updated'))
      onSaved()
      onClose()
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      void message.error(err?.response?.data?.detail || t('error.save_failed'))
    }
  }

  return (
    <Drawer
      title={shipment ? t('shipment.edit', { number: shipment.shipment_number }) : ''}
      width={420}
      open={open}
      onClose={onClose}
      footer={
        <Space style={{ float: 'right' }}>
          <Button onClick={onClose}>{t('button.cancel')}</Button>
          <Button type="primary" onClick={handleSave}>
            {t('button.save')}
          </Button>
        </Space>
      }
    >
      <Form form={form} layout="vertical">
        <Form.Item name="status" label={t('field.status')}>
          <Select
            options={[
              { value: 'pending', label: t('status.pending') },
              { value: 'in_transit', label: t('status.in_transit') },
              { value: 'arrived', label: t('status.arrived') },
              { value: 'accepted', label: t('status.accepted') },
              { value: 'partially_accepted', label: t('status.partially_accepted') },
              { value: 'rejected', label: t('status.rejected') },
              { value: 'cancelled', label: t('status.cancelled') },
            ]}
          />
        </Form.Item>
        <Form.Item name="carrier" label={t('field.carrier')}>
          <Input />
        </Form.Item>
        <Form.Item name="tracking_number" label={t('field.tracking_number')}>
          <Input />
        </Form.Item>
        <Form.Item name="expected_date" label={t('field.expected_date')}>
          <Input type="date" />
        </Form.Item>
        <Form.Item name="actual_date" label={t('field.actual_date')}>
          <Input type="date" />
        </Form.Item>
        <Form.Item name="notes" label={t('shipment.notes')}>
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Drawer>
  )
}
