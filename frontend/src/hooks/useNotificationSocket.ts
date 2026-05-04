import { useEffect, useRef, useState, useCallback } from 'react'
import { getToken } from '../api/client'
import { useNotificationStore } from '../stores/notification'

interface WsMessage {
  type: string
  notification_id?: string
  category?: string
  title?: string
  unread_count?: number
}

export function useNotificationSocket() {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const refresh = useNotificationStore((s) => s.refresh)

  const connect = useCallback(() => {
    const token = getToken()
    if (!token) return
    if (wsRef.current) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/notifications?token=${encodeURIComponent(token)}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)

    ws.onmessage = (event) => {
      try {
        const data: WsMessage = JSON.parse(event.data)
        if (data.type === 'new_notification') {
          refresh()
        }
      } catch {
        /* ignore malformed messages */
      }
    }

    ws.onerror = () => {
      // silently fall back to polling — no retry
      wsRef.current = null
    }

    ws.onclose = () => {
      setConnected(false)
      wsRef.current = null
    }
  }, [refresh])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.onerror = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  return { connected }
}
