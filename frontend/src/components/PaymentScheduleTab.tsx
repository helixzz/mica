import {
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  FileWordOutlined,
  PlusOutlined,
  SendOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import dayjs from 'dayjs'

import { api, type PaymentScheduleItem, type PaymentScheduleSummary } from '@/api'
import { PaymentExecuteModal, type InvoiceTiming } from '@/components/PaymentExecuteModal'
import { extractError } from '@/api/client'
import { fmtAmount, fmtAmountNode, getCurrencySymbol } from '@/utils/format'

function StatusTag({ status }: { status: string }) {
  const { t } = useTranslation()
  const colorMap: Record<string, string> = {
    planned: 'default',
    due: 'warning',
    paid: 'success',
    partially_paid: 'processing',
    cancelled: 'error',
  }
  return <Tag color={colorMap[status] || 'default'}>{t(`status.${status}` as 'status.pending')}</Tag>
}

interface ScheduleTemplate {
  key: string
  labelKey: string
  rows: { labelKey: string; ratio: number; trigger: string }[]
}

// The splits the procurement team actually uses, so a schedule is one click
// instead of four typed installments. Anything else remains "custom": the form
// is never locked to a template.
const SCHEDULE_TEMPLATES: ScheduleTemplate[] = [
  {
    key: 'prepay_100',
    labelKey: 'contract.tpl_prepay_100',
    rows: [{ labelKey: 'contract.tpl_prepay', ratio: 1, trigger: 'fixed_date' }],
  },
  {
    key: 'acceptance_100',
    labelKey: 'contract.tpl_acceptance_100',
    rows: [{ labelKey: 'contract.tpl_acceptance', ratio: 1, trigger: 'acceptance' }],
  },
  {
    key: 'prepay_30_70',
    labelKey: 'contract.tpl_prepay_30_70',
    rows: [
      { labelKey: 'contract.tpl_prepay', ratio: 0.3, trigger: 'fixed_date' },
      { labelKey: 'contract.tpl_acceptance', ratio: 0.7, trigger: 'acceptance' },
    ],
  },
  {
    key: 'prepay_50_50',
    labelKey: 'contract.tpl_prepay_50_50',
    rows: [
      { labelKey: 'contract.tpl_prepay', ratio: 0.5, trigger: 'fixed_date' },
      { labelKey: 'contract.tpl_acceptance', ratio: 0.5, trigger: 'acceptance' },
    ],
  },
]

export interface PaymentScheduleTabProps {
  contractId?: string
  poId?: string
  currency: string
  canWrite: boolean
  onExecutePayment?: (item: PaymentScheduleItem) => void
}

export function PaymentScheduleTab({
  contractId,
  poId,
  currency,
  canWrite,
  onExecutePayment,
}: PaymentScheduleTabProps) {
  const { t } = useTranslation()
  const [schedule, setSchedule] = useState<PaymentScheduleSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<PaymentScheduleItem | null>(null)
  const [form] = Form.useForm()

  // What the buyer needs in front of them when deciding how to split payments:
  // how far the order has been received, and the amount a template applies to.
  const [baseAmount, setBaseAmount] = useState<number | null>(null)
  const [receiptProgress, setReceiptProgress] = useState<{
    received: number
    ordered: number
  } | null>(null)
  const [executing, setExecuting] = useState<PaymentScheduleItem | null>(null)

  useEffect(() => {
    let cancelled = false
    const loadContext = async () => {
      try {
        if (poId) {
          const po = await api.getPO(poId)
          if (cancelled) return
          setBaseAmount(Number(po.total_amount || 0))
          const ordered = (po.items || []).reduce((sum, item) => sum + Number(item.qty || 0), 0)
          setReceiptProgress({ received: Number(po.qty_received || 0), ordered })
        } else if (contractId) {
          const contract = await api.getContract(contractId)
          if (cancelled) return
          setBaseAmount(Number(contract.total_amount || 0))
        }
      } catch {
        // Context only: the form still works without it.
      }
    }
    void loadContext()
    return () => {
      cancelled = true
    }
  }, [poId, contractId])

  const applyTemplate = (template: ScheduleTemplate) => {
    form.setFieldsValue({
      items: template.rows.map((row) => ({
        label: t(row.labelKey),
        planned_amount:
          baseAmount != null ? Number((baseAmount * row.ratio).toFixed(2)) : undefined,
        trigger_type: row.trigger,
      })),
    })
  }

  if ((contractId == null) === (poId == null)) {
    throw new Error('PaymentScheduleTab requires exactly one of contractId or poId')
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = contractId
        ? await api.getPaymentSchedule(contractId)
        : await api.getPOPaymentSchedule(poId!)
      setSchedule(data)
    } catch {
      setSchedule(null)
    } finally {
      setLoading(false)
    }
  }, [contractId, poId])

  useEffect(() => {
    void load()
  }, [load])

  const handleSave = async () => {
    const values = await form.validateFields()
    const items = (values.items || []).map(
      (row: Record<string, unknown>, idx: number) => ({
        installment_no: idx + 1,
        label: row.label,
        planned_amount: row.planned_amount,
        planned_date: row.planned_date
          ? (row.planned_date as { format(fmt: string): string }).format('YYYY-MM-DD')
          : null,
        trigger_type: row.trigger_type || 'fixed_date',
        trigger_description: row.trigger_description || null,
      }),
    )
    try {
      if (editingItem) {
        const updateBody = {
          label: items[0].label as string | undefined,
          planned_amount: items[0].planned_amount as number | string | undefined,
          planned_date: items[0].planned_date as string | null,
          trigger_type: items[0].trigger_type as string,
          trigger_description: items[0].trigger_description as string | null,
        }
        if (contractId) {
          await api.updateScheduleItem(contractId, editingItem.installment_no, updateBody)
        } else {
          await api.updatePOScheduleItem(poId!, editingItem.installment_no, updateBody)
        }
        void message.success(t('contract.schedule_updated'))
      } else {
        if (contractId) {
          await api.createPaymentSchedule(contractId, items)
        } else {
          await api.createPOPaymentSchedule(poId!, items)
        }
        void message.success(t('contract.schedule_saved'))
      }
      setDrawerOpen(false)
      form.resetFields()
      setEditingItem(null)
      void load()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const handleExecute = (item: PaymentScheduleItem) => {
    if (onExecutePayment) {
      onExecutePayment(item)
      return
    }
    // The dialog collects 先票/后票 (and the invoice, when prepaid) before the
    // money moves; the backend refuses a prepaid payment without one.
    setExecuting(item)
  }

  const submitExecution = async ({
    invoice_timing,
    file,
    invoice_number,
    invoice_date,
    amount,
  }: {
    invoice_timing: InvoiceTiming
    file: File | null
    invoice_number?: string
    invoice_date?: string
    amount?: number
  }) => {
    if (!executing) return

    let invoiceId: string | undefined
    if (invoice_timing === 'prepaid' && file) {
      // A schedule can hang off an order or off a contract, and only the contract
      // carries its own supplier — resolving here covers both, which is exactly
      // what a preloaded value got wrong.
      let supplierId: string | null | undefined
      if (contractId) {
        supplierId = (await api.getContract(contractId)).supplier_id
      } else if (poId) {
        supplierId = (await api.getPO(poId)).supplier_id
      }
      if (!supplierId) {
        throw new Error(t('pay.supplier_missing'))
      }

      const document = await api.uploadDocument(file, 'invoice')
      const created = await api.createInvoice({
        supplier_id: supplierId,
        invoice_number: invoice_number ?? '',
        invoice_date: invoice_date ?? new Date().toISOString().slice(0, 10),
        attachment_document_ids: [document.id],
        lines: [
          {
            line_type: 'note',
            item_name: executing.label || t('pay.execution_line'),
            qty: 1,
            unit_price: amount ?? Number(executing.planned_amount),
          },
        ],
      })
      invoiceId = created.invoice.id
    }

    const payload = {
      payment_method: 'bank_transfer',
      invoice_timing,
      invoice_id: invoiceId,
    }
    if (contractId) {
      await api.executeScheduleItem(contractId, executing.installment_no, payload)
    } else {
      await api.executePOScheduleItem(poId!, executing.installment_no, payload)
    }
    void message.success(t('contract.payment_executed'))
    setExecuting(null)
    void load()
  }

  const handleDelete = (item: PaymentScheduleItem) => {
    Modal.confirm({
      title: t('contract.delete_title', { name: item.label }),
      content: t('contract.confirm_delete_schedule'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          if (contractId) {
            await api.deleteScheduleItem(contractId, item.installment_no)
          } else {
            await api.deletePOScheduleItem(poId!, item.installment_no)
          }
          void message.success(t('message.deleted'))
          void load()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  const handleEdit = (item: PaymentScheduleItem) => {
    setEditingItem(item)
    form.setFieldsValue({
      items: [
        {
          label: item.label,
          planned_amount: item.planned_amount,
          planned_date: item.planned_date ? dayjs(item.planned_date) : null,
          trigger_type: item.trigger_type,
          trigger_description: item.trigger_description,
        },
      ],
    })
    setDrawerOpen(true)
  }

  const handleGeneratePaymentForm = async (item: PaymentScheduleItem) => {
    const hide = message.loading(t('contract.generating_payment_form'), 0)
    try {
      const { blob, filename } = await api.generateScheduleDocument(
        item.id,
        'finance_payment_form',
      )
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      void message.success(t('contract.payment_form_generated'))
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      hide()
    }
  }

  const columns: ColumnsType<PaymentScheduleItem> = [
    { title: t('field.installment_no'), dataIndex: 'installment_no', width: 60 },
    { title: t('contract.installment_label'), dataIndex: 'label' },
    {
      title: t('field.status'),
      dataIndex: 'status',
      width: 120,
      render: (s: string) => <StatusTag status={s} />,
    },
    {
      title: t('contract.planned_amount'),
      dataIndex: 'planned_amount',
      align: 'right',
      render: (v: string) => fmtAmountNode(v, currency),
    },
    {
      title: t('contract.planned_date'),
      dataIndex: 'planned_date',
      width: 120,
    },
    {
      title: t('contract.trigger_type'),
      dataIndex: 'trigger_type',
      render: (v: string, r) => (
        <Space direction="vertical" size={0}>
          <Tag>{t(`contract.trigger_${v}` as 'contract.trigger_fixed_date')}</Tag>
          {r.trigger_description && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {r.trigger_description}
            </Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: t('field.actions'),
      key: 'actions',
      width: 320,
      render: (_, r) => (
        <Space size="small" wrap>
          <Button
            size="small"
            icon={<FileWordOutlined />}
            onClick={() => handleGeneratePaymentForm(r)}
            title={t('contract.generate_payment_form')}
          >
            {t('contract.generate_payment_form_short')}
          </Button>
          {canWrite && r.status !== 'paid' && (
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(r)}
              title={t('button.edit')}
            >
              {t('button.edit')}
            </Button>
          )}
          {canWrite && r.status !== 'paid' && (
            <Button
              size="small"
              type="primary"
              icon={<SendOutlined />}
              onClick={() => handleExecute(r)}
            >
              {t('contract.execute')}
            </Button>
          )}
          {canWrite && r.status !== 'paid' && r.status !== 'partially_paid' && (
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDelete(r)}
            />
          )}
          {r.status === 'paid' && <CheckCircleOutlined style={{ color: 'var(--color-viz-positive)' }} />}
        </Space>
      ),
    },
  ]

  const hasItems = Boolean(schedule && schedule.items.length > 0)

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {receiptProgress && receiptProgress.ordered > 0 && (
        <Alert
          type={receiptProgress.received >= receiptProgress.ordered ? 'success' : 'info'}
          showIcon
          message={t('contract.receipt_progress', {
            received: receiptProgress.received,
            ordered: receiptProgress.ordered,
          })}
        />
      )}
      {schedule && hasItems && (
        <>
           <Row gutter={16}>
            <Col xs={12} md={6}>
              <Statistic
                title={t('contract.contract_total')}
                value={Number(schedule.contract_total)}
                prefix={getCurrencySymbol(currency)}
                precision={2}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('contract.planned_total')}
                value={Number(schedule.planned_total)}
                prefix={getCurrencySymbol(currency)}
                precision={2}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('contract.paid_total')}
                value={Number(schedule.paid_total)}
                prefix={getCurrencySymbol(currency)}
                precision={2}
                valueStyle={{ color: 'var(--color-viz-positive)' }}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('contract.remaining')}
                value={Number(schedule.remaining)}
                prefix={getCurrencySymbol(currency)}
                precision={2}
                valueStyle={{ color: 'var(--color-primary-500)' }}
              />
            </Col>
          </Row>
          {schedule.total_mismatch && (
            <Alert
              type="warning"
              showIcon
              message={t('contract.mismatch_warning')}
              description={t('contract.current_total_hint', { amount: schedule.contract_total })}
            />
          )}
        </>
      )}

      <Card
        title={t('contract.schedule_details')}
        extra={
          canWrite && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingItem(null)
                form.resetFields()
                setDrawerOpen(true)
              }}
            >
              {t('contract.new_schedule')}
            </Button>
          )
        }
      >
        {hasItems ? (
          <Table
            rowKey="id"
            dataSource={schedule?.items}
            columns={columns}
            pagination={false}
            size="small"
            loading={loading}
          />
        ) : (
          <Typography.Text type="secondary">{t('contract.no_schedule_hint')}</Typography.Text>
        )}
      </Card>

      <PaymentExecuteModal
        open={executing !== null}
        item={executing}
        currency={currency}
        defaultTiming="postpaid"
        onCancel={() => setExecuting(null)}
        onSubmit={submitExecution}
      />

      <Drawer
        title={
          editingItem
            ? t('contract.edit_schedule_title', { name: editingItem.label })
            : t('contract.new_schedule')
        }
        width={640}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setEditingItem(null)
          form.resetFields()
        }}
        extra={
          <Space>
            <Button
              onClick={() => {
                setDrawerOpen(false)
                setEditingItem(null)
                form.resetFields()
              }}
            >
              {t('button.cancel')}
            </Button>
            <Button type="primary" onClick={handleSave}>
              {t('button.save')}
            </Button>
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          message={
            editingItem ? t('contract.edit_schedule_help') : t('contract.schedule_form_help')
          }
          style={{ marginBottom: 16 }}
        />
        {!editingItem && (
          <div style={{ marginBottom: 16 }}>
            <Typography.Text type="secondary">{t('contract.tpl_title')}</Typography.Text>
            <Space wrap style={{ marginTop: 8, display: 'flex' }}>
              {SCHEDULE_TEMPLATES.map((template) => (
                <Button key={template.key} size="small" onClick={() => applyTemplate(template)}>
                  {t(template.labelKey)}
                </Button>
              ))}
            </Space>
          </div>
        )}
        <Form form={form} layout="vertical">
          <Form.List name="items" initialValue={[{}]}>
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Card
                    key={field.key}
                    size="small"
                    style={{ marginBottom: 12 }}
                    title={
                      editingItem
                        ? t('contract.installment_n', { n: editingItem.installment_no })
                        : t('contract.installment_n', { n: field.name + 1 })
                    }
                    extra={
                      !editingItem && fields.length > 1 ? (
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(field.name)}
                        />
                      ) : null
                    }
                  >
                    <Row gutter={12}>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'label']}
                          label={t('contract.installment_label')}
                          rules={[{ required: true, message: t('validation.required') }]}
                        >
                          <Input placeholder={t('contract.label_placeholder')} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'planned_amount']}
                          label={t('contract.planned_amount')}
                          rules={[{ required: true, message: t('validation.required') }]}
                        >
                          <InputNumber
                            style={{ width: '100%' }}
                            min={0}
                            precision={2}
                            prefix={getCurrencySymbol(currency)}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={12}>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'planned_date']}
                          label={t('contract.planned_date')}
                        >
                          <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'trigger_type']}
                          label={t('contract.trigger_type')}
                          initialValue="fixed_date"
                        >
                          <Select
                            options={[
                              { value: 'fixed_date', label: t('contract.trigger_fixed_date') },
                              { value: 'milestone', label: t('contract.trigger_milestone') },
                              { value: 'invoice_received', label: t('contract.trigger_invoice') },
                              { value: 'acceptance', label: t('contract.trigger_acceptance') },
                            ]}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item
                      {...field}
                      name={[field.name, 'trigger_description']}
                      label={t('contract.trigger_desc')}
                    >
                      <Input placeholder={t('contract.trigger_desc_placeholder')} />
                    </Form.Item>
                  </Card>
                ))}
                {!editingItem && (
                  <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                    {t('contract.add_installment')}
                  </Button>
                )}
              </>
            )}
          </Form.List>
        </Form>
      </Drawer>
    </Space>
  )
}
