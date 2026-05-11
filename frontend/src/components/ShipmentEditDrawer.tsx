import { Button, DatePicker, Drawer, Form, Input, Select, Space, message } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type DeliveryPlan, type Shipment } from '@/api'

interface Props {
  shipment: Shipment | null
  open: boolean
  onClose: () => void
  onSaved: () => void
}

export function ShipmentEditDrawer({ shipment, open, onClose, onSaved }: Props) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [deliveryPlans, setDeliveryPlans] = useState<DeliveryPlan[]>([])
  const [loadingPlans, setLoadingPlans] = useState(false)

  useEffect(() => {
    if (open && shipment) {
      form.resetFields()
      form.setFieldsValue({
        status: shipment.status,
        carrier: shipment.carrier,
        tracking_number: shipment.tracking_number,
        expected_date: shipment.expected_date ? dayjs(shipment.expected_date) : null,
        actual_date: shipment.actual_date ? dayjs(shipment.actual_date) : null,
        notes: shipment.notes,
      })
      setDeliveryPlans([])
      if (shipment.po_id) {
        setLoadingPlans(true)
        api.getPODeliveryPlan(shipment.po_id)
          .then((summary) => setDeliveryPlans(summary.po_plans || []))
          .catch(() => {})
          .finally(() => setLoadingPlans(false))
      }
    }
  }, [open, shipment, form])

  const handleDeliveryPlanSelect = (planId: string) => {
    const plan = deliveryPlans.find((dp) => dp.id === planId)
    if (plan) {
      form.setFieldsValue({ expected_date: dayjs(plan.planned_date) })
    }
  }

  const handleSave = async () => {
    if (!shipment) return
    try {
      const values = form.getFieldsValue()
      await api.updateShipment(shipment.id, {
        ...values,
        expected_date: values.expected_date ? values.expected_date.format('YYYY-MM-DD') : null,
        actual_date: values.actual_date ? values.actual_date.format('YYYY-MM-DD') : null,
      })
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
        {deliveryPlans.length > 0 && (
          <Form.Item label={t('shipment.fulfills_delivery_plan')}>
            <Select
              placeholder={t('shipment.fulfills_delivery_plan')}
              loading={loadingPlans}
              allowClear
              onChange={handleDeliveryPlanSelect}
            >
              {deliveryPlans.map((dp) => (
                <Select.Option key={dp.id} value={dp.id}>
                  {dp.plan_name} — {dp.planned_qty} — {dayjs(dp.planned_date).format('YYYY-MM-DD')}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        )}
        <Form.Item name="expected_date" label={t('shipment.planned_date')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="actual_date" label={t('field.actual_date')}>
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="notes" label={t('shipment.notes')}>
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Drawer>
  )
}