import { renderWithProviders, screen, waitFor } from '@/test/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api'
import { DeliveryPlansPage } from '@/pages/DeliveryPlans'

vi.mock('@/api', async () => {
  const actual = await vi.importActual<typeof import('@/api')>('@/api')
  return {
    ...actual,
    api: {
      ...actual.api,
      getDeliveryPlansOverview: vi.fn(),
      listPOs: vi.fn(),
      listContracts: vi.fn(),
    },
  }
})

vi.mock('@/components/DeliveryPlanModal', () => ({
  DeliveryPlanModal: (_props: { open: boolean; onClose: () => void; onSuccess: () => void; plan?: unknown }) => null,
}))

const mockOverview = {
  total_planned: 100,
  total_actual: 45,
  completion_pct: 45,
  plans: [
    {
      id: 'plan-1',
      po_id: 'po-1',
      contract_id: null,
      item_id: 'item-1',
      item_name: 'Test Server',
      plan_name: 'Batch 1',
      planned_qty: 10,
      actual_qty: 5,
      planned_date: '2026-06-01',
      status: 'partial' as const,
      notes: 'First delivery',
    },
    {
      id: 'plan-2',
      po_id: 'po-2',
      contract_id: 'ct-1',
      item_id: 'item-2',
      item_name: 'Test Router',
      plan_name: 'Complete delivery',
      planned_qty: 20,
      actual_qty: 20,
      planned_date: '2026-05-15',
      status: 'complete' as const,
      notes: null,
    },
  ],
}

const mockEmptyOverview = {
  total_planned: 0,
  total_actual: 0,
  completion_pct: 0,
  plans: [],
}

const mockPOs = [
  { id: 'po-1', po_number: 'PO-2026-001', total_amount: '5000' },
  { id: 'po-2', po_number: 'PO-2026-002', total_amount: '8000' },
]

const mockContracts = [
  {
    id: 'ct-1',
    contract_number: 'CT-2026-001',
    title: 'Annual IT Contract',
    supplier_name: 'IT Vendor Inc',
    start_date: '2026-01-01',
    end_date: '2026-12-31',
    total_amount: 100000,
    status: 'active',
  },
]

function mockAllResolved() {
  vi.mocked(api.getDeliveryPlansOverview).mockResolvedValue(mockOverview)
  vi.mocked(api.listPOs).mockResolvedValue(mockPOs)
  vi.mocked(api.listContracts).mockResolvedValue(mockContracts)
}

function mockEmpty() {
  vi.mocked(api.getDeliveryPlansOverview).mockResolvedValue(mockEmptyOverview)
  vi.mocked(api.listPOs).mockResolvedValue([])
  vi.mocked(api.listContracts).mockResolvedValue([])
}

describe('DeliveryPlansPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', async () => {
    mockEmpty()
    renderWithProviders(<DeliveryPlansPage />)
    await waitFor(() => {
      expect(screen.getByText('delivery_plan.title')).toBeInTheDocument()
    })
  })

  it('shows correct title', async () => {
    mockAllResolved()
    renderWithProviders(<DeliveryPlansPage />)
    await waitFor(() => {
      expect(screen.getByText('delivery_plan.title')).toBeInTheDocument()
    })
  })

  it('shows loading state', () => {
    const pending = new Promise<never>(() => {})
    vi.mocked(api.getDeliveryPlansOverview).mockReturnValue(pending)
    vi.mocked(api.listPOs).mockReturnValue(pending)
    vi.mocked(api.listContracts).mockReturnValue(pending)

    renderWithProviders(<DeliveryPlansPage />)
    expect(document.querySelector('.ant-spin')).toBeInTheDocument()
  })

  it('shows empty state when no plans', async () => {
    mockEmpty()
    renderWithProviders(<DeliveryPlansPage />)
    await waitFor(() => {
      expect(screen.getByText('delivery_plan.no_plans')).toBeInTheDocument()
    })
    expect(screen.getByText('delivery_plan.create_first')).toBeInTheDocument()
  })

  it('shows stat cards with overview data', async () => {
    mockAllResolved()
    renderWithProviders(<DeliveryPlansPage />)
    await waitFor(() => {
      expect(screen.getByText('delivery_plan.total_planned')).toBeInTheDocument()
    })
    expect(screen.getByText('delivery_plan.total_actual')).toBeInTheDocument()
    expect(screen.getByText('delivery_plan.completion')).toBeInTheDocument()
  })

  it('shows delivery plans in table', async () => {
    mockAllResolved()
    renderWithProviders(<DeliveryPlansPage />)
    await waitFor(() => {
      expect(screen.getByText('Test Server')).toBeInTheDocument()
    })
    expect(screen.getByText('Test Router')).toBeInTheDocument()
    expect(screen.getByText('Batch 1')).toBeInTheDocument()
  })

  it('handles API error without crashing', async () => {
    vi.mocked(api.getDeliveryPlansOverview).mockRejectedValue(new Error('server error'))
    vi.mocked(api.listPOs).mockRejectedValue(new Error('server error'))
    vi.mocked(api.listContracts).mockRejectedValue(new Error('server error'))

    renderWithProviders(<DeliveryPlansPage />)
    await waitFor(() => {
      expect(screen.getByText('delivery_plan.title')).toBeInTheDocument()
    })
  })

  it('shows new plan button', async () => {
    mockEmpty()
    renderWithProviders(<DeliveryPlansPage />)
    await waitFor(() => {
      expect(screen.getByText('delivery_plan.new_plan')).toBeInTheDocument()
    })
  })
})
