import { Alert, Button, Empty, Modal, Space, Table, Tag, Typography, Upload, message } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type RfqQuoteExtract } from '@/api'
import { extractError } from '@/api/client'
import { fmtQty } from '@/utils/format'

interface Props {
  open: boolean
  onClose: () => void
}

/**
 * Look at what the model read off a supplier's scanned quotation.
 *
 * Deliberately read-only: prices typed by hand are checked against a person's own
 * reading, but a wrong number copied out of a scan silently corrupts the price
 * history it feeds. So this shows the result and stops there.
 */
export function RfqQuoteImportModal({ open, onClose }: Props) {
  const { t } = useTranslation()
  const [result, setResult] = useState<RfqQuoteExtract | null>(null)
  const [busy, setBusy] = useState(false)

  const upload = async (file: File) => {
    setBusy(true)
    setResult(null)
    try {
      const document = await api.uploadDocument(file, 'invoice')
      const extracted = await api.extractRfqQuote(document.id)
      if (extracted.error) {
        void message.error(
          t('rfq.import_scan_failed', { error: extracted.error }),
        )
      }
      setResult(extracted)
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      title={t('rfq.import_scan')}
      open={open}
      onCancel={onClose}
      footer={<Button onClick={onClose}>{t('button.close')}</Button>}
      width={860}
      destroyOnHidden
    >
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Alert type="info" showIcon message={t('rfq.import_scan_hint')} />

        <Upload.Dragger
          accept=".pdf,image/*"
          maxCount={1}
          showUploadList={false}
          beforeUpload={(file) => {
            void upload(file as unknown as File)
            return false
          }}
          disabled={busy}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">
            {busy ? t('status.processing') : t('rfq.import_scan')}
          </p>
        </Upload.Dragger>

        {result && (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Space size="middle" wrap>
              <Tag color={result.confidence >= 0.7 ? 'success' : 'warning'}>
                {t('rfq.import_scan_confidence')}: {Math.round(result.confidence * 100)}%
              </Tag>
              <Typography.Text type="secondary">
                {t('rfq.import_scan_pages', {
                  read: result.pages_read,
                  total: result.pages_total,
                })}
              </Typography.Text>
              {result.supplier_name && <Tag>{result.supplier_name}</Tag>}
              {result.currency && <Tag>{result.currency}</Tag>}
            </Space>

            {result.warnings.length > 0 && (
              <Alert
                type="warning"
                showIcon
                message={t('rfq.import_scan_warnings')}
                description={
                  <ul style={{ margin: 0, paddingInlineStart: 18 }}>
                    {result.warnings.map((warning) => (
                      <li key={warning}>
                        <Typography.Text type="secondary">{warning}</Typography.Text>
                      </li>
                    ))}
                  </ul>
                }
              />
            )}

            {result.lines.length === 0 ? (
              <Empty description={t('rfq.import_scan_empty')} />
            ) : (
              <Table
                dataSource={result.lines}
                rowKey={(row) => `${row.line_no ?? '-'}-${row.item_name ?? ''}`}
                size="small"
                pagination={false}
                scroll={{ x: 'max-content' }}
                columns={[
                  { title: t('rfq.line_no'), dataIndex: 'line_no', width: 70 },
                  { title: t('rfq.item_name'), dataIndex: 'item_name' },
                  { title: t('rfq.specification'), dataIndex: 'specification' },
                  {
                    title: t('rfq.qty'),
                    dataIndex: 'qty',
                    align: 'right',
                    render: (value: string | null) => (value ? fmtQty(value) : '—'),
                  },
                  {
                    title: t('rfq.unit_price'),
                    dataIndex: 'unit_price',
                    align: 'right',
                    render: (value: string | null) => value ?? '—',
                  },
                  {
                    title: t('rfq.tax_rate'),
                    dataIndex: 'tax_rate',
                    align: 'right',
                    render: (value: string | null) => value ?? '—',
                  },
                  {
                    title: t('rfq.delivery_days'),
                    dataIndex: 'delivery_days',
                    align: 'right',
                    render: (value: number | null) => value ?? '—',
                  },
                  {
                    title: t('rfq.import_scan_confidence'),
                    dataIndex: 'confidence',
                    align: 'right',
                    render: (value: number) => (
                      <Tag color={value >= 0.7 ? 'success' : 'default'}>
                        {Math.round(value * 100)}%
                      </Tag>
                    ),
                  },
                ]}
              />
            )}

            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {t('rfq.import_scan_tip')}
            </Typography.Text>
          </Space>
        )}
      </Space>
    </Modal>
  )
}
