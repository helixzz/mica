import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import { RELEASES } from './releases'

function asNumbers(version: string): number[] {
  return version.split('.').map((part) => Number(part) || 0)
}

function compare(a: string, b: string): number {
  const left = asNumbers(a)
  const right = asNumbers(b)
  for (let i = 0; i < Math.max(left.length, right.length); i += 1) {
    const diff = (left[i] ?? 0) - (right[i] ?? 0)
    if (diff !== 0) return diff
  }
  return 0
}

describe("What's new", () => {
  // This is the guard that was missing: v1.63.1 through v1.65.0 shipped without
  // entries, so the drawer kept showing an old version as latest and nobody saw
  // what had changed.
  it('leads with the version being shipped', () => {
    const manifest = JSON.parse(
      readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'),
    ) as { version: string }

    expect(RELEASES[0]?.version).toBe(manifest.version)
  })

  it('lists versions newest first, without duplicates', () => {
    const versions = RELEASES.map((release) => release.version)

    expect(new Set(versions).size).toBe(versions.length)
    const expected = [...versions].sort((a, b) => compare(b, a))
    expect(versions).toEqual(expected)
  })

  it('gives every entry at least one line in both languages', () => {
    for (const release of RELEASES) {
      expect(release.items.length).toBeGreaterThan(0)
      for (const item of release.items) {
        expect(item.zh.trim().length).toBeGreaterThan(0)
        expect(item.en.trim().length).toBeGreaterThan(0)
      }
    }
  })
})
