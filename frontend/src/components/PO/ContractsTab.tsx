import { DisconnectOutlined, FileTextOutlined, LinkOutlined } from '@ant-design/icons'
import { Button, Space, Table, Tag, Typography } from 'antd'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

import { type Contract, type PurchaseOrder } from '@/api'
import { fmtAmount } from '@/utils/format'

interface ContractsTabProps {
  contracts: Contract[]
  po: PurchaseOrder
  canCreateContract: boolean
  onCreateContract: () => void
  onLinkContract: () => void
  onUnlinkContract: (contract: Contract) => void
}

export function ContractsTab({
  contracts,
  po,
  canCreateContract,
  onCreateContract,
  onLinkContract,
  onUnlinkContract,
}: ContractsTabProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <>
      <div style={{ marginBottom: 12, textAlign: 'right' }}>
        <Space>
          {canCreateContract && (
            <Button
              icon={<LinkOutlined />}
              onClick={onLinkContract}
              disabled={po.status === 'draft' || po.status === 'cancelled'}
            >
              {t('po.link_existing_contract')}
            </Button>
          )}
          {canCreateContract && (
            <Button
              type="primary"
              icon={<FileTextOutlined />}
              onClick={onCreateContract}
              disabled={po.status === 'draft' || po.status === 'cancelled'}
            >
              {t('contract.create_btn')}
            </Button>
          )}
        </Space>
      </div>
      {contracts.length === 0 ? (
        <Typography.Text type="secondary">
          {t('po.no_contracts_hint')}
        </Typography.Text>
      ) : (
        <Table
          rowKey="id"
          dataSource={contracts}
          pagination={false}
          size="small"
          columns={[
            {
              title: t('field.contract_number'),
              dataIndex: 'contract_number',
              render: (v: string, r: Contract) => (
                <a onClick={() => navigate(`/contracts/${r.id}`)}>{v}</a>
              ),
            },
            { title: t('field.title'), dataIndex: 'title' },
            {
              title: t('field.status'),
              dataIndex: 'status',
              render: (s: string) => (
                <Tag>{t(`status.${s}` as 'status.active')}</Tag>
              ),
            },
            {
              title: t('field.total_amount'),
              align: 'right',
              render: (_: unknown, r: Contract) =>
                fmtAmount(r.total_amount, r.currency),
            },
            { title: t('field.signed_date'), dataIndex: 'signed_date' },
            { title: t('field.expiry_date'), dataIndex: 'expiry_date' },
            {
              title: t('common.actions'),
              width: 100,
              render: (_: unknown, r: Contract) =>
                r.po_id !== po.id ? (
                  <Button
                    size="small"
                    icon={<DisconnectOutlined />}
                    onClick={() => onUnlinkContract(r)}
                    title={t('po.unlink_contract')}
                  >
                    {t('po.unlink')}
                  </Button>
                ) : (
                  <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                    {t('po.primary_contract')}
                  </Typography.Text>
                ),
            },
          ]}
        />
      )}
    </>
  )
}