import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons'
import { Button, Space, Tag, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { type PurchaseOrder } from '@/api'
import { getToken } from '@/api/client'

interface POHeaderProps {
  po: PurchaseOrder
  contractsCount: number
  canCreateContract: boolean
  onCreateContract: () => void
}

function statusTag(s: string): string {
  return s
}

export function POHeader({ po, contractsCount, canCreateContract, onCreateContract }: POHeaderProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <Space align="center">
        <Typography.Title level={3} style={{ margin: 0 }}>
          {po.po_number}
        </Typography.Title>
        <Tag color="success">{t(`status.${statusTag(po.status)}` as 'status.confirmed')}</Tag>
      </Space>
      <Space>
        {canCreateContract && (
          <Button
            type="primary"
            icon={<FileTextOutlined />}
            className="no-print"
            onClick={onCreateContract}
            disabled={po.status === 'draft' || po.status === 'cancelled'}
          >
            {contractsCount > 0
              ? t('contract.add_another')
              : t('contract.create_btn')}
          </Button>
        )}
        <Button
          icon={<DownloadOutlined />}
          className="no-print"
          onClick={async () => {
            const resp = await fetch(`/api/v1/purchase-orders/${po.id}/export/pdf`, {
              headers: { Authorization: `Bearer ${getToken() ?? ''}` },
            })
            if (!resp.ok) return
            const blob = await resp.blob()
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `${po.po_number}.pdf`
            document.body.appendChild(a)
            a.click()
            a.remove()
            URL.revokeObjectURL(url)
          }}
        >
          {t('button.export_pdf')}
        </Button>
        <Button className="no-print" onClick={() => window.print()}>{t('button.print')}</Button>
        <Button onClick={() => navigate('/purchase-orders')}>{t('button.back')}</Button>
      </Space>
    </div>
  )
}