import {
  Alert,
  Button,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Typography,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Contract, type PaymentScheduleItem, type PurchaseOrder } from '@/api'
import { extractError } from '@/api/client'
import { AutosaveBanner, AutosaveUnavailableBanner } from '@/components/AutosaveBanner'
import { ContractFormModal } from '@/components/ContractFormModal'
import { useAutosave } from '@/hooks/useAutosave'
import { fmtAmount } from '@/utils/format'

interface PaymentModalProps {
  open: boolean
  po: PurchaseOrder
  onClose: () => void
  onDone: () => void
  busy: boolean
  setBusy: (b: boolean) => void
}

export function PaymentModal({ open, po, onClose, onDone, busy, setBusy }: PaymentModalProps) {
  const { t } = useTranslation()
  const remaining = Math.max(0, Number(po.total_amount) - Number(po.amount_paid || 0))
  const [amount, setAmount] = useState<number>(remaining)
  const [method, setMethod] = useState('bank_transfer')
  const [dueDate, setDueDate] = useState<dayjs.Dayjs | null>(dayjs().add(30, 'day'))
  const [payDate, setPayDate] = useState<dayjs.Dayjs | null>(null)
  const [txRef, setTxRef] = useState('')
  const [contractOptions, setContractOptions] = useState<Contract[]>([])
  const [contractId, setContractId] = useState<string | null>(null)
  const [scheduleOptions, setScheduleOptions] = useState<PaymentScheduleItem[]>([])
  const [scheduleItemId, setScheduleItemId] = useState<string | null>(null)
  const [contractFormOpen, setContractFormOpen] = useState(false)
  const autosavePayment = useAutosave(`po-payment-${po.id}`)
  const [autosaveDismissedPayment, setAutosaveDismissedPayment] = useState(false)

  const loadContracts = async () => {
    try {
      const list = await api.listContracts(po.id)
      setContractOptions(list)
      if (list.length === 1) {
        setContractId(list[0].id)
      } else if (list.length > 1 && contractId === null) {
        const active = list.find((c) => c.status === 'active')
        setContractId((active ?? list[0]).id)
      } else if (list.length === 0) {
        setContractId(null)
      }
    } catch {
      setContractOptions([])
    }
  }

  useEffect(() => {
    if (!open) return
    setAmount(Math.max(0, Number(po.total_amount) - Number(po.amount_paid || 0)))
    setScheduleItemId(null)
    void loadContracts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, po.id])

  useEffect(() => {
    if (!contractId) {
      setScheduleOptions([])
      return
    }
    api
      .getPaymentSchedule(contractId)
      .then((s) => setScheduleOptions(s.items.filter((i) => i.status !== 'paid')))
      .catch(() => setScheduleOptions([]))
  }, [contractId])

  useEffect(() => {
    autosavePayment.save({
      amount,
      method,
      dueDate: dueDate?.toISOString() ?? null,
      payDate: payDate?.toISOString() ?? null,
      txRef,
      contractId,
      scheduleItemId,
    })
  })

  const submit = async () => {
    if (!contractId) {
      void message.error(t('po.payment_contract_required'))
      return
    }
    try {
      setBusy(true)
      await api.createPayment({
        po_id: po.id,
        contract_id: contractId,
        schedule_item_id: scheduleItemId,
        amount,
        due_date: dueDate ? dueDate.format('YYYY-MM-DD') : null,
        payment_date: payDate ? payDate.format('YYYY-MM-DD') : null,
        payment_method: method,
        transaction_ref: txRef || null,
      })
      autosavePayment.clear()
      void message.success(t('message.payment_recorded'))
      onDone()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  const noContractsYet = contractOptions.length === 0

  return (
    <>
      <Modal
        title={t('button.record_payment')}
        open={open}
        onCancel={onClose}
        onOk={submit}
        confirmLoading={busy}
        okButtonProps={{ disabled: noContractsYet || !contractId }}
        width={600}
      >
        {!autosaveDismissedPayment && autosavePayment.hasAutosave && autosavePayment.savedAt && (
          <AutosaveBanner
            savedAt={autosavePayment.savedAt}
            onRestore={() => {
              const v = autosavePayment.restore()
              if (v) {
                if (v.amount !== undefined) setAmount(v.amount as number)
                if (v.method !== undefined) setMethod(v.method as string)
                if (v.dueDate) setDueDate(dayjs(v.dueDate as string))
                else setDueDate(null)
                if (v.payDate) setPayDate(dayjs(v.payDate as string))
                else setPayDate(null)
                if (v.txRef !== undefined) setTxRef(v.txRef as string)
                if (v.contractId !== undefined) setContractId(v.contractId as string | null)
                if (v.scheduleItemId !== undefined) setScheduleItemId(v.scheduleItemId as string | null)
              }
            }}
            onDismiss={() => setAutosaveDismissedPayment(true)}
          />
        )}
        {!autosavePayment.storageAvailable && <AutosaveUnavailableBanner />}
        <Form layout="vertical">
          <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            {t('po.payment_help')}
          </Typography.Text>

          {noContractsYet ? (
            <Alert
              type="warning"
              showIcon
              message={t('po.payment_no_contract_title')}
              description={t('po.payment_no_contract_body')}
              action={
                <Button
                  size="small"
                  type="primary"
                  onClick={() => setContractFormOpen(true)}
                >
                  {t('contract.create_btn')}
                </Button>
              }
              style={{ marginBottom: 16 }}
            />
          ) : (
            <Form.Item label={t('po.payment_linked_contract')} required>
              <Select
                value={contractId}
                onChange={(v) => setContractId(v)}
                options={contractOptions.map((c) => ({
                  value: c.id,
                  label: `${c.contract_number} · ${c.title}`,
                }))}
              />
            </Form.Item>
          )}

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
                  label: `${t('contract.installment_n', { n: s.installment_no })} · ${s.label} · ${fmtAmount(s.planned_amount, po.currency)}${s.planned_date ? ` · ${s.planned_date}` : ''}`,
                }))}
              />
            </Form.Item>
          )}

          <Row gutter={12}>
            <Col span={12}>
              <Form.Item label={t('field.amount')} help={t('po.payment_amount_help')} required>
                <InputNumber min={0} value={amount} onChange={(v) => setAmount(Number(v ?? 0))} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label={t('field.payment_method')} help={t('po.payment_method_help')}>
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
              <Form.Item label={t('field.due_date')} help={t('po.payment_due_date_help')}>
                <DatePicker value={dueDate} onChange={setDueDate} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label={t('field.payment_date')} help={t('po.payment_date_help')}>
                <DatePicker value={payDate} onChange={setPayDate} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label={t('field.transaction_ref')} help={t('po.payment_ref_help')}>
            <Input value={txRef} onChange={(e) => setTxRef(e.target.value)} />
          </Form.Item>
        </Form>
      </Modal>

      <ContractFormModal
        open={contractFormOpen}
        mode="create"
        poId={po.id}
        onClose={() => setContractFormOpen(false)}
        onSaved={(saved) => {
          setContractFormOpen(false)
          setContractOptions((list) => [...list, saved])
          setContractId(saved.id)
        }}
      />
    </>
  )
}