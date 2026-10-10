import { act, fireEvent, renderWithProviders, screen, waitFor } from '@/test/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type Contract, type ContractSearchHit } from '@/api'
import { useAuth } from '@/auth/useAuth'
import { useUiConfig } from '@/stores/uiConfig'
import { ContractsPage } from '@/pages/Contracts'

vi.mock('@/api', async () => {
  const actual = await vi.importActual<typeof import('@/api')>('@/api')
  return {
    ...actual,
    api: {
      ...actual.api,
      listContracts: vi.fn(),
      listExpiringContracts: vi.fn(),
      searchContracts: vi.fn(),
    },
  }
})

function makeContracts(count: number): Contract[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `c-${index}`,
    contract_number: `CT-2026-${String(index).padStart(4, '0')}`,
    po_id: `po-${index}`,
    po_number: `PO-2026-${index}`,
    supplier_id: 's-1',
    supplier_name: 'Supplier',
    title: `Contract ${index}`,
    current_version: 1,
    status: 'active',
    currency: 'CNY',
    total_amount: '1000',
    signed_date: null,
    effective_date: null,
    expiry_date: null,
    notes: null,
    created_at: '2026-01-01T00:00:00Z',
  })) as unknown as Contract[]
}

const HITS: ContractSearchHit[] = [
  {
    id: 'c-7',
    contract_number: 'CT-2026-0007',
    title: 'Matched contract',
    status: 'active',
    total_amount: '1000',
    expiry_date: null,
    matched_in: ['title'],
  },
] as unknown as ContractSearchHit[]

function tableDataRows(): number {
  const all = Array.from(document.querySelectorAll('tbody tr'))
  // Search hits, expiring list and the main list share the DOM; count only rows
  // that carry a contract id in the main (last) table.
  const mainTable = document.querySelectorAll('.ant-table-wrapper')
  const last = mainTable[mainTable.length - 1] as HTMLElement | undefined
  return last ? last.querySelectorAll('tbody tr.ant-table-row').length : all.length
}

describe('ContractsPage — search and page size', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useAuth.setState({
      user: {
        id: 'u-1',
        username: 'admin',
        email: 'admin@mica.local',
        display_name: 'Admin',
        role: 'admin',
        company_id: 'co-1',
        department_id: null,
        preferred_locale: 'zh-CN',
        is_active: true,
      },
      loading: false,
      initialized: true,
    })
    vi.mocked(api.listExpiringContracts).mockResolvedValue([])
    // Empty page-size config: tables fall back to their own default.
    useUiConfig.setState({ defaultPageSize: null, loaded: true })
  })

  it('renders the search hits returned by the backend', async () => {
    vi.mocked(api.listContracts).mockResolvedValue(makeContracts(3))
    vi.mocked(api.searchContracts).mockResolvedValue(HITS)

    renderWithProviders(<ContractsPage />, { route: '/contracts' })

    await waitFor(() => expect(api.listContracts).toHaveBeenCalled())

    const searchInput = document.querySelector('.ant-input-search input') as HTMLInputElement
    fireEvent.change(searchInput, { target: { value: 'matched' } })
    fireEvent.click(document.querySelector('.ant-input-search-button') as Element)

    await waitFor(() => expect(api.searchContracts).toHaveBeenCalledWith('matched'))
    expect(await screen.findByText('Matched contract')).toBeInTheDocument()
  })

  it('shows an empty state when the search matches nothing', async () => {
    vi.mocked(api.listContracts).mockResolvedValue(makeContracts(3))
    vi.mocked(api.searchContracts).mockResolvedValue([])

    renderWithProviders(<ContractsPage />, { route: '/contracts' })
    await waitFor(() => expect(api.listContracts).toHaveBeenCalled())

    const searchInput = document.querySelector('.ant-input-search input') as HTMLInputElement
    fireEvent.change(searchInput, { target: { value: 'zzz-no-match' } })
    fireEvent.click(document.querySelector('.ant-input-search-button') as Element)

    await waitFor(() => expect(api.searchContracts).toHaveBeenCalledWith('zzz-no-match'))
    // Before this fix a zero-hit search rendered nothing at all, which read as
    // "search is broken". Assert on the placeholder echoing the query rather
    // than on localized copy, so the test survives copy changes.
    await waitFor(() =>
      expect(
        document.querySelector('.ant-table-placeholder')?.textContent ?? '',
      ).toContain('zzz-no-match'),
    )
  })

  it('reports a failed search instead of failing silently', async () => {
    vi.mocked(api.listContracts).mockResolvedValue(makeContracts(3))
    vi.mocked(api.searchContracts).mockRejectedValue(new Error('boom'))

    renderWithProviders(<ContractsPage />, { route: '/contracts' })
    await waitFor(() => expect(api.listContracts).toHaveBeenCalled())

    const searchInput = document.querySelector('.ant-input-search input') as HTMLInputElement
    fireEvent.change(searchInput, { target: { value: 'boom' } })
    fireEvent.click(document.querySelector('.ant-input-search-button') as Element)

    await waitFor(() => expect(api.searchContracts).toHaveBeenCalled())
    await waitFor(() =>
      expect(document.querySelector('.ant-message-error')).not.toBeNull(),
    )
  })

  it('starts from pagination.default_page_size when it is configured', async () => {
    useUiConfig.setState({ defaultPageSize: 50, loaded: true })
    vi.mocked(api.listContracts).mockResolvedValue(makeContracts(60))
    vi.mocked(api.searchContracts).mockResolvedValue([])

    renderWithProviders(<ContractsPage />, { route: '/contracts' })

    await waitFor(() => expect(api.listContracts).toHaveBeenCalled())
    // The system parameter used to be read by nobody.
    await waitFor(() => expect(tableDataRows()).toBe(50))
  })

  it('keeps the size the user picked when the config arrives late', async () => {
    vi.mocked(api.listContracts).mockResolvedValue(makeContracts(60))
    vi.mocked(api.searchContracts).mockResolvedValue([])

    renderWithProviders(<ContractsPage />, { route: '/contracts' })
    await waitFor(() => expect(tableDataRows()).toBe(20))

    const sizeChanger = document.querySelector('.ant-pagination-options .ant-select-selector')
    fireEvent.mouseDown(sizeChanger as Element)
    fireEvent.click(await screen.findByTitle('50 / page'))
    await waitFor(() => expect(tableDataRows()).toBe(50))

    // Simulate the bootstrap response landing after the user already chose.
    act(() => useUiConfig.setState({ defaultPageSize: 100, loaded: true }))
    await waitFor(() => expect(tableDataRows()).toBe(50))
  })

  it('honours a page-size change on the main table', async () => {
    vi.mocked(api.listContracts).mockResolvedValue(makeContracts(60))
    vi.mocked(api.searchContracts).mockResolvedValue([])

    renderWithProviders(<ContractsPage />, { route: '/contracts' })

    await waitFor(() => expect(api.listContracts).toHaveBeenCalled())
    await waitFor(() => expect(tableDataRows()).toBe(20))

    const sizeChanger = document.querySelector('.ant-pagination-options .ant-select-selector')
    expect(sizeChanger).not.toBeNull()

    fireEvent.mouseDown(sizeChanger as Element)
    const option50 = await screen.findByTitle('50 / page')
    fireEvent.click(option50)

    await waitFor(() => expect(tableDataRows()).toBe(50))
  })
})
