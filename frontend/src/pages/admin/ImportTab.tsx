import { DownloadOutlined, UploadOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'
import { extractError } from '@/api/client'

type ImportResult = {
  created: number
  skipped?: number
  errors: string[]
}

type ImportSection = {
  key: 'suppliers' | 'items' | 'prices'
  titleKey: string
  descKey: string
  downloadKind: 'suppliers' | 'items' | 'prices'
  importFn: (file: File) => Promise<ImportResult>
}

export function ImportTab() {
  const { t } = useTranslation()
  const [results, setResults] = useState<Record<string, ImportResult | null>>({})
  const [uploading, setUploading] = useState<Record<string, boolean>>({})

  const handleDownload = async (kind: 'suppliers' | 'items' | 'prices') => {
    try {
      const blob = await api.downloadTemplate(kind)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const filenames: Record<string, string> = {
        suppliers: 'supplier_import_template.xlsx',
        items: 'item_import_template.xlsx',
        prices: 'price_import_template.xlsx',
      }
      a.download = filenames[kind]
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const handleUpload = async (
    key: string,
    importFn: (file: File) => Promise<ImportResult>,
    file: File,
  ) => {
    setUploading((prev) => ({ ...prev, [key]: true }))
    setResults((prev) => ({ ...prev, [key]: null }))
    try {
      const result = await importFn(file)
      setResults((prev) => ({ ...prev, [key]: result }))
      const createdMsg = t('import.created') + ': ' + result.created
      const skippedMsg = result.skipped !== undefined ? `, ${t('import.skipped')}: ${result.skipped}` : ''
      void message.success(createdMsg + skippedMsg)
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setUploading((prev) => ({ ...prev, [key]: false }))
    }
  }

  const sections: ImportSection[] = [
    {
      key: 'suppliers',
      titleKey: 'import.import_suppliers',
      descKey: 'admin.import_suppliers_desc',
      downloadKind: 'suppliers',
      importFn: api.importSuppliers,
    },
    {
      key: 'items',
      titleKey: 'import.import_items',
      descKey: 'admin.import_items_desc',
      downloadKind: 'items',
      importFn: api.importItems,
    },
    {
      key: 'prices',
      titleKey: 'import.import_prices',
      descKey: 'admin.import_prices_desc',
      downloadKind: 'prices',
      importFn: api.importPrices,
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card title={t('import.title')}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {sections.map((section) => (
            <Card
              key={section.key}
              size="small"
              type="inner"
              title={t(section.titleKey)}
            >
              <Typography.Text
                type="secondary"
                style={{ display: 'block', marginBottom: 12, fontSize: 12 }}
              >
                {t(section.descKey)}
              </Typography.Text>
              <Space>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={() => handleDownload(section.downloadKind)}
                >
                  {t('import.download_template')}
                </Button>
                <Upload
                  accept=".xlsx,.xls"
                  beforeUpload={(file) => {
                    void handleUpload(section.key, section.importFn, file as File)
                    return false
                  }}
                  showUploadList={false}
                  maxCount={1}
                >
                  <Button
                    type="primary"
                    icon={<UploadOutlined />}
                    loading={uploading[section.key]}
                  >
                    {t('import.upload')}
                  </Button>
                </Upload>
              </Space>
              {results[section.key] && (
                <Card
                  size="small"
                  style={{ marginTop: 12, background: 'var(--color-bg-container)' }}
                  title={t('import.result')}
                >
                  <Space wrap>
                    <Tag color="success">
                      {t('import.created')}: {results[section.key]!.created}
                    </Tag>
                    {results[section.key]!.skipped !== undefined && (
                      <Tag color="warning">
                        {t('import.skipped')}: {results[section.key]!.skipped}
                      </Tag>
                    )}
                  </Space>
                  {results[section.key]!.errors.length > 0 && (
                    <Alert
                      type="error"
                      style={{ marginTop: 8 }}
                      message={t('import.errors')}
                      description={results[section.key]!.errors.slice(0, 10).join('\n')}
                      showIcon
                    />
                  )}
                </Card>
              )}
            </Card>
          ))}
        </Space>
      </Card>
    </Space>
  )
}