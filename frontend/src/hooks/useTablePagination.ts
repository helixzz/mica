import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { FALLBACK_PAGE_SIZE, useUiConfig } from '@/stores/uiConfig'

const PAGE_SIZE_OPTIONS = ['10', '20', '50', '100']

/**
 * Client-side table pagination that actually keeps the page size.
 *
 * Passing `pagination={{ pageSize: 20 }}` to an AntD Table looks reasonable but
 * breaks the size changer: `usePagination` merges `extendsObject(inner, props)`,
 * so the prop's `pageSize` overwrites the value the user picked on every render
 * and the table snaps back. AntD only honours a size change when the page size
 * lives in app state (or is passed as `defaultPageSize`), so this hook keeps it
 * and returns a ready-to-spread pagination config.
 */
export function useTablePagination(initialPageSize?: number) {
  const { t } = useTranslation()
  const configuredPageSize = useUiConfig((s) => s.defaultPageSize)
  const [current, setCurrent] = useState(1)
  const [pageSize, setPageSize] = useState(
    initialPageSize ?? configuredPageSize ?? FALLBACK_PAGE_SIZE,
  )
  const sizeChosenByUser = useRef(false)

  // The config arrives with the session bootstrap, which can land after the
  // first render; adopt it unless the user already picked a size.
  useEffect(() => {
    if (initialPageSize === undefined && !sizeChosenByUser.current && configuredPageSize) {
      setPageSize(configuredPageSize)
    }
  }, [configuredPageSize, initialPageSize])

  const pagination = useMemo(
    () => ({
      current,
      pageSize,
      showSizeChanger: true,
      pageSizeOptions: PAGE_SIZE_OPTIONS,
      showTotal: (total: number) => t('item.total_count', { total }),
      onChange: (page: number, size: number) => {
        sizeChosenByUser.current = true
        setCurrent(page)
        setPageSize(size)
      },
    }),
    [current, pageSize, t],
  )

  return { pagination, pageSize, current, setCurrent }
}
