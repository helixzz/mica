import { SearchOutlined } from '@ant-design/icons'
import { Button, Card, Input, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

import { api, type Contract, type ContractExpiring, type ContractSearchHit } from '@/api'
import { fmtAmount } from '@/utils/format'

export function ContractsPage() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Contract[]>([])
  const [expiring, setExpiring] = useState<ContractExpiring[]>([])
  const [query, setQuery] = useState('')
  const [searchHits, setSearchHits] = useState<ContractSearchHit[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([api.listContracts(), api.listExpiringContracts(30)])
      .then(([a, b]) => { setRows(a); setExpiring(b) })
      .finally(() => setLoading(false))
  }, [])

  const doSearch = async () => {
    if (!query.trim()) {
      setSearchHits([])
      return
    }
    const hits = await api.searchContracts(query)
    setSearchHits(hits)
  }

  const columns: ColumnsType<Contract> = [
    {
      title: t('field.contract_number'),
      dataIndex: 'contract_number',
      render: (v, r) => <Link to={`/contracts/${r.id}`}>{v}</Link>,
    },
    { title: t('field.title'), dataIndex: 'title' },
    { title: t('field.status'), dataIndex: 'status',
      filters: [{text:'active',value:'active'},{text:'superseded',value:'superseded'},{text:'terminated',value:'terminated'},{text:'expired',value:'expired'}],
      onFilter: (value: any, record: any) => record.status === value, render: (s) => <Tag>{t(`status.${s}` as 'status.active')}</Tag> },
    { title: t('field.total_amount'), align: 'right', render: (_, r) => `${r.currency} ${r.total_amount}` },
    { title: t('field.signed_date'), dataIndex: 'signed_date' },
    { title: t('field.expiry_date'), dataIndex: 'expiry_date' },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3}>{t('nav.contracts')}</Typography.Title>

      <Card>
        <Input.Search
          placeholder="搜索合同标题 / 编号 / 扫描件 OCR 文本"
          enterButton={<Button icon={<SearchOutlined />} type="primary">检索</Button>}
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
                title: '合同号',
                dataIndex: 'contract_number',
                render: (v, r) => <Link to={`/contracts/${r.id}`}>{v}</Link>,
              },
              { title: '标题', dataIndex: 'title' },
              {
                title: '匹配位置',
                dataIndex: 'matched_in',
                render: (v: string[]) => v.map((m, i) => <Tag key={i}>{m.slice(0, 60)}</Tag>),
              },
              { title: '到期日', dataIndex: 'expiry_date' },
            ]}
          />
        )}
      </Card>

      {expiring.length > 0 && (
        <Card title={`30 天内到期的合同（${expiring.length}）`} style={{ background: '#fff7e6', borderColor: '#ffd591' }}>
          <Table
            rowKey="id"
            dataSource={expiring}
            pagination={false}
            size="small"
            columns={[
              {
                title: '合同号',
                dataIndex: 'contract_number',
                render: (v, r) => <Link to={`/contracts/${r.id}`}>{v}</Link>,
              },
              { title: '标题', dataIndex: 'title' },
              { title: '到期日', dataIndex: 'expiry_date' },
              { title: '金额', render: (_, r) => `${r.currency} ${r.total_amount}`, align: 'right' },
            ]}
          />
        </Card>
      )}

      <Card title="全部合同">
        <Table<Contract> rowKey="id" dataSource={rows} columns={columns} loading={loading} pagination={{ pageSize: 20 }} />
      </Card>
    </Space>
  )
}
