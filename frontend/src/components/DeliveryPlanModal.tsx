import { Checkbox, DatePicker, Form, Input, InputNumber, Modal, Radio, Select, message } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, Contract, DeliveryPlan, PurchaseOrderListItem } from '@/api'

interface DeliveryPlanModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  plan?: DeliveryPlan
  poId?: string
  contractId?: string
}

export function DeliveryPlanModal({
  open,
  onClose,
  onSuccess,
  plan,
  poId,
  contractId,
}: DeliveryPlanModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [type, setType] = useState<'po' | 'contract'>(poId ? 'po' : contractId ? 'contract' : 'po')
  const [pos, setPos] = useState<PurchaseOrderListItem[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [items, setItems] = useState<{ id: string; name: string; remaining: number }[]>([])
  const [bulkMode, setBulkMode] = useState(false)

  useEffect(() => {
    if (open) {
      if (plan) {
        setType(plan.po_id ? 'po' : 'contract')
        setBulkMode(false)
        form.setFieldsValue({
          type: plan.po_id ? 'po' : 'contract',
          po_id: plan.po_id,
          contract_id: plan.contract_id,
          item_id: plan.item_id,
          plan_name: plan.plan_name,
          planned_qty: plan.planned_qty,
          planned_date: dayjs(plan.planned_date),
          notes: plan.notes,
        })
        if (plan.po_id) loadPOItems(plan.po_id)
        if (plan.contract_id) loadContractItems(plan.contract_id)
      } else {
        setType(poId ? 'po' : contractId ? 'contract' : 'po')
        setBulkMode(false)
        form.setFieldsValue({
          type: poId ? 'po' : contractId ? 'contract' : 'po',
          po_id: poId,
          contract_id: contractId,
        })
        if (poId) loadPOItems(poId)
        if (contractId) loadContractItems(contractId)
      }
      loadPOs()
      loadContracts()
    } else {
      form.resetFields()
      setItems([])
      setBulkMode(false)
    }
  }, [open, plan, poId, contractId, form])

  const loadPOs = async () => {
    try {
      const data = await api.listPOs()
      setPos(data)
    } catch (err) {
      console.error(err)
    }
  }

  const loadContracts = async () => {
    try {
      const data = await api.listContracts()
      setContracts(data)
    } catch (err) {
      console.error(err)
    }
  }

  const loadPOItems = async (id: string) => {
    try {
      const po = await api.getPO(id)
      setItems(
        po.items.map((i) => ({
          id: i.id,
          name: i.item_name,
          remaining: Number(i.qty) - Number(i.qty_received),
        }))
      )
    } catch (err) {
      console.error(err)
    }
  }

  const loadContractItems = async (id: string) => {
    try {
      const linkedPos = await api.listLinkedPos(id)
      if (linkedPos.length > 0) {
        loadPOItems(linkedPos[0].id)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const handleTypeChange = (e: any) => {
    setType(e.target.value)
    form.setFieldsValue({ po_id: undefined, contract_id: undefined, item_id: undefined })
    setItems([])
  }

  const handlePOChange = (val: string) => {
    form.setFieldsValue({ item_id: undefined })
    loadPOItems(val)
  }

  const handleContractChange = (val: string) => {
    form.setFieldsValue({ item_id: undefined })
    loadContractItems(val)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)

      if (plan) {
        const payload = {
          po_id: values.type === 'po' ? values.po_id : undefined,
          contract_id: values.type === 'contract' ? values.contract_id : undefined,
          item_id: values.item_id,
          plan_name: values.plan_name,
          planned_qty: values.planned_qty,
          planned_date: values.planned_date.format('YYYY-MM-DD'),
          notes: values.notes,
        }
        await api.updateDeliveryPlan(plan.id, payload)
        message.success(t('common.saved'))
        onSuccess()
        onClose()
      } else if (bulkMode && values.batch_count > 1) {
        const batchCount = values.batch_count
        const totalQty = values.planned_qty
        const qtyPerBatch = Math.floor(totalQty / batchCount)
        const remainder = totalQty - qtyPerBatch * batchCount

        const dateRange = values.date_range as [dayjs.Dayjs, dayjs.Dayjs]
        const startDate = dateRange[0]
        const endDate = dateRange[1]
        const intervalMs = (endDate.valueOf() - startDate.valueOf()) / (batchCount - 1 || 1)

        const basePayload = {
          po_id: values.type === 'po' ? values.po_id : undefined,
          contract_id: values.type === 'contract' ? values.contract_id : undefined,
          item_id: values.item_id,
          notes: values.notes,
        }

        let created = 0
        for (let i = 0; i < batchCount; i++) {
          const batchQty = i === batchCount - 1 ? qtyPerBatch + remainder : qtyPerBatch
          const batchDate = dayjs(startDate.valueOf() + intervalMs * i).format('YYYY-MM-DD')
          await api.createDeliveryPlan({
            ...basePayload,
            plan_name: `${values.plan_name} #${i + 1}`,
            planned_qty: batchQty,
            planned_date: batchDate,
          })
          created++
        }
        message.success(t('delivery_plan.bulk_created', { count: created }))
        onSuccess()
        onClose()
      } else {
        const payload = {
          po_id: values.type === 'po' ? values.po_id : undefined,
          contract_id: values.type === 'contract' ? values.contract_id : undefined,
          item_id: values.item_id,
          plan_name: values.plan_name,
          planned_qty: values.planned_qty,
          planned_date: values.planned_date.format('YYYY-MM-DD'),
          notes: values.notes,
        }
        await api.createDeliveryPlan(payload)
        message.success(t('common.created'))
        onSuccess()
        onClose()
      }
    } catch (err: any) {
      if (err.errorFields) return
      message.error(err.response?.data?.detail || err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={plan ? t('delivery_plan.edit_plan') : t('delivery_plan.new_plan')}
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={submitting}
      destroyOnClose
      width={520}
    >
      <Form form={form} layout="vertical">
        <Form.Item name="type" label={t('delivery_plan.type')}>
          <Radio.Group onChange={handleTypeChange} disabled={!!poId || !!contractId || !!plan}>
            <Radio value="po">{t('nav.purchase_orders')}</Radio>
            <Radio value="contract">{t('nav.contracts')}</Radio>
          </Radio.Group>
        </Form.Item>

        {type === 'po' && (
          <Form.Item
            name="po_id"
            label={t('nav.purchase_orders')}
            rules={[{ required: true, message: t('common.required') }]}
          >
            <Select
              showSearch
              optionFilterProp="children"
              onChange={handlePOChange}
              disabled={!!poId || !!plan}
            >
              {pos.map((p) => (
                <Select.Option key={p.id} value={p.id}>
                  {p.po_number}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        )}

        {type === 'contract' && (
          <Form.Item
            name="contract_id"
            label={t('nav.contracts')}
            rules={[{ required: true, message: t('common.required') }]}
          >
            <Select
              showSearch
              optionFilterProp="children"
              onChange={handleContractChange}
              disabled={!!contractId || !!plan}
            >
              {contracts.map((c) => (
                <Select.Option key={c.id} value={c.id}>
                  {c.contract_number} - {c.title}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        )}

        <Form.Item
          name="item_id"
          label={t('nav.items')}
          rules={[{ required: true, message: t('common.required') }]}
        >
          <Select showSearch optionFilterProp="children" disabled={!!plan}>
            {items.map((i) => (
              <Select.Option key={i.id} value={i.id}>
                {i.name} (Remaining: {i.remaining})
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="plan_name"
          label={t('delivery_plan.plan_name')}
          rules={[{ required: true, message: t('common.required') }]}
        >
          <Input />
        </Form.Item>

        <Form.Item
          name="planned_qty"
          label={t('delivery_plan.planned_qty')}
          rules={[{ required: true, message: t('common.required') }]}
        >
          <InputNumber min={1} style={{ width: '100%' }} />
        </Form.Item>

        {!plan && (
          <Form.Item name="bulk_mode" valuePropName="checked">
            <Checkbox onChange={(e) => setBulkMode(e.target.checked)}>
              {t('delivery_plan.bulk_create')}
            </Checkbox>
          </Form.Item>
        )}

        {bulkMode && !plan ? (
          <>
            <Form.Item
              name="batch_count"
              label={t('delivery_plan.batch_count')}
              rules={[{ required: true, message: t('common.required') }]}
              initialValue={2}
              extra={t('delivery_plan.bulk_create_hint')}
            >
              <InputNumber min={2} max={100} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="date_range"
              label={t('delivery_plan.planned_date')}
              rules={[{ required: true, message: t('common.required') }]}
            >
              <DatePicker.RangePicker style={{ width: '100%' }} />
            </Form.Item>
          </>
        ) : (
          <Form.Item
            name="planned_date"
            label={t('delivery_plan.planned_date')}
            rules={[{ required: true, message: t('common.required') }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        )}

        <Form.Item name="notes" label={t('delivery_plan.notes')}>
          <Input.TextArea rows={3} />
        </Form.Item>
      </Form>
    </Modal>
  )
}