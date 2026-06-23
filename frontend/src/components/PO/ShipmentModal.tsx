import {
  Col,
  DatePicker,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Typography,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type DeliveryPlan, type PurchaseOrder } from '@/api'
import { extractError } from '@/api/client'
import { AutosaveBanner, AutosaveUnavailableBanner } from '@/components/AutosaveBanner'
import { MarqueeOption } from '@/components/ui/MarqueeOption'
import { useAutosave } from '@/hooks/useAutosave'
import { fmtQty, fmtQtyNode } from '@/utils/format'

interface ShipmentModalProps {
  open: boolean
  po: PurchaseOrder
  onClose: () => void
  onDone: () => void
  busy: boolean
  setBusy: (b: boolean) => void
}

export function ShipmentModal({ open, po, onClose, onDone, busy, setBusy }: ShipmentModalProps) {
  const { t } = useTranslation()
  const [lines, setLines] = useState<{ po_item_id: string; qty_shipped: number; qty_received?: number }[]>(
    po.items.map((i) => ({ po_item_id: i.id, qty_shipped: Number(i.qty) - Number(i.qty_received || 0), qty_received: Number(i.qty) - Number(i.qty_received || 0) }))
  )
  const [carrier, setCarrier] = useState('')
  const [tracking, setTracking] = useState('')
  const [plannedDate, setPlannedDate] = useState<dayjs.Dayjs | null>(null)
  const [actualDate, setActualDate] = useState<dayjs.Dayjs | null>(dayjs())
  const [deliveryPlans, setDeliveryPlans] = useState<DeliveryPlan[]>([])
  const [selectedDeliveryPlanId, setSelectedDeliveryPlanId] = useState<string | undefined>(undefined)
  const autosaveShipment = useAutosave(`po-shipment-${po.id}`)
  const [autosaveDismissedShipment, setAutosaveDismissedShipment] = useState(false)

  useEffect(() => {
    if (open) {
      setLines(po.items.map((i) => ({
        po_item_id: i.id,
        qty_shipped: Math.max(0, Number(i.qty) - Number(i.qty_received || 0)),
        qty_received: Math.max(0, Number(i.qty) - Number(i.qty_received || 0)),
      })))
      setDeliveryPlans([])
      setSelectedDeliveryPlanId(undefined)
      setPlannedDate(null)
      api.getPODeliveryPlan(po.id).then(summary => {
        setDeliveryPlans(summary.po_plans || [])
      }).catch(() => {})
    }
  }, [open, po])

  useEffect(() => {
    autosaveShipment.save({
      lines,
      carrier,
      tracking,
      plannedDate: plannedDate?.toISOString() ?? null,
      actualDate: actualDate?.toISOString() ?? null,
    })
  })

  const onSelectDeliveryPlan = (planId: string) => {
    setSelectedDeliveryPlanId(planId)
    const plan = deliveryPlans.find(dp => dp.id === planId)
    if (plan) {
      setPlannedDate(dayjs(plan.planned_date))
      setLines(prev => prev.map(line => {
        const poItem = po.items.find(i => i.id === line.po_item_id)
        if (poItem && poItem.item_id === plan.item_id) {
          return { ...line, qty_shipped: plan.planned_qty, qty_received: plan.planned_qty }
        }
        return line
      }))
    }
  }

  const submit = async () => {
    try {
      setBusy(true)
      await api.createShipment({
        po_id: po.id,
        items: lines.filter((l) => l.qty_shipped > 0),
        carrier: carrier || null,
        tracking_number: tracking || null,
        expected_date: plannedDate ? plannedDate.format('YYYY-MM-DD') : null,
        actual_date: actualDate ? actualDate.format('YYYY-MM-DD') : null,
      })
      autosaveShipment.clear()
      void message.success(t('message.shipment_recorded'))
      onDone()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={t('button.record_shipment')} open={open} onCancel={onClose} onOk={submit} confirmLoading={busy} width={800}>
      {!autosaveDismissedShipment && autosaveShipment.hasAutosave && autosaveShipment.savedAt && (
        <AutosaveBanner
          savedAt={autosaveShipment.savedAt}
          onRestore={() => {
            const v = autosaveShipment.restore()
            if (v) {
              if (v.lines) setLines(v.lines as typeof lines)
              if (v.carrier !== undefined) setCarrier(v.carrier as string)
              if (v.tracking !== undefined) setTracking(v.tracking as string)
              if (v.plannedDate) setPlannedDate(dayjs(v.plannedDate as string))
              if (v.actualDate) setActualDate(dayjs(v.actualDate as string))
            }
          }}
          onDismiss={() => setAutosaveDismissedShipment(true)}
        />
      )}
      {!autosaveShipment.storageAvailable && <AutosaveUnavailableBanner />}
      <Space direction="vertical" style={{ width: '100%' }}>
        <Typography.Text type="secondary">
          {t('po.shipment_help')}
        </Typography.Text>
        <Row gutter={12}>
          <Col span={6}>
            <Input placeholder={t('field.carrier')} value={carrier} onChange={(e) => setCarrier(e.target.value)} />
          </Col>
          <Col span={6}>
            <Input placeholder={t('field.tracking_number')} value={tracking} onChange={(e) => setTracking(e.target.value)} />
          </Col>
          <Col span={6}>
            <DatePicker
              placeholder={t('shipment.planned_date')}
              value={plannedDate}
              onChange={(v) => setPlannedDate(v)}
              style={{ width: '100%' }}
            />
          </Col>
          <Col span={6}>
            <DatePicker value={actualDate} onChange={(v) => setActualDate(v)} style={{ width: '100%' }} />
          </Col>
        </Row>
        {deliveryPlans.length > 0 && (
          <Select
            placeholder={t('shipment.fulfills_delivery_plan')}
            style={{ width: '100%' }}
            allowClear
            value={selectedDeliveryPlanId}
            onChange={onSelectDeliveryPlan}
            popupMatchSelectWidth={false}
            optionRender={(option) => <MarqueeOption>{option.label}</MarqueeOption>}
          >
            {deliveryPlans.map(dp => (
              <Select.Option key={dp.id} value={dp.id} label={`${dp.plan_name} — ${t('delivery_plan.planned_qty')}: ${dp.planned_qty} — ${dayjs(dp.planned_date).format('YYYY-MM-DD')}`}>
                {dp.plan_name} — {t('delivery_plan.planned_qty')}: {dp.planned_qty} — {dayjs(dp.planned_date).format('YYYY-MM-DD')}
              </Select.Option>
            ))}
          </Select>
        )}
        <Table
          rowKey="po_item_id"
          size="small"
          pagination={false}
          dataSource={po.items.map((i, idx) => ({ ...i, __idx: idx }))}
          columns={[
            { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
            { title: t('field.item_name'), dataIndex: 'item_name' },
             { title: t('field.qty'), dataIndex: 'qty', align: 'right', width: 90, render: (v: string) => fmtQtyNode(v) },
             { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right', width: 100, render: (v: string) => fmtQtyNode(v) },
            {
              title: t('field.qty_shipped'),
              width: 140,
              render: (_: unknown, r: PurchaseOrder['items'][number] & { __idx: number }) => (
                <InputNumber
                  min={0}
                  value={lines[r.__idx]?.qty_shipped}
                  onChange={(v) => {
                    setLines((ls) => ls.map((x, i) => i === r.__idx ? { ...x, qty_shipped: Number(v ?? 0), qty_received: Number(v ?? 0) } : x))
                  }}
                  style={{ width: '100%' }}
                />
              ),
            },
          ]}
        />
      </Space>
    </Modal>
  )
}
