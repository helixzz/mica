import { createInstance, type i18n } from 'i18next'
import { beforeAll, describe, expect, it } from 'vitest'

import enUSCommon from './locales/en-US/common.json'
import zhCNCommon from './locales/zh-CN/common.json'

const catalogs = {
  'zh-CN': zhCNCommon,
  'en-US': enUSCommon,
} as const

type Locale = keyof typeof catalogs
type TranslationEntry = [key: string, value: string]

function flattenTranslations(catalog: object, prefix = ''): TranslationEntry[] {
  return Object.entries(catalog).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return typeof value === 'string'
      ? [[path, value]]
      : flattenTranslations(value, path)
  })
}

function interpolationVariables(value: string): string[] {
  return [...value.matchAll(/{{\s*-?\s*(\w+)\s*}}/g)].map((match) => match[1])
}

const translators = {} as Record<Locale, i18n>

beforeAll(async () => {
  for (const locale of Object.keys(catalogs) as Locale[]) {
    const translator = createInstance()
    await translator.init({
      lng: locale,
      fallbackLng: false,
      ns: ['common'],
      defaultNS: 'common',
      resources: { [locale]: { common: catalogs[locale] } },
      interpolation: { escapeValue: false },
      returnNull: false,
    })
    translators[locale] = translator
  }
})

describe('locale interpolation', () => {
  it.each(Object.keys(catalogs) as Locale[])(
    'does not use Python-style single braces in %s translations',
    (locale) => {
      const invalid = flattenTranslations(catalogs[locale]).filter(([, value]) =>
        /(?<!{){[a-z_][a-z0-9_]*}(?!})/.test(value),
      )

      expect(invalid).toEqual([])
    },
  )

  it('uses the same interpolation variables in both locales', () => {
    const zhEntries = new Map(flattenTranslations(catalogs['zh-CN']))
    const enEntries = new Map(flattenTranslations(catalogs['en-US']))

    expect([...zhEntries.keys()].sort()).toEqual([...enEntries.keys()].sort())
    for (const [key, zhValue] of zhEntries) {
      expect(interpolationVariables(zhValue).sort(), key).toEqual(
        interpolationVariables(enEntries.get(key) ?? '').sort(),
      )
    }
  })

  it.each(Object.keys(catalogs) as Locale[])(
    'resolves every catalog key and its variables through i18next in %s',
    (locale) => {
      for (const [key, value] of flattenTranslations(catalogs[locale])) {
        const variables = Object.fromEntries(
          interpolationVariables(value).map((name) => [name, `<${name}>`]),
        )
        const expected = value.replace(/{{\s*-?\s*(\w+)\s*}}/g, '<$1>')
        const translated = translators[locale].t(key, variables)

        expect(translated, key).toBe(expected)
      }
    },
  )

  it('shows the elapsed approval time instead of the original placeholder', () => {
    expect(translators['zh-CN'].t('approvals.waiting_hours', { hours: '3.5' })).toBe(
      '已等待 3.5 小时',
    )
    expect(translators['en-US'].t('approvals.waiting_hours', { hours: '3.5' })).toBe(
      'Waiting 3.5h',
    )
  })
})
