import { renderWithProviders, screen, waitFor } from '@/test/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api'
import ItemsPage from '@/pages/Items'

vi.mock('@/api', async () => {
  const actual = await vi.importActual<typeof import('@/api')>('@/api')
  return {
    ...actual,
    api: {
      ...actual.api,
      itemsPaginated: vi.fn(),
      getCategoryTree: vi.fn(),
    },
  }
})

vi.mock('@/utils/export', () => ({
  downloadCSV: vi.fn(),
}))

vi.mock('@/utils/undo', () => ({
  showUndoToast: vi.fn(),
}))

const mockItems = [
  {
    id: 'item-1',
    code: 'SRV-001',
    name: 'Test Server',
    category: null,
    category_id: null,
    uom: 'EA',
    specification: 'Test spec',
    requires_serial: false,
    is_enabled: true,
    is_deleted: false,
  },
  {
    id: 'item-2',
    code: 'SRV-002',
    name: 'Test Router',
    category: null,
    category_id: null,
    uom: 'EA',
    specification: 'Router spec',
    requires_serial: true,
    is_enabled: false,
    is_deleted: false,
  },
]

const mockCategories = [
  {
    id: 'cat-1',
    code: 'HW',
    label_zh: 'Hardware',
    label_en: 'Hardware',
    parent_id: null,
    level: 1,
    children: [],
  },
]

function mockEmpty() {
  vi.mocked(api.itemsPaginated).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    page_size: 50,
  })
  vi.mocked(api.getCategoryTree).mockResolvedValue(mockCategories)
}

function mockWithData() {
  vi.mocked(api.itemsPaginated).mockResolvedValue({
    items: mockItems,
    total: mockItems.length,
    page: 1,
    page_size: 50,
  })
  vi.mocked(api.getCategoryTree).mockResolvedValue(mockCategories)
}

describe('ItemsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders without crashing', async () => {
    mockEmpty()
    renderWithProviders(<ItemsPage />)
    await waitFor(() => {
      expect(screen.getByText('item.title')).toBeInTheDocument()
    })
  })

  it('shows correct title', async () => {
    mockEmpty()
    renderWithProviders(<ItemsPage />)
    await waitFor(() => {
      expect(screen.getByText('item.title')).toBeInTheDocument()
    })
  })

  it('shows loading state in table', () => {
    const pending = new Promise<never>(() => {})
    vi.mocked(api.itemsPaginated).mockReturnValue(pending)
    vi.mocked(api.getCategoryTree).mockResolvedValue(mockCategories)

    renderWithProviders(<ItemsPage />)
    expect(document.querySelector('.ant-spin')).toBeInTheDocument()
  })

  it('shows empty state when no items', async () => {
    mockEmpty()
    renderWithProviders(<ItemsPage />)
    await waitFor(() => {
      expect(screen.getByText('button.export_excel')).toBeInTheDocument()
    })
    expect(screen.getByText('item.count')).toBeInTheDocument()
  })

  it('shows items in table after data loads', async () => {
    mockWithData()
    renderWithProviders(<ItemsPage />)
    await waitFor(() => {
      expect(screen.getByText('Test Server')).toBeInTheDocument()
    })
    expect(screen.getByText('Test Router')).toBeInTheDocument()
  })

  it('shows category sidebar', async () => {
    mockWithData()
    renderWithProviders(<ItemsPage />)
    await waitFor(() => {
      expect(screen.getByText('item.category_label')).toBeInTheDocument()
    })
    expect(screen.getByText('Hardware')).toBeInTheDocument()
  })

  it('handles API error without crashing', async () => {
    vi.mocked(api.itemsPaginated).mockRejectedValue(new Error('server error'))
    vi.mocked(api.getCategoryTree).mockRejectedValue(new Error('server error'))

    renderWithProviders(<ItemsPage />)
    await waitFor(() => {
      expect(screen.getByText('item.title')).toBeInTheDocument()
    })
  })

  it('shows new item button', async () => {
    mockEmpty()
    renderWithProviders(<ItemsPage />)
    await waitFor(() => {
      expect(screen.getByText('item.new')).toBeInTheDocument()
    })
  })
})
