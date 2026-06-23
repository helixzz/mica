import React from 'react';
import { MonoNum, MonoId } from '../components/ui/Mono';

const CURRENCY_SYMBOLS: Record<string, string> = {
  CNY: '¥',
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
  KRW: '₩',
  HKD: 'HK$',
  TWD: 'NT$',
};

export function getCurrencySymbol(currency?: string): string {
  if (!currency) return '¥';
  return CURRENCY_SYMBOLS[currency] || currency;
}

export function fmtPrice(value: number | string | null | undefined, currency = '¥'): string {
  if (value === null || value === undefined || value === '') return '-';
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(n)) return '-';
  return `${currency}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function fmtAmount(value: number | string | null | undefined, currency?: string): string {
  if (value === null || value === undefined || value === '') return '-';
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(n)) return '-';
  const symbol = getCurrencySymbol(currency);
  return `${symbol}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function fmtQty(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '-';
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(n)) return '-';
  return n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

// JSX-returning variants for AntD Table `render` and other React contexts.
// They wrap the formatted string in <MonoNum> (JetBrains Mono + tabular-nums).
// See docs/DESIGN.md §4.2 — Mica VI Phase 2 (v1.40.0).

export function fmtAmountNode(
  value: number | string | null | undefined,
  currency?: string,
  align: 'left' | 'right' = 'right',
): React.ReactNode {
  const s = fmtAmount(value, currency);
  if (s === '-') return <span>-</span>;
  return <MonoNum align={align}>{s}</MonoNum>;
}

export function fmtQtyNode(
  value: number | string | null | undefined,
  align: 'left' | 'right' = 'right',
): React.ReactNode {
  const s = fmtQty(value);
  if (s === '-') return <span>-</span>;
  return <MonoNum align={align}>{s}</MonoNum>;
}

export function fmtIdNode(value: string | null | undefined): React.ReactNode {
  if (!value) return <span>-</span>;
  return <MonoId>{value}</MonoId>;
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export function fmtDate(value: string | Date | null | undefined, withTime = false): string {
  if (value == null || value === '') return '-';
  const d = value instanceof Date ? value : new Date(value);
  if (isNaN(d.getTime())) return '-';
  const date = `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
  if (!withTime) return date;
  return `${date} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

export function fmtDateNode(value: string | Date | null | undefined, withTime = false): React.ReactNode {
  const s = fmtDate(value, withTime);
  if (s === '-') return <span>-</span>;
  return <MonoNum>{s}</MonoNum>;
}
