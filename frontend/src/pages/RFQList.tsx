import { useTranslation } from 'react-i18next'
import { PlusOutlined } from '@ant-design/icons'
import { Button, Space, Table, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { client } from '@/api/client'

const statusColors: Record<string, string> = {
  draft: 'default', sent: 'processing', quoting: 'cyan',
  evaluation: 'orange', awarded: 'success', closed: 'default', cancelled: 'error',
}

export default function RFQListPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [rfqs, setRfqs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void client.get('/rfqs').then((r) => { setRfqs(r.data); setLoading(false) })
  }, [])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('nav.rfqs')}</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/rfqs/new')}>{t('rfq.new')}</Button>
      </div>
      <Table
        dataSource={rfqs} rowKey="id" loading={loading} size="small"
        columns={[
          { title: t('rfq.number'), dataIndex: 'rfq_number', render: (v: string, r: any) => <Link to={`/rfqs/${r.id}`}>{v}</Link> },
          { title: t('field.title'), dataIndex: 'title' },
          { title: t('field.status'), dataIndex: 'status', render: (v: string) => <Tag color={statusColors[v]}>{v}</Tag> },
          { title: t('field.deadline'), dataIndex: 'deadline', render: (v: string | null) => v || '-' },
          { title: t('field.created_at'), dataIndex: 'created_at', render: (v: string) => v?.slice(0, 10) },
        ]}
      />
    </Space>
  )
}
