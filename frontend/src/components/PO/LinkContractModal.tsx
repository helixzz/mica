import {
  Modal,
  Select,
  Space,
  Typography,
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type Contract, type PurchaseOrder } from '@/api'
import { extractError } from '@/api/client'

interface LinkContractModalProps {
  open: boolean
  po: PurchaseOrder
  alreadyLinkedIds: string[]
  onClose: () => void
  onLinked: () => void
}

export function LinkContractModal({
  open,
  po,
  alreadyLinkedIds,
  onClose,
  onLinked,
}: LinkContractModalProps) {
  const { t } = useTranslation()
  const [options, setOptions] = useState<Contract[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setSelectedId(null)
    api
      .listContracts()
      .then((list) => {
        const filtered = list.filter((contract) => !alreadyLinkedIds.includes(contract.id))
        setOptions(filtered)
      })
      .catch(() => setOptions([]))
      .finally(() => setLoading(false))
  }, [alreadyLinkedIds, open])

  const submit = async () => {
    if (!selectedId) return
    try {
      setLoading(true)
      await api.linkPoContract(po.id, selectedId)
      void message.success(t('po.link_success'))
      onLinked()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title={t('po.link_existing_contract')}
      open={open}
      onCancel={onClose}
      onOk={submit}
      confirmLoading={loading}
      okButtonProps={{ disabled: !selectedId }}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Typography.Text type="secondary">
          {t('po.link_existing_contract_help')}
        </Typography.Text>
        <Select
          showSearch
          value={selectedId ?? undefined}
          placeholder={t('po.link_existing_contract_placeholder')}
          onChange={(value) => setSelectedId(value)}
          loading={loading}
          options={options.map((contract) => ({
            value: contract.id,
            label: `${contract.contract_number} · ${contract.title} · ${contract.po_number ?? '-'}`,
          }))}
          optionFilterProp="label"
        />
        {options.length === 0 && !loading ? (
          <Typography.Text type="secondary">
            {t('po.no_available_contracts')}
          </Typography.Text>
        ) : null}
      </Space>
    </Modal>
  )
}