import { Button, Modal } from 'antd'
import { useTranslation } from 'react-i18next'
import { useEffect } from 'react'

interface Props {
  open: boolean
  url: string
  title: string
  onClose: () => void
}

export function DocumentPreview({ open, url, title, onClose }: Props) {
  const { t } = useTranslation()

  useEffect(() => {
    if (open && url) {
      window.open(url, '_blank', 'noopener,noreferrer')
      onClose()
    }
  }, [open, url, onClose])

  return (
    <Modal
      title={title}
      open={false}
      footer={null}
    />
  )
}
