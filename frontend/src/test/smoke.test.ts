import { describe, expect, it } from 'vitest'

describe('vitest infrastructure smoke', () => {
  it('runs basic arithmetic', () => {
    expect(1 + 1).toBe(2)
  })

  it('has jsdom document', () => {
    const el = document.createElement('div')
    el.textContent = 'hello'
    expect(el).toBeInTheDocument
    expect(el.textContent).toBe('hello')
  })

  it('has matchMedia polyfill from setup.ts', () => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    expect(mq.matches).toBe(false)
    expect(typeof mq.addEventListener).toBe('function')
  })
})
