import { describe, expect, it } from 'vitest'
import { renderWithProviders, screen } from '@/test/utils'
import { EmptyState } from './EmptyState'

describe('<EmptyState />', () => {
  it('renders title', () => {
    renderWithProviders(<EmptyState title="没有数据" />)
    expect(screen.getByText('没有数据')).toBeInTheDocument()
  })

  it('renders description and action', () => {
    renderWithProviders(
      <EmptyState
        title="empty"
        description="尝试调整筛选条件"
        action={<button>清除筛选</button>}
      />,
    )
    expect(screen.getByText('尝试调整筛选条件')).toBeInTheDocument()
    expect(screen.getByText('清除筛选')).toBeInTheDocument()
  })

  it('renders default otter-empty illustration', () => {
    const { container } = renderWithProviders(<EmptyState title="x" />)
    const img = container.querySelector('img')
    expect(img).toBeInTheDocument()
    expect(img?.getAttribute('alt')).toBe('empty')
  })

  it('renders welcome illustration when specified', () => {
    const { container } = renderWithProviders(
      <EmptyState illustration="welcome" title="x" />,
    )
    const img = container.querySelector('img')
    expect(img?.getAttribute('alt')).toBe('welcome')
  })
})
