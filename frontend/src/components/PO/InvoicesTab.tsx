import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Modal, Table, Tag, message } from 'antd'
import { useTranslation } from 'react-i18next'

import { api, type InvoiceListRow } from '@/api'
import { fmtAmount } from '@/utils/format'

interface InvoicesTabProps {
  invoices: InvoiceListRow[]
  onRecordInvoice: () => void
  onChanged?: () => void
}

export function InvoicesTab({ invoices, onRecordInvoice, onChanged }: InvoicesTabProps) {
  const { t } = useTranslation()

  const handleDelete = (inv: InvoiceListRow) => {
    Modal.confirm({
      title: t('invoice.confirm_delete_title', '确认删除发票'),
      content: t('invoice.confirm_delete_body', {
        number: inv.invoice_number,
        amount: inv.total_amount,
        defaultValue: `确认删除发票 ${inv.invoice_number}（金额 ${inv.total_amount}）？此操作不可撤销。`,
      }),
      okText: t('button.delete', '删除'),
      okType: 'danger',
      cancelText: t('button.cancel', '取消'),
      onOk: async () => {
        try {
          await api.deleteInvoice(inv.id)
          message.success(t('invoice.deleted', '发票已删除'))
          onChanged?.()
        } catch {
          message.error(t('admin.operation_failed', '操作失败'))
        }
      },
    })
  }

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
          { title: t('field.subtotal'), dataIndex: 'subtotal', align: 'right', render: (v: string, r: InvoiceListRow) => fmtAmount(v, r.currency) },
          { title: t('field.tax_amount'), dataIndex: 'tax_amount', align: 'right', render: (v: string, r: InvoiceListRow) => fmtAmount(v, r.currency) },
          { title: t('field.total_amount'), dataIndex: 'total_amount', align: 'right', render: (v: string, r: InvoiceListRow) => fmtAmount(v, r.currency) },
          { title: t('field.status'), dataIndex: 'status',
            render: (s: string) => <Tag>{t(`status.${s}` as 'status.draft')}</Tag> },
          {
            title: '',
            width: 50,
            render: (_: unknown, r: InvoiceListRow) => (
              <Button
                size="small"
                type="text"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(r)}
                title={t('button.delete')}
              />
            ),
          },
        ]}
      />
    </>
  )
}
