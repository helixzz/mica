import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
  api,
  flattenCategoryTree,
  type ExportDataset,
} from '@/api'
import { bilingualLabel } from './exportRoles'

export interface ExportSelectOption {
  value: string
  label: string
}

// The catalog is identical for every page and every opening of the drawer, so
// cache the in-flight/settled promise at module scope instead of refetching it
// on each of the 8 pages that host an export entry point.
let catalogPromise: Promise<ExportDataset[]> | null = null

export function fetchExportCatalog(): Promise<ExportDataset[]> {
  if (!catalogPromise) {
    catalogPromise = api.listExportDatasets().catch((error) => {
      catalogPromise = null // allow a later retry after a transient failure
      throw error
    })
  }
  return catalogPromise
}

/** Test seam: drop the module-level catalog cache. */
export function resetExportCatalogCache(): void {
  catalogPromise = null
}

export interface ExportCatalogState {
  datasets: ExportDataset[] | null
  loading: boolean
  dataset: ExportDataset | undefined
}

export function useExportCatalog(datasetKey: string, open: boolean): ExportCatalogState {
  const [datasets, setDatasets] = useState<ExportDataset[] | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || datasets) return
    let alive = true
    setLoading(true)
    fetchExportCatalog()
      .then((rows) => {
        if (alive) setDatasets(rows)
      })
      .catch(() => {
        if (alive) setDatasets([])
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [open, datasets])

  const dataset = useMemo(
    () => datasets?.find((entry) => entry.key === datasetKey),
    [datasets, datasetKey],
  )

  return { datasets, loading, dataset }
}

const LOOKUP_FILTERS = ['company', 'department', 'cost_center', 'category', 'supplier', 'item']

export type ExportLookups = Record<string, ExportSelectOption[]>

/**
 * Lazily loads only the master-data lists needed by the dataset's declared
 * filters. Lookups without an existing API are simply omitted.
 */
export function useExportLookups(filters: string[], open: boolean): ExportLookups {
  const { i18n } = useTranslation()
  const language = i18n.language
  const [lookups, setLookups] = useState<ExportLookups>({})

  const wanted = useMemo(
    () => filters.filter((key) => LOOKUP_FILTERS.includes(key)).sort().join(','),
    [filters],
  )

  useEffect(() => {
    if (!open || !wanted) return
    let alive = true
    const keys = wanted.split(',')

    const tasks: Promise<[string, ExportSelectOption[]]>[] = []
    if (keys.includes('company')) {
      tasks.push(
        api.companies().then((rows) => [
          'company',
          rows.map((c) => ({
            value: c.id,
            label: bilingualLabel(language, c.name_zh, c.name_en, c.code),
          })),
        ]),
      )
    }
    if (keys.includes('department')) {
      tasks.push(
        api.departments().then((rows) => [
          'department',
          rows.map((d) => ({
            value: d.id,
            label: bilingualLabel(language, d.name_zh, d.name_en, d.code),
          })),
        ]),
      )
    }
    if (keys.includes('cost_center')) {
      tasks.push(
        api.listCostCenters().then((rows) => [
          'cost_center',
          rows.map((c) => ({
            value: c.id,
            label: bilingualLabel(language, c.label_zh, c.label_en, c.code),
          })),
        ]),
      )
    }
    if (keys.includes('category')) {
      tasks.push(
        api.getCategoryTree().then((tree) => [
          'category',
          flattenCategoryTree(tree).map((c) => ({
            value: c.id,
            label: bilingualLabel(language, c.label_zh, c.label_en, c.code),
          })),
        ]),
      )
    }
    if (keys.includes('supplier')) {
      tasks.push(
        api.suppliers().then((rows) => [
          'supplier',
          rows.map((s) => ({ value: s.id, label: s.code ? `${s.name} (${s.code})` : s.name })),
        ]),
      )
    }
    if (keys.includes('item')) {
      tasks.push(
        api.items().then((rows) => [
          'item',
          rows.map((i) => ({ value: i.id, label: i.code ? `${i.name} (${i.code})` : i.name })),
        ]),
      )
    }

    Promise.all(tasks)
      .then((entries) => {
        if (alive) setLookups(Object.fromEntries(entries))
      })
      .catch(() => {
        if (alive) setLookups({})
      })
    return () => {
      alive = false
    }
  }, [open, wanted, language])

  return lookups
}
