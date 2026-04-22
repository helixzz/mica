import { describe, expect, it } from 'vitest'
import { renderWithProviders, screen } from '@/test/utils'
import { StatCard } from './StatCard'

describe('<StatCard />', () => {
  it('renders label and value', () => {
    renderWithProviders(<StatCard label="待审批" value={12} />)
    expect(screen.getByText('待审批')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
  })

  it('renders loading skeleton when loading', () => {
    const { container } = renderWithProviders(
      <StatCard label="x" value={0} loading />,
    )
    expect(container.querySelector('.ant-skeleton')).toBeInTheDocument()
  })

  it('renders trend up when provided', () => {
    renderWithProviders(
      <StatCard
        label="x"
        value={10}
        trend={{ direction: 'up', delta: '+12%' }}
      />,
    )
    expect(screen.getByText('+12%')).toBeInTheDocument()
  })

  it('renders trend down when provided', () => {
    renderWithProviders(
      <StatCard
        label="x"
        value={10}
        trend={{ direction: 'down', delta: '-8%' }}
      />,
    )
    expect(screen.getByText('-8%')).toBeInTheDocument()
  })

  it('does not render trend when prop absent', () => {
    renderWithProviders(<StatCard label="x" value={10} />)
    expect(screen.queryByText(/[+-]\d+%/)).not.toBeInTheDocument()
  })

  it('accepts variant=accent without crashing', () => {
    renderWithProviders(
      <StatCard label="x" value={10} variant="accent" />,
    )
    expect(screen.getByText('x')).toBeInTheDocument()
  })
})
