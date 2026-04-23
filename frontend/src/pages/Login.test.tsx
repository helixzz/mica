import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api'
import { LoginPage } from '@/pages/Login'

vi.mock('@/api', async () => {
  const actual = await vi.importActual<typeof import('@/api')>('@/api')
  return {
    ...actual,
    api: {
      ...actual.api,
      loginOptions: vi.fn(),
    },
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows SSO button when login options enable saml', async () => {
    vi.mocked(api.loginOptions).mockResolvedValue({
      saml_enabled: true,
      saml_login_url: '/api/v1/saml/login',
    })

    renderWithProviders(<LoginPage />, { route: '/login' })

    expect(await screen.findByRole('button', { name: /SSO/i })).toBeInTheDocument()
  })

  it('redirects browser to saml login url when SSO button clicked', async () => {
    vi.mocked(api.loginOptions).mockResolvedValue({
      saml_enabled: true,
      saml_login_url: '/api/v1/saml/login',
    })
    const assign = vi.fn()
    const originalLocation = window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...originalLocation, assign },
    })

    renderWithProviders(<LoginPage />, { route: '/login' })

    fireEvent.click(await screen.findByRole('button', { name: /SSO/i }))

    expect(assign).toHaveBeenCalledWith('/api/v1/saml/login')
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
    })
  })

  it('hides SSO button when login options disable saml', async () => {
    vi.mocked(api.loginOptions).mockResolvedValue({
      saml_enabled: false,
      saml_login_url: null,
    })

    renderWithProviders(<LoginPage />, { route: '/login' })

    await waitFor(() => {
      expect(api.loginOptions).toHaveBeenCalled()
    })
    expect(screen.queryByRole('button', { name: /SSO/i })).not.toBeInTheDocument()
  })
})
