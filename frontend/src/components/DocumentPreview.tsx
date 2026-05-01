import { Button, Modal } from 'antd'
import { useTranslation } from 'react-i18next'

interface Props {
  open: boolean
  url: string
  title: string
  onClose: () => void
}

export function DocumentPreview({ open, url, title, onClose }: Props) {
  const { t } = useTranslation()

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onClose}
      width="90vw"
      style={{ top: 20 }}
      footer={<Button onClick={onClose}>{t('button.close')}</Button>}
      destroyOnClose
    >
      {url.endsWith('.pdf') || url.includes('application/pdf') ? (
        <iframe
          src={url}
          style={{ width: '100%', height: '80vh', border: 'none' }}
          title={title}
        />
      ) : (
        <img
          src={url}
          alt={title}
          style={{ maxWidth: '100%', maxHeight: '80vh', display: 'block', margin: '0 auto' }}
        />
      )}
    </Modal>
  )
}
