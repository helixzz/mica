import { DeleteOutlined, UploadOutlined } from '@ant-design/icons'
import { Button, Popconfirm, Space, Table, Typography, Upload, message } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'

interface Attachment {
  document_id: string
  role: string
  original_filename: string
  content_type: string
  file_size: number
  created_at: string
}

interface Props {
  poId: string
}

export function POAttachmentsTab({ poId }: Props) {
  const { t } = useTranslation()
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  const reload = async () => {
    setLoading(true)
    try {
      const docs = await api.listPODocuments(poId)
      setAttachments(docs as Attachment[])
    } catch {
      setAttachments([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void reload() }, [poId])

  const handleDelete = async (documentId: string) => {
    try {
      await api.deletePODocument(poId, documentId)
      void message.success(t('message.deleted'))
      void reload()
    } catch {
      void message.error(t('error.delete_failed'))
    }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Upload
        accept=".pdf,.jpg,.jpeg,.png,.xlsx,.xls,.docx,.doc,.csv,.txt,.zip"
        showUploadList={false}
        beforeUpload={async (file) => {
          setUploading(true)
          try {
            const formData = new FormData()
            formData.append('file', file)
            const response = await fetch('/api/v1/documents/upload', {
              method: 'POST',
              headers: { Authorization: `Bearer ${localStorage.getItem('mica.token')}` },
              body: formData,
            })
            const doc = await response.json()
            await api.attachPODocument(poId, doc.id, 'attachment')
            void message.success(t('common.saved'))
            void reload()
          } catch {
            void message.error(t('error.upload_failed'))
          } finally {
            setUploading(false)
          }
          return false
        }}
      >
        <Button icon={<UploadOutlined />} loading={uploading}>
          {t('button.upload')}
        </Button>
      </Upload>
      <Typography.Text type="secondary">
        {t('po.attachments_hint')}
      </Typography.Text>
      <Table
        rowKey="document_id"
        dataSource={attachments}
        loading={loading}
        pagination={false}
        size="small"
        columns={[
          { title: t('field.filename'), dataIndex: 'original_filename' },
          { title: t('field.file_size'), dataIndex: 'file_size', render: (v: number) => `${(v / 1024).toFixed(1)} KB` },
          { title: t('field.created_at'), dataIndex: 'created_at', render: (v: string) => new Date(v).toLocaleDateString() },
          {
            title: t('common.actions'), key: 'actions', width: 80,
            render: (_: unknown, r: Attachment) => (
              <Popconfirm title={t('message.confirm_delete')} onConfirm={() => handleDelete(r.document_id)} okText={t('button.delete')} cancelText={t('button.cancel')}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            ),
          },
        ]}
      />
    </Space>
  )
}