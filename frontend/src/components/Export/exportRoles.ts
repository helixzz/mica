import type { ExportDataset } from '@/api'

/**
 * Roles allowed to export any dataset. Mirrors ``EXPORT_ROLES`` in
 * ``backend/app/services/export_registry.py`` (AGENTS §5.15): any other role
 * gets 403 from ``GET /exports/{key}`` and an empty catalog.
 */
export const EXPORT_ROLES = ['admin', 'it_buyer', 'procurement_mgr', 'finance_auditor']

export function canExport(role: string | null | undefined): boolean {
  return EXPORT_ROLES.includes(role ?? '')
}

/** Pick the zh label when the current locale is Chinese, else the en one. */
export function bilingualLabel(
  language: string | undefined,
  labelZh: string | null | undefined,
  labelEn: string | null | undefined,
  fallback = '',
): string {
  const zh = (labelZh ?? '').trim()
  const en = (labelEn ?? '').trim()
  if ((language ?? '').startsWith('zh')) return zh || en || fallback
  return en || zh || fallback
}

export function datasetLabel(language: string | undefined, dataset: ExportDataset): string {
  return bilingualLabel(language, dataset.label_zh, dataset.label_en, dataset.key)
}
