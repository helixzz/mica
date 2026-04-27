import { DeleteOutlined, PaperClipOutlined, UploadOutlined } from '@ant-design/icons'
import { Button, Drawer, Space, Table, Typography, Upload, message } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Shipment } from '@/api'

interface Attachment {
  document_id: string
  role: string
  original_filename: string
  content_type: string
  file_size: number
  created_at: string
}

interface Props {
  shipment: Shipment | null
  open: boolean
  onClose: () => void
}

export function ShipmentAttachmentsDrawer({ shipment, open, onClose }: Props) {
  const { t } = useTranslation()
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loading, setLoading] = useState(false)

  const reload = async (shipmentId: string) => {
    setLoading(true)
    try {
      const docs = await api.listShipmentAttachments(shipmentId)
      setAttachments(docs as Attachment[])
    } catch {
      setAttachments([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && shipment) {
      void reload(shipment.id)
    } else {
      setAttachments([])
    }
  }, [open, shipment])

  const handleUpload = async (file: File) => {
    if (!shipment) return false
    try {
      const doc = await api.uploadDocument(file, 'shipment')
      await api.attachShipmentDocument(shipment.id, doc.id)
      void message.success(t('shipment.attachment_added'))
      await reload(shipment.id)
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      void message.error(err?.response?.data?.detail || t('admin.operation_failed'))
    }
    return false
  }

  const handleDownload = (attachment: Attachment) => {
    const url = `/api/v1/documents/${attachment.document_id}/download`
    const a = document.createElement('a')
    a.href = url
    a.download = attachment.original_filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  const handleRemove = async (documentId: string) => {
    if (!shipment) return
    try {
      await api.removeShipmentAttachment(shipment.id, documentId)
      void message.success(t('message.deleted'))
      await reload(shipment.id)
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } }
      void message.error(err?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  return (
    <Drawer
      title={shipment ? t('shipment.attachments', { number: shipment.shipment_number }) : ''}
      width={560}
      open={open}
      onClose={onClose}
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Upload beforeUpload={handleUpload} showUploadList={false} multiple>
          <Button icon={<UploadOutlined />}>{t('shipment.upload_attachment')}</Button>
        </Upload>
        <Typography.Text type="secondary">{t('shipment.attachment_hint')}</Typography.Text>
        <Table<Attachment>
          dataSource={attachments}
          rowKey="document_id"
          size="small"
          loading={loading}
          pagination={false}
          locale={{ emptyText: t('shipment.no_attachments') }}
          columns={[
            {
              title: t('shipment.filename'),
              dataIndex: 'original_filename',
              render: (v: string, r) => (
                <Button
                  type="link"
                  size="small"
                  style={{ padding: 0 }}
                  onClick={() => handleDownload(r)}
                >
                  {v}
                </Button>
              ),
            },
            {
              title: t('shipment.file_size'),
              dataIndex: 'file_size',
              width: 100,
              render: (v: number) => `${(v / 1024).toFixed(1)} KB`,
            },
            {
              title: t('common.actions'),
              width: 80,
              render: (_: unknown, r) => (
                <Space size={4}>
                  <Button
                    size="small"
                    icon={<PaperClipOutlined />}
                    onClick={() => handleDownload(r)}
                    title={t('button.download')}
                  />
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => void handleRemove(r.document_id)}
                  />
                </Space>
              ),
            },
          ]}
        />
      </Space>
    </Drawer>
  )
}
