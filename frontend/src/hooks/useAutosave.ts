import { useCallback, useEffect, useRef, useState } from 'react'

const PREFIX = 'mica:autosave:'

interface AutosaveState {
  savedAt: number
  formValues: Record<string, unknown>
}

interface AutosaveReturn {
  storageAvailable: boolean
  hasAutosave: boolean
  savedAt: number | null
  restore: () => Record<string, unknown> | null
  clear: () => void
  save: (values: Record<string, unknown>) => void
}

function _storageAvailable(): boolean {
  try {
    const key = '__mica_storage_test__'
    localStorage.setItem(key, '1')
    localStorage.removeItem(key)
    return true
  } catch {
    return false
  }
}

export function useAutosave(key: string, debounceMs = 2000): AutosaveReturn {
  const fullKey = `${PREFIX}${key}`
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [state, setState] = useState<AutosaveState | null>(null)
  const storageAvailable = useRef(_storageAvailable()).current

  useEffect(() => {
    if (!storageAvailable) return
    try {
      const raw = localStorage.getItem(fullKey)
      if (raw) {
        const parsed = JSON.parse(raw) as AutosaveState
        if (parsed.savedAt && parsed.formValues) {
          setState(parsed)
        }
      }
    } catch {
      // corrupted data: ignore
    }
  }, [fullKey, storageAvailable])

  const save = useCallback(
    (values: Record<string, unknown>) => {
      if (!storageAvailable) return
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        try {
          const entry: AutosaveState = { savedAt: Date.now(), formValues: values }
          localStorage.setItem(fullKey, JSON.stringify(entry))
          setState(entry)
        } catch {
          // storage full: ignore
        }
      }, debounceMs)
    },
    [fullKey, debounceMs, storageAvailable],
  )

  const restore = useCallback((): Record<string, unknown> | null => {
    if (!storageAvailable || !state) return null
    return state.formValues
  }, [storageAvailable, state])

  const clear = useCallback(() => {
    try {
      localStorage.removeItem(fullKey)
    } catch {
      // ignore
    }
    setState(null)
  }, [fullKey])

  return {
    storageAvailable,
    hasAutosave: storageAvailable && state !== null,
    savedAt: state?.savedAt ?? null,
    restore,
    clear,
    save,
  }
}
