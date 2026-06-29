import { Timeline, Typography, Tag, Spin, Empty } from 'antd'
import { ClockCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'

interface AuditLogItem {
  id: string
  occurred_at: string
  actor_name: string | null
  event_type: string
  resource_type: string | null
  resource_id: string | null
  comment: string | null
  metadata: Record<string, unknown> | null
}

interface ActivityTimelineProps {
  resourceType: string
  resourceId: string
}

function formatMetadata(metadata: Record<string, unknown> | null): string | null {
  if (!metadata || Object.keys(metadata).length === 0) return null

  const changes: string[] = []
  for (const [key, value] of Object.entries(metadata)) {
    if (typeof value === 'object' && value !== null && 'old' in value && 'new' in value) {
      const oldVal = (value as { old: unknown; new: unknown }).old
      const newVal = (value as { old: unknown; new: unknown }).new
      changes.push(`${key}: ${String(oldVal ?? '-')} → ${String(newVal ?? '-')}`)
    } else {
      changes.push(`${key}: ${typeof value === 'object' ? JSON.stringify(value) : String(value)}`)
    }
  }
  return changes.join(' · ')
}

function getEventTypeColor(eventType: string): string {
  if (eventType.includes('.created')) return 'green'
  if (eventType.includes('.updated') || eventType.includes('.upserted')) return 'blue'
  if (eventType.includes('.deleted')) return 'red'
  if (eventType.includes('.submitted')) return 'orange'
  if (eventType.includes('.approved')) return 'green'
  if (eventType.includes('.rejected')) return 'red'
  if (eventType.includes('.returned')) return 'gold'
  if (eventType.includes('.converted')) return 'cyan'
  if (eventType.startsWith('notification.')) return 'purple'
  return 'default'
}

export function ActivityTimeline({ resourceType, resourceId }: ActivityTimelineProps) {
  const { t } = useTranslation()
  const [items, setItems] = useState<AuditLogItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .resourceActivityLogs({
        resource_type: resourceType,
        resource_id: resourceId,
        page_size: 50,
      })
      .then((items) => {
        if (!cancelled) {
          setItems((items as unknown as AuditLogItem[]) ?? [])
        }
      })
      .catch(() => {
        if (!cancelled) setItems([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [resourceType, resourceId])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 24 }}>
        <Spin />
      </div>
    )
  }

  if (items.length === 0) {
    return <Empty description={t('activity.no_events', '暂无活动记录')} />
  }

  return (
    <Timeline
      items={items.map((item) => {
        const metadataText = formatMetadata(item.metadata)
        return {
          dot: <ClockCircleOutlined style={{ fontSize: 14 }} />,
          children: (
            <div>
              <div style={{ marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <Tag color={getEventTypeColor(item.event_type)} style={{ margin: 0 }}>
                  {t(`event_type.${item.event_type}` as 'event_type.pr.created', item.event_type)}
                </Tag>
                {item.actor_name && (
                  <Typography.Text strong style={{ fontSize: 13 }}>
                    {item.actor_name}
                  </Typography.Text>
                )}
              </div>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {dayjs(item.occurred_at).format('YYYY-MM-DD HH:mm:ss')}
              </Typography.Text>
              {metadataText && (
                <div style={{ marginTop: 4 }}>
                  <Typography.Text
                    style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}
                  >
                    {metadataText}
                  </Typography.Text>
                </div>
              )}
              {item.comment && (
                <div style={{ marginTop: 4 }}>
                  <Typography.Text type="secondary" style={{ fontSize: 12, fontStyle: 'italic' }}>
                    {item.comment}
                  </Typography.Text>
                </div>
              )}
            </div>
          ),
        }
      })}
    />
  )
}