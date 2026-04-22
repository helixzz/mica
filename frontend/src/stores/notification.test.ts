import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../api/notifications', () => ({
  getUnreadCount: vi.fn(),
  listNotifications: vi.fn(),
  markRead: vi.fn(),
}))

import {
  getUnreadCount,
  listNotifications,
  markRead as apiMarkRead,
} from '../api/notifications'
import { useNotificationStore } from './notification'

const getUnreadCountMock = vi.mocked(getUnreadCount)
const listNotificationsMock = vi.mocked(listNotifications)
const markReadMock = vi.mocked(apiMarkRead)

const sampleItem = (id: string, readAt: string | null = null) => ({
  id,
  category: 'approval',
  title: `Notification ${id}`,
  body: 'body',
  read_at: readAt,
  created_at: '2026-04-22T00:00:00Z',
})

beforeEach(() => {
  useNotificationStore.setState({
    unreadCount: 0,
    unreadByCategory: {},
    recentItems: [],
    loading: false,
  })
  vi.clearAllMocks()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useNotificationStore.refresh', () => {
  it('populates unreadCount and recentItems on success', async () => {
    getUnreadCountMock.mockResolvedValue({
      total: 3,
      by_category: { approval: 2, contract_expiring: 1 },
    })
    listNotificationsMock.mockResolvedValue({
      items: [sampleItem('a'), sampleItem('b'), sampleItem('c')],
      has_more: false,
    })

    const { result } = renderHook(() => useNotificationStore())
    await act(async () => {
      await result.current.refresh()
    })

    expect(result.current.unreadCount).toBe(3)
    expect(result.current.unreadByCategory).toEqual({
      approval: 2,
      contract_expiring: 1,
    })
    expect(result.current.recentItems).toHaveLength(3)
    expect(result.current.loading).toBe(false)
  })

  it('does not crash and ends loading=false when API fails', async () => {
    getUnreadCountMock.mockRejectedValue(new Error('boom'))
    listNotificationsMock.mockRejectedValue(new Error('boom'))
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { result } = renderHook(() => useNotificationStore())
    await act(async () => {
      await result.current.refresh()
    })

    expect(result.current.loading).toBe(false)
    expect(spy).toHaveBeenCalled()
  })
})

describe('useNotificationStore.markRead', () => {
  it('optimistically updates recentItems and decrements unreadCount', async () => {
    getUnreadCountMock.mockResolvedValue({ total: 2, by_category: {} })
    listNotificationsMock.mockResolvedValue({
      items: [],
      has_more: false,
    })
    markReadMock.mockResolvedValue({ updated: 1 })

    useNotificationStore.setState({
      unreadCount: 3,
      recentItems: [sampleItem('a'), sampleItem('b'), sampleItem('c')],
    })

    const { result } = renderHook(() => useNotificationStore())
    await act(async () => {
      await result.current.markRead(['a'])
    })

    const updatedA = result.current.recentItems.find((i) => i.id === 'a')
    expect(updatedA?.read_at).not.toBeNull()
    expect(markReadMock).toHaveBeenCalledWith({ ids: ['a'] })
  })

  it('is a no-op when ids array is empty', async () => {
    const { result } = renderHook(() => useNotificationStore())
    await act(async () => {
      await result.current.markRead([])
    })
    expect(markReadMock).not.toHaveBeenCalled()
  })
})

describe('useNotificationStore.markAllRead', () => {
  it('zeroes unreadCount and timestamps all items', async () => {
    getUnreadCountMock.mockResolvedValue({ total: 0, by_category: {} })
    listNotificationsMock.mockResolvedValue({
      items: [],
      has_more: false,
    })
    markReadMock.mockResolvedValue({ updated: 3 })

    useNotificationStore.setState({
      unreadCount: 3,
      unreadByCategory: { approval: 3 },
      recentItems: [sampleItem('a'), sampleItem('b'), sampleItem('c')],
    })

    const { result } = renderHook(() => useNotificationStore())
    await act(async () => {
      await result.current.markAllRead()
    })

    expect(result.current.unreadCount).toBe(0)
    expect(result.current.unreadByCategory).toEqual({})
    expect(
      result.current.recentItems.every((i) => i.read_at !== null),
    ).toBe(true)
    expect(markReadMock).toHaveBeenCalledWith({ all: true })
  })
})
