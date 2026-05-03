import {
  Card,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useEffect, useState } from 'react'

import { api } from '@/api'

export function AILogsPanel() {
  const [logs, setLogs] = useState<Record<string, unknown>[]>([])
  const [stats, setStats] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([api.adminAICallLogs({ since_days: 7 }), api.adminAICallStats(7)])
      .then(([l, s]) => { setLogs(l); setStats(s) })
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Space wrap>
        {stats.map((s) => (
          <Card key={String(s.feature_code)} size="small" style={{ minWidth: 180 }}>
            <Statistic
              title={String(s.feature_code)}
              value={Number(s.total_calls)}
              suffix={`calls · ${Number(s.total_tokens)} tokens`}
            />
            <Typography.Text type="secondary">
              avg {Number(s.avg_latency_ms).toFixed(0)}ms
            </Typography.Text>
          </Card>
        ))}
      </Space>
      <Table
        rowKey="id"
        dataSource={logs}
        loading={loading}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: 'Time', dataIndex: 'occurred_at', render: (v: string) => new Date(v).toLocaleString() },
          { title: 'Feature', dataIndex: 'feature_code' },
          { title: 'Model', dataIndex: 'model_name' },
          { title: 'Provider', dataIndex: 'provider' },
          { title: 'Tokens', render: (_, r) => `${r.prompt_tokens}/${r.completion_tokens}` },
          { title: 'Latency', dataIndex: 'latency_ms', render: (v: number) => `${v}ms` },
          { title: 'Status', dataIndex: 'status', render: (v: string) => v === 'success' ? <Tag color="success">{v}</Tag> : <Tag color="error">{v}</Tag> },
          { title: 'Error', dataIndex: 'error', ellipsis: true },
        ]}
      />
    </Space>
  )
}