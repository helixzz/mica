import { Alert, Button, Card, Empty, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type PendingCollectionItem } from '@/api'
import { MonoId } from '@/components/ui'

/**
 * Quotations that went out and still owe us answers.
 *
 * A to-do list rather than a notification: procurement chases suppliers by hand,
 * so this just says what is outstanding and what is already late.
 */
export function PendingCollectionCard() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<PendingCollectionItem[]>([])

  useEffect(() => {
    void api
      .listPendingCollection()
      .then(setRows)
      .catch(() => setRows([]))
  }, [])

  const overdue = rows.filter((row) => row.overdue_days > 0).length

  return (
    <Card
      title={t('rfq.pending_collection')}
      size="small"
      style={{ height: '100%' }}
      extra={
        overdue > 0 ? (
          <Tag color="error">{t('rfq.overdue_days', { days: overdue })}</Tag>
        ) : undefined
      }
    >
      {rows.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('rfq.pending_collection_all_clear')}
        />
      ) : (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Alert
            type={overdue > 0 ? 'warning' : 'info'}
            showIcon
            message={t('rfq.pending_collection_hint', { count: rows.length, overdue })}
          />
          <Table
            dataSource={rows}
            rowKey="id"
            size="small"
            pagination={false}
            columns={[
              {
                title: t('rfq.number'),
                dataIndex: 'rfq_number',
                render: (value: string, record: PendingCollectionItem) => (
                  <Link to={`/rfqs/${record.id}`}>
                    <MonoId>{value}</MonoId>
                  </Link>
                ),
              },
              {
                title: t('rfq.pending_collection_deadline'),
                dataIndex: 'deadline',
                render: (value: string | null, record: PendingCollectionItem) =>
                  value ? (
                    record.overdue_days > 0 ? (
                      <Tag color="error">
                        {t('rfq.overdue_days', { days: record.overdue_days })}
                      </Tag>
                    ) : (
                      <Typography.Text>{value}</Typography.Text>
                    )
                  ) : (
                    '—'
                  ),
              },
              {
                title: t('rfq.pending_collection_outstanding'),
                dataIndex: 'outstanding_count',
                align: 'right',
                render: (value: number, record: PendingCollectionItem) => (
                  <Tag color="warning">
                    {value} / {record.invited_count}
                  </Tag>
                ),
              },
            ]}
          />
          <Button type="link" size="small" style={{ paddingInline: 0 }}>
            <Link to="/rfqs">{t('rfq.pending_collection')}</Link>
          </Button>
        </Space>
      )}
    </Card>
  )
}
