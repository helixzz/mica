import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import enUSCommon from './locales/en-US/common.json'
import zhCNCommon from './locales/zh-CN/common.json'

export const SUPPORTED_LOCALES = ['zh-CN', 'en-US'] as const
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      'zh-CN': { common: zhCNCommon },
      'en-US': { common: enUSCommon },
    },
    fallbackLng: 'zh-CN',
    supportedLngs: SUPPORTED_LOCALES as unknown as string[],
    ns: ['common'],
    defaultNS: 'common',
    detection: {
      order: ['localStorage', 'cookie', 'navigator', 'htmlTag'],
      lookupLocalStorage: 'mica.locale',
      lookupCookie: 'mica_locale',
      caches: ['localStorage', 'cookie'],
    },
    interpolation: { escapeValue: false },
    returnNull: false,
  })

export default i18n
