import { useTranslation } from 'react-i18next'
import { CheckCircleOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Card, Col, Descriptions, InputNumber, Modal, Row, Select, Space, Table, Tag, Typography, message } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'

const statusColors: Record<string, string> = {
  draft: 'default', sent: 'processing', quoting: 'cyan',
  evaluation: 'orange', awarded: 'success', closed: 'default', cancelled: 'error',
}

export default function RFQDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [rfq, setRfq] = useState<any>(null)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [quoteModal, setQuoteModal] = useState<{ rfqItemId: string; supplierId: string } | null>(null)
  const [quotePrice, setQuotePrice] = useState<number>(0)
  const [quoteDays, setQuoteDays] = useState<number | null>(null)

  const load = () => {
    if (!id) return
    void client.get(`/rfqs/${id}`).then((r) => setRfq(r.data))
    void api.suppliers().then(setSuppliers)
  }
  useEffect(load, [id])

  if (!rfq) return <div>加载中...</div>

  const supplierMap = Object.fromEntries(suppliers.map((s) => [s.id, s.name]))
  const canSend = rfq.status === 'draft'
  const canQuote = rfq.status === 'sent' || rfq.status === 'quoting'
  const canAward = rfq.status === 'quoting' || rfq.status === 'evaluation'

  const doSend = async () => {
    try {
      await client.post(`/rfqs/${id}/send`)
      void message.success('询价单已发出')
      load()
    } catch (e) { void message.error(extractError(e).detail || '发送失败') }
  }

  const doAddQuote = async () => {
    if (!quoteModal || !quotePrice) return
    try {
      await client.post(`/rfqs/${id}/quotes`, {
        rfq_item_id: quoteModal.rfqItemId,
        supplier_id: quoteModal.supplierId,
        unit_price: quotePrice,
        delivery_days: quoteDays,
      })
      void message.success('报价已录入')
      setQuoteModal(null)
      setQuotePrice(0)
      setQuoteDays(null)
      load()
    } catch (e) { void message.error(extractError(e).detail || '录入失败') }
  }

  const doAward = async (quoteIds: string[]) => {
    try {
      await client.post(`/rfqs/${id}/award`, { quote_ids: quoteIds })
      void message.success('已定标')
      load()
    } catch (e) { void message.error(extractError(e).detail || '定标失败') }
  }

  const comparisonData = rfq.items.map((item: any) => {
    const row: any = { key: item.id, item_name: item.item_name, qty: Number(item.qty), uom: item.uom }
    for (const sup of rfq.suppliers) {
      const quote = rfq.quotes.find((q: any) => q.rfq_item_id === item.id && q.supplier_id === sup.supplier_id)
      row[`sup_${sup.supplier_id}`] = quote ? { price: Number(quote.unit_price), days: quote.delivery_days, id: quote.id, selected: quote.is_selected } : null
    }
    return row
  })

  const supplierCols = rfq.suppliers.map((sup: any) => ({
    title: sup.supplier_name || supplierMap[sup.supplier_id] || sup.supplier_id.slice(0, 8),
    key: `sup_${sup.supplier_id}`,
    align: 'center' as const,
    render: (_: unknown, row: any) => {
      const q = row[`sup_${sup.supplier_id}`]
      if (!q) {
        return canQuote ? (
          <Button size="small" icon={<PlusOutlined />} onClick={() => setQuoteModal({ rfqItemId: row.key, supplierId: sup.supplier_id })}>录入</Button>
        ) : '-'
      }
      return (
        <Space direction="vertical" size={0}>
          <Typography.Text strong style={q.selected ? { color: '#22C55E' } : undefined}>
            ¥{q.price.toLocaleString()}
          </Typography.Text>
          {q.days && <Typography.Text type="secondary" style={{ fontSize: 11 }}>{q.days}天交付</Typography.Text>}
          {q.selected && <Tag color="success" icon={<CheckCircleOutlined />}>中标</Tag>}
        </Space>
      )
    },
  }))

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Typography.Title level={3} style={{ margin: 0 }}>{rfq.rfq_number}</Typography.Title>
          <Tag color={statusColors[rfq.status]}>{rfq.status}</Tag>
        </Space>
        <Space>
          <Button onClick={() => navigate('/rfqs')}>返回</Button>
          {canSend && <Button type="primary" onClick={doSend}>发出询价</Button>}
          {canAward && (
            <Button type="primary" onClick={() => {
              const selectedIds = rfq.quotes.filter((q: any) => !q.is_selected).length > 0
                ? [] : rfq.quotes.filter((q: any) => q.is_selected).map((q: any) => q.id)
              if (selectedIds.length === 0) {
                const lowestPerItem: string[] = []
                for (const item of rfq.items) {
                  const itemQuotes = rfq.quotes.filter((q: any) => q.rfq_item_id === item.id)
                  if (itemQuotes.length > 0) {
                    const lowest = itemQuotes.reduce((a: any, b: any) => Number(a.unit_price) < Number(b.unit_price) ? a : b)
                    lowestPerItem.push(lowest.id)
                  }
                }
                if (lowestPerItem.length === 0) { void message.warning('暂无报价可定标'); return }
                Modal.confirm({
                  title: '自动选择最低价定标？',
                  content: `将自动选择每个物料的最低报价（共 ${lowestPerItem.length} 项）`,
                  onOk: () => doAward(lowestPerItem),
                })
              } else {
                doAward(selectedIds)
              }
            }}>
              定标（选最低价）
            </Button>
          )}
        </Space>
      </div>

      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label="标题">{rfq.title}</Descriptions.Item>
          <Descriptions.Item label="截止日期">{rfq.deadline || '-'}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColors[rfq.status]}>{rfq.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="创建时间">{rfq.created_at?.slice(0, 10)}</Descriptions.Item>
          {rfq.notes && <Descriptions.Item label="备注" span={2}>{rfq.notes}</Descriptions.Item>}
        </Descriptions>
      </Card>

      <Card title="比价表">
        <Table
          dataSource={comparisonData}
          rowKey="key"
          size="small"
          pagination={false}
          scroll={{ x: 'max-content' }}
          columns={[
            { title: '物料', dataIndex: 'item_name', fixed: 'left', width: 200 },
            { title: '数量', dataIndex: 'qty', width: 80, align: 'right', render: (v: number, r: any) => `${v} ${r.uom}` },
            ...supplierCols,
          ]}
        />
      </Card>

      <Modal title="录入报价" open={!!quoteModal} onCancel={() => setQuoteModal(null)} onOk={doAddQuote} okText="保存">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div><Typography.Text>单价</Typography.Text><InputNumber style={{ width: '100%' }} min={0} value={quotePrice} onChange={(v) => setQuotePrice(Number(v ?? 0))} prefix="¥" /></div>
          <div><Typography.Text>交货天数（可选）</Typography.Text><InputNumber style={{ width: '100%' }} min={0} value={quoteDays ?? undefined} onChange={(v) => setQuoteDays(v ? Number(v) : null)} /></div>
        </Space>
      </Modal>
    </Space>
  )
}
