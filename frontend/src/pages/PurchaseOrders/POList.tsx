import { DownloadOutlined } from '@ant-design/icons'
import { Button, Dropdown, Space, Table, Tag, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { ColumnSettings, type ColumnOption } from '@/components/ColumnSettings'
import { usePersistedColumns } from '@/hooks/usePersistedColumns'
import { api, type PurchaseOrderListItem } from '@/api'
import { getToken } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import i18n from '@/i18n'
import { fmtAmount, fmtAmountNode, fmtQty, fmtQtyNode } from '@/utils/format'
import { MonoId } from '@/components/ui/Mono'

const PO_STATUSES = [
  'draft',
  'confirmed',
  'partially_received',
  'fully_received',
  'closed',
  'cancelled',
]

// Keep in sync with the require_roles(...) guard on GET
// /purchase-orders/export/ledger (AGENTS §5.15).
const LEDGER_EXPORT_ROLES = ['admin', 'it_buyer', 'procurement_mgr', 'finance_auditor']

const poStatusStateClass: Record<string, string> = {
  draft: 'tag-state tag-state--neutral',
  confirmed: 'tag-state tag-state--success',
  partially_received: 'tag-state tag-state--progress',
  fully_received: 'tag-state tag-state--success',
  closed: 'tag-state tag-state--neutral',
  cancelled: 'tag-state tag-state--error',
}

const COLUMN_KEYS = {
  poNumber: 'po_number',
  prNumber: 'pr_number',
  prTitle: 'pr_title',
  supplier: 'supplier',
  status: 'status',
  totalAmount: 'total_amount',
  amountPaid: 'amount_paid',
  amountInvoiced: 'amount_invoiced',
  qtyReceived: 'qty_received',
  currency: 'currency',
  sourceType: 'source_type',
  createdAt: 'created_at',
} as const

const DEFAULT_VISIBLE: string[] = [
  COLUMN_KEYS.poNumber,
  COLUMN_KEYS.supplier,
  COLUMN_KEYS.status,
  COLUMN_KEYS.totalAmount,
  COLUMN_KEYS.amountPaid,
  COLUMN_KEYS.createdAt,
]

export function POListPage() {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const [rows, setRows] = useState<PurchaseOrderListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [statusFilter, setStatusFilter] = useState<string[]>([])
  const cols = usePersistedColumns('po-list', DEFAULT_VISIBLE)

  const canExportLedger = LEDGER_EXPORT_ROLES.includes(user?.role ?? '')

  useEffect(() => {
    setLoading(true)
    api.listPOs().then(setRows).finally(() => setLoading(false))
  }, [])

  const exportLedger = async (format: 'xlsx' | 'csv') => {
    const params = new URLSearchParams({ format })
    statusFilter.forEach((value) => params.append('status', value))
    setExporting(true)
    try {
      const resp = await fetch(`/api/v1/purchase-orders/export/ledger?${params.toString()}`, {
        headers: {
          Authorization: `Bearer ${getToken() ?? ''}`,
          'Accept-Language': i18n.language || 'zh-CN',
        },
      })
      if (!resp.ok) {
        const body = (await resp.json().catch(() => null)) as { detail?: string } | null
        message.error(typeof body?.detail === 'string' ? body.detail : t('export.failed'))
        return
      }
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mica-procurement-ledger-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.${format}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      message.error(t('export.failed'))
    } finally {
      setExporting(false)
    }
  }

  const allColumns: ColumnsType<PurchaseOrderListItem> = useMemo(
    () => [
      {
        key: COLUMN_KEYS.poNumber,
        title: t('field.po_number'),
        dataIndex: 'po_number',
        render: (v, r) => <Link to={`/purchase-orders/${r.id}`}><MonoId>{v}</MonoId></Link>,
        fixed: 'left' as const,
      },
      {
        key: COLUMN_KEYS.prNumber,
        title: t('field.pr_number'),
        dataIndex: 'pr_number',
        render: (v: string | null, r) =>
          v ? <Link to={`/purchase-requisitions/${r.pr_id}`}><MonoId>{v}</MonoId></Link> : '-',
      },
      {
        key: COLUMN_KEYS.prTitle,
        title: t('field.pr_title'),
        dataIndex: 'pr_title',
        render: (v: string | null) => v || '-',
      },
      {
        key: COLUMN_KEYS.supplier,
        title: t('field.supplier'),
        dataIndex: 'supplier_name',
        render: (v: string | null, r) =>
          v ? (
            <Space size={4}>
              <span>{v}</span>
              {r.supplier_code && (
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  ({r.supplier_code})
                </Typography.Text>
              )}
            </Space>
          ) : (
            '-'
          ),
      },
      {
        key: COLUMN_KEYS.status,
        title: t('field.status'),
        dataIndex: 'status',
        filters: PO_STATUSES.map((s) => ({
          text: t(`status.${s}` as 'status.confirmed'),
          value: s,
        })),
        onFilter: (value, record) => record.status === value,
        render: (s) => <span className={poStatusStateClass[s] ?? 'tag-state tag-state--neutral'}>{t(`status.${s}` as 'status.confirmed')}</span>,
      },
      {
        key: COLUMN_KEYS.totalAmount,
        title: t('field.total_amount'),
        render: (_, r) => fmtAmountNode(r.total_amount, r.currency),
        align: 'right' as const,
        sorter: (a, b) => Number(a.total_amount) - Number(b.total_amount),
      },
      {
        key: COLUMN_KEYS.amountPaid,
        title: t('field.amount_paid'),
        render: (_, r) => fmtAmountNode(r.amount_paid ?? '0', r.currency),
        align: 'right' as const,
        sorter: (a, b) => Number(a.amount_paid ?? 0) - Number(b.amount_paid ?? 0),
      },
      {
        key: COLUMN_KEYS.amountInvoiced,
        title: t('field.amount_invoiced'),
        render: (_, r) => fmtAmountNode(r.amount_invoiced ?? '0', r.currency),
        align: 'right' as const,
        sorter: (a, b) => Number(a.amount_invoiced ?? 0) - Number(b.amount_invoiced ?? 0),
      },
      {
        key: COLUMN_KEYS.qtyReceived,
        title: t('field.qty_received'),
        render: (_, r) => fmtQtyNode(r.qty_received ?? '0'),
        align: 'right' as const,
      },
      {
        key: COLUMN_KEYS.currency,
        title: t('field.currency'),
        dataIndex: 'currency',
      },
      {
        key: COLUMN_KEYS.sourceType,
        title: t('field.source_type'),
        dataIndex: 'source_type',
        render: (v: string) => <Tag>{v}</Tag>,
      },
      {
        key: COLUMN_KEYS.createdAt,
        title: t('field.created_at'),
        dataIndex: 'created_at',
        render: (v: string) => new Date(v).toLocaleString(),
        sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        defaultSortOrder: 'descend' as const,
      },
    ],
    [t],
  )

  const columnOptions: ColumnOption[] = useMemo(
    () =>
      allColumns.map((c) => ({
        key: c.key as string,
        label: typeof c.title === 'string' ? c.title : (c.key as string),
        alwaysVisible: c.key === COLUMN_KEYS.poNumber,
      })),
    [allColumns],
  )

  const visibleColumns = useMemo(
    () =>
      allColumns.filter(
        (c) => c.key === COLUMN_KEYS.poNumber || cols.isVisible(c.key as string),
      ),
    [allColumns, cols],
  )

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>
          {t('nav.purchase_orders')}
        </Typography.Title>
        <Space>
          {canExportLedger && (
            <Dropdown
              menu={{
                items: [
                  { key: 'xlsx', label: t('button.export_excel') },
                  { key: 'csv', label: t('button.export_csv') },
                ],
                onClick: ({ key }) => void exportLedger(key as 'xlsx' | 'csv'),
              }}
              trigger={['click']}
            >
              <Button icon={<DownloadOutlined />} loading={exporting}>
                {t('button.export_ledger')}
              </Button>
            </Dropdown>
          )}
          <ColumnSettings
            options={columnOptions}
            visibleKeys={cols.visibleKeys}
            onToggle={cols.toggle}
            onReset={cols.reset}
          />
        </Space>
      </div>
      <Table<PurchaseOrderListItem>
        rowKey="id"
        dataSource={rows}
        columns={visibleColumns}
        loading={loading}
        onChange={(_, filters) => {
          setStatusFilter((filters[COLUMN_KEYS.status] ?? []).map(String))
        }}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showTotal: (total) => t('item.total_count', { total }),
        }}
        size="small"
        scroll={{ x: 'max-content' }}
      />
    </Space>
  )
}
