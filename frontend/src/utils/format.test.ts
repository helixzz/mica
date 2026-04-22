import { describe, expect, it } from 'vitest'

import { fmtAmount, fmtPrice } from './format'

describe('fmtPrice', () => {
  it('formats numeric values with the default currency', () => {
    expect(fmtPrice(1234.56)).toBe('¥1,234.56')
  })

  it('formats string values', () => {
    expect(fmtPrice('1234.5')).toBe('¥1,234.5')
  })

  it('supports custom currency symbols', () => {
    expect(fmtPrice(99.9, '$')).toBe('$99.9')
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
    expect(fmtAmount('1234.5')).toBe('¥1,234.5')
  })

  it('supports custom currency codes', () => {
    expect(fmtAmount(99.9, 'USD')).toBe('USD 99.9')
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
