import { act, render, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Component, ReactNode } from 'react'
import { ThemeProvider, useTheme } from './ThemeProvider'

const wrapper = ({ children }: { children: ReactNode }) => (
  <ThemeProvider>{children}</ThemeProvider>
)

class ErrorBoundary extends Component<
  { children: ReactNode; onError: (error: Error) => void },
  { hasError: boolean }
> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error) {
    this.props.onError(error)
  }

  render() {
    return this.state.hasError ? null : this.props.children
  }
}

function HookProbe() {
  useTheme()
  return null
}

beforeEach(() => {
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('<ThemeProvider /> and useTheme', () => {
  it('defaults to system mode when no localStorage entry', () => {
    const { result } = renderHook(() => useTheme(), { wrapper })
    expect(result.current.mode).toBe('system')
  })

  it('reads stored mode from localStorage on init', () => {
    localStorage.setItem('mica.theme', 'dark')
    const { result } = renderHook(() => useTheme(), { wrapper })
    expect(result.current.mode).toBe('dark')
    expect(result.current.resolvedMode).toBe('dark')
  })

  it('setMode persists to localStorage', () => {
    const { result } = renderHook(() => useTheme(), { wrapper })
    act(() => {
      result.current.setMode('dark')
    })
    expect(localStorage.getItem('mica.theme')).toBe('dark')
    expect(result.current.mode).toBe('dark')
  })

  it('setMode updates data-theme attr on documentElement', () => {
    const { result } = renderHook(() => useTheme(), { wrapper })
    act(() => {
      result.current.setMode('dark')
    })
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')

    act(() => {
      result.current.setMode('light')
    })
    expect(document.documentElement.getAttribute('data-theme')).toBe('light')
  })

  it('system mode with prefers-dark resolves to dark', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation((q: string) => ({
      matches: q.includes('dark'),
      media: q,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    } as unknown as MediaQueryList))

    const { result } = renderHook(() => useTheme(), { wrapper })
    expect(result.current.resolvedMode).toBe('dark')
  })

  it('system mode with prefers-light resolves to light', () => {
    vi.spyOn(window, 'matchMedia').mockImplementation((q: string) => ({
      matches: false,
      media: q,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    } as unknown as MediaQueryList))

    const { result } = renderHook(() => useTheme(), { wrapper })
    expect(result.current.resolvedMode).toBe('light')
  })

  it('throws when useTheme called outside provider', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    let thrown: unknown

    render(
      <ErrorBoundary onError={(error) => {
        thrown = error
      }}>
        <HookProbe />
      </ErrorBoundary>,
    )

    try {
      expect(thrown).toBeInstanceOf(Error)
      expect((thrown as Error).message).toMatch(
        /useTheme must be used within a ThemeProvider/,
      )
    } finally {
      spy.mockRestore()
    }
  })
})
