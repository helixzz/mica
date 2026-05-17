const CURRENCY_SYMBOLS: Record<string, string> = {
  CNY: '¥',
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
  KRW: '₩',
  HKD: 'HK$',
  TWD: 'NT$',
}

export function getCurrencySymbol(currency?: string): string {
  if (!currency) return '¥'
  return CURRENCY_SYMBOLS[currency] || currency
}

export function fmtPrice(value: number | string | null | undefined, currency = '¥'): string {
  if (value === null || value === undefined || value === '') return '-'
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '-'
  return `${currency}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function fmtAmount(value: number | string | null | undefined, currency?: string): string {
  if (value === null || value === undefined || value === '') return '-'
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '-'
  const symbol = getCurrencySymbol(currency)
  return `${symbol}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function fmtQty(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '-'
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '-'
  return n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}
