import { Card, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type SchedulerJob } from '@/api'

export function SchedulerTab() {
  const { t } = useTranslation()
  const [jobs, setJobs] = useState<SchedulerJob[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api
      .adminSchedulerStatus()
      .then(setJobs)
      .finally(() => setLoading(false))
  }, [])

  const columns: ColumnsType<SchedulerJob> = [
    {
      title: t('admin.scheduler_job_name'),
      dataIndex: 'name',
      width: 240,
      render: (v: string) => <Typography.Text strong>{v}</Typography.Text>,
    },
    {
      title: t('admin.scheduler_schedule'),
      dataIndex: 'schedule',
      width: 240,
    },
    {
      title: t('admin.scheduler_description'),
      dataIndex: 'description',
    },
    {
      title: t('admin.scheduler_status'),
      dataIndex: 'enabled',
      width: 120,
      render: (v: boolean) => (
        <Tag color={v ? 'success' : 'default'}>
          {v ? t('admin.scheduler_enabled') : t('admin.scheduler_disabled')}
        </Tag>
      ),
    },
  ]

  return (
    <Card>
      <Typography.Paragraph type="secondary">
        {t('admin.scheduler_help')}
      </Typography.Paragraph>
      <Table
        rowKey="id"
        dataSource={jobs}
        columns={columns}
        loading={loading}
        pagination={false}
      />
    </Card>
  )
}
