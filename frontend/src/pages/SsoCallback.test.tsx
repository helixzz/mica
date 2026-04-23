import { renderWithProviders, screen, waitFor } from '@/test/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from '@/auth/useAuth'
import { SsoCallbackPage } from '@/pages/SsoCallback'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('SsoCallbackPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    mockNavigate.mockReset()
    useAuth.setState({
      user: null,
      loading: false,
      initialized: false,
      login: async () => {},
      loginWithToken: async () => {},
      logout: () => {},
      loadMe: async () => {},
    })
  })

  it('stores token through auth flow and navigates to next path', async () => {
    const loginWithToken = vi.fn().mockResolvedValue(undefined)
    const replaceState = vi.spyOn(window.history, 'replaceState')
    useAuth.setState({ loginWithToken })
    window.location.hash = '#token=fake.jwt.token&next=%2Fdashboard'

    renderWithProviders(<SsoCallbackPage />, { route: '/sso-callback' })

    await waitFor(() => {
      expect(loginWithToken).toHaveBeenCalledWith('fake.jwt.token')
    })
    expect(replaceState).toHaveBeenCalledWith(null, '', '/sso-callback')
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
  })

  it('shows an error when hash token is missing', async () => {
    window.location.hash = ''

    renderWithProviders(<SsoCallbackPage />, { route: '/sso-callback' })

    expect(await screen.findByRole('alert')).toHaveTextContent(/SSO/i)
  })
})
