import {
  Button,
  DatePicker,
  Drawer,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Table,
  Typography,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type DeliveryPlan, type PurchaseOrder, type Shipment } from '@/api'
import { fmtQtyNode } from '@/utils/format'

interface Props {
  shipment: Shipment | null
  open: boolean
  onClose: () => void
  onSaved: () => void
}

interface QtyLine {
  shipment_item_id: string
  po_item_id: string
  line_no: number
  item_name: string
  qty_shipped: number
  qty_received: number
}

export function ShipmentEditDrawer({ shipment, open, onClose, onSaved }: Props) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [deliveryPlans, setDeliveryPlans] = useState<DeliveryPlan[]>([])
  const [loadingPlans, setLoadingPlans] = useState(false)
  const [selectedPlanId, setSelectedPlanId] = useState<string | undefined>(undefined)
  const [saving, setSaving] = useState(false)
  // Line quantities are kept in their own state rather than in `form`: they are
  // a list keyed by shipment item id, and correcting them is the whole point of
  // this drawer — before v1.58.3 the only way to fix a mistyped receipt was to
  // delete the batch and record it again.
  const [qtyLines, setQtyLines] = useState<QtyLine[]>([])
  const [po, setPo] = useState<PurchaseOrder | null>(null)

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
      setQtyLines(
        (shipment.items || []).map((item) => ({
          shipment_item_id: item.id,
          po_item_id: item.po_item_id,
          line_no: item.line_no,
          item_name: item.item_name,
          qty_shipped: Number(item.qty_shipped || 0),
          qty_received: Number(item.qty_received || 0),
        }))
      )
      setPo(null)
      setDeliveryPlans([])
      setSelectedPlanId(undefined)
      if (shipment.po_id) {
        // Ordered quantities put the edit in context: a receipt above the
        // ordered quantity is refused by the API.
        api
          .getPO(shipment.po_id)
          .then(setPo)
          .catch(() => {})
        setLoadingPlans(true)
        api
          .getPODeliveryPlan(shipment.po_id)
          .then((summary) => {
            const plans = summary.po_plans || []
            setDeliveryPlans(plans)
            // Auto-select matching plan
            if (shipment.expected_date) {
              const matched = plans.find((dp) => dp.planned_date === shipment.expected_date)
              if (matched) setSelectedPlanId(matched.id)
            }
          })
          .catch(() => {})
          .finally(() => setLoadingPlans(false))
      }
    }
  }, [open, shipment, form])

  const handleDeliveryPlanSelect = (planId: string | undefined) => {
    setSelectedPlanId(planId)
    if (planId) {
      const plan = deliveryPlans.find((dp) => dp.id === planId)
      if (plan) {
        form.setFieldsValue({ expected_date: dayjs(plan.planned_date) })
      }
    }
  }

  const orderedQtyOf = (poItemId: string) =>
    po?.items.find((item) => item.id === poItemId)?.qty

  const handleSave = async () => {
    if (!shipment) return
    setSaving(true)
    try {
      const values = form.getFieldsValue()
      await api.updateShipment(shipment.id, {
        ...values,
        expected_date: values.expected_date ? values.expected_date.format('YYYY-MM-DD') : null,
        actual_date: values.actual_date ? values.actual_date.format('YYYY-MM-DD') : null,
        items: qtyLines.map((line) => ({
          shipment_item_id: line.shipment_item_id,
          qty_shipped: line.qty_shipped,
          qty_received: line.qty_received,
        })),
      })
      void message.success(t('shipment.updated'))
      onSaved()
      onClose()
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      void message.error(err?.response?.data?.detail || t('error.save_failed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Drawer
      title={shipment ? t('shipment.edit', { number: shipment.shipment_number }) : ''}
      width={640}
      open={open}
      onClose={onClose}
      footer={
        <Space style={{ float: 'right' }}>
          <Button onClick={onClose}>{t('button.cancel')}</Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
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
              value={selectedPlanId}
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

      {qtyLines.length > 0 && (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Text type="secondary">{t('shipment.quantity_help')}</Typography.Text>
          <Table
            rowKey="shipment_item_id"
            size="small"
            pagination={false}
            dataSource={qtyLines}
            columns={[
              { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
              { title: t('field.item_name'), dataIndex: 'item_name', ellipsis: true },
              {
                title: t('field.qty'),
                width: 90,
                align: 'right',
                render: (_: unknown, r: QtyLine) => (
                  <Typography.Text type="secondary">
                    {fmtQtyNode(orderedQtyOf(r.po_item_id) ?? '—')}
                  </Typography.Text>
                ),
              },
              {
                title: t('field.qty_shipped'),
                width: 110,
                render: (_: unknown, r: QtyLine) => (
                  <InputNumber
                    min={0}
                    value={r.qty_shipped}
                    style={{ width: '100%' }}
                    onChange={(value) =>
                      setQtyLines((lines) =>
                        lines.map((line) =>
                          line.shipment_item_id === r.shipment_item_id
                            ? { ...line, qty_shipped: Number(value ?? 0) }
                            : line
                        )
                      )
                    }
                  />
                ),
              },
              {
                title: t('field.qty_received'),
                width: 110,
                render: (_: unknown, r: QtyLine) => (
                  <InputNumber
                    min={0}
                    value={r.qty_received}
                    style={{ width: '100%' }}
                    onChange={(value) =>
                      setQtyLines((lines) =>
                        lines.map((line) =>
                          line.shipment_item_id === r.shipment_item_id
                            ? { ...line, qty_received: Number(value ?? 0) }
                            : line
                        )
                      )
                    }
                  />
                ),
              },
            ]}
          />
        </Space>
      )}
    </Drawer>
  )
}
