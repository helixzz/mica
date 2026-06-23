import { DeleteOutlined, DownloadOutlined, EditOutlined, RobotOutlined, ScanOutlined, SearchOutlined, StopOutlined, UploadOutlined } from '@ant-design/icons'
import {
  Button,
  Card,
  Dropdown,
  Input,
  Modal,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type Contract, type ContractExpiring, type ContractSearchHit } from '@/api'
import { extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { ContractFormModal } from '@/components/ContractFormModal'
import { downloadCSV } from '@/utils/export'
import { fmtAmount, fmtAmountNode } from '@/utils/format'
import { showUndoToast } from '@/utils/undo'
import { MonoId } from '@/components/ui/Mono'

export function ContractsPage() {
  const { t } = useTranslation()
  const user = useAuth((s) => s.user)
  const [rows, setRows] = useState<Contract[]>([])
  const [expiring, setExpiring] = useState<ContractExpiring[]>([])
  const [query, setQuery] = useState('')
  const [searchHits, setSearchHits] = useState<ContractSearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<Contract | null>(null)
  const [scanCreateOpen, setScanCreateOpen] = useState(false)
  const [extractedData, setExtractedData] = useState<Record<string, unknown> | null>(null)

  const canWrite = Boolean(
    user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role),
  )
  const canDelete = Boolean(user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role))
  const canTransition = Boolean(
    user && ['admin', 'procurement_mgr', 'it_buyer'].includes(user.role),
  )

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [a, b] = await Promise.all([
        api.listContracts().catch(() => []),
        api.listExpiringContracts(30).catch(() => [])
      ])
      setRows(a)
      setExpiring(b)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleExport = () => {
    const headers = [
      t('field.contract_number'), t('field.title'), t('field.po_number'),
      t('field.status'), t('field.total_amount'), t('field.signed_date'), t('field.expiry_date'),
    ]
    const data = rows.map(r => [
      r.contract_number, r.title, r.po_number || '',
      t(`status.${r.status}` as 'status.active'), fmtAmount(r.total_amount, r.currency),
      r.signed_date || '', r.expiry_date || '',
    ])
    downloadCSV(`mica-contracts-${new Date().toISOString().slice(0, 10)}.csv`, headers, data)
  }

  const doSearch = async () => {
    if (!query.trim()) {
      setSearchHits([])
      return
    }
    const hits = await api.searchContracts(query)
    setSearchHits(hits)
  }

  const handleDelete = (contract: Contract) => {
    Modal.confirm({
      title: t('contract.confirm_delete_title', { number: contract.contract_number }),
      content: t('contract.confirm_delete_body'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteContract(contract.id)
          showUndoToast(t('undo.deleted', { item: t('nav.contracts') }), async () => {
            await api.restoreFromRecycleBin('contract', contract.id)
            void load()
          }, 8000)
          void load()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  const handleStatusChange = (
    contract: Contract,
    next: 'superseded' | 'terminated' | 'expired',
  ) => {
    Modal.confirm({
      title: t('contract.confirm_status_title', { status: t(`status.${next}` as 'status.active') }),
      content: t('contract.confirm_status_body'),
      okText: t('button.confirm'),
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.updateContractStatus(contract.id, next)
          void message.success(t('contract.status_changed_ok'))
          void load()
        } catch (e) {
          void message.error(extractError(e).detail)
        }
      },
    })
  }

  const columns: ColumnsType<Contract> = [
    {
      title: t('field.contract_number'),
      dataIndex: 'contract_number',
      render: (v, r) => <Link to={`/contracts/${r.id}`}><MonoId>{v}</MonoId></Link>,
    },
    { title: t('field.title'), dataIndex: 'title' },
    {
      title: t('field.po_number'),
      dataIndex: 'po_number',
      render: (v: string | null, r) =>
        v ? <Link to={`/purchase-orders/${r.po_id}`}><MonoId>{v}</MonoId></Link> : '-',
    },
    {
      title: t('field.status'),
      dataIndex: 'status',
      filters: [
        { text: t('status.active'), value: 'active' },
        { text: t('status.superseded'), value: 'superseded' },
        { text: t('status.terminated'), value: 'terminated' },
        { text: t('status.expired'), value: 'expired' },
      ],
      onFilter: (value, record) => record.status === value,
      render: (s: string) => <Tag>{t(`status.${s}` as 'status.active')}</Tag>,
    },
    {
      title: t('field.total_amount'),
      align: 'right',
      render: (_, r) => fmtAmountNode(r.total_amount, r.currency),
    },
    { title: t('field.signed_date'), dataIndex: 'signed_date' },
    { title: t('field.expiry_date'), dataIndex: 'expiry_date' },
    {
      title: t('field.actions'),
      key: 'actions',
      width: 200,
      render: (_, r) => {
        const isActive = r.status === 'active'
        const canEdit = canWrite && isActive
        const statusMenu = {
          items: [
            {
              key: 'terminated',
              label: t('contract.transition_to_terminated'),
              disabled: !isActive,
            },
            {
              key: 'superseded',
              label: t('contract.transition_to_superseded'),
              disabled: !isActive,
            },
            {
              key: 'expired',
              label: t('contract.transition_to_expired'),
              disabled: !isActive,
            },
          ],
          onClick: ({ key }: { key: string }) =>
            handleStatusChange(r, key as 'superseded' | 'terminated' | 'expired'),
        }
        return (
          <Space size="small">
            <Button
              size="small"
              icon={<EditOutlined />}
              disabled={!canEdit}
              onClick={() => setEditing(r)}
            >
              {t('button.edit')}
            </Button>
            {canTransition && (
              <Dropdown menu={statusMenu} disabled={!isActive} trigger={['click']}>
                <Button size="small" icon={<StopOutlined />}>
                  {t('contract.change_status')}
                </Button>
              </Dropdown>
            )}
            {canDelete && (
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(r)}
              >
                {t('button.delete')}
              </Button>
            )}
          </Space>
        )
      },
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{t('nav.contracts')}</Typography.Title>
        <Space>
        <Button icon={<DownloadOutlined />} onClick={handleExport}>{t('button.export_excel')}</Button>
        <Upload
          accept=".pdf,.jpg,.jpeg,.png"
          showUploadList={false}
          beforeUpload={async (file) => {
            const hideLoading = message.loading(t('contract.extracting'), 0)
            try {
              const doc = await api.uploadDocument(file, 'contract')
              const result = await api.extractContract(doc.id)
              hideLoading()
              if (result.error) { void message.error(result.error); return false }
              setExtractedData(result as unknown as Record<string, unknown>)
              setScanCreateOpen(true)
            } catch (e) {
              hideLoading()
              void message.error(extractError(e).detail)
            }
            return false
          }}
        >
          <Button icon={<ScanOutlined />}>{t('contract.scan_create')}</Button>
        </Upload>
        </Space>
      </div>

      <Card>
        <Input.Search
          placeholder={t('contract.search_placeholder')}
          enterButton={
            <Button icon={<SearchOutlined />} type="primary">
              {t('contract.search_btn')}
            </Button>
          }
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onSearch={doSearch}
          size="large"
        />
        {searchHits.length > 0 && (
          <Table
            style={{ marginTop: 16 }}
            rowKey="id"
            dataSource={searchHits}
            pagination={false}
            size="small"
            columns={[
              {
                title: t('field.contract_number'),
                dataIndex: 'contract_number',
                render: (v, r) => <Link to={`/contracts/${r.id}`}><MonoId>{v}</MonoId></Link>,
              },
              { title: t('field.title'), dataIndex: 'title' },
              {
                title: t('contract.match_col'),
                dataIndex: 'matched_in',
                render: (v: string[]) => v.map((m, i) => <Tag key={i}>{m.slice(0, 60)}</Tag>),
              },
              { title: t('field.expiry_date'), dataIndex: 'expiry_date' },
            ]}
          />
        )}
      </Card>

      {expiring.length > 0 && (
        <Card
          title={t('contract.expiring_title', { count: expiring.length })}
          style={{ background: '#fff7e6', borderColor: '#ffd591' }}
        >
          <Table
            rowKey="id"
            dataSource={expiring}
            pagination={false}
            size="small"
            columns={[
              {
                title: t('field.contract_number'),
                dataIndex: 'contract_number',
                render: (v, r) => <Link to={`/contracts/${r.id}`}><MonoId>{v}</MonoId></Link>,
              },
              { title: t('field.title'), dataIndex: 'title' },
              { title: t('field.expiry_date'), dataIndex: 'expiry_date' },
              {
                title: t('field.amount'),
                render: (_, r) => fmtAmountNode(r.total_amount, r.currency),
                align: 'right',
              },
            ]}
          />
        </Card>
      )}

      <Card title={t('contract.all_title')}>
        <Table<Contract>
          rowKey="id"
          dataSource={rows}
          columns={columns}
          loading={loading}
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1100 }}
        />
      </Card>

      <ContractFormModal
        open={editing !== null}
        mode="edit"
        contract={editing}
        onClose={() => setEditing(null)}
        onSaved={() => {
          setEditing(null)
          void load()
        }}
      />
      <ContractFormModal
        open={scanCreateOpen}
        mode="create"
        initialValues={extractedData || undefined}
        onClose={() => { setScanCreateOpen(false); setExtractedData(null) }}
        onSaved={() => {
          setScanCreateOpen(false)
          setExtractedData(null)
          void load()
        }}
      />
    </Space>
  )
}
