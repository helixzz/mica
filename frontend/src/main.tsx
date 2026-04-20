import { ConfigProvider, theme } from 'antd'
import enUS from 'antd/locale/en_US'
import zhCN from 'antd/locale/zh_CN'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { useTranslation } from 'react-i18next'
import { BrowserRouter } from 'react-router-dom'

import { AppRoutes } from '@/routes'

import '@/i18n'

function App() {
  const { i18n } = useTranslation()
  const antLocale = i18n.language === 'en-US' ? enUS : zhCN
  return (
    <ConfigProvider
      locale={antLocale}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#2E5266',
          colorLink: '#2E5266',
          borderRadius: 6,
        },
      }}
    >
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ConfigProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
