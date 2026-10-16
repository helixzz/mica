import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MonoId, MonoNum } from '@/components/ui/Mono'

describe('MonoId', () => {
  it('renders a code element for a real identifier', () => {
    render(<MonoId>PR-2026-0017</MonoId>)
    const element = screen.getByText('PR-2026-0017')
    expect(element.tagName).toBe('CODE')
    expect(element).toHaveClass('mono-id')
  })

  it.each([
    ['a dash', '-', '-'],
    ['an empty string', '', ''],
  ])('falls back to plain text for %s', (_label, value, expected) => {
    const { container } = render(<MonoId>{value}</MonoId>)
    expect(container.textContent).toBe(expected)
    // Placeholders must not look like identifiers.
    expect(container.querySelector('code')).toBeNull()
  })

  it('shows a dash when there is no value at all', () => {
    const { container } = render(<MonoId>{null}</MonoId>)
    expect(container.textContent).toBe('-')
    expect(container.querySelector('code')).toBeNull()
  })

  it('keeps the caller className alongside the mono class', () => {
    render(<MonoId className="text-muted">PO-1</MonoId>)
    expect(screen.getByText('PO-1')).toHaveClass('mono-id', 'text-muted')
  })
})

describe('MonoNum', () => {
  it('adds the right-align modifier only when asked', () => {
    render(<MonoNum align="right">1,234.00</MonoNum>)
    expect(screen.getByText('1,234.00')).toHaveClass('mono-num', 'mono-num--right')
  })

  it('stays left aligned by default', () => {
    render(<MonoNum>1,234.00</MonoNum>)
    expect(screen.getByText('1,234.00')).toHaveClass('mono-num')
    expect(screen.getByText('1,234.00')).not.toHaveClass('mono-num--right')
  })
})
