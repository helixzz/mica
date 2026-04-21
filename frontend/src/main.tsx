import { ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import zhCN from 'antd/locale/zh_CN'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { useTranslation } from 'react-i18next'
import { BrowserRouter } from 'react-router-dom'

import { AppRoutes } from '@/routes'
import { ThemeProvider } from '@/theme/ThemeProvider'

import '@/i18n'
import '@/styles/global.css'

function App() {
  const { i18n } = useTranslation()
  const antLocale = i18n.language === 'en-US' ? enUS : zhCN
  
  return (
    <ThemeProvider>
      <ConfigProvider locale={antLocale}>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </ConfigProvider>
    </ThemeProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
