import { renderWithProviders, screen, waitFor } from '@/test/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api'
import { DashboardPage } from '@/pages/Dashboard'

vi.mock('@/api', async () => {
  const actual = await vi.importActual<typeof import('@/api')>('@/api')
  return {
    ...actual,
    api: {
      ...actual.api,
      listPRs: vi.fn(),
      listPOs: vi.fn(),
      myPendingApprovals: vi.fn(),
      listExpiringContracts: vi.fn(),
      listSKUAnomalies: vi.fn(),
      getDashboardMetrics: vi.fn(),
      getDeliveryPlansOverview: vi.fn(),
      getBudgetSummary: vi.fn(),
      getAgingApprovals: vi.fn(),
    },
  }
})

vi.mock('@/auth/useAuth', () => ({
  useAuth: () => ({
    user: {
      id: '1',
      username: 'admin',
      role: 'admin',
      display_name: 'Admin',
      email: 'admin@test.com',
      company_id: 'c1',
      department_id: null,
      preferred_locale: 'zh-CN',
      is_active: true,
    },
    loading: false,
    initialized: true,
  }),
}))

vi.mock('@/components/PaymentForecastChart', () => ({
  PaymentTracker: () => <div data-testid="payment-tracker">PaymentTracker</div>,
}))

vi.mock('@/components/InvoiceTrackerChart', () => ({
  InvoiceTracker: () => <div data-testid="invoice-tracker">InvoiceTracker</div>,
}))

function mockAllResolved() {
  vi.mocked(api.listPRs).mockResolvedValue([])
  vi.mocked(api.listPOs).mockResolvedValue([])
  vi.mocked(api.myPendingApprovals).mockResolvedValue([])
  vi.mocked(api.listExpiringContracts).mockResolvedValue([])
  vi.mocked(api.listSKUAnomalies).mockResolvedValue([])
  vi.mocked(api.getDashboardMetrics).mockResolvedValue(null)
  vi.mocked(api.getDeliveryPlansOverview).mockResolvedValue(null)
  vi.mocked(api.getBudgetSummary).mockResolvedValue(null)
  vi.mocked(api.getAgingApprovals).mockResolvedValue([])
}

function mockAllPending() {
  const pending = new Promise<never>(() => {})
  vi.mocked(api.listPRs).mockReturnValue(pending)
  vi.mocked(api.listPOs).mockReturnValue(pending)
  vi.mocked(api.myPendingApprovals).mockReturnValue(pending)
  vi.mocked(api.listExpiringContracts).mockReturnValue(pending)
  vi.mocked(api.listSKUAnomalies).mockReturnValue(pending)
  vi.mocked(api.getDashboardMetrics).mockReturnValue(pending)
  vi.mocked(api.getDeliveryPlansOverview).mockReturnValue(pending)
  vi.mocked(api.getBudgetSummary).mockReturnValue(pending)
  vi.mocked(api.getAgingApprovals).mockReturnValue(pending)
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', async () => {
    mockAllResolved()
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText(/Admin/)).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    mockAllPending()
    renderWithProviders(<DashboardPage />)
    const loadingElements = screen.getAllByText('message.loading')
    expect(loadingElements.length).toBeGreaterThan(0)
  })

  it('shows page title with user greeting', async () => {
    mockAllResolved()
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText(/Admin/)).toBeInTheDocument()
    })
  })

  it('shows stat cards after data loads', async () => {
    mockAllResolved()
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('nav.purchase_requisitions')).toBeInTheDocument()
    })
    expect(screen.getByText('nav.purchase_orders')).toBeInTheDocument()
    expect(screen.getByText('nav.approvals')).toBeInTheDocument()
    expect(screen.getByText('dashboard.total_amount_cny')).toBeInTheDocument()
  })

  it('shows alerts section', async () => {
    mockAllResolved()
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('dashboard.alerts')).toBeInTheDocument()
    })
  })

  it('shows pending approvals section', async () => {
    mockAllResolved()
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('dashboard.pending_approvals')).toBeInTheDocument()
    })
  })

  it('handles API failures without crashing', async () => {
    vi.mocked(api.listPRs).mockRejectedValue(new Error('network error'))
    vi.mocked(api.listPOs).mockRejectedValue(new Error('network error'))
    vi.mocked(api.myPendingApprovals).mockRejectedValue(new Error('network error'))
    vi.mocked(api.listExpiringContracts).mockRejectedValue(new Error('network error'))
    vi.mocked(api.listSKUAnomalies).mockRejectedValue(new Error('network error'))
    vi.mocked(api.getDashboardMetrics).mockRejectedValue(new Error('network error'))
    vi.mocked(api.getDeliveryPlansOverview).mockRejectedValue(new Error('network error'))
    vi.mocked(api.getBudgetSummary).mockRejectedValue(new Error('network error'))
    vi.mocked(api.getAgingApprovals).mockRejectedValue(new Error('network error'))

    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('dashboard.alerts')).toBeInTheDocument()
    })
  })

  it('shows quick actions section', async () => {
    mockAllResolved()
    renderWithProviders(<DashboardPage />)
    await waitFor(() => {
      expect(screen.getByText('dashboard.quick_actions')).toBeInTheDocument()
    })
  })
})
