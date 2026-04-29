import { Alert, Button, Space, Typography } from 'antd'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'

interface Props {
  savedAt: number | null
  onRestore: () => void
  onDismiss: () => void
}

function relativeTime(ms: number, t: TFunction): string {
  const diff = Date.now() - ms
  const minutes = Math.round(diff / 60_000)
  if (minutes < 1) return t('autosave.just_now', 'just now')
  if (minutes === 1) return t('autosave.minute_ago', '1 minute ago')
  if (minutes < 60)
    return t('autosave.minutes_ago', { defaultValue: '{{n}} minutes ago', n: minutes }) as string
  const hours = Math.round(minutes / 60)
  if (hours === 1) return t('autosave.hour_ago', '1 hour ago')
  return t('autosave.hours_ago', { defaultValue: '{{n}} hours ago', n: hours }) as string
}

export function AutosaveBanner({ savedAt, onRestore, onDismiss }: Props) {
  const { t } = useTranslation()

  return (
    <Alert
      type="info"
      showIcon
      style={{ marginBottom: 12 }}
      message={
        <Space>
          <Typography.Text>
            {t('autosave.banner_text', {
              defaultValue: 'An unsaved draft from {{time}} was found.',
              time: savedAt ? relativeTime(savedAt, t) : '',
            }) as string}
          </Typography.Text>
          <Button size="small" type="primary" onClick={onRestore}>
            {t('autosave.restore', 'Restore')}
          </Button>
          <Button size="small" onClick={onDismiss}>
            {t('autosave.discard', 'Discard')}
          </Button>
        </Space>
      }
    />
  )
}

export function AutosaveUnavailableBanner() {
  const { t } = useTranslation()
  return (
    <Alert
      type="warning"
      showIcon
      style={{ marginBottom: 12 }}
      message={t(
        'autosave.unavailable',
        'Autosave is unavailable — your browser may be in private mode or has disabled local storage. Unsaved changes may be lost.',
      )}
      closable
    />
  )
}
