import { describe, expect, it } from 'vitest'
import { renderWithProviders, screen } from '@/test/utils'
import { Section } from './Section'

describe('<Section />', () => {
  it('renders children', () => {
    renderWithProviders(
      <Section>
        <div>inner content</div>
      </Section>,
    )
    expect(screen.getByText('inner content')).toBeInTheDocument()
  })

  it('renders title and description when provided', () => {
    renderWithProviders(
      <Section title="合同到期" description="最近 30 天">
        <div>rows</div>
      </Section>,
    )
    expect(screen.getByText('合同到期')).toBeInTheDocument()
    expect(screen.getByText('最近 30 天')).toBeInTheDocument()
  })

  it('renders extra slot', () => {
    renderWithProviders(
      <Section title="x" extra={<a>查看全部</a>}>
        <div>y</div>
      </Section>,
    )
    expect(screen.getByText('查看全部')).toBeInTheDocument()
  })
})
