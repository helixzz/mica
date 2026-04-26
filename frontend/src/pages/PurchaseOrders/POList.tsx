import { Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { ColumnSettings, type ColumnOption } from '@/components/ColumnSettings'
import { usePersistedColumns } from '@/hooks/usePersistedColumns'
import { api, type PurchaseOrderListItem } from '@/api'
import { fmtAmount, fmtQty } from '@/utils/format'

const PO_STATUSES = ['draft', 'confirmed', 'partially_received', 'fully_received', 'closed']

const COLUMN_KEYS = {
  poNumber: 'po_number',
  prNumber: 'pr_number',
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
  const [rows, setRows] = useState<PurchaseOrderListItem[]>([])
  const [loading, setLoading] = useState(false)
  const cols = usePersistedColumns('po-list', DEFAULT_VISIBLE)

  useEffect(() => {
    setLoading(true)
    api.listPOs().then(setRows).finally(() => setLoading(false))
  }, [])

  const allColumns: ColumnsType<PurchaseOrderListItem> = useMemo(
    () => [
      {
        key: COLUMN_KEYS.poNumber,
        title: t('field.po_number'),
        dataIndex: 'po_number',
        render: (v, r) => <Link to={`/purchase-orders/${r.id}`}>{v}</Link>,
        fixed: 'left' as const,
      },
      {
        key: COLUMN_KEYS.prNumber,
        title: t('field.pr_number'),
        dataIndex: 'pr_number',
        render: (v: string | null, r) =>
          v ? <Link to={`/purchase-requisitions/${r.pr_id}`}>{v}</Link> : '-',
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
        render: (s) => <Tag color="success">{t(`status.${s}` as 'status.confirmed')}</Tag>,
      },
      {
        key: COLUMN_KEYS.totalAmount,
        title: t('field.total_amount'),
        render: (_, r) => fmtAmount(r.total_amount, r.currency),
        align: 'right' as const,
        sorter: (a, b) => Number(a.total_amount) - Number(b.total_amount),
      },
      {
        key: COLUMN_KEYS.amountPaid,
        title: t('field.amount_paid'),
        render: (_, r) => fmtAmount(r.amount_paid ?? '0', r.currency),
        align: 'right' as const,
        sorter: (a, b) => Number(a.amount_paid ?? 0) - Number(b.amount_paid ?? 0),
      },
      {
        key: COLUMN_KEYS.amountInvoiced,
        title: t('field.amount_invoiced'),
        render: (_, r) => fmtAmount(r.amount_invoiced ?? '0', r.currency),
        align: 'right' as const,
        sorter: (a, b) => Number(a.amount_invoiced ?? 0) - Number(b.amount_invoiced ?? 0),
      },
      {
        key: COLUMN_KEYS.qtyReceived,
        title: t('field.qty_received'),
        render: (_, r) => fmtQty(r.qty_received ?? '0'),
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
        <ColumnSettings
          options={columnOptions}
          visibleKeys={cols.visibleKeys}
          onToggle={cols.toggle}
          onReset={cols.reset}
        />
      </div>
      <Table<PurchaseOrderListItem>
        rowKey="id"
        dataSource={rows}
        columns={visibleColumns}
        loading={loading}
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
