import {
  CheckCircleOutlined,
  DeleteOutlined,
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

import { api, type PaymentScheduleItem, type PaymentScheduleSummary } from '@/api'
import { extractError } from '@/api/client'
import { fmtAmount } from '@/utils/format'

function StatusTag({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    planned: 'default',
    due: 'warning',
    paid: 'success',
    partially_paid: 'processing',
    cancelled: 'error',
  }
  return <Tag color={colorMap[status] || 'default'}>{status}</Tag>
}

export interface PaymentScheduleTabProps {
  contractId?: string
  poId?: string
  currency: string
  canWrite: boolean
}

export function PaymentScheduleTab({
  contractId,
  poId,
  currency,
  canWrite,
}: PaymentScheduleTabProps) {
  const { t } = useTranslation()
  const [schedule, setSchedule] = useState<PaymentScheduleSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [form] = Form.useForm()

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
      if (contractId) {
        await api.createPaymentSchedule(contractId, items)
      } else {
        await api.createPOPaymentSchedule(poId!, items)
      }
      void message.success(t('contract.schedule_saved'))
      setDrawerOpen(false)
      form.resetFields()
      void load()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const handleExecute = (item: PaymentScheduleItem) => {
    Modal.confirm({
      title: t('contract.execute_title', { name: item.label }),
      content: t('contract.confirm_execute', {
        amount: fmtAmount(item.planned_amount, currency),
      }),
      okText: t('contract.confirm_execute_ok'),
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          if (contractId) {
            await api.executeScheduleItem(contractId, item.installment_no, {
              payment_method: 'bank_transfer',
            })
          } else {
            await api.executePOScheduleItem(poId!, item.installment_no, {
              payment_method: 'bank_transfer',
            })
          }
          void message.success(t('contract.payment_executed'))
          void load()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
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
      render: (v: string) => fmtAmount(v, currency),
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
          <Tag>{v}</Tag>
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
      width: 260,
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
          {r.status === 'paid' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
        </Space>
      ),
    },
  ]

  const hasItems = Boolean(schedule && schedule.items.length > 0)

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      {schedule && hasItems && (
        <>
          <Row gutter={16}>
            <Col xs={12} md={6}>
              <Statistic
                title={t('contract.contract_total')}
                value={Number(schedule.contract_total)}
                prefix={currency}
                precision={2}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('contract.planned_total')}
                value={Number(schedule.planned_total)}
                prefix={currency}
                precision={2}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('contract.paid_total')}
                value={Number(schedule.paid_total)}
                prefix={currency}
                precision={2}
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col xs={12} md={6}>
              <Statistic
                title={t('contract.remaining')}
                value={Number(schedule.remaining)}
                prefix={currency}
                precision={2}
                valueStyle={{ color: '#8B5E3C' }}
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
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setDrawerOpen(true)}>
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

      <Drawer
        title={t('contract.new_schedule')}
        width={640}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>{t('button.cancel')}</Button>
            <Button type="primary" onClick={handleSave}>
              {t('button.save')}
            </Button>
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          message={t('contract.schedule_form_help')}
          style={{ marginBottom: 16 }}
        />
        <Form form={form} layout="vertical">
          <Form.List name="items" initialValue={[{}]}>
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Card
                    key={field.key}
                    size="small"
                    style={{ marginBottom: 12 }}
                    title={t('contract.installment_n', { n: field.name + 1 })}
                    extra={
                      fields.length > 1 && (
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={() => remove(field.name)}
                        />
                      )
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
                            prefix={currency}
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
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                  {t('contract.add_installment')}
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Drawer>
    </Space>
  )
}
