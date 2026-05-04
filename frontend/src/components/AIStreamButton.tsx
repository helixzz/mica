import { ThunderboltOutlined } from '@ant-design/icons'
import { Button, Space, Tooltip } from 'antd'
import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'

interface Props {
  feature: 'pr_description_polish' | 'sku_suggest'
  body: { draft?: string; query?: string }
  onChunk: (text: string) => void
  onDone?: () => void
  disabled?: boolean
  available?: boolean
  label?: string
}

export function AIStreamButton({ feature, body, onChunk, onDone, disabled, available = true, label }: Props) {
  const { t } = useTranslation()
  const [running, setRunning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const click = async () => {
    if (running) {
      abortRef.current?.abort()
      setRunning(false)
      return
    }
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setRunning(true)
    try {
      await api.aiStream(feature, body, onChunk, () => {
        setRunning(false)
        onDone?.()
      }, ctrl.signal)
    } catch {
      setRunning(false)
    }
  }

  const btn = (
    <Button
      icon={<ThunderboltOutlined />}
      onClick={click}
      disabled={disabled || !available}
      danger={running}
    >
      {running ? t('message.ai_thinking') : label || t('button.ai_polish')}
    </Button>
  )

  if (!available) {
    return (
      <Tooltip title={!available ? t('message.ai_not_configured') : undefined}>
        <span>{btn}</span>
      </Tooltip>
    )
  }

  return <Space>{btn}</Space>
}
