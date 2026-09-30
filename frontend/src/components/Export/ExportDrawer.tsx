import { DownloadOutlined } from '@ant-design/icons'
import {
  Button,
  DatePicker,
  Drawer,
  Form,
  Input,
  Segmented,
  Select,
  Skeleton,
  Space,
  Typography,
  message,
} from 'antd'
import dayjs, { type Dayjs } from 'dayjs'
import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

import { downloadExport, type ExportFormat, type ExportParams } from '@/api'
import { datasetLabel } from './exportRoles'
import { useExportCatalog, useExportLookups } from './useExportCatalog'

/**
 * Values a page already holds in component state, used to pre-select the
 * drawer's matching controls. Best-effort only — every field is optional and
 * keys the dataset does not declare are ignored.
 */
export interface ExportPageFilters {
  dateFrom?: string
  dateTo?: string
  status?: string[]
  supplierId?: string
  companyId?: string
  departmentId?: string
  costCenterId?: string
  categoryId?: string
  itemId?: string
  keyword?: string
}

export interface ExportDrawerProps {
  datasetKey: string
  open: boolean
  onClose: () => void
  pageFilters?: ExportPageFilters
}

/** Display order for the filter controls (unknown keys keep API order after). */
const FILTER_ORDER = [
  'date_range',
  'status',
  'supplier',
  'company',
  'department',
  'cost_center',
  'category',
  'item',
  'keyword',
]

const LOOKUP_FILTERS = ['company', 'cost_center', 'category', 'department', 'item', 'supplier']

const EMPTY_FILTERS: string[] = []

/** Known filters first (in FILTER_ORDER), anything unexpected after them. */
function filterOrder(key: string): number {
  const index = FILTER_ORDER.indexOf(key)
  return index === -1 ? FILTER_ORDER.length : index
}

export function ExportDrawer({ datasetKey, open, onClose, pageFilters }: ExportDrawerProps) {
  const { t, i18n } = useTranslation()
  const { dataset, loading } = useExportCatalog(datasetKey, open)

  const [format, setFormat] = useState<ExportFormat>('xlsx')
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null)
  const [statuses, setStatuses] = useState<string[]>([])
  const [keyword, setKeyword] = useState('')
  const [lookupValues, setLookupValues] = useState<Record<string, string | undefined>>({})
  const [exporting, setExporting] = useState(false)

  const filters = dataset?.filters ?? EMPTY_FILTERS
  const lookups = useExportLookups(filters, open)

  useEffect(() => {
    if (!open) return
    setFormat('xlsx')
    setDateRange(
      pageFilters?.dateFrom && pageFilters?.dateTo
        ? [dayjs(pageFilters.dateFrom), dayjs(pageFilters.dateTo)]
        : null,
    )
    setStatuses(pageFilters?.status ?? [])
    setKeyword(pageFilters?.keyword ?? '')
    setLookupValues({
      supplier: pageFilters?.supplierId,
      company: pageFilters?.companyId,
      department: pageFilters?.departmentId,
      cost_center: pageFilters?.costCenterId,
      category: pageFilters?.categoryId,
      item: pageFilters?.itemId,
    })
    // Re-prefill every time the drawer is (re)opened; pageFilters is a snapshot.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const orderedFilters = [...filters].sort(
    (a, b) => filterOrder(a) - filterOrder(b),
  )

  const filterLabel = (key: string): string => {
    switch (key) {
      case 'date_range':
        return t('export.filter_date_range')
      case 'status':
        return t('field.status')
      case 'supplier':
        return t('field.supplier')
      case 'company':
        return t('field.company')
      case 'department':
        return t('field.department')
      case 'cost_center':
        return t('field.cost_center')
      case 'category':
        return t('export.filter_category')
      case 'item':
        return t('export.filter_item')
      case 'keyword':
        return t('export.filter_keyword')
      default:
        return key
    }
  }

  const renderLookup = (key: string): ReactNode => (
    <Select
      allowClear
      showSearch
      optionFilterProp="label"
      style={{ width: '100%' }}
      placeholder={t('export.filter_any')}
      value={lookupValues[key]}
      options={lookups[key] ?? []}
      onChange={(value) =>
        setLookupValues((prev) => ({ ...prev, [key]: value ?? undefined }))
      }
    />
  )

  const renderFilter = (key: string): ReactNode => {
    if (key === 'date_range') {
      return (
        <DatePicker.RangePicker
          style={{ width: '100%' }}
          value={dateRange}
          onChange={(dates) =>
            setDateRange(dates?.[0] && dates?.[1] ? [dates[0], dates[1]] : null)
          }
        />
      )
    }
    if (key === 'keyword') {
      return (
        <Input
          allowClear
          value={keyword}
          placeholder={t('export.filter_keyword_placeholder')}
          onChange={(e) => setKeyword(e.target.value)}
        />
      )
    }
    if (key === 'status') {
      // The allowed values come from the backend catalog, so this list cannot
      // drift from the enums (it previously missed PRStatus.cancelled and
      // InvoiceStatus.mismatched).
      const values = dataset?.status_values ?? []
      return (
        <Select
          allowClear
          mode={values.length > 0 ? 'multiple' : 'tags'}
          style={{ width: '100%' }}
          placeholder={t('export.filter_status_placeholder')}
          value={statuses}
          onChange={(value) => setStatuses(value as string[])}
          options={values.map((value) => ({
            value,
            label: t(`status.${value}` as 'status.draft'),
          }))}
        />
      )
    }
    if (LOOKUP_FILTERS.includes(key)) return renderLookup(key)
    return null
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      // Only ever send filters this dataset declares, otherwise the backend
      // rejects the whole request with 400 export.unsupported_filter.
      const params: ExportParams = { format }
      if (filters.includes('date_range') && dateRange?.[0] && dateRange?.[1]) {
        params.date_from = dateRange[0].format('YYYY-MM-DD')
        params.date_to = dateRange[1].format('YYYY-MM-DD')
      }
      if (filters.includes('status') && statuses.length > 0) params.status = statuses
      if (filters.includes('supplier') && lookupValues.supplier) {
        params.supplier_id = lookupValues.supplier
      }
      if (filters.includes('company') && lookupValues.company) {
        params.company_id = lookupValues.company
      }
      if (filters.includes('department') && lookupValues.department) {
        params.department_id = lookupValues.department
      }
      if (filters.includes('cost_center') && lookupValues.cost_center) {
        params.cost_center_id = lookupValues.cost_center
      }
      if (filters.includes('category') && lookupValues.category) {
        params.category_id = lookupValues.category
      }
      if (filters.includes('item') && lookupValues.item) params.item_id = lookupValues.item
      if (filters.includes('keyword') && keyword.trim()) params.q = keyword.trim()

      await downloadExport(datasetKey, params)
      void message.success(t('export.success'))
      onClose()
    } catch (error) {
      const detail = error instanceof Error ? error.message : ''
      void message.error(detail || t('export.failed'))
    } finally {
      setExporting(false)
    }
  }

  const title = dataset
    ? `${t('export.title')} · ${datasetLabel(i18n.language, dataset)}`
    : t('export.title')

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={title}
      width={480}
      footer={
        <Space style={{ float: 'right' }}>
          <Button onClick={onClose}>{t('button.cancel')}</Button>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            loading={exporting}
            disabled={!dataset}
            onClick={() => void handleExport()}
          >
            {t('button.export')}
          </Button>
        </Space>
      }
    >
      {loading && !dataset ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : !dataset ? (
        <Typography.Text type="secondary">{t('export.dataset_unavailable')}</Typography.Text>
      ) : (
        <Form layout="vertical">
          {orderedFilters.map((key) => (
            <Form.Item
              key={key}
              label={filterLabel(key)}
              style={{ marginBottom: 'var(--space-4)' }}
            >
              {renderFilter(key)}
            </Form.Item>
          ))}
          <Form.Item label={t('export.filter_format')} style={{ marginBottom: 0 }}>
            <Segmented
              block
              value={format}
              onChange={(value) => setFormat(value as ExportFormat)}
              options={[
                { value: 'xlsx', label: t('export.format_excel') },
                { value: 'csv', label: t('export.format_csv') },
              ]}
            />
          </Form.Item>
        </Form>
      )}
    </Drawer>
  )
}
