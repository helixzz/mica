import { renderWithProviders, waitFor } from '@/test/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type ExportDataset } from '@/api'
import { ExportDrawer, resetExportCatalogCache } from '@/components/Export'

vi.mock('@/api', async () => {
  const actual = await vi.importActual<typeof import('@/api')>('@/api')
  return {
    ...actual,
    api: {
      ...actual.api,
      listExportDatasets: vi.fn(),
    },
  }
})

const CATALOG: ExportDataset[] = [
  {
    key: 'purchase_requisitions',
    label_zh: '采购申请',
    label_en: 'Purchase Requisitions',
    filters: ['date_range', 'status'],
    status_values: ['draft', 'approved'],
    sheets: [],
  },
  {
    key: 'suppliers',
    label_zh: '供应商',
    label_en: 'Suppliers',
    filters: ['keyword'],
    status_values: [],
    sheets: [],
  },
]

function openDrawer(datasetKey: string) {
  return renderWithProviders(
    <ExportDrawer datasetKey={datasetKey} open onClose={() => {}} />,
  )
}

const formItems = () => document.querySelectorAll('.ant-form-item')

describe('ExportDrawer', () => {
  beforeEach(() => {
    resetExportCatalogCache()
    vi.mocked(api.listExportDatasets).mockResolvedValue(CATALOG)
  })

  it('renders only the keyword filter for the suppliers dataset', async () => {
    openDrawer('suppliers')

    await waitFor(() => expect(formItems()).toHaveLength(2)) // keyword + format

    expect(document.querySelectorAll('.ant-picker')).toHaveLength(0)
    expect(document.querySelectorAll('.ant-select')).toHaveLength(0)
    expect(document.querySelectorAll('input.ant-input')).toHaveLength(1)
  })

  it('renders a date range and a status select for purchase requisitions', async () => {
    openDrawer('purchase_requisitions')

    await waitFor(() => expect(formItems()).toHaveLength(3)) // date_range + status + format

    expect(document.querySelectorAll('.ant-picker').length).toBeGreaterThan(0)
    expect(document.querySelectorAll('.ant-select').length).toBeGreaterThan(0)
    expect(document.querySelectorAll('input.ant-input')).toHaveLength(0)
  })

  it('shows the unavailable hint when the dataset is not in the catalog', async () => {
    vi.mocked(api.listExportDatasets).mockResolvedValue([])

    openDrawer('suppliers')

    const exportButton = document.querySelector<HTMLButtonElement>(
      '.ant-drawer-footer button.ant-btn-primary',
    )
    await waitFor(() => expect(exportButton).toBeDisabled())
    expect(formItems()).toHaveLength(0)
  })
})
