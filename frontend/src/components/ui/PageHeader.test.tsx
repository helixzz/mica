import { describe, expect, it } from 'vitest'
import { renderWithProviders, screen } from '@/test/utils'
import { PageHeader } from './PageHeader'

describe('<PageHeader />', () => {
  it('renders title', () => {
    renderWithProviders(<PageHeader title="仪表盘" />)
    expect(screen.getByText('仪表盘')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    renderWithProviders(
      <PageHeader title="x" subtitle="欢迎回来" />,
    )
    expect(screen.getByText('欢迎回来')).toBeInTheDocument()
  })

  it('renders breadcrumbs when provided', () => {
    renderWithProviders(
      <PageHeader
        title="详情"
        breadcrumbs={[{ title: '首页', href: '/' }, { title: '详情' }]}
      />,
    )
    expect(screen.getByText('首页')).toBeInTheDocument()
  })

  it('renders actions slot', () => {
    renderWithProviders(
      <PageHeader title="x" actions={<button>新建</button>} />,
    )
    expect(screen.getByText('新建')).toBeInTheDocument()
  })
})
