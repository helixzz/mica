import { beforeEach, describe, expect, it, vi } from 'vitest'

const { getUiConfig } = vi.hoisted(() => ({ getUiConfig: vi.fn() }))

vi.mock('@/api', () => ({ api: { getUiConfig } }))

import { FALLBACK_PAGE_SIZE, useUiConfig } from '@/stores/uiConfig'

describe('useUiConfig', () => {
  beforeEach(() => {
    getUiConfig.mockReset()
    useUiConfig.setState({ defaultPageSize: null, loaded: false })
  })

  it('fetches the page size once and keeps it', async () => {
    getUiConfig.mockResolvedValue({ default_page_size: 50 })

    await useUiConfig.getState().load()

    expect(useUiConfig.getState().defaultPageSize).toBe(50)
    expect(useUiConfig.getState().loaded).toBe(true)

    // Boot-time call, then any late caller: only one request may go out.
    await useUiConfig.getState().load()
    expect(getUiConfig).toHaveBeenCalledTimes(1)
  })

  it('marks itself loaded when the request fails so tables can fall back', async () => {
    getUiConfig.mockRejectedValue(new Error('ui-config unavailable'))

    await useUiConfig.getState().load()

    expect(useUiConfig.getState().loaded).toBe(true)
    expect(useUiConfig.getState().defaultPageSize).toBeNull()
    expect(FALLBACK_PAGE_SIZE).toBe(20)
  })
})
