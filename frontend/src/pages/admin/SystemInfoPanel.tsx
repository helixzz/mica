import { Card, Descriptions } from 'antd'
import { useEffect, useState } from 'react'
import { api } from '@/api'

export function SystemInfoPanel() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null)
  useEffect(() => {
    void api.adminSystemInfo().then(setInfo)
  }, [])
  if (!info) return null
  return (
    <Card>
      <Descriptions bordered column={2} size="small">
        {Object.entries(info).map(([k, v]) => (
          <Descriptions.Item key={k} label={k}>
            {Array.isArray(v) ? v.join(', ') : String(v)}
          </Descriptions.Item>
        ))}
      </Descriptions>
    </Card>
  )
}
