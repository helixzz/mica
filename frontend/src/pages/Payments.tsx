import { DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import { Button, Input, InputNumber, Modal, Space, Table, Tag, Typography, Upload, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PaymentRecord } from '@/api'
import { extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { ExportDrawer, canExport } from '@/components/Export'
import { useTablePagination } from '@/hooks/useTablePagination'
import { fmtAmountNode } from '@/utils/format'
import { MonoId } from '@/components/ui/Mono'

export function PaymentsPage() {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const [rows, setRows] = useState<PaymentRecord[]>([])
  const [loading, setLoading] = useState(false)
  const { pagination } = useTablePagination()
  const [exportOpen, setExportOpen] = useState(false)
  const [attaching, setAttaching] = useState<PaymentRecord | null>(null)
  const [attachFile, setAttachFile] = useState<File | null>(null)
  const [attachNumber, setAttachNumber] = useState('')
  const [attachAmount, setAttachAmount] = useState<number | null>(null)
  const [attachingBusy, setAttachingBusy] = useState(false)

  const canExportData = canExport(user?.role)

  const load = () => {
    setLoading(true)
    api
      .listPayments()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const columns: ColumnsType<PaymentRecord> = [
    { title: t('field.payment_number'), dataIndex: 'payment_number', render: (v: string) => <MonoId>{v}</MonoId> },
    { title: t('field.installment_no'), dataIndex: 'installment_no' },
    { title: t('field.amount'), align: 'right', render: (_, r) => fmtAmountNode(r.amount, r.currency) },
    { title: t('field.status'), dataIndex: 'status',
      filters: [{text:'pending',value:'pending'},{text:'confirmed',value:'confirmed'},{text:'cancelled',value:'cancelled'}],
      onFilter: (value: any, record: any) => record.status === value,
      render: (s: string) => {
        const cls = s === 'confirmed' ? 'tag-state--success' : s === 'cancelled' ? 'tag-state--error' : 'tag-state--warning'
        return <span className={`tag-state ${cls}`}>{t(`status.${s}` as 'status.pending')}</span>
      } },
    { title: t('field.due_date'), dataIndex: 'due_date' },
    { title: t('field.payment_date'), dataIndex: 'payment_date' },
    { title: t('field.transaction_ref'), dataIndex: 'transaction_ref' },
    {
      title: t('pay.invoice_timing'),
      key: 'invoice_timing',
      render: (_: unknown, r: PaymentRecord) => {
        if (!r.invoice_timing) return <span className="muted">—</span>
        if (r.invoice_id) return <Tag color="success">{t('pay.invoice_settled')}</Tag>
        const days = r.invoice_due_date
          ? Math.ceil((new Date(r.invoice_due_date).getTime() - Date.now()) / 86400000)
          : null
        const overdue = days !== null && days < 0
        return (
          <>
          <Space size={4}>
            <Tag color={overdue ? 'error' : 'warning'}>{t('pay.outstanding_invoice')}</Tag>
            {days !== null && (
              <Typography.Text type={overdue ? 'danger' : 'secondary'} style={{ fontSize: 12 }}>
                {overdue
                  ? t('pay.invoice_overdue', { days: Math.abs(days) })
                  : t('pay.invoice_due_in', { days })}
              </Typography.Text>
            )}
          </Space>
          {!r.invoice_id && (
            <Button size="small" type="link" onClick={() => openAttach(r)}>
              {t('pay.attach_invoice')}
            </Button>
          )}
        </>
        )
      },
    },
  ]

  const openAttach = (payment: PaymentRecord) => {
    setAttaching(payment)
    setAttachFile(null)
    setAttachNumber('')
    setAttachAmount(Number(payment.amount))
  }

  const submitAttach = async () => {
    if (!attaching || !attachFile || !attachNumber) {
      void message.warning(t('pay.attach_required'))
      return
    }
    setAttachingBusy(true)
    try {
      // The invoice has to exist before it can be attached, and creating one
      // needs the supplier — so read it from the order the payment belongs to.
      const po = await api.getPO(attaching.po_id)
      const document = await api.uploadDocument(attachFile, 'invoice')
      const created = await api.createInvoice({
        supplier_id: po.supplier_id,
        invoice_number: attachNumber,
        invoice_date: new Date().toISOString().slice(0, 10),
        attachment_document_ids: [document.id],
        lines: [
          {
            line_type: 'note',
            item_name: t('pay.execution_line'),
            qty: 1,
            unit_price: attachAmount ?? Number(attaching.amount),
          },
        ],
      })
      await api.attachPaymentInvoice(attaching.id, created.invoice.id)
      void message.success(t('pay.invoice_attached'))
      setAttaching(null)
      await load()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setAttachingBusy(false)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('nav.payments')}</Typography.Title>
        {canExportData && (
          <Button icon={<DownloadOutlined />} onClick={() => setExportOpen(true)}>{t('button.export')}</Button>
        )}
      </div>
      <ExportDrawer
        datasetKey="payments"
        open={exportOpen}
        onClose={() => setExportOpen(false)}
      />
      <Table<PaymentRecord> rowKey="id" dataSource={rows} columns={columns} loading={loading} pagination={pagination} scroll={{ x: 'max-content' }} />
      <Modal
        title={t('pay.attach_invoice')}
        open={attaching !== null}
        onCancel={() => setAttaching(null)}
        onOk={submitAttach}
        confirmLoading={attachingBusy}
        okText={t('pay.attach_invoice')}
        cancelText={t('button.cancel')}
        destroyOnHidden
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Upload
            maxCount={1}
            accept="application/pdf,image/*"
            beforeUpload={(selected) => {
              setAttachFile(selected)
              return false
            }}
            onRemove={() => setAttachFile(null)}
          >
            <Button icon={<UploadOutlined />}>{t('pay.invoice_upload')}</Button>
          </Upload>
          <Input
            placeholder={t('field.invoice_number')}
            value={attachNumber}
            onChange={(e) => setAttachNumber(e.target.value)}
          />
          <InputNumber
            style={{ width: '100%' }}
            value={attachAmount ?? undefined}
            onChange={(value) => setAttachAmount(value === null ? null : Number(value))}
            placeholder={t('field.invoice_amount')}
          />
        </Space>
      </Modal>
    </Space>
  )
}
