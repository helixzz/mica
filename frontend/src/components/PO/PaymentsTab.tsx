import { PlusOutlined } from '@ant-design/icons'
import { Button, Modal, Space, Table, Tag, Typography, message } from 'antd'
import dayjs from 'dayjs'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { api, type PaymentRecord } from '@/api'
import { extractError } from '@/api/client'
import { fmtAmount } from '@/utils/format'

interface PaymentsTabProps {
  payments: PaymentRecord[]
  loadAll: () => void
  onRecordPayment: () => void
  onEditPayment: (payment: PaymentRecord) => void
}

export function PaymentsTab({ payments, loadAll, onRecordPayment, onEditPayment }: PaymentsTabProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <>
      <div style={{ marginBottom: 12, textAlign: 'right' }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={onRecordPayment}>
          {t('button.record_payment')}
        </Button>
      </div>
      <Table
        rowKey="id"
        dataSource={payments}
        pagination={false}
        columns={[
          { title: t('field.payment_number'), dataIndex: 'payment_number' },
          {
            title: t('field.contract_number'),
            dataIndex: 'contract_number',
            render: (v: string | null, r: PaymentRecord) =>
              v && r.contract_id ? (
                <a onClick={() => navigate(`/contracts/${r.contract_id}`)}>{v}</a>
              ) : (
                <Typography.Text type="secondary">-</Typography.Text>
              ),
          },
          { title: t('field.installment_no'), dataIndex: 'installment_no', width: 80 },
          {
            title: t('field.amount'),
            dataIndex: 'amount',
            align: 'right',
            render: (v: string) => fmtAmount(v),
          },
          { title: t('field.due_date'), dataIndex: 'due_date' },
          { title: t('field.payment_date'), dataIndex: 'payment_date' },
          {
            title: t('field.status'),
            dataIndex: 'status',
            render: (s: string) => (
              <Tag color={s === 'confirmed' ? 'success' : 'default'}>
                {t(`status.${s}` as 'status.pending')}
              </Tag>
            ),
          },
          {
            title: t('common.actions'),
            width: 220,
            render: (_: unknown, r: PaymentRecord) => (
              <Space size="small">
                {r.status === 'pending' && (
                  <Button
                    size="small"
                    onClick={async () => {
                      try {
                        await api.confirmPayment(r.id, {
                          payment_date: dayjs().format('YYYY-MM-DD'),
                        })
                        void message.success(t('message.save_success'))
                        void loadAll()
                      } catch (e) {
                        void message.error(extractError(e).detail)
                      }
                    }}
                  >
                    {t('button.mark_paid')}
                  </Button>
                )}
                <Button
                  size="small"
                  onClick={() => onEditPayment(r)}
                >
                  {t('button.edit')}
                </Button>
                {r.status !== 'confirmed' && (
                  <Button
                    size="small"
                    danger
                    onClick={() => {
                      Modal.confirm({
                        title: t('po.payment_confirm_delete_title'),
                        content: t('po.payment_confirm_delete_body'),
                        okText: t('button.delete'),
                        okType: 'danger',
                        cancelText: t('button.cancel'),
                        onOk: async () => {
                          try {
                            await api.deletePayment(r.id)
                            void message.success(t('message.deleted'))
                            void loadAll()
                          } catch (e) {
                            void message.error(extractError(e).detail)
                          }
                        },
                      })
                    }}
                  >
                    {t('button.delete')}
                  </Button>
                )}
              </Space>
            ),
          },
        ]}
      />
    </>
  )
}