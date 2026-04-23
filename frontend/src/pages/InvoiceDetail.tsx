import { CheckCircleTwoTone, DownloadOutlined, WarningTwoTone } from '@ant-design/icons'
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
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'

import { api, type Invoice } from '@/api'
import { extractError } from '@/api/client'
import { fmtAmount, fmtQty } from '@/utils/format'

export function InvoiceDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [inv, setInv] = useState<Invoice | null>(null)

  useEffect(() => {
    if (!id) return
    void api.getInvoice(id).then(setInv)
  }, [id])

  if (!inv) return <div>{t('message.loading')}</div>

  const downloadAttachment = async (document_id: string, filename: string) => {
    try {
      const { download_url } = await api.getDocumentDownloadUrl(document_id)
      const a = document.createElement('a')
      a.href = download_url
      a.download = filename
      a.target = '_blank'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      void message.info(t('invoice.download_hint'))
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const statusColor: Record<string, string> = {
    matched: 'success',
    pending_match: 'warning',
    mismatched: 'error',
    approved: 'processing',
    paid: 'cyan',
    cancelled: 'default',
    draft: 'default',
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space align="center">
          <Typography.Title level={3} style={{ margin: 0 }}>
            {inv.internal_number} · {inv.invoice_number}
          </Typography.Title>
          <Tag color={statusColor[inv.status] || 'default'}>
            {t(`status.${inv.status}` as 'status.draft')}
          </Tag>
          {inv.is_fully_matched ? (
            <CheckCircleTwoTone twoToneColor="#52c41a" style={{ fontSize: 20 }} />
          ) : (
            <WarningTwoTone twoToneColor="#faad14" style={{ fontSize: 20 }} />
          )}
        </Space>
        <Button onClick={() => navigate('/invoices')}>{t('button.back')}</Button>
      </div>

      <Card>
        <Descriptions bordered size="small" column={3}>
          <Descriptions.Item label={t('field.invoice_date')}>{inv.invoice_date}</Descriptions.Item>
          <Descriptions.Item label={t('field.due_date')}>{inv.due_date || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.tax_number')}>{inv.tax_number || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.subtotal')}>
            {fmtAmount(inv.subtotal, inv.currency)}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.tax_amount')}>
            {fmtAmount(inv.tax_amount, inv.currency)}
          </Descriptions.Item>
          <Descriptions.Item label={t('field.total_amount')}>
            <strong>
              {fmtAmount(inv.total_amount, inv.currency)}
            </strong>
          </Descriptions.Item>
          {inv.notes && (
            <Descriptions.Item label={t('field.notes')} span={3}>
              {inv.notes}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      <Card title={t('invoice.attachments')}>
        {inv.attachments && inv.attachments.length > 0 ? (
          <Row gutter={[12, 12]}>
            {inv.attachments.map((a) => (
              <Col key={a.document_id} xs={24} md={12} lg={8}>
                <Card size="small" type="inner">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Typography.Text strong>{a.original_filename}</Typography.Text>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {a.content_type} · {(a.file_size / 1024).toFixed(1)} KB · {a.role}
                    </Typography.Text>
                    <Button
                      size="small"
                      icon={<DownloadOutlined />}
                      onClick={() => downloadAttachment(a.document_id, a.original_filename)}
                      block
                    >
                      {t('common.download')}
                    </Button>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Typography.Text type="secondary">{t('message.no_data')}</Typography.Text>
        )}
      </Card>

      <Card title={t('field.item_name')}>
        <Table
          rowKey="id"
          dataSource={inv.lines}
          pagination={false}
          size="small"
          columns={[
            { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
            {
              title: 'Type',
              dataIndex: 'line_type',
              width: 100,
              render: (v: string) => <Tag color={v === 'product' ? 'blue' : 'default'}>{v}</Tag>,
            },
            { title: t('field.item_name'), dataIndex: 'item_name' },
            { title: t('field.qty'), dataIndex: 'qty', align: 'right', width: 80, render: (v: string) => fmtQty(v) },
            { title: t('field.unit_price'), dataIndex: 'unit_price', align: 'right', width: 110, render: (v: string) => fmtAmount(v) },
            { title: t('field.subtotal'), dataIndex: 'subtotal', align: 'right', width: 110, render: (v: string) => fmtAmount(v) },
            { title: t('field.tax_amount'), dataIndex: 'tax_amount', align: 'right', width: 100, render: (v: string) => fmtAmount(v) },
            {
              title: 'PO Item',
              dataIndex: 'po_item_id',
              width: 100,
              render: (v: string | null) => (v ? <Tag color="green">✓</Tag> : <Tag>-</Tag>),
            },
          ]}
        />
      </Card>
    </Space>
  )
}
