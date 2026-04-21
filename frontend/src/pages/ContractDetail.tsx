import { DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import {
  Button,
  Card,
  Col,
  Descriptions,
  Row,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type Contract, type ContractAttachment } from '@/api'
import { extractError } from '@/api/client'

export function ContractDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [contract, setContract] = useState<Contract | null>(null)
  const [attachments, setAttachments] = useState<ContractAttachment[]>([])
  const [uploading, setUploading] = useState(false)

  const load = async () => {
    if (!id) return
    const list = await api.listContracts()
    const found = list.find((c) => c.id === id)
    setContract(found || null)
    const att = await api.listContractAttachments(id)
    setAttachments(att)
  }

  useEffect(() => {
    void load()
  }, [id])

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

  if (!contract) return <div>{t('message.loading')}</div>

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
  )
}
