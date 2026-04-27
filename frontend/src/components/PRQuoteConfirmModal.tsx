import { Checkbox, Modal, Space, Table, Typography, message } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type PRQuoteCandidate } from '@/api'
import { fmtAmount } from '@/utils/format'

interface Props {
  prId: string
  open: boolean
  onClose: (saved: boolean) => void
}

export function PRQuoteConfirmModal({ prId, open, onClose }: Props) {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [candidates, setCandidates] = useState<PRQuoteCandidate[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (!open) {
      setCandidates([])
      setSelected(new Set())
      return
    }
    setLoading(true)
    void api
      .listPRQuoteCandidates(prId)
      .then((list) => {
        setCandidates(list)
        const freshOrChanged = list.filter((c) => !c.already_up_to_date)
        setSelected(new Set(freshOrChanged.map((c) => c.line_no)))
      })
      .catch(() => {
        setCandidates([])
        setSelected(new Set())
      })
      .finally(() => setLoading(false))
  }, [prId, open])

  const toggleRow = (line_no: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(line_no)) next.delete(line_no)
      else next.add(line_no)
      return next
    })
  }

  const handleSave = async () => {
    if (selected.size === 0) {
      onClose(false)
      return
    }
    setSaving(true)
    try {
      const result = await api.savePRSupplierQuotes(prId, {
        line_nos: Array.from(selected),
      })
      void message.success(
        t('pr.sku_quote_saved', {
          written: result.written_count,
          skipped: result.skipped_unchanged_count,
        }),
      )
      onClose(true)
    } catch {
      void message.error(t('error.save_failed'))
      onClose(false)
    } finally {
      setSaving(false)
    }
  }

  const actionableCount = candidates.filter((c) => !c.already_up_to_date).length

  const columns: ColumnsType<PRQuoteCandidate> = [
    {
      title: '',
      dataIndex: 'line_no',
      width: 40,
      render: (line_no: number, r) => (
        <Checkbox
          checked={selected.has(line_no)}
          disabled={r.already_up_to_date}
          onChange={() => toggleRow(line_no)}
        />
      ),
    },
    { title: t('field.line_no'), dataIndex: 'line_no', width: 60 },
    { title: t('field.item_name'), dataIndex: 'item_name' },
    {
      title: t('field.supplier'),
      dataIndex: 'supplier_name',
      render: (v: string | null, r) => v ?? r.supplier_code ?? r.supplier_id,
    },
    {
      title: t('field.unit_price'),
      dataIndex: 'unit_price',
      align: 'right',
      render: (v: string, r) => fmtAmount(v, r.currency),
    },
    {
      title: t('pr.sku_quote_state_col'),
      width: 120,
      render: (_: unknown, r) => {
        if (r.already_up_to_date) {
          return (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {t('pr.sku_quote_state_unchanged')}
            </Typography.Text>
          )
        }
        if (r.already_exists) {
          return (
            <Typography.Text style={{ fontSize: 12, color: '#B48A6A' }}>
              {t('pr.sku_quote_state_update')}
            </Typography.Text>
          )
        }
        return (
          <Typography.Text style={{ fontSize: 12, color: '#1677ff' }}>
            {t('pr.sku_quote_state_new')}
          </Typography.Text>
        )
      },
    },
  ]

  return (
    <Modal
      title={t('pr.sku_quote_confirm_title', { count: actionableCount })}
      open={open}
      onCancel={() => onClose(false)}
      onOk={handleSave}
      okText={t('pr.sku_quote_confirm_ok', { count: selected.size })}
      cancelText={t('button.skip')}
      okButtonProps={{ loading: saving, disabled: selected.size === 0 }}
      confirmLoading={saving}
      width={760}
    >
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Typography.Text type="secondary">{t('pr.sku_quote_confirm_desc')}</Typography.Text>
        <Table<PRQuoteCandidate>
          rowKey="line_no"
          size="small"
          pagination={false}
          loading={loading}
          dataSource={candidates}
          columns={columns}
          locale={{ emptyText: t('pr.sku_quote_no_candidates') }}
        />
      </Space>
    </Modal>
  )
}
