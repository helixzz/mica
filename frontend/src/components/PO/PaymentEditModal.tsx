import {
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Contract, type PaymentRecord, type PaymentScheduleItem } from '@/api'
import { extractError } from '@/api/client'
import { AutosaveBanner, AutosaveUnavailableBanner } from '@/components/AutosaveBanner'
import { useAutosave } from '@/hooks/useAutosave'
import { fmtAmount } from '@/utils/format'

interface PaymentEditModalProps {
  open: boolean
  payment: PaymentRecord | null
  onClose: () => void
  onSaved: () => void
}

export function PaymentEditModal({ open, payment, onClose, onSaved }: PaymentEditModalProps) {
  const { t } = useTranslation()
  const [amount, setAmount] = useState<number>(0)
  const [dueDate, setDueDate] = useState<dayjs.Dayjs | null>(null)
  const [payDate, setPayDate] = useState<dayjs.Dayjs | null>(null)
  const [method, setMethod] = useState('bank_transfer')
  const [txRef, setTxRef] = useState('')
  const [notes, setNotes] = useState('')
  const [contractId, setContractId] = useState<string | null>(null)
  const [scheduleItemId, setScheduleItemId] = useState<string | null>(null)
  const [contractOptions, setContractOptions] = useState<Contract[]>([])
  const [scheduleOptions, setScheduleOptions] = useState<PaymentScheduleItem[]>([])
  const [busy, setBusy] = useState(false)
  const autosavePaymentEdit = useAutosave(`po-payment-edit-${payment?.id}`)
  const [autosaveDismissedPaymentEdit, setAutosaveDismissedPaymentEdit] = useState(false)

  useEffect(() => {
    if (!open || !payment) return
    setAmount(Number(payment.amount))
    setDueDate(payment.due_date ? dayjs(payment.due_date) : null)
    setPayDate(payment.payment_date ? dayjs(payment.payment_date) : null)
    setMethod(payment.payment_method || 'bank_transfer')
    setTxRef(payment.transaction_ref || '')
    setNotes(payment.notes || '')
    setContractId(payment.contract_id)
    setScheduleItemId(payment.schedule_item_id)
    api
      .listContracts(payment.po_id)
      .then(setContractOptions)
      .catch(() => setContractOptions([]))
  }, [open, payment])

  useEffect(() => {
    if (!contractId) {
      setScheduleOptions([])
      return
    }
    api
      .getPaymentSchedule(contractId)
      .then((s) => {
        setScheduleOptions(
          s.items.filter(
            (i) => i.status !== 'paid' || i.id === scheduleItemId,
          ),
        )
      })
      .catch(() => setScheduleOptions([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contractId])

  useEffect(() => {
    autosavePaymentEdit.save({
      amount,
      dueDate: dueDate?.toISOString() ?? null,
      payDate: payDate?.toISOString() ?? null,
      method,
      txRef,
      notes,
      contractId,
      scheduleItemId,
    })
  })

  const submit = async () => {
    if (!payment) return
    if (!contractId) {
      void message.error(t('po.payment_contract_required'))
      return
    }
    try {
      setBusy(true)
      const patch: Record<string, unknown> = {
        amount,
        due_date: dueDate ? dueDate.format('YYYY-MM-DD') : null,
        payment_date: payDate ? payDate.format('YYYY-MM-DD') : null,
        payment_method: method,
        transaction_ref: txRef || null,
        notes: notes || null,
      }
      if (contractId !== payment.contract_id) {
        patch.contract_id = contractId
      }
      if (scheduleItemId !== payment.schedule_item_id) {
        patch.schedule_item_id = scheduleItemId
      }
      await api.updatePayment(payment.id, patch)
      autosavePaymentEdit.clear()
      void message.success(t('message.save_success'))
      onSaved()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      title={t('po.payment_edit_title', { number: payment?.payment_number ?? '' })}
      open={open}
      onCancel={onClose}
      onOk={submit}
      confirmLoading={busy}
      width={600}
    >
      {!autosaveDismissedPaymentEdit && autosavePaymentEdit.hasAutosave && autosavePaymentEdit.savedAt && (
        <AutosaveBanner
          savedAt={autosavePaymentEdit.savedAt}
          onRestore={() => {
            const v = autosavePaymentEdit.restore()
            if (v) {
              if (v.amount !== undefined) setAmount(v.amount as number)
              if (v.dueDate) setDueDate(dayjs(v.dueDate as string))
              else setDueDate(null)
              if (v.payDate) setPayDate(dayjs(v.payDate as string))
              else setPayDate(null)
              if (v.method !== undefined) setMethod(v.method as string)
              if (v.txRef !== undefined) setTxRef(v.txRef as string)
              if (v.notes !== undefined) setNotes(v.notes as string)
              if (v.contractId !== undefined) setContractId(v.contractId as string | null)
              if (v.scheduleItemId !== undefined) setScheduleItemId(v.scheduleItemId as string | null)
            }
          }}
          onDismiss={() => setAutosaveDismissedPaymentEdit(true)}
        />
      )}
      {!autosavePaymentEdit.storageAvailable && <AutosaveUnavailableBanner />}
      <Form layout="vertical">
        <Form.Item label={t('po.payment_linked_contract')} required>
          <Select
            value={contractId}
            onChange={(v) => {
              setContractId(v)
              setScheduleItemId(null)
            }}
            placeholder={
              contractOptions.length === 0
                ? t('po.payment_no_contract_body')
                : undefined
            }
            disabled={contractOptions.length === 0}
            options={contractOptions.map((c) => ({
              value: c.id,
              label: `${c.contract_number} · ${c.title}`,
            }))}
          />
        </Form.Item>
        {contractId && scheduleOptions.length > 0 && (
          <Form.Item
            label={t('po.payment_linked_schedule')}
            help={t('po.payment_linked_schedule_help')}
          >
            <Select
              allowClear
              placeholder={t('po.payment_linked_schedule_placeholder')}
              value={scheduleItemId}
              onChange={(v) => setScheduleItemId(v ?? null)}
              options={scheduleOptions.map((s) => ({
                value: s.id,
                label: `${t('contract.installment_n', { n: s.installment_no })} · ${s.label} · ${fmtAmount(s.planned_amount, payment?.currency ?? 'CNY')}${s.planned_date ? ` · ${s.planned_date}` : ''}${s.status === 'paid' ? ` · ${t('status.paid')}` : ''}`,
              }))}
            />
          </Form.Item>
        )}
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item label={t('field.amount')} required>
              <InputNumber
                min={0}
                value={amount}
                onChange={(v) => setAmount(Number(v ?? 0))}
                style={{ width: '100%' }}
              />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label={t('field.payment_method')}>
              <Select
                value={method}
                onChange={setMethod}
                options={[
                  { value: 'bank_transfer', label: 'Bank Transfer' },
                  { value: 'check', label: 'Check' },
                  { value: 'cash', label: 'Cash' },
                ]}
              />
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item label={t('field.due_date')}>
              <DatePicker value={dueDate} onChange={setDueDate} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label={t('field.payment_date')}>
              <DatePicker value={payDate} onChange={setPayDate} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
        </Row>
        <Form.Item label={t('field.transaction_ref')}>
          <Input value={txRef} onChange={(e) => setTxRef(e.target.value)} />
        </Form.Item>
        <Form.Item label={t('field.notes')}>
          <Input.TextArea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}