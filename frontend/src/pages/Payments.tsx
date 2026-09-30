import { DownloadOutlined } from '@ant-design/icons'
import { Button, Space, Table, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PaymentRecord } from '@/api'
import { useAuth } from '@/auth/useAuth'
import { ExportDrawer, canExport } from '@/components/Export'
import { fmtAmountNode } from '@/utils/format'
import { MonoId } from '@/components/ui/Mono'

export function PaymentsPage() {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const [rows, setRows] = useState<PaymentRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)

  const canExportData = canExport(user?.role)

  useEffect(() => {
    setLoading(true)
    api.listPayments().then(setRows).catch(() => setRows([])).finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<PaymentRecord> = [
    { title: t('field.payment_number'), dataIndex: 'payment_number', render: (v: string) => <MonoId>{v}</MonoId> },
    { title: t('field.installment_no'), dataIndex: 'installment_no' },
    { title: t('field.amount'), align: 'right', render: (_, r) => fmtAmountNode(r.amount, r.currency) },
    { title: t('field.status'), dataIndex: 'status',
      filters: [{text:'pending',value:'pending'},{text:'confirmed',value:'confirmed'},{text:'cancelled',value:'cancelled'}],
      onFilter: (value: any, record: any) => record.status === value,
      render: (s: string) => {
        const cls = s === 'confirmed' ? 'tag-state--success' : s === 'cancelled' ? 'tag-state--error' : 'tag-state--warning'
        return <span className={`tag-state ${cls}`}>{t(`status.${s}` as 'status.pending')}</span>
      } },
    { title: t('field.due_date'), dataIndex: 'due_date' },
    { title: t('field.payment_date'), dataIndex: 'payment_date' },
    { title: t('field.transaction_ref'), dataIndex: 'transaction_ref' },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('nav.payments')}</Typography.Title>
        {canExportData && (
          <Button icon={<DownloadOutlined />} onClick={() => setExportOpen(true)}>{t('button.export')}</Button>
        )}
      </div>
      <ExportDrawer
        datasetKey="payments"
        open={exportOpen}
        onClose={() => setExportOpen(false)}
      />
      <Table<PaymentRecord> rowKey="id" dataSource={rows} columns={columns} loading={loading} pagination={{ pageSize: 20 }} scroll={{ x: 'max-content' }} />
    </Space>
  )
}
