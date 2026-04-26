import { SettingOutlined } from '@ant-design/icons'
import { Button, Checkbox, Divider, Popover, Space, Typography } from 'antd'
import { useTranslation } from 'react-i18next'

export interface ColumnOption {
  key: string
  label: string
  alwaysVisible?: boolean
}

interface Props {
  options: ColumnOption[]
  visibleKeys: Set<string>
  onToggle: (key: string) => void
  onReset: () => void
}

export function ColumnSettings({ options, visibleKeys, onToggle, onReset }: Props) {
  const { t } = useTranslation()

  const content = (
    <div style={{ minWidth: 220 }}>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {t('column_settings.hint')}
      </Typography.Text>
      <Divider style={{ margin: '8px 0' }} />
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {options.map((opt) => (
          <Checkbox
            key={opt.key}
            checked={visibleKeys.has(opt.key)}
            disabled={opt.alwaysVisible}
            onChange={() => onToggle(opt.key)}
          >
            {opt.label}
          </Checkbox>
        ))}
      </Space>
      <Divider style={{ margin: '8px 0' }} />
      <Button size="small" type="link" onClick={onReset} style={{ padding: 0 }}>
        {t('column_settings.reset')}
      </Button>
    </div>
  )

  return (
    <Popover
      content={content}
      title={t('column_settings.title')}
      trigger="click"
      placement="bottomRight"
    >
      <Button icon={<SettingOutlined />} size="small">
        {t('column_settings.button')}
      </Button>
    </Popover>
  )
}
