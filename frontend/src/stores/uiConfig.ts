import { create } from 'zustand'

import { api } from '@/api'

export const FALLBACK_PAGE_SIZE = 20

interface UiConfigState {
  /** ``pagination.default_page_size`` from system_parameters; null until loaded. */
  defaultPageSize: number | null
  loaded: boolean
  load: () => Promise<void>
}

/**
 * UI configuration delivered by ``GET /ui-config``.
 *
 * ``pagination.default_page_size`` used to be a setting nothing read, so admins
 * could change it with no effect. It is fetched once per session at boot.
 */
export const useUiConfig = create<UiConfigState>((set, get) => ({
  defaultPageSize: null,
  loaded: false,
  load: async () => {
    if (get().loaded) return
    try {
      const config = await api.getUiConfig()
      set({ defaultPageSize: config.default_page_size, loaded: true })
    } catch {
      // A failure here must not block the app; tables fall back to 20.
      set({ loaded: true })
    }
  },
}))
