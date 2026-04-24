import {
  ClockCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  StopOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import {
  Button,
  Card,
  Col,
  Descriptions,
  Dropdown,
  Modal,
  Row,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import {
  api,
  type Contract,
  type ContractAttachment,
  type ContractVersion,
} from '@/api'
import { extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { ContractFormModal } from '@/components/ContractFormModal'
import { PaymentScheduleTab } from '@/components/PaymentScheduleTab'
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

export function ContractDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const user = useAuth((s) => s.user)
  const [contract, setContract] = useState<Contract | null>(null)
  const [attachments, setAttachments] = useState<ContractAttachment[]>([])
  const [uploading, setUploading] = useState(false)
  const [versions, setVersions] = useState<ContractVersion[]>([])
  const [editOpen, setEditOpen] = useState(false)

  const canWrite = Boolean(
    user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role),
  )
  const canDelete = Boolean(user && user.role === 'admin')
  const canTransition = Boolean(
    user && ['admin', 'procurement_mgr'].includes(user.role),
  )

  const load = useCallback(async () => {
    if (!id) return
    const list = await api.listContracts()
    const found = list.find((c) => c.id === id)
    setContract(found || null)
    const att = await api.listContractAttachments(id)
    setAttachments(att)
  }, [id])

  useEffect(() => {
    void load()
    if (id) void api.listContractVersions(id).then(setVersions).catch(() => setVersions([]))
  }, [load, id])

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

  const handleDeleteContract = () => {
    if (!contract) return
    Modal.confirm({
      title: t('contract.confirm_delete_title', { number: contract.contract_number }),
      content: t('contract.confirm_delete_body'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteContract(contract.id)
          void message.success(t('message.deleted'))
          navigate('/contracts')
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  const handleStatusChange = (next: 'superseded' | 'terminated' | 'expired') => {
    if (!contract) return
    Modal.confirm({
      title: t('contract.confirm_status_title', { status: t(`status.${next}` as 'status.active') }),
      content: t('contract.confirm_status_body'),
      okText: t('button.confirm'),
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          const updated = await api.updateContractStatus(contract.id, next)
          setContract(updated)
          void message.success(t('contract.status_changed_ok'))
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  if (!contract) return <div>{t('message.loading')}</div>

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
                {fmtAmount(contract.total_amount, contract.currency)}
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
          <ClockCircleOutlined />
          {t('contract.payment_schedule')}
        </Space>
      ),
      children: (
        <PaymentScheduleTab
          contractId={id!}
          currency={contract.currency}
          canWrite={canWrite}
        />
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
             { title: t('field.total_amount'), render: (_: unknown, r: ContractVersion) => fmtAmount((r.snapshot_json as Record<string, unknown>)?.total_amount as string, contract.currency), align: 'right' as const },
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
        <Space>
          {canWrite && contract.status === 'active' && (
            <Button icon={<EditOutlined />} onClick={() => setEditOpen(true)}>
              {t('button.edit')}
            </Button>
          )}
          {canTransition && contract.status === 'active' && (
            <Dropdown
              menu={{
                items: [
                  {
                    key: 'terminated',
                    label: t('contract.transition_to_terminated'),
                  },
                  {
                    key: 'superseded',
                    label: t('contract.transition_to_superseded'),
                  },
                  {
                    key: 'expired',
                    label: t('contract.transition_to_expired'),
                  },
                ],
                onClick: ({ key }) =>
                  handleStatusChange(key as 'superseded' | 'terminated' | 'expired'),
              }}
              trigger={['click']}
            >
              <Button icon={<StopOutlined />}>{t('contract.change_status')}</Button>
            </Dropdown>
          )}
          {canDelete && (
            <Button danger icon={<DeleteOutlined />} onClick={handleDeleteContract}>
              {t('button.delete')}
            </Button>
          )}
          <Button onClick={() => navigate('/contracts')}>{t('button.back')}</Button>
        </Space>
      </div>

      <Tabs items={tabItems} defaultActiveKey="info" />

      <ContractFormModal
        open={editOpen}
        mode="edit"
        contract={contract}
        onClose={() => setEditOpen(false)}
        onSaved={(saved) => {
          setContract(saved)
          setEditOpen(false)
        }}
      />

    </Space>
  )
}
