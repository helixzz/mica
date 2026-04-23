import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  PlusOutlined,
  SendOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  DatePicker,
  Modal,
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
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import {
  api,
  type Contract,
  type ContractAttachment,
  type ContractVersion,
  type PaymentScheduleItem,
  type PaymentScheduleSummary,
} from '@/api'
import { extractError } from '@/api/client'

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

export function ContractDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [contract, setContract] = useState<Contract | null>(null)
  const [attachments, setAttachments] = useState<ContractAttachment[]>([])
  const [uploading, setUploading] = useState(false)
  const [schedule, setSchedule] = useState<PaymentScheduleSummary | null>(null)
  const [scheduleLoading, setScheduleLoading] = useState(false)
  const [versions, setVersions] = useState<ContractVersion[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    if (!id) return
    const list = await api.listContracts()
    const found = list.find((c) => c.id === id)
    setContract(found || null)
    const att = await api.listContractAttachments(id)
    setAttachments(att)
  }, [id])

  const loadSchedule = useCallback(async () => {
    if (!id) return
    setScheduleLoading(true)
    try {
      const s = await api.getPaymentSchedule(id)
      setSchedule(s)
    } catch {
      setSchedule(null)
    } finally {
      setScheduleLoading(false)
    }
  }, [id])

  useEffect(() => {
    void load()
    void loadSchedule()
    if (id) void api.listContractVersions(id).then(setVersions).catch(() => setVersions([]))
  }, [load, loadSchedule, id])

  const handleUpload = async (file: File) => {
    if (!id) return false
    setUploading(true)
    try {
      const doc = await api.uploadDocument(file, 'contract')
      const res = await api.attachContractDocument(id, doc.id, true)
      if (res.ocr_chars > 0) {
        void message.success(t('contract.attachment_uploaded_ocr', { chars: res.ocr_chars }))
      } else {
        void message.success(t('contract.attachment_uploaded'))
      }
      void load()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setUploading(false)
    }
    return false
  }

  const download = async (document_id: string, filename: string) => {
    try {
      const { download_url } = await api.getDocumentDownloadUrl(document_id)
      const a = document.createElement('a')
      a.href = download_url
      a.download = filename
      a.target = '_blank'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const handleAddSchedule = async (values: {
    items: { label: string; planned_amount: number; planned_date: dayjs.Dayjs | null; trigger_type: string; trigger_description?: string }[]
  }) => {
    if (!id) return
    try {
      const items = values.items.map((item, idx) => ({
        installment_no: idx + 1,
        label: item.label,
        planned_amount: item.planned_amount,
        planned_date: item.planned_date?.format('YYYY-MM-DD') ?? null,
        trigger_type: item.trigger_type || 'fixed_date',
        trigger_description: item.trigger_description,
      }))
      await api.createPaymentSchedule(id, items)
      void message.success(t('contract.schedule_saved'))
      setDrawerOpen(false)
      form.resetFields()
      void loadSchedule()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const handleExecute = (item: PaymentScheduleItem) => {
    if (!id) return
    Modal.confirm({
      title: t('contract.execute_title', { name: item.label }),
      content: t('contract.confirm_execute', { amount: item.planned_amount }),
      okText: t('contract.confirm_execute_ok'),
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.executeScheduleItem(id, item.installment_no, {
            payment_method: 'bank_transfer',
          })
          void message.success(t('contract.payment_executed'))
          void loadSchedule()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  const handleDelete = (item: PaymentScheduleItem) => {
    if (!id) return
    Modal.confirm({
      title: t('contract.delete_title', { name: item.label }),
      content: t('contract.confirm_delete_schedule'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteScheduleItem(id, item.installment_no)
          void message.success(t('message.deleted'))
          void loadSchedule()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  if (!contract) return <div>{t('message.loading')}</div>

  const scheduleColumns: ColumnsType<PaymentScheduleItem> = [
    { title: t('field.installment_no'), dataIndex: 'installment_no', width: 60 },
    { title: t('contract.installment_label'), dataIndex: 'label' },
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
  ]

  const tabItems: { key: string; label: React.ReactNode; children: React.ReactNode }[] = [
    {
      key: 'info',
      label: t('contract.basic_info'),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <Card>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label={t('field.title')}>{contract.title}</Descriptions.Item>
              <Descriptions.Item label={t('field.total_amount')}>
                {contract.currency} {contract.total_amount}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.signed_date')}>
                {contract.signed_date || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.effective_date')}>
                {contract.effective_date || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.expiry_date')}>
                {contract.expiry_date || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('contract.version')}>v{contract.current_version}</Descriptions.Item>
              {contract.notes && (
                <Descriptions.Item label={t('field.notes')} span={2}>
                  {contract.notes}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          <Card
            title={t('contract.scan_archive')}
            extra={
              <Upload
                accept=".pdf,.ofd,.xml,.jpg,.jpeg,.png,.tiff"
                beforeUpload={handleUpload}
                showUploadList={false}
                maxCount={1}
              >
                <Button type="primary" icon={<UploadOutlined />} loading={uploading}>{t('contract.upload_scan')}
                </Button>
              </Upload>
            }
          >
            {attachments.length > 0 ? (
              <Row gutter={[12, 12]}>
                {attachments.map((a) => (
                  <Col key={a.document_id} xs={24} md={12} lg={8}>
                    <Card size="small" type="inner">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Typography.Text strong>{a.original_filename}</Typography.Text>
                        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                          {a.content_type} · {(a.file_size / 1024).toFixed(1)} KB
                        </Typography.Text>
                        <Space>
                          <Tag color={a.has_ocr ? 'success' : 'default'}>
                            OCR {a.has_ocr ? `${a.ocr_chars} chars` : '-'}
                          </Tag>
                          <Tag>{a.role}</Tag>
                        </Space>
                        <Button
                          size="small"
                          icon={<DownloadOutlined />}
                          onClick={() => download(a.document_id, a.original_filename)}
                          block
                        >{t('common.download')}
                        </Button>
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            ) : (
              <Typography.Text type="secondary">
                {t('contract.upload_hint')}
              </Typography.Text>
            )}
          </Card>
        </Space>
      ),
    },
    {
      key: 'schedule',
      label: (
        <Space>
          <ClockCircleOutlined />{t('contract.payment_schedule')}
          {schedule && schedule.items.length > 0 && (
            <Tag>{t('contract.installments_count', { count: schedule.items.length })}</Tag>
          )}
        </Space>
      ),
      children: (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {schedule && schedule.items.length > 0 && (
            <>
              <Row gutter={16}>
                <Col span={6}>
                  <Statistic
                    title={t('contract.contract_total')}
                    value={Number(schedule.contract_total)}
                    prefix="¥"
                    precision={2}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title={t('contract.planned_total')}
                    value={Number(schedule.planned_total)}
                    prefix="¥"
                    precision={2}
                    valueStyle={schedule.total_mismatch ? { color: '#faad14' } : undefined}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title={t('contract.paid_total')}
                    value={Number(schedule.paid_total)}
                    prefix="¥"
                    precision={2}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title={t('contract.remaining')}
                    value={Number(schedule.remaining)}
                    prefix="¥"
                    precision={2}
                  />
                </Col>
              </Row>
              {schedule.total_mismatch && (
                <Alert
                  type="warning"
                  message={t('contract.mismatch_warning')}
                  description={`${t('contract.contract_total')} ¥${Number(schedule.contract_total).toLocaleString()} / ${t('contract.planned_total')} ¥${Number(schedule.planned_total).toLocaleString()}`}
                  showIcon
                />
              )}
            </>
          )}

          <Card
            title={t('contract.schedule_details')}
            extra={
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => {
                  form.setFieldsValue({
                    items: [{ label: '', planned_amount: 0, trigger_type: 'fixed_date' }],
                  })
                  setDrawerOpen(true)
                }}
              >{t('contract.new_schedule')}
              </Button>
            }
          >
            <Table
              dataSource={schedule?.items || []}
              columns={scheduleColumns}
              rowKey="id"
              loading={scheduleLoading}
              pagination={false}
              size="small"
              locale={{ emptyText: t('contract.no_schedule_hint') }}
            />
          </Card>
        </Space>
      ),
    },
    {
      key: 'versions',
      label: (
        <Space>
          {t('contract.version_history')}
          {versions.length > 0 && <Tag>{versions.length}</Tag>}
        </Space>
      ),
      children: (
        <Table<ContractVersion>
          rowKey="id"
          dataSource={versions}
          pagination={false}
          size="small"
          locale={{ emptyText: t('contract.no_versions_hint') }}
          columns={[
            { title: t('contract.version_col'), dataIndex: 'version_number', width: 80, render: (v: number) => `v${v}` },
            { title: t('contract.change_type_col'), dataIndex: 'change_type', width: 120, render: (v: string) => <Tag>{v}</Tag> },
            { title: t('field.title'), render: (_: unknown, r: ContractVersion) => (r.snapshot_json as Record<string, unknown>)?.title as string || '-' },
            { title: t('field.total_amount'), render: (_: unknown, r: ContractVersion) => (r.snapshot_json as Record<string, unknown>)?.total_amount as string || '-', align: 'right' as const },
            { title: t('contract.change_reason_col'), dataIndex: 'change_reason', render: (v: string | null) => v || '-' },
            { title: t('field.created_at'), dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleString() },
          ]}
        />
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space align="center">
          <Typography.Title level={3} style={{ margin: 0 }}>
            {contract.contract_number}
          </Typography.Title>
          <Tag>{t(`status.${contract.status}` as 'status.active')}</Tag>
        </Space>
        <Button onClick={() => navigate('/contracts')}>{t('button.back')}</Button>
      </div>

      <Tabs items={tabItems} defaultActiveKey="info" />

      <Drawer
        title={t('contract.new_schedule')}
        width={640}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setDrawerOpen(false)}>{t('button.cancel')}</Button>
            <Button type="primary" onClick={() => form.submit()}>{t('button.save')}
            </Button>
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={t('contract.plan_amount_hint')}
          description={t('contract.current_total_hint', { amount: Number(contract.total_amount).toLocaleString() })}
        />
        <Form form={form} onFinish={handleAddSchedule} layout="vertical">
          <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            {t('contract.schedule_form_help')}
          </Typography.Text>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field, idx) => (
                  <Card
                    key={field.key}
                    size="small"
                    title={t('contract.installment_n', { n: idx + 1 })}
                    extra={
                      fields.length > 1 && (
                        <Button size="small" danger onClick={() => remove(field.name)}>{t('button.delete')}
                        </Button>
                      )
                    }
                    style={{ marginBottom: 12 }}
                  >
                    <Row gutter={12}>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'label']}
                          label={t('contract.installment_label')}
                          help={t('contract.installment_label_help')}
                          rules={[{ required: true }]}
                        >
                          <Input placeholder={t('contract.label_placeholder')} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'planned_amount']}
                          label={t('contract.planned_amount')}
                          help={t('contract.planned_amount_help')}
                          rules={[{ required: true }]}
                        >
                          <InputNumber
                            style={{ width: '100%' }}
                            min={0}
                            precision={2}
                            prefix="¥"
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
                          help={t('contract.planned_date_help')}
                        >
                          <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'trigger_type']}
                          label={t('contract.trigger_type')}
                          help={t('contract.trigger_type_help')}
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
                      help={t('contract.trigger_desc_help')}
                    >
                      <Input placeholder={t('contract.trigger_desc_placeholder')} />
                    </Form.Item>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>{t('contract.add_installment')}
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Drawer>
    </Space>
  )
}
