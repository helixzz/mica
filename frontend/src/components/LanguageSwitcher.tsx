import { GlobalOutlined } from '@ant-design/icons'
import { Button, Dropdown } from 'antd'
import { useTranslation } from 'react-i18next'

import { SUPPORTED_LOCALES } from '@/i18n'

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()

  const items = SUPPORTED_LOCALES.map((code) => ({
    key: code,
    label: t(`language.${code}`),
    onClick: () => {
      void i18n.changeLanguage(code)
      document.documentElement.lang = code
    },
  }))

  return (
    <Dropdown menu={{ items, selectedKeys: [i18n.language] }} placement="bottomRight">
      <Button type="text" icon={<GlobalOutlined />}>
        {t(`language.${i18n.language}` as 'language.zh-CN')}
      </Button>
    </Dropdown>
  )
}
