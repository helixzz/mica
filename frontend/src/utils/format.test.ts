import { describe, expect, it } from 'vitest'

import { fmtAmount, fmtPrice, fmtQty } from './format'

describe('fmtPrice', () => {
  it('formats numeric values with the default currency', () => {
    expect(fmtPrice(1234.56)).toBe('¥1,234.56')
  })

  it('formats string values', () => {
    expect(fmtPrice('1234.5')).toBe('¥1,234.50')
  })

  it('supports custom currency symbols', () => {
    expect(fmtPrice(99.9, '$')).toBe('$99.90')
  })

  it('returns a dash for null values', () => {
    expect(fmtPrice(null)).toBe('-')
  })

  it('returns a dash for undefined values', () => {
    expect(fmtPrice(undefined)).toBe('-')
  })

  it('returns a dash for invalid strings', () => {
    expect(fmtPrice('not-a-number')).toBe('-')
  })
})

describe('fmtAmount', () => {
  it('formats numeric values with the default currency prefix', () => {
    expect(fmtAmount(1234.56)).toBe('¥1,234.56')
  })

  it('formats string values', () => {
    expect(fmtAmount('1234.5')).toBe('¥1,234.50')
  })

  it('supports custom currency codes', () => {
    expect(fmtAmount(99.9, 'USD')).toBe('USD 99.90')
  })

  it('returns a dash for null values', () => {
    expect(fmtAmount(null)).toBe('-')
  })

  it('returns a dash for undefined values', () => {
    expect(fmtAmount(undefined)).toBe('-')
  })

  it('returns a dash for empty strings', () => {
    expect(fmtAmount('')).toBe('-')
  })
})

describe('fmtQty', () => {
  it('hides decimals for integers', () => {
    expect(fmtQty(10)).toBe('10')
  })

  it('shows up to 2 decimals for fractional values', () => {
    expect(fmtQty(2.5)).toBe('2.5')
  })

  it('truncates to 2 decimals', () => {
    expect(fmtQty('10.1234')).toBe('10.12')
  })

  it('adds thousands separator', () => {
    expect(fmtQty(1500)).toBe('1,500')
  })

  it('returns a dash for null', () => {
    expect(fmtQty(null)).toBe('-')
  })

  it('strips trailing zeros from backend decimals', () => {
    expect(fmtQty('100.0000')).toBe('100')
  })
})
