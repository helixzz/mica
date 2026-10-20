import { Alert, DatePicker, Form, Input, InputNumber, Modal, Radio, Space, Typography, Upload, message } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PaymentScheduleItem } from '@/api'
import { extractError } from '@/api/client'
import { fmtAmount } from '@/utils/format'

export type InvoiceTiming = 'prepaid' | 'postpaid'

interface Props {
  open: boolean
  item: PaymentScheduleItem | null
  currency: string
  supplierId?: string | null
  /** The supplier's usual arrangement; the default the buyer can override. */
  defaultTiming: InvoiceTiming
  onCancel: () => void
  onSubmit: (payload: { invoice_timing: InvoiceTiming; invoice_id: string | null }) => Promise<void>
}

/**
 * Confirm a payment and settle "invoice first or invoice later" at the same time.
 *
 * 先票 requires the invoice here: the file is uploaded, an invoice record is
 * created from it (so it shows up on the invoice page like any other) and only
 * then does the payment go through. 后票 records the intent and leaves the
 * invoice owed — the deadline comes from the backend.
 */
export function PaymentExecuteModal({
  open,
  item,
  currency,
  supplierId,
  defaultTiming,
  onCancel,
  onSubmit,
}: Props) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [timing, setTiming] = useState<InvoiceTiming>(defaultTiming)
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    setTiming(defaultTiming)
    setFile(null)
    form.setFieldsValue({
      invoice_number: '',
      amount: item ? Number(item.planned_amount) : 0,
      invoice_date: dayjs(),
    })
  }, [open, defaultTiming, item, form])

  const submit = async () => {
    if (timing === 'prepaid') {
      if (!file) {
        void message.warning(t('pay.invoice_file_required'))
        return
      }
      if (!supplierId) {
        void message.error(t('pay.supplier_missing'))
        return
      }
    }
    const values = await form.validateFields()
    setSubmitting(true)
    try {
      let invoiceId: string | null = null
      if (timing === 'prepaid' && file) {
        const document = await api.uploadDocument(file, 'invoice')
        const created = await api.createInvoice({
          supplier_id: supplierId!,
          invoice_number: values.invoice_number,
          invoice_date: (values.invoice_date as dayjs.Dayjs).format('YYYY-MM-DD'),
          attachment_document_ids: [document.id],
          lines: [
            {
              line_type: 'note',
              item_name: item ? item.label : t('pay.execution_line'),
              qty: 1,
              unit_price: Number(values.amount ?? item?.planned_amount ?? 0),
            },
          ],
        })
        invoiceId = created.invoice.id
      }
      await onSubmit({ invoice_timing: timing, invoice_id: invoiceId })
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      title={t('pay.execute_title', { name: item?.label ?? '' })}
      open={open}
      onCancel={onCancel}
      onOk={submit}
      confirmLoading={submitting}
      okText={t('pay.execute_ok')}
      cancelText={t('button.cancel')}
      width={560}
      destroyOnClose
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Typography.Text type="secondary">
          {t('pay.execute_amount', {
            amount: fmtAmount(item?.planned_amount ?? 0, currency),
          })}
        </Typography.Text>

        <Form form={form} layout="vertical">
          <Form.Item label={t('pay.invoice_timing')} required>
            <Radio.Group
              value={timing}
              onChange={(event) => setTiming(event.target.value as InvoiceTiming)}
            >
              <Radio.Button value="prepaid">{t('pay.timing_prepaid')}</Radio.Button>
              <Radio.Button value="postpaid">{t('pay.timing_postpaid')}</Radio.Button>
            </Radio.Group>
          </Form.Item>

          {timing === 'prepaid' ? (
            <>
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
                message={t('pay.prepaid_help')}
              />
              <Form.Item label={t('pay.invoice_file')} required>
                <Upload
                  maxCount={1}
                  beforeUpload={(selected) => {
                    setFile(selected)
                    return false
                  }}
                  onRemove={() => setFile(null)}
                  accept="application/pdf,image/*"
                >
                  <Typography.Link>
                    <InboxOutlined /> {t('pay.invoice_upload')}
                  </Typography.Link>
                </Upload>
              </Form.Item>
              <Form.Item
                name="invoice_number"
                label={t('field.invoice_number')}
                rules={[{ required: true, message: t('error.required') }]}
              >
                <Input />
              </Form.Item>
              <Space size="middle" style={{ display: 'flex' }}>
                <Form.Item
                  name="amount"
                  label={t('field.invoice_amount')}
                  rules={[{ required: true, message: t('error.required') }]}
                  style={{ flex: 1 }}
                >
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item
                  name="invoice_date"
                  label={t('field.invoice_date')}
                  rules={[{ required: true, message: t('error.required') }]}
                  style={{ flex: 1 }}
                >
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Space>
            </>
          ) : (
            <Alert type="warning" showIcon message={t('pay.postpaid_help')} />
          )}
        </Form>
      </Space>
    </Modal>
  )
}
