import { DownloadOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons'
import {
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import {
  api,
  type InvoiceListRow,
  type PaymentRecord,
  type POProgress,
  type PurchaseOrder,
  type Shipment,
} from '@/api'
import { extractError } from '@/api/client'
import { getToken } from '@/api/client'

function statusTag(s: string): string {
  return s
}

export function PODetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [po, setPo] = useState<PurchaseOrder | null>(null)
  const [progress, setProgress] = useState<POProgress | null>(null)
  const [shipments, setShipments] = useState<Shipment[]>([])
  const [payments, setPayments] = useState<PaymentRecord[]>([])
  const [invoices, setInvoices] = useState<InvoiceListRow[]>([])

  const [shipmentOpen, setShipmentOpen] = useState(false)
  const [paymentOpen, setPaymentOpen] = useState(false)
  const [invoiceOpen, setInvoiceOpen] = useState(false)
  const [busy, setBusy] = useState(false)

  const loadAll = async () => {
    if (!id) return
    const [po0, pr0, sh, pay, inv] = await Promise.all([
      api.getPO(id),
      api.getPOProgress(id).catch(() => null),
      api.listShipments(id).catch(() => []),
      api.listPayments(id).catch(() => []),
      api.listInvoices(id).catch(() => []),
    ])
    setPo(po0)
    setProgress(pr0)
    setShipments(sh)
    setPayments(pay)
    setInvoices(inv)
  }

  useEffect(() => {
    void loadAll()
  }, [id])

  if (!po) return <div>{t('message.loading')}</div>

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space align="center">
          <Typography.Title level={3} style={{ margin: 0 }}>
            {po.po_number}
          </Typography.Title>
          <Tag color="success">{t(`status.${statusTag(po.status)}` as 'status.confirmed')}</Tag>
        </Space>
        <Space>
          <Button
            icon={<DownloadOutlined />}
            className="no-print"
            onClick={async () => {
              const resp = await fetch(`/api/v1/purchase-orders/${po.id}/export/pdf`, {
                headers: { Authorization: `Bearer ${getToken() ?? ''}` },
              })
              if (!resp.ok) return
              const blob = await resp.blob()
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = `${po.po_number}.pdf`
              document.body.appendChild(a)
              a.click()
              a.remove()
              URL.revokeObjectURL(url)
            }}
          >
            {t('button.export_pdf')}
          </Button>
          <Button className="no-print" onClick={() => window.print()}>{t('button.print')}</Button>
          <Button onClick={() => navigate('/purchase-orders')}>{t('button.back')}</Button>
        </Space>
      </div>

      <Card>
        <Descriptions bordered size="small" column={3}>
          <Descriptions.Item label={t('field.total_amount')}>
            {po.currency} {po.total_amount}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.amount_invoiced')}>
            {po.currency} {po.amount_invoiced}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.amount_paid')}>
            {po.currency} {po.amount_paid}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.created_at')} span={3}>
            {new Date(po.created_at).toLocaleString()}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {progress && (
        <Card title={t('progress.title')}>
          <Row gutter={24}>
            <Col span={8}>
              <Statistic title={t('progress.received')} value={progress.pct_received} suffix="%" />
              <Progress percent={Math.min(100, progress.pct_received)} status="active" />
            </Col>
            <Col span={8}>
              <Statistic title={t('progress.invoiced')} value={progress.pct_invoiced} suffix="%" />
              <Progress percent={Math.min(100, progress.pct_invoiced)} status="active" strokeColor="#faad14" />
            </Col>
            <Col span={8}>
              <Statistic title={t('progress.paid')} value={progress.pct_paid} suffix="%" />
              <Progress percent={Math.min(100, progress.pct_paid)} status="active" strokeColor="#52c41a" />
            </Col>
          </Row>
        </Card>
      )}

      <Tabs
        items={[
          {
            key: 'items',
            label: `${t('nav.purchase_orders')} · ${t('field.item_name')}`,
            children: (
              <Table
                rowKey="id"
                dataSource={po.items}
                pagination={false}
                columns={[
                  { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
                  { title: t('field.item_name'), dataIndex: 'item_name' },
                  { title: t('field.qty'), dataIndex: 'qty', align: 'right', width: 90 },
                  { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right', width: 110 },
                  { title: t('field.qty_invoiced'), dataIndex: 'qty_invoiced', align: 'right', width: 110 },
                  { title: t('field.uom'), dataIndex: 'uom', width: 60 },
                  { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', width: 110 },
                  { title: t('field.amount'), dataIndex: 'amount', align: 'right', width: 110 },
                ]}
              />
            ),
          },
          {
            key: 'shipments',
            label: `${t('nav.shipments')} (${shipments.length})`,
            children: (
              <>
                <div style={{ marginBottom: 12, textAlign: 'right' }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setShipmentOpen(true)}>
                    {t('button.record_shipment')}
                  </Button>
                </div>
                <Table
                  rowKey="id"
                  dataSource={shipments}
                  pagination={false}
                  columns={[
                    { title: t('field.shipment_number'), dataIndex: 'shipment_number' },
                    { title: t('field.status'), dataIndex: 'status',
                      render: (s: string) => <Tag>{t(`status.${s}` as 'status.pending')}</Tag> },
                    { title: t('field.carrier'), dataIndex: 'carrier' },
                    { title: t('field.tracking_number'), dataIndex: 'tracking_number' },
                    { title: t('field.expected_date'), dataIndex: 'expected_date' },
                    { title: t('field.actual_date'), dataIndex: 'actual_date' },
                  ]}
                  expandable={{
                    expandedRowRender: (r) => (
                      <Table
                        rowKey="id"
                        dataSource={r.items}
                        pagination={false}
                        size="small"
                        columns={[
                          { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
                          { title: t('field.item_name'), dataIndex: 'item_name' },
                          { title: t('field.qty_shipped'), dataIndex: 'qty_shipped', align: 'right' },
                          { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right' },
                          { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right' },
                        ]}
                      />
                    ),
                  }}
                />
              </>
            ),
          },
          {
            key: 'payments',
            label: `${t('nav.payments')} (${payments.length})`,
            children: (
              <>
                <div style={{ marginBottom: 12, textAlign: 'right' }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setPaymentOpen(true)}>
                    {t('button.record_payment')}
                  </Button>
                </div>
                <Table
                  rowKey="id"
                  dataSource={payments}
                  pagination={false}
                  columns={[
                    { title: t('field.payment_number'), dataIndex: 'payment_number' },
                    { title: t('field.installment_no'), dataIndex: 'installment_no', width: 80 },
                    { title: t('field.amount'), dataIndex: 'amount', align: 'right' },
                    { title: t('field.due_date'), dataIndex: 'due_date' },
                    { title: t('field.payment_date'), dataIndex: 'payment_date' },
                    { title: t('field.status'), dataIndex: 'status',
                      render: (s: string) => <Tag color={s === 'confirmed' ? 'success' : 'default'}>{t(`status.${s}` as 'status.pending')}</Tag> },
                    {
                      title: '',
                      render: (_, r) =>
                        r.status === 'pending' ? (
                          <Button size="small" onClick={async () => {
                            try {
                              await api.confirmPayment(r.id, { payment_date: dayjs().format('YYYY-MM-DD') })
                              void message.success(t('message.save_success'))
                              void loadAll()
                            } catch (e) {
                              void message.error(extractError(e).detail)
                            }
                          }}>{t('button.mark_paid')}</Button>
                        ) : null,
                    },
                  ]}
                />
              </>
            ),
          },
          {
            key: 'invoices',
            label: `${t('nav.invoices')} (${invoices.length})`,
            children: (
              <>
                <div style={{ marginBottom: 12, textAlign: 'right' }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setInvoiceOpen(true)}>
                    {t('button.record_invoice')}
                  </Button>
                </div>
                <Table
                  rowKey="id"
                  dataSource={invoices}
                  pagination={false}
                  columns={[
                    { title: t('field.internal_number'), dataIndex: 'internal_number' },
                    { title: t('field.invoice_number'), dataIndex: 'invoice_number' },
                    { title: t('field.invoice_date'), dataIndex: 'invoice_date' },
                    { title: t('field.subtotal'), dataIndex: 'subtotal', align: 'right' },
                    { title: t('field.tax_amount'), dataIndex: 'tax_amount', align: 'right' },
                    { title: t('field.total_amount'), dataIndex: 'total_amount', align: 'right' },
                    { title: t('field.status'), dataIndex: 'status',
                      render: (s: string) => <Tag>{t(`status.${s}` as 'status.draft')}</Tag> },
                  ]}
                />
              </>
            ),
          },
        ]}
      />

      <ShipmentModal
        open={shipmentOpen}
        po={po}
        onClose={() => setShipmentOpen(false)}
        onDone={() => { setShipmentOpen(false); void loadAll() }}
        busy={busy}
        setBusy={setBusy}
      />
      <PaymentModal
        open={paymentOpen}
        po={po}
        onClose={() => setPaymentOpen(false)}
        onDone={() => { setPaymentOpen(false); void loadAll() }}
        busy={busy}
        setBusy={setBusy}
      />
      <InvoiceModal
        open={invoiceOpen}
        po={po}
        onClose={() => setInvoiceOpen(false)}
        onDone={() => { setInvoiceOpen(false); void loadAll() }}
        busy={busy}
        setBusy={setBusy}
      />
    </Space>
  )
}

interface ModalProps {
  open: boolean
  po: PurchaseOrder
  onClose: () => void
  onDone: () => void
  busy: boolean
  setBusy: (b: boolean) => void
}

function ShipmentModal({ open, po, onClose, onDone, busy, setBusy }: ModalProps) {
  const { t } = useTranslation()
  const [lines, setLines] = useState<{ po_item_id: string; qty_shipped: number; qty_received?: number }[]>(
    po.items.map((i) => ({ po_item_id: i.id, qty_shipped: Number(i.qty) - Number(i.qty_received || 0), qty_received: Number(i.qty) - Number(i.qty_received || 0) }))
  )
  const [carrier, setCarrier] = useState('')
  const [tracking, setTracking] = useState('')
  const [actualDate, setActualDate] = useState<dayjs.Dayjs | null>(dayjs())

  useEffect(() => {
    if (open) {
      setLines(po.items.map((i) => ({
        po_item_id: i.id,
        qty_shipped: Math.max(0, Number(i.qty) - Number(i.qty_received || 0)),
        qty_received: Math.max(0, Number(i.qty) - Number(i.qty_received || 0)),
      })))
    }
  }, [open, po])

  const submit = async () => {
    try {
      setBusy(true)
      await api.createShipment({
        po_id: po.id,
        items: lines.filter((l) => l.qty_shipped > 0),
        carrier: carrier || null,
        tracking_number: tracking || null,
        actual_date: actualDate ? actualDate.format('YYYY-MM-DD') : null,
      })
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
      <Space direction="vertical" style={{ width: '100%' }}>
        <Row gutter={12}>
          <Col span={8}>
            <Input placeholder={t('field.carrier')} value={carrier} onChange={(e) => setCarrier(e.target.value)} />
          </Col>
          <Col span={8}>
            <Input placeholder={t('field.tracking_number')} value={tracking} onChange={(e) => setTracking(e.target.value)} />
          </Col>
          <Col span={8}>
            <DatePicker value={actualDate} onChange={(v) => setActualDate(v)} style={{ width: '100%' }} />
          </Col>
        </Row>
        <Table
          rowKey="po_item_id"
          size="small"
          pagination={false}
          dataSource={po.items.map((i, idx) => ({ ...i, __idx: idx }))}
          columns={[
            { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
            { title: t('field.item_name'), dataIndex: 'item_name' },
            { title: t('field.qty'), dataIndex: 'qty', align: 'right', width: 90 },
            { title: t('field.qty_received'), dataIndex: 'qty_received', align: 'right', width: 100 },
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

function PaymentModal({ open, po, onClose, onDone, busy, setBusy }: ModalProps) {
  const { t } = useTranslation()
  const remaining = Math.max(0, Number(po.total_amount) - Number(po.amount_paid || 0))
  const [amount, setAmount] = useState<number>(remaining)
  const [method, setMethod] = useState('bank_transfer')
  const [dueDate, setDueDate] = useState<dayjs.Dayjs | null>(dayjs().add(30, 'day'))
  const [payDate, setPayDate] = useState<dayjs.Dayjs | null>(null)
  const [txRef, setTxRef] = useState('')

  useEffect(() => {
    if (open) {
      setAmount(Math.max(0, Number(po.total_amount) - Number(po.amount_paid || 0)))
    }
  }, [open, po])

  const submit = async () => {
    try {
      setBusy(true)
      await api.createPayment({
        po_id: po.id,
        amount,
        due_date: dueDate ? dueDate.format('YYYY-MM-DD') : null,
        payment_date: payDate ? payDate.format('YYYY-MM-DD') : null,
        payment_method: method,
        transaction_ref: txRef || null,
      })
      void message.success(t('message.payment_recorded'))
      onDone()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={t('button.record_payment')} open={open} onCancel={onClose} onOk={submit} confirmLoading={busy} width={600}>
      <Form layout="vertical">
        <Row gutter={12}>
          <Col span={12}>
            <Form.Item label={t('field.amount')} required>
              <InputNumber min={0} value={amount} onChange={(v) => setAmount(Number(v ?? 0))} style={{ width: '100%' }} />
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
      </Form>
    </Modal>
  )
}

function InvoiceModal({ open, po, onClose, onDone, busy, setBusy }: ModalProps) {
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
            `AI 来源: ${ex.raw_extract_source} · 置信度 ${(ex.confidence * 100).toFixed(0)}%`
          )
        }
      } catch (e) {
        setExtractMsg(`AI 失败: ${extractError(e).detail}`)
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
      void message.error('必须上传至少一份发票文件 / At least one invoice file required')
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
      const warns = result.validations.filter((v) => v.severity === 'warn')
      if (warns.length > 0) {
        const details = warns.map((w) => `行 ${w.line_no}: ${w.message} (超额 ${w.overage})`).join('; ')
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
      <Form layout="vertical">
        <Row gutter={12}>
          <Col span={24}>
            <Form.Item label="上传发票文件（PDF / OFD / XML / 图片）— 必需">
              <Upload
                accept=".pdf,.ofd,.xml,.jpg,.jpeg,.png,.tiff"
                beforeUpload={handleUpload}
                showUploadList={false}
                maxCount={1}
              >
                <Button icon={<UploadOutlined />} loading={extracting}>
                  选择文件自动识别 / Upload & Extract
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
