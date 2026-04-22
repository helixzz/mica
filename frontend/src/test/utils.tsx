import { ReactElement, ReactNode } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { ConfigProvider } from 'antd'
import { MemoryRouter } from 'react-router-dom'
import { I18nextProvider, initReactI18next } from 'react-i18next'
import i18n from 'i18next'

i18n.use(initReactI18next).init({
  lng: 'zh-CN',
  fallbackLng: 'zh-CN',
  interpolation: { escapeValue: false },
  resources: {
    'zh-CN': { common: {} },
  },
})

interface Providers {
  route?: string
}

function AllProviders({
  children,
  route = '/',
}: Providers & { children: ReactNode }) {
  return (
    <MemoryRouter initialEntries={[route]}>
      <I18nextProvider i18n={i18n}>
        <ConfigProvider>{children}</ConfigProvider>
      </I18nextProvider>
    </MemoryRouter>
  )
}

export function renderWithProviders(
  ui: ReactElement,
  {
    route,
    ...renderOptions
  }: Providers & Omit<RenderOptions, 'wrapper'> = {},
) {
  return render(ui, {
    wrapper: ({ children }) => (
      <AllProviders route={route}>{children}</AllProviders>
    ),
    ...renderOptions,
  })
}

export * from '@testing-library/react'
