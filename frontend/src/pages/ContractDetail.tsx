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
  }, [load, loadSchedule])

  const handleUpload = async (file: File) => {
    if (!id) return false
    setUploading(true)
    try {
      const doc = await api.uploadDocument(file, 'contract')
      const res = await api.attachContractDocument(id, doc.id, true)
      if (res.ocr_chars > 0) {
        void message.success(`附件已上传 · OCR 提取 ${res.ocr_chars} 字符`)
      } else {
        void message.success('附件已上传（无 OCR 文本）')
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
      void message.success('付款计划已保存')
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
      title: `执行付款: ${item.label}`,
      content: `确认支付 ¥${item.planned_amount}？`,
      okText: '确认执行',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.executeScheduleItem(id, item.installment_no, {
            payment_method: 'bank_transfer',
          })
          void message.success('付款已执行')
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
      title: `删除计划: ${item.label}`,
      content: '确认删除该期付款计划？',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await api.deleteScheduleItem(id, item.installment_no)
          void message.success('已删除')
          void loadSchedule()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  if (!contract) return <div>{t('message.loading')}</div>

  const scheduleColumns: ColumnsType<PaymentScheduleItem> = [
    { title: '期次', dataIndex: 'installment_no', width: 60 },
    { title: '名称', dataIndex: 'label' },
    {
      title: '触发条件',
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
      title: '计划日期',
      dataIndex: 'planned_date',
      render: (v: string | null) => v || '-',
    },
    {
      title: '计划金额',
      dataIndex: 'planned_amount',
      align: 'right' as const,
      render: (v: string) => `¥${Number(v).toLocaleString()}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (v: string) => <StatusTag status={v} />,
    },
    {
      title: '实际金额',
      dataIndex: 'actual_amount',
      align: 'right' as const,
      render: (v: string | null) => (v ? `¥${Number(v).toLocaleString()}` : '-'),
    },
    { title: '实际日期', dataIndex: 'actual_date', render: (v: string | null) => v || '-' },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: PaymentScheduleItem) => (
        <Space>
          {record.status === 'planned' && (
            <>
              <Button
                size="small"
                type="primary"
                icon={<SendOutlined />}
                onClick={() => handleExecute(record)}
              >
                执行
              </Button>
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record)}
              />
            </>
          )}
          {record.status === 'paid' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
        </Space>
      ),
    },
  ]

  const tabItems = [
    {
      key: 'info',
      label: '基本信息',
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
              <Descriptions.Item label="版本">v{contract.current_version}</Descriptions.Item>
              {contract.notes && (
                <Descriptions.Item label={t('field.notes')} span={2}>
                  {contract.notes}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          <Card
            title="合同扫描件归档"
            extra={
              <Upload
                accept=".pdf,.ofd,.xml,.jpg,.jpeg,.png,.tiff"
                beforeUpload={handleUpload}
                showUploadList={false}
                maxCount={1}
              >
                <Button type="primary" icon={<UploadOutlined />} loading={uploading}>
                  上传扫描件（自动 OCR）
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
                            OCR {a.has_ocr ? `${a.ocr_chars} chars` : '无'}
                          </Tag>
                          <Tag>{a.role}</Tag>
                        </Space>
                        <Button
                          size="small"
                          icon={<DownloadOutlined />}
                          onClick={() => download(a.document_id, a.original_filename)}
                          block
                        >
                          下载
                        </Button>
                      </Space>
                    </Card>
                  </Col>
                ))}
              </Row>
            ) : (
              <Typography.Text type="secondary">
                暂无扫描件。点击右上角上传 PDF / OFD / XML / 图片，系统会自动 OCR 识别便于后续全文检索。
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
          <ClockCircleOutlined />
          付款计划
          {schedule && schedule.items.length > 0 && (
            <Tag>{schedule.items.length} 期</Tag>
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
                    title="合同总额"
                    value={Number(schedule.contract_total)}
                    prefix="¥"
                    precision={2}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="计划总额"
                    value={Number(schedule.planned_total)}
                    prefix="¥"
                    precision={2}
                    valueStyle={schedule.total_mismatch ? { color: '#faad14' } : undefined}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="已付总额"
                    value={Number(schedule.paid_total)}
                    prefix="¥"
                    precision={2}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="待付余额"
                    value={Number(schedule.remaining)}
                    prefix="¥"
                    precision={2}
                  />
                </Col>
              </Row>
              {schedule.total_mismatch && (
                <Alert
                  type="warning"
                  message="计划总额与合同总额不一致"
                  description={`合同总额 ¥${Number(schedule.contract_total).toLocaleString()}，计划总额 ¥${Number(schedule.planned_total).toLocaleString()}`}
                  showIcon
                />
              )}
            </>
          )}

          <Card
            title="付款明细"
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
              >
                新建付款计划
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
              locale={{ emptyText: '暂无付款计划。点击右上角"新建付款计划"开始创建。' }}
            />
          </Card>
        </Space>
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
        title="新建付款计划"
        width={640}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={() => form.submit()}>
              保存
            </Button>
          </Space>
        }
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="各期计划金额之和应等于合同总额"
          description={`当前合同总额: ¥${Number(contract.total_amount).toLocaleString()}`}
        />
        <Form form={form} onFinish={handleAddSchedule} layout="vertical">
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field, idx) => (
                  <Card
                    key={field.key}
                    size="small"
                    title={`第 ${idx + 1} 期`}
                    extra={
                      fields.length > 1 && (
                        <Button size="small" danger onClick={() => remove(field.name)}>
                          删除
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
                          label="名称"
                          rules={[{ required: true }]}
                        >
                          <Input placeholder="首付30% / 验收款 / 质保金" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'planned_amount']}
                          label="计划金额"
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
                          label="计划日期"
                        >
                          <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          {...field}
                          name={[field.name, 'trigger_type']}
                          label="触发条件"
                          initialValue="fixed_date"
                        >
                          <Select
                            options={[
                              { value: 'fixed_date', label: '固定日期' },
                              { value: 'milestone', label: '里程碑' },
                              { value: 'invoice_received', label: '收到发票后' },
                              { value: 'acceptance', label: '验收合格后' },
                            ]}
                          />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item
                      {...field}
                      name={[field.name, 'trigger_description']}
                      label="条件说明（可选）"
                    >
                      <Input placeholder="如：设备安装调试完成 / 质保期满 12 个月" />
                    </Form.Item>
                  </Card>
                ))}
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                  添加一期
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Drawer>
    </Space>
  )
}
