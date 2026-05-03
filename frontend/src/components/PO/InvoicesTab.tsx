import { PlusOutlined } from '@ant-design/icons'
import { Button, Table, Tag } from 'antd'
import { useTranslation } from 'react-i18next'

import { type InvoiceListRow } from '@/api'
import { fmtAmount } from '@/utils/format'

interface InvoicesTabProps {
  invoices: InvoiceListRow[]
  onRecordInvoice: () => void
}

export function InvoicesTab({ invoices, onRecordInvoice }: InvoicesTabProps) {
  const { t } = useTranslation()

  return (
    <>
      <div style={{ marginBottom: 12, textAlign: 'right' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={onRecordInvoice}>
          {t('button.record_invoice')}
        </Button>
      </div>
      <Table
        rowKey="id"
        dataSource={invoices}
        pagination={false}
        columns={[
          { title: t('field.internal_number'), dataIndex: 'internal_number' },
          { title: t('field.invoice_number'), dataIndex: 'invoice_number' },
          { title: t('field.invoice_date'), dataIndex: 'invoice_date' },
          { title: t('field.subtotal'), dataIndex: 'subtotal', align: 'right', render: (v: string) => fmtAmount(v) },
          { title: t('field.tax_amount'), dataIndex: 'tax_amount', align: 'right', render: (v: string) => fmtAmount(v) },
          { title: t('field.total_amount'), dataIndex: 'total_amount', align: 'right', render: (v: string) => fmtAmount(v) },
          { title: t('field.status'), dataIndex: 'status',
            render: (s: string) => <Tag>{t(`status.${s}` as 'status.draft')}</Tag> },
        ]}
      />
    </>
  )
}