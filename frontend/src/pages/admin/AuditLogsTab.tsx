import { SearchOutlined } from '@ant-design/icons'
import {
  Button,
  DatePicker,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'

const { RangePicker } = DatePicker

interface AuditLogItem {
  id: string
  occurred_at: string
  actor_id: string | null
  actor_name: string | null
  event_type: string
  resource_type: string | null
  resource_id: string | null
  comment: string | null
  metadata: Record<string, unknown> | null
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  'admin.ai_model.created': 'green',
  'admin.ai_model.updated': 'blue',
  'admin.ai_model.deleted': 'red',
  'admin.ai_routing.upserted': 'purple',
  'admin.user.created': 'green',
  'admin.user.updated': 'blue',
  'admin.user.deleted': 'red',
  'admin.user.password_reset': 'orange',
}

function getEventTypeColor(eventType: string): string {
  for (const [prefix, color] of Object.entries(EVENT_TYPE_COLORS)) {
    if (eventType === prefix) return color
  }
  if (eventType.includes('.created')) return 'green'
  if (eventType.includes('.updated') || eventType.includes('.upserted')) return 'blue'
  if (eventType.includes('.deleted')) return 'red'
  return 'default'
}

export function AuditLogsTab() {
  const { t } = useTranslation()
  const [data, setData] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const [filterEventType, setFilterEventType] = useState<string | undefined>()
  const [filterResourceType, setFilterResourceType] = useState<string | undefined>()
  const [filterDateRange, setFilterDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)

  const [eventTypes, setEventTypes] = useState<string[]>([])
  const [resourceTypes, setResourceTypes] = useState<string[]>([])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
      }
      if (filterEventType) params.event_type = filterEventType
      if (filterResourceType) params.resource_type = filterResourceType
      if (filterDateRange?.[0]) params.date_from = filterDateRange[0].startOf('day').toISOString()
      if (filterDateRange?.[1]) params.date_to = filterDateRange[1].endOf('day').toISOString()

      const result = await api.adminAuditLogs(params as Parameters<typeof api.adminAuditLogs>[0])
      const items = result.items as unknown as AuditLogItem[]
      setData(items)
      setTotal(result.total)

      setEventTypes((prev) => {
        const seen = new Set(prev)
        for (const item of items) {
          seen.add(item.event_type)
        }
        return Array.from(seen).sort()
      })
      setResourceTypes((prev) => {
        const seen = new Set(prev)
        for (const item of items) {
          if (item.resource_type) seen.add(item.resource_type)
        }
        return Array.from(seen).sort()
      })
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filterEventType, filterResourceType, filterDateRange])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  const handleSearch = () => {
    setPage(1)
    void fetchData()
  }

  const handleReset = () => {
    setFilterEventType(undefined)
    setFilterResourceType(undefined)
    setFilterDateRange(null)
    setPage(1)
  }

  const columns: ColumnsType<AuditLogItem> = useMemo(
    () => [
      {
        title: t('audit_log.timestamp'),
        dataIndex: 'occurred_at',
        width: 180,
        render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm:ss'),
      },
      {
        title: t('audit_log.actor'),
        dataIndex: 'actor_name',
        width: 140,
        render: (v: string | null) => v || '-',
      },
      {
        title: t('audit_log.event_type'),
        dataIndex: 'event_type',
        width: 200,
        render: (v: string) => (
          <Tag color={getEventTypeColor(v)}>{v}</Tag>
        ),
      },
      {
        title: t('audit_log.resource'),
        key: 'resource',
        width: 180,
        render: (_: unknown, r: AuditLogItem) => (
          <Space size={4}>
            {r.resource_type && <Tag>{r.resource_type}</Tag>}
            <Typography.Text
              ellipsis
              style={{ maxWidth: 100, fontSize: 12 }}
              type="secondary"
            >
              {r.resource_id || '-'}
            </Typography.Text>
          </Space>
        ),
      },
      {
        title: t('audit_log.comment'),
        dataIndex: 'comment',
        ellipsis: true,
        render: (v: string | null) => v || '-',
      },
    ],
    [t],
  )

  const expandedRowRender = (record: AuditLogItem) => {
    if (!record.metadata || Object.keys(record.metadata).length === 0) {
      return (
        <Typography.Text type="secondary">
          {t('message.no_data')}
        </Typography.Text>
      )
    }
    return (
      <pre
        style={{
          margin: 0,
          padding: 12,
          background: 'var(--color-bg-container, #fafafa)',
          borderRadius: 6,
          fontSize: 12,
          maxHeight: 300,
          overflow: 'auto',
        }}
      >
        {JSON.stringify(record.metadata, null, 2)}
      </pre>
    )
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Select
          allowClear
          showSearch
          style={{ minWidth: 200 }}
          placeholder={t('audit_log.filter_event_type')}
          value={filterEventType}
          onChange={(val) => setFilterEventType(val)}
          options={eventTypes.map((et) => ({ value: et, label: et }))}
        />
        <Select
          allowClear
          style={{ minWidth: 140 }}
          placeholder={t('audit_log.filter_resource_type')}
          value={filterResourceType}
          onChange={(val) => setFilterResourceType(val)}
          options={resourceTypes.map((rt) => ({ value: rt, label: rt }))}
        />
        <RangePicker
          value={filterDateRange}
          onChange={(dates) => setFilterDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
          placeholder={[t('audit_log.filter_date'), t('audit_log.filter_date')]}
        />
        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={handleSearch}
        >
          {t('button.search')}
        </Button>
        <Button onClick={handleReset}>{t('button.reset')}</Button>
      </Space>

      <Table<AuditLogItem>
        rowKey="id"
        dataSource={data}
        columns={columns}
        loading={loading}
        expandable={{
          expandedRowRender,
          rowExpandable: (record) =>
            !!record.metadata && Object.keys(record.metadata).length > 0,
        }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t2) => t('common.total_count', { count: t2 }),
          onChange: (p, ps) => {
            setPage(p)
            setPageSize(ps)
          },
        }}
        scroll={{ x: 900 }}
      />
    </Space>
  )
}
