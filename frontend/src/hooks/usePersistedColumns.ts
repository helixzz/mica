import { useCallback, useEffect, useMemo, useState } from 'react'

const STORAGE_PREFIX = 'mica:column-prefs:'

export interface PersistedColumnsApi {
  visibleKeys: Set<string>
  isVisible: (key: string) => boolean
  toggle: (key: string) => void
  setVisible: (keys: string[]) => void
  reset: () => void
}

export function usePersistedColumns(
  storageId: string,
  defaultVisibleKeys: string[],
): PersistedColumnsApi {
  const fullKey = `${STORAGE_PREFIX}${storageId}`

  const [visibleKeys, setVisibleState] = useState<Set<string>>(() => {
    try {
      const raw = localStorage.getItem(fullKey)
      if (raw) {
        const parsed = JSON.parse(raw) as unknown
        if (Array.isArray(parsed)) {
          return new Set(parsed.filter((v): v is string => typeof v === 'string'))
        }
      }
    } catch {
      // localStorage unavailable or corrupted JSON; fall through to default
    }
    return new Set(defaultVisibleKeys)
  })

  useEffect(() => {
    try {
      localStorage.setItem(fullKey, JSON.stringify(Array.from(visibleKeys)))
    } catch {
      // quota exceeded / private mode; silently ignore
    }
  }, [fullKey, visibleKeys])

  const isVisible = useCallback((key: string) => visibleKeys.has(key), [visibleKeys])

  const toggle = useCallback((key: string) => {
    setVisibleState((prev) => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }, [])

  const setVisible = useCallback((keys: string[]) => {
    setVisibleState(new Set(keys))
  }, [])

  const reset = useCallback(() => {
    setVisibleState(new Set(defaultVisibleKeys))
  }, [defaultVisibleKeys])

  return useMemo(
    () => ({ visibleKeys, isVisible, toggle, setVisible, reset }),
    [visibleKeys, isVisible, toggle, setVisible, reset],
  )
}
