import { App as AntApp, ConfigProvider } from 'antd'
import enUS from 'antd/locale/en_US'
import zhCN from 'antd/locale/zh_CN'
import dayjs from 'dayjs'
import { StrictMode, useEffect } from 'react'
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

  useEffect(() => {
    if (i18n.language === 'en-US') {
      import('dayjs/locale/en').then(() => {
        dayjs.locale('en')
      })
    } else {
      import('dayjs/locale/zh-cn').then(() => {
        dayjs.locale('zh-cn')
      })
    }
  }, [i18n.language])
  
  return (
    <ThemeProvider>
      <ConfigProvider locale={antLocale}>
        <AntApp>
          <BrowserRouter>
            <AppRoutes />
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </ThemeProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
