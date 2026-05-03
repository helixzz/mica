import { UploadOutlined } from '@ant-design/icons'
import {
  Button,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PurchaseOrder } from '@/api'
import { extractError } from '@/api/client'
import { AutosaveBanner, AutosaveUnavailableBanner } from '@/components/AutosaveBanner'
import { useAutosave } from '@/hooks/useAutosave'

interface InvoiceModalProps {
  open: boolean
  po: PurchaseOrder
  onClose: () => void
  onDone: () => void
  busy: boolean
  setBusy: (b: boolean) => void
}

export function InvoiceModal({ open, po, onClose, onDone, busy, setBusy }: InvoiceModalProps) {
  const { t } = useTranslation()
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [invoiceDate, setInvoiceDate] = useState<dayjs.Dayjs>(dayjs())
  const [dueDate, setDueDate] = useState<dayjs.Dayjs | null>(dayjs().add(30, 'day'))
  const [taxNumber, setTaxNumber] = useState('')
  const [attachments, setAttachments] = useState<{ id: string; name: string; size: number; content_type: string }[]>([])
  const [extractMsg, setExtractMsg] = useState<string>('')
  const [extracting, setExtracting] = useState(false)
  const [lines, setLines] = useState(
    po.items.map((i) => ({
      po_item_id: i.id as string | null,
      line_type: 'product' as const,
      item_name: i.item_name,
      qty: Math.max(0, Number(i.qty) - Number(i.qty_invoiced || 0)),
      unit_price: Number(i.unit_price),
      tax_amount: 0,
    }))
  )
  const autosaveInvoice = useAutosave(`po-invoice-${po.id}`)
  const [autosaveDismissedInvoice, setAutosaveDismissedInvoice] = useState(false)

  useEffect(() => {
    if (open) {
      setInvoiceNumber('')
      setAttachments([])
      setExtractMsg('')
      setLines(po.items.map((i) => ({
        po_item_id: i.id as string | null,
        line_type: 'product' as const,
        item_name: i.item_name,
        qty: Math.max(0, Number(i.qty) - Number(i.qty_invoiced || 0)),
        unit_price: Number(i.unit_price),
        tax_amount: Number(((Number(i.qty) - Number(i.qty_invoiced || 0)) * Number(i.unit_price) * 0.13).toFixed(2)),
      })))
    }
  }, [open, po])

  useEffect(() => {
    autosaveInvoice.save({
      invoiceNumber,
      invoiceDate: invoiceDate.toISOString(),
      dueDate: dueDate?.toISOString() ?? null,
      taxNumber,
      attachments,
      lines,
    })
  })

  const handleUpload = async (file: File) => {
    try {
      const doc = await api.uploadDocument(file, 'invoice')
      const att = { id: doc.id, name: doc.original_filename, size: doc.file_size, content_type: doc.content_type }
      setAttachments((a) => [...a, att])
      setExtracting(true)
      setExtractMsg(t('message.ai_thinking'))
      try {
        const ex = await api.extractInvoice(doc.id)
        if (ex.error) {
          setExtractMsg(`AI: ${ex.error}`)
        } else {
          if (ex.invoice_number) setInvoiceNumber(ex.invoice_number)
          if (ex.invoice_date && /^\d{4}-\d{1,2}-\d{1,2}$/.test(ex.invoice_date)) {
            setInvoiceDate(dayjs(ex.invoice_date))
          }
          if (ex.seller_tax_id) setTaxNumber(ex.seller_tax_id)
          setExtractMsg(
            `${t('po.ai_source')}: ${ex.raw_extract_source} · ${t('po.confidence')} ${(ex.confidence * 100).toFixed(0)}%`
          )
        }
      } catch (e) {
        setExtractMsg(`${t('po.ai_failed')}: ${extractError(e).detail}`)
      } finally {
        setExtracting(false)
      }
    } catch (e) {
      void message.error(extractError(e).detail)
    }
    return false
  }

  const removeAttachment = (id: string) => {
    setAttachments((a) => a.filter((x) => x.id !== id))
  }

  const submit = async () => {
    if (!invoiceNumber) {
      void message.error(t('error.unexpected'))
      return
    }
    if (attachments.length === 0) {
      void message.error(t('po.invoice_file_required'))
      return
    }
    try {
      setBusy(true)
      const result = await api.createInvoice({
        supplier_id: po.supplier_id,
        invoice_number: invoiceNumber,
        invoice_date: invoiceDate.format('YYYY-MM-DD'),
        due_date: dueDate ? dueDate.format('YYYY-MM-DD') : null,
        tax_number: taxNumber || null,
        attachment_document_ids: attachments.map((a) => a.id),
        lines: lines.filter((l) => l.qty > 0),
      })
      autosaveInvoice.clear()
      const warns = result.validations.filter((v) => v.severity === 'warn')
      if (warns.length > 0) {
        const details = warns.map((w) => t('po.line_overage', { line: w.line_no, msg: w.message, overage: w.overage })).join('; ')
        void message.warning(`${t('message.invoice_recorded')} (${warns.length} warnings: ${details})`, 8)
      } else {
        void message.success(t('message.invoice_recorded'))
      }
      onDone()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={t('button.record_invoice')} open={open} onCancel={onClose} onOk={submit} confirmLoading={busy} width={960}>
      {!autosaveDismissedInvoice && autosaveInvoice.hasAutosave && autosaveInvoice.savedAt && (
        <AutosaveBanner
          savedAt={autosaveInvoice.savedAt}
          onRestore={() => {
            const v = autosaveInvoice.restore()
            if (v) {
              if (v.invoiceNumber !== undefined) setInvoiceNumber(v.invoiceNumber as string)
              if (v.invoiceDate) setInvoiceDate(dayjs(v.invoiceDate as string))
              if (v.dueDate) setDueDate(dayjs(v.dueDate as string))
              else setDueDate(null)
              if (v.taxNumber !== undefined) setTaxNumber(v.taxNumber as string)
              if (v.attachments) setAttachments(v.attachments as typeof attachments)
              if (v.lines) setLines(v.lines as typeof lines)
            }
          }}
          onDismiss={() => setAutosaveDismissedInvoice(true)}
        />
      )}
      {!autosaveInvoice.storageAvailable && <AutosaveUnavailableBanner />}
      <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
        {t('po.invoice_help')}
      </Typography.Text>
      <Form layout="vertical">
        <Row gutter={12}>
          <Col span={24}>
            <Form.Item label={t('po.upload_invoice_label')}>
              <Upload
                accept=".pdf,.ofd,.xml,.jpg,.jpeg,.png,.tiff"
                beforeUpload={handleUpload}
                showUploadList={false}
                maxCount={1}
              >
                <Button icon={<UploadOutlined />} loading={extracting}>{t('po.upload_extract')}
                </Button>
              </Upload>
              {extractMsg && (
                <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
                  {extractMsg}
                </Typography.Text>
              )}
              {attachments.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  {attachments.map((a) => (
                    <Tag key={a.id} closable onClose={() => removeAttachment(a.id)} color="blue">
                      {a.name} ({(a.size / 1024).toFixed(1)} KB)
                    </Tag>
                  ))}
                </div>
              )}
            </Form.Item>
          </Col>
        </Row>
        <Row gutter={12}>
          <Col span={8}>
            <Form.Item label={t('field.invoice_number')} required>
              <Input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} placeholder={t('placeholder.enter_invoice_number')} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label={t('field.invoice_date')} required>
              <DatePicker value={invoiceDate} onChange={(v) => v && setInvoiceDate(v)} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={8}>
            <Form.Item label={t('field.due_date')}>
              <DatePicker value={dueDate} onChange={setDueDate} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label={t('field.tax_number')}>
              <Input value={taxNumber} onChange={(e) => setTaxNumber(e.target.value)} />
            </Form.Item>
          </Col>
        </Row>
        <Table
          rowKey="po_item_id"
          size="small"
          pagination={false}
          dataSource={lines.map((l, i) => ({ ...l, __idx: i }))}
          columns={[
            { title: t('field.item_name'), dataIndex: 'item_name' },
            {
              title: t('field.qty'),
              width: 100,
              render: (_: unknown, r) => (
                <InputNumber
                  min={0}
                  value={lines[r.__idx]?.qty}
                  onChange={(v) => setLines((ls) => ls.map((x, i) => i === r.__idx ? { ...x, qty: Number(v ?? 0) } : x))}
                  style={{ width: '100%' }}
                />
              ),
            },
            {
              title: t('field.unit_price'),
              width: 120,
              render: (_: unknown, r) => (
                <InputNumber
                  min={0}
                  value={lines[r.__idx]?.unit_price}
                  onChange={(v) => setLines((ls) => ls.map((x, i) => i === r.__idx ? { ...x, unit_price: Number(v ?? 0) } : x))}
                  style={{ width: '100%' }}
                />
              ),
            },
            {
              title: t('field.subtotal'),
              align: 'right', width: 110,
              render: (_: unknown, r) => (lines[r.__idx]?.qty * lines[r.__idx]?.unit_price).toFixed(2),
            },
            {
              title: t('field.tax_amount'),
              width: 120,
              render: (_: unknown, r) => (
                <InputNumber
                  min={0}
                  value={lines[r.__idx]?.tax_amount}
                  onChange={(v) => setLines((ls) => ls.map((x, i) => i === r.__idx ? { ...x, tax_amount: Number(v ?? 0) } : x))}
                  style={{ width: '100%' }}
                />
              ),
            },
          ]}
        />
      </Form>
    </Modal>
  )
}