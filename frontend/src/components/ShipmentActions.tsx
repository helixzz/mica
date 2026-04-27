import { DeleteOutlined, EditOutlined, PaperClipOutlined } from '@ant-design/icons'
import { Button, Modal, Space, message } from 'antd'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Shipment } from '@/api'
import { ShipmentAttachmentsDrawer } from './ShipmentAttachmentsDrawer'
import { ShipmentEditDrawer } from './ShipmentEditDrawer'

interface Props {
  shipment: Shipment
  onChanged: () => void
  allowDelete?: boolean
}

export function ShipmentActions({ shipment, onChanged, allowDelete = true }: Props) {
  const { t } = useTranslation()
  const [editOpen, setEditOpen] = useState(false)
  const [attachOpen, setAttachOpen] = useState(false)

  const handleDelete = () => {
    Modal.confirm({
      title: t('shipment.confirm_delete'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteShipment(shipment.id)
          void message.success(t('shipment.deleted'))
          onChanged()
        } catch (e) {
          const err = e as { response?: { data?: { detail?: string } } }
          void message.error(err?.response?.data?.detail || t('admin.operation_failed'))
        }
      },
    })
  }

  return (
    <>
      <Space size={4}>
        <Button
          size="small"
          icon={<EditOutlined />}
          onClick={() => setEditOpen(true)}
          title={t('button.edit')}
        />
        <Button
          size="small"
          icon={<PaperClipOutlined />}
          onClick={() => setAttachOpen(true)}
          title={t('shipment.attachments_short')}
        />
        {allowDelete && (
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={handleDelete}
            title={t('button.delete')}
          />
        )}
      </Space>
      <ShipmentEditDrawer
        shipment={editOpen ? shipment : null}
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSaved={onChanged}
      />
      <ShipmentAttachmentsDrawer
        shipment={attachOpen ? shipment : null}
        open={attachOpen}
        onClose={() => setAttachOpen(false)}
      />
    </>
  )
}
