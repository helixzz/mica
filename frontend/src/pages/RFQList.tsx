import { useTranslation } from 'react-i18next'
import { PlusOutlined } from '@ant-design/icons'
import { Alert, Button, Modal, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { client } from '@/api/client'
import { api, type PendingCollectionItem } from '@/api'
import { MonoId } from '@/components/ui/Mono'

const statusStateClass: Record<string, string> = {
  draft: 'tag-state tag-state--neutral',
  sent: 'tag-state tag-state--progress',
  quoting: 'tag-state tag-state--info',
  evaluation: 'tag-state tag-state--warning',
  awarded: 'tag-state tag-state--success',
  closed: 'tag-state tag-state--neutral',
  cancelled: 'tag-state tag-state--error',
}

export default function RFQListPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [rfqs, setRfqs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState<PendingCollectionItem[]>([])
  const [pendingOpen, setPendingOpen] = useState(false)

  useEffect(() => {
    void client.get('/rfqs').then((r) => { setRfqs(r.data); setLoading(false) })
    // A to-do list, not a notification: procurement chases suppliers by hand.
    void api
      .listPendingCollection()
      .then(setPending)
      .catch(() => setPending([]))
  }, [])

  const overdue = pending.filter((item) => item.overdue_days > 0).length

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('nav.rfqs')}</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/rfqs/new')}>{t('rfq.new')}</Button>
      </div>
      {pending.length > 0 && (
        <Alert
          type={overdue > 0 ? 'warning' : 'info'}
          showIcon
          message={t('rfq.pending_collection_hint', {
            count: pending.length,
            overdue,
          })}
          action={
            <Button size="small" onClick={() => setPendingOpen(true)}>
              {t('rfq.pending_collection')}
            </Button>
          }
        />
      )}
      <Table
        dataSource={rfqs} rowKey="id" loading={loading} size="small"
        scroll={{ x: 'max-content' }}
        columns={[
          { title: t('rfq.number'), dataIndex: 'rfq_number', render: (v: string, r: any) => <Link to={`/rfqs/${r.id}`}><MonoId>{v}</MonoId></Link> },
          { title: t('field.title'), dataIndex: 'title' },
          { title: t('field.status'), dataIndex: 'status', render: (v: string) => <span className={statusStateClass[v] ?? 'tag-state tag-state--neutral'}>{v}</span> },
          { title: t('field.deadline'), dataIndex: 'deadline', render: (v: string | null) => v || '-' },
          { title: t('field.created_at'), dataIndex: 'created_at', render: (v: string) => v?.slice(0, 10) },
        ]}
      />

      <Modal
        title={t('rfq.pending_collection')}
        open={pendingOpen}
        onCancel={() => setPendingOpen(false)}
        footer={null}
        width={760}
      >
        <Table
          dataSource={pending}
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
            { title: t('field.title'), dataIndex: 'title' },
            {
              title: t('rfq.pending_collection_deadline'),
              dataIndex: 'deadline',
              render: (value: string | null, record: PendingCollectionItem) => {
                if (!value) return '—'
                if (record.overdue_days > 0) {
                  return (
                    <Space size={4}>
                      <span>{value}</span>
                      <Tag color="error">
                        {t('rfq.overdue_days', { days: record.overdue_days })}
                      </Tag>
                    </Space>
                  )
                }
                return value
              },
            },
            {
              title: t('rfq.pending_collection_outstanding'),
              dataIndex: 'outstanding_count',
              render: (value: number, record: PendingCollectionItem) => (
                <Space size={4}>
                  <Tag color="warning">
                    {value} / {record.invited_count}
                  </Tag>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {record.outstanding_suppliers.slice(0, 3).join('、')}
                    {record.outstanding_suppliers.length > 3 ? ' …' : ''}
                  </Typography.Text>
                </Space>
              ),
            },
          ]}
        />
      </Modal>
    </Space>
  )
}
