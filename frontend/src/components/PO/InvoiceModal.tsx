import { UploadOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type InvoiceExtractResult, type PurchaseOrder } from '@/api'
import { extractError } from '@/api/client'
import { AutosaveBanner, AutosaveUnavailableBanner } from '@/components/AutosaveBanner'
import { fmtAmount } from '@/utils/format'
import { useAutosave } from '@/hooks/useAutosave'

interface InvoiceModalProps {
  open: boolean
  po: PurchaseOrder
  onClose: () => void
  onDone: () => void
  busy: boolean
  setBusy: (b: boolean) => void
}

interface InvoiceLine {
  po_item_id: string | null
  line_type: 'product'
  item_name: string
  qty: number
  unit_price: number
  tax_amount: number
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
  const [ocrResult, setOcrResult] = useState<InvoiceExtractResult | null>(null)
  const [lines, setLines] = useState<InvoiceLine[]>([])
  const autosaveInvoice = useAutosave(`po-invoice-${po.id}`)
  const [autosaveDismissedInvoice, setAutosaveDismissedInvoice] = useState(false)

  useEffect(() => {
    if (open) {
      setInvoiceNumber('')
      setAttachments([])
      setExtractMsg('')
      setOcrResult(null)
      setLines([])
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

  const autoMatchLines = (ocr: InvoiceExtractResult) => {
    if (!ocr.lines || ocr.lines.length === 0) {
      setLines(po.items.map((i) => ({
        po_item_id: i.id as string | null,
        line_type: 'product' as const,
        item_name: i.item_name,
        qty: Math.max(0, Number(i.qty) - Number(i.qty_invoiced || 0)),
        unit_price: Number(i.unit_price),
        tax_amount: 0,
      })))
      return
    }

    const matched: InvoiceLine[] = ocr.lines.map((ocrLine) => {
      const bestMatch = po.items.find((pi) =>
        ocrLine.item_name && pi.item_name.includes(ocrLine.item_name.slice(0, 6))
      ) || po.items.find((pi) =>
        ocrLine.item_name && ocrLine.item_name.includes(pi.item_name.slice(0, 6))
      )
      return {
        po_item_id: bestMatch?.id ?? null,
        line_type: 'product' as const,
        item_name: ocrLine.item_name || bestMatch?.item_name || '',
        qty: Number(ocrLine.qty || 0),
        unit_price: Number(ocrLine.unit_price || 0),
        tax_amount: Number(ocrLine.tax_amount || 0),
      }
    })
    setLines(matched)
  }

  const handleUpload = async (file: File) => {
    try {
      const doc = await api.uploadDocument(file, 'invoice')
      const att = { id: doc.id, name: doc.original_filename, size: doc.file_size, content_type: doc.content_type }
      setAttachments((a) => [...a, att])
      setExtracting(true)
      setExtractMsg(t('message.ai_thinking'))
      try {
        const ex = await api.extractInvoice(doc.id)
        setOcrResult(ex)
        if (ex.error) {
          setExtractMsg(`AI: ${ex.error}`)
        } else {
          if (ex.invoice_number) setInvoiceNumber(ex.invoice_number)
          if (ex.invoice_date && /^\d{4}-\d{1,2}-\d{1,2}$/.test(ex.invoice_date)) {
            setInvoiceDate(dayjs(ex.invoice_date))
          }
          if (ex.seller_tax_id) setTaxNumber(ex.seller_tax_id)
          autoMatchLines(ex)
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
    if (lines.filter((l) => l.qty > 0).length === 0) {
      void message.error(t('invoice.no_lines'))
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

  const poItemOptions = po.items.map((i) => ({
    value: i.id,
    label: `${i.item_name} (${t('field.qty')}: ${i.qty})`,
  }))

  return (
    <Modal title={t('button.record_invoice')} open={open} onCancel={onClose} onOk={submit} confirmLoading={busy} width={1060}>
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
                <Button icon={<UploadOutlined />} loading={extracting}>{t('po.upload_extract')}</Button>
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

        {ocrResult && !ocrResult.error && (
          <Card size="small" title={t('invoice.ocr_result')} style={{ marginBottom: 16 }}>
            <Descriptions size="small" column={3} bordered>
              {ocrResult.invoice_number && (
                <Descriptions.Item label={t('field.invoice_number')}>{ocrResult.invoice_number}</Descriptions.Item>
              )}
              {ocrResult.invoice_date && (
                <Descriptions.Item label={t('field.invoice_date')}>{ocrResult.invoice_date}</Descriptions.Item>
              )}
              {ocrResult.seller_name && (
                <Descriptions.Item label={t('invoice.seller_name')}>{ocrResult.seller_name}</Descriptions.Item>
              )}
              {ocrResult.seller_tax_id && (
                <Descriptions.Item label={t('field.tax_number')}>{ocrResult.seller_tax_id}</Descriptions.Item>
              )}
              {ocrResult.subtotal && (
                <Descriptions.Item label={t('invoice.subtotal_excl_tax')}>
                  {fmtAmount(ocrResult.subtotal, ocrResult.currency)}
                </Descriptions.Item>
              )}
              {ocrResult.tax_amount && (
                <Descriptions.Item label={t('invoice.total_tax')}>
                  {fmtAmount(ocrResult.tax_amount, ocrResult.currency)}
                </Descriptions.Item>
              )}
              {ocrResult.total_amount && (
                <Descriptions.Item label={t('invoice.total_incl_tax')}>
                  <Typography.Text strong>{fmtAmount(ocrResult.total_amount, ocrResult.currency)}</Typography.Text>
                </Descriptions.Item>
              )}
            </Descriptions>
            {ocrResult.lines.length > 0 && (
              <Table
                size="small"
                pagination={false}
                rowKey={(_, i) => String(i)}
                style={{ marginTop: 8 }}
                dataSource={ocrResult.lines}
                columns={[
                  { title: t('field.item_name'), dataIndex: 'item_name', ellipsis: true },
                  { title: t('field.spec'), dataIndex: 'spec', width: 100, ellipsis: true },
                  { title: t('field.qty'), dataIndex: 'qty', width: 70, align: 'right' },
                  { title: t('field.unit_price'), dataIndex: 'unit_price', width: 100, align: 'right' },
                  { title: t('invoice.tax_rate'), dataIndex: 'tax_rate', width: 70, align: 'right' },
                  { title: t('field.tax_amount'), dataIndex: 'tax_amount', width: 100, align: 'right' },
                  { title: t('field.subtotal'), dataIndex: 'subtotal', width: 100, align: 'right' },
                ]}
              />
            )}
          </Card>
        )}

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
            <Form.Item label={t('field.due_date')} help={t('invoice.due_date_hint')}>
              <DatePicker value={dueDate} onChange={setDueDate} style={{ width: '100%' }} />
            </Form.Item>
          </Col>
          <Col span={12}>
            <Form.Item label={t('field.tax_number')}>
              <Input value={taxNumber} onChange={(e) => setTaxNumber(e.target.value)} />
            </Form.Item>
          </Col>
        </Row>

        {lines.length === 0 && !extracting && (
          <Alert
            type="info"
            showIcon
            message={t('invoice.upload_first_hint')}
            style={{ marginBottom: 16 }}
          />
        )}

        {lines.length > 0 && (
          <Card size="small" title={t('invoice.match_to_po')} style={{ marginBottom: 0 }}>
            <Table
              rowKey={(_, i) => String(i)}
              size="small"
              pagination={false}
              dataSource={lines.map((l, i) => ({ ...l, __idx: i }))}
              columns={[
                {
                  title: t('invoice.match_po_item'),
                  width: 220,
                  render: (_: unknown, r) => (
                    <Select
                      size="small"
                      allowClear
                      style={{ width: '100%' }}
                      value={lines[r.__idx]?.po_item_id}
                      onChange={(v) => setLines((ls) => ls.map((x, i) => i === r.__idx ? { ...x, po_item_id: v ?? null } : x))}
                      options={poItemOptions}
                      placeholder={t('invoice.select_po_item')}
                    />
                  ),
                },
                { title: t('field.item_name'), dataIndex: 'item_name', ellipsis: true },
                {
                  title: t('field.qty'),
                  width: 90,
                  render: (_: unknown, r) => (
                    <InputNumber
                      size="small"
                      min={0}
                      value={lines[r.__idx]?.qty}
                      onChange={(v) => setLines((ls) => ls.map((x, i) => i === r.__idx ? { ...x, qty: Number(v ?? 0) } : x))}
                      style={{ width: '100%' }}
                    />
                  ),
                },
                {
                  title: t('field.unit_price'),
                  width: 110,
                  render: (_: unknown, r) => (
                    <InputNumber
                      size="small"
                      min={0}
                      value={lines[r.__idx]?.unit_price}
                      onChange={(v) => setLines((ls) => ls.map((x, i) => i === r.__idx ? { ...x, unit_price: Number(v ?? 0) } : x))}
                      style={{ width: '100%' }}
                    />
                  ),
                },
                {
                  title: t('field.subtotal'),
                  align: 'right', width: 100,
                  render: (_: unknown, r) => fmtAmount(String(lines[r.__idx]?.qty * lines[r.__idx]?.unit_price), po.currency),
                },
                {
                  title: t('field.tax_amount'),
                  width: 110,
                  render: (_: unknown, r) => (
                    <InputNumber
                      size="small"
                      min={0}
                      value={lines[r.__idx]?.tax_amount}
                      onChange={(v) => setLines((ls) => ls.map((x, i) => i === r.__idx ? { ...x, tax_amount: Number(v ?? 0) } : x))}
                      style={{ width: '100%' }}
                    />
                  ),
                },
              ]}
            />
          </Card>
        )}
      </Form>
    </Modal>
  )
}
