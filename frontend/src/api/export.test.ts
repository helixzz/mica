import { describe, expect, it } from 'vitest'

import { buildExportUrl } from '@/api'

describe('buildExportUrl', () => {
  it('repeats the status param once per selected value', () => {
    const url = buildExportUrl('invoices', {
      format: 'csv',
      status: ['draft', 'paid'],
      date_from: '2026-01-01',
      date_to: '2026-01-31',
    })

    expect(url).toBe(
      '/api/v1/exports/invoices?format=csv&date_from=2026-01-01&date_to=2026-01-31&status=draft&status=paid',
    )
  })

  it('omits empty optional filters and keeps the dataset key path', () => {
    const url = buildExportUrl('suppliers', { format: 'xlsx', status: [], q: '' })
    expect(url).toBe('/api/v1/exports/suppliers?format=xlsx')
  })

  it('adds a leading ? only when there is at least one param', () => {
    expect(buildExportUrl('items')).toBe('/api/v1/exports/items')
  })
})
