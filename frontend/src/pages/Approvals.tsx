import { Card, Empty, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type ApprovalTask } from '@/api'

export function ApprovalsPage() {
  const { t } = useTranslation()
  const [tasks, setTasks] = useState<ApprovalTask[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.myPendingApprovals().then(setTasks).finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<ApprovalTask> = [
    { title: t('field.status'), dataIndex: 'status', render: (s) => <Tag color="processing">{t(`status.${s}` as 'status.pending')}</Tag> },
    { title: t('field.display_name'), dataIndex: 'stage_name' },
    {
      title: t('field.pr_number'),
      dataIndex: 'instance_id',
      render: (_, r) => (
        <Link to={`/approvals/instance/${r.instance_id}`}>
          {r.instance_id.slice(0, 8)}
        </Link>
      ),
    },
    {
      title: t('field.created_at'),
      dataIndex: 'assigned_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        {t('nav.approvals')}
      </Typography.Title>
      {tasks.length === 0 && !loading ? (
        <Card>
          <Empty description={t('message.no_pending_tasks')} />
        </Card>
      ) : (
        <Table<ApprovalTask> rowKey="id" dataSource={tasks} columns={columns} loading={loading} pagination={false} />
      )}
    </Space>
  )
}
