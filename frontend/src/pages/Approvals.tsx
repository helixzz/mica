import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'

import { api, type ApprovalTask } from '@/api'
import { fmtAmount } from '@/utils/format'

type ApprovalAction = 'approve' | 'reject' | 'return'

/** Hours the task has been waiting; shown so a deep-linked card does not hide urgency. */
function waitingHours(assignedAt: string): number {
  const assigned = new Date(assignedAt).getTime()
  if (Number.isNaN(assigned)) return 0
  return Math.max(0, (Date.now() - assigned) / 3_600_000)
}

export function ApprovalsPage() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tasks, setTasks] = useState<ApprovalTask[]>([])
  const [loading, setLoading] = useState(false)
  const [acting, setActing] = useState(false)
  const [comment, setComment] = useState('')

  const deepLinkId = searchParams.get('task')

  const load = useCallback(() => {
    setLoading(true)
    api
      .myPendingApprovals()
      .then(setTasks)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const activeTask = tasks.find((task) => task.id === deepLinkId) ?? null
  const deepLinkMissing = Boolean(deepLinkId) && !loading && !activeTask

  const closeTask = () => {
    setComment('')
    setSearchParams((prev) => {
      prev.delete('task')
      return prev
    })
  }

  const submit = async (action: ApprovalAction) => {
    if (!activeTask) return
    setActing(true)
    try {
      await api.actOnApprovalTask(activeTask.id, { action, comment: comment || null })
      message.success(t('approvals.action_done'))
      closeTask()
      load()
    } catch {
      message.error(t('approvals.action_failed'))
    } finally {
      setActing(false)
    }
  }

  const columns: ColumnsType<ApprovalTask> = [
    {
      title: t('field.pr_number'),
      dataIndex: 'biz_number',
      render: (_, r) => (
        <Link to={`/purchase-requisitions/${r.biz_id}`}>
          {r.biz_number || r.instance_id.slice(0, 8)}
        </Link>
      ),
    },
    { title: t('field.title'), dataIndex: 'biz_title', ellipsis: true },
    { title: t('field.requester'), dataIndex: 'submitter_name' },
    {
      title: t('field.total_amount'),
      dataIndex: 'biz_amount',
      align: 'right',
      render: (v: number | null) => (v != null ? fmtAmount(v, 'CNY') : '-'),
    },
    {
      title: t('field.status'),
      dataIndex: 'status',
      width: 100,
      render: (s) => <Tag color="processing">{t(`status.${s}` as 'status.pending')}</Tag>,
    },
    { title: t('field.display_name'), dataIndex: 'stage_name' },
    {
      title: t('field.created_at'),
      dataIndex: 'assigned_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
    {
      title: '',
      key: 'actions',
      width: 120,
      render: (_, r) => (
        <Button
          size="small"
          type="primary"
          onClick={() => setSearchParams((prev) => {
            prev.set('task', r.id)
            return prev
          })}
        >
          {t('approvals.review')}
        </Button>
      ),
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        {t('nav.approvals')}
      </Typography.Title>

      {deepLinkMissing && (
        <Alert
          type="warning"
          showIcon
          message={t('approvals.deep_link_missing')}
          action={
            <Button size="small" onClick={closeTask}>
              {t('button.close')}
            </Button>
          }
        />
      )}

      {tasks.length === 0 && !loading ? (
        <Card>
          <Empty description={t('message.no_pending_tasks')} />
        </Card>
      ) : (
        <Table<ApprovalTask>
          rowKey="id"
          dataSource={tasks}
          columns={columns}
          loading={loading}
          pagination={false}
        />
      )}

      <Modal
        open={Boolean(activeTask)}
        title={t('approvals.task_detail')}
        onCancel={closeTask}
        destroyOnHidden
        footer={
          <Space>
            <Button onClick={closeTask} disabled={acting}>
              {t('button.cancel')}
            </Button>
            <Button danger loading={acting} onClick={() => submit('reject')}>
              {t('approvals.reject')}
            </Button>
            <Button loading={acting} onClick={() => submit('return')}>
              {t('button.return')}
            </Button>
            <Button type="primary" loading={acting} onClick={() => submit('approve')}>
              {t('button.approve')}
            </Button>
          </Space>
        }
      >
        {activeTask && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label={t('field.pr_number')}>
                {activeTask.biz_number || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.total_amount')}>
                {activeTask.biz_amount != null ? fmtAmount(activeTask.biz_amount, 'CNY') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.title')} span={2}>
                {activeTask.biz_title || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.requester')}>
                {activeTask.submitter_name || '-'}
              </Descriptions.Item>
              <Descriptions.Item label={t('field.display_name')}>
                {activeTask.stage_name}
              </Descriptions.Item>
            </Descriptions>
            <Typography.Text type="secondary">
              {t('approvals.waiting_hours', {
                hours: waitingHours(activeTask.assigned_at).toFixed(1),
              })}
            </Typography.Text>
            <Input.TextArea
              rows={3}
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder={t('approvals.comment_placeholder')}
            />
            <Link to={`/purchase-requisitions/${activeTask.biz_id}`}>
              {t('approvals.open_in_mica')}
            </Link>
          </Space>
        )}
      </Modal>
    </Space>
  )
}
