import { fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router-dom'

import { api, type PurchaseRequisition } from '@/api'
import { useAuth } from '@/auth/useAuth'
import { PRDetailPage } from '@/pages/PurchaseRequisitions/PRDetail'

vi.mock('@/api', async () => {
  const actual = await vi.importActual<typeof import('@/api')>('@/api')
  return {
    ...actual,
    api: {
      ...actual.api,
      getPR: vi.fn(),
      getPRDownstream: vi.fn(),
      suppliers: vi.fn(),
      listCollaboratorCandidates: vi.fn(),
      listProxyCandidates: vi.fn(),
    },
  }
})

const PR_ID = 'pr-1'

function makePR(overrides: Partial<PurchaseRequisition> = {}): PurchaseRequisition {
  return {
    id: PR_ID,
    pr_number: 'PR-2026-0100',
    title: 'Prod 防火墙采购',
    business_reason: null,
    status: 'draft',
    requester_id: 'u-chris',
    requester_name: 'Chris Wang',
    company_id: 'c-1',
    company_name: 'General',
    department_id: null,
    department_name: 'IT',
    cost_center_id: null,
    cost_center_name: '',
    expense_type_id: null,
    procurement_category_id: null,
    currency: 'CNY',
    total_amount: '0',
    required_date: null,
    delivery_address: null,
    delivery_contact_name: null,
    delivery_contact_phone: null,
    delivery_address_id: null,
    expected_delivery_date: null,
    submitted_at: null,
    decided_at: null,
    decided_by_id: null,
    decision_comment: null,
    preferred_first_approver_id: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    items: [],
    collaborators: [],
    ...overrides,
  }
}

function signIn(role: string, id = 'u-chris') {
  useAuth.setState({
    user: {
      id,
      username: 'chris_wang',
      email: 'chris.wang@general-int.com',
      display_name: 'Chris Wang',
      role,
      department_id: null,
      company_id: 'c-1',
    } as never,
    initialized: true,
    loading: false,
  })
}

function renderDetail() {
  return renderWithProviders(
    <Routes>
      <Route path="/purchase-requisitions/:id" element={<PRDetailPage />} />
    </Routes>,
    { route: `/purchase-requisitions/${PR_ID}` },
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getPR).mockResolvedValue(makePR())
  vi.mocked(api.getPRDownstream).mockResolvedValue({ purchase_orders: [], contracts: [] })
  vi.mocked(api.suppliers).mockResolvedValue([])
  vi.mocked(api.listCollaboratorCandidates).mockResolvedValue([
    {
      id: 'u-jean',
      display_name: 'Jean Wu',
      email: 'jean.wu@general-int.com',
      role: 'requester',
      department_id: null,
    },
  ])
})

describe('PR detail collaborators', () => {
  // Regression guard for v1.73.3: the picker used /proxy-candidates, which is
  // only served to admin/procurement_mgr/it_buyer. A requester managing their
  // own PR then got 403, the error was swallowed, and the dropdown rendered as
  // "user not found" — so they could not add anybody.
  it('offers the PR requester colleagues from the collaborator endpoint', async () => {
    signIn('requester')
    const { container } = renderDetail()

    await waitFor(() => expect(api.listCollaboratorCandidates).toHaveBeenCalledWith(PR_ID))
    expect(api.listProxyCandidates).not.toHaveBeenCalled()

    const selector = container.querySelector('.ant-select-selector') as HTMLElement
    expect(selector).not.toBeNull()
    fireEvent.mouseDown(selector)

    await waitFor(() =>
      expect(screen.getByText('Jean Wu (jean.wu@general-int.com)')).toBeInTheDocument(),
    )
  })

  it('hides the picker from roles that may not manage collaborators', async () => {
    signIn('finance_auditor', 'u-carol')
    const { container } = renderDetail()

    await waitFor(() => expect(api.getPR).toHaveBeenCalledWith(PR_ID))
    await waitFor(() => expect(api.getPRDownstream).toHaveBeenCalledWith(PR_ID))

    expect(container.querySelector('.ant-select-selector')).toBeNull()
    expect(api.listCollaboratorCandidates).not.toHaveBeenCalled()
  })
})
