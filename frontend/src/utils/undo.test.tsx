import { fireEvent, render, screen } from '@testing-library/react'
import { notification } from 'antd'
import type { ReactElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { showUndoToast } from '@/utils/undo'

describe('showUndoToast', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a toast whose button runs the undo callback', () => {
    const onUndo = vi.fn()
    const infoSpy = vi.spyOn(notification, 'info')
    const destroySpy = vi.spyOn(notification, 'destroy')

    showUndoToast('Purchase order deleted', onUndo, 7)

    expect(infoSpy).toHaveBeenCalledTimes(1)
    const config = infoSpy.mock.calls[0][0]
    expect(config.message).toBe('Purchase order deleted')
    expect(config.duration).toBe(7)

    // The undo affordance lives inside the toast, so render it in isolation.
    render(config.btn as ReactElement)
    fireEvent.click(screen.getByText('Undo'))

    expect(onUndo).toHaveBeenCalledTimes(1)
    expect(destroySpy).toHaveBeenCalledWith(config.key)
  })
})
