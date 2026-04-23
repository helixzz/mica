import { useTranslation } from 'react-i18next'
import { CheckCircleOutlined, PlusOutlined } from '@ant-design/icons'
import { Button, Card, Col, Descriptions, InputNumber, Modal, Row, Select, Space, Table, Tag, Typography, message } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Supplier } from '@/api'
import { client, extractError } from '@/api/client'
import { fmtQty } from '@/utils/format'

const statusColors: Record<string, string> = {
  draft: 'default', sent: 'processing', quoting: 'cyan',
  evaluation: 'orange', awarded: 'success', closed: 'default', cancelled: 'error',
}

export default function RFQDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()
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

  if (!rfq) return <div>{t('message.loading')}</div>

  const supplierMap = Object.fromEntries(suppliers.map((s) => [s.id, s.name]))
  const canSend = rfq.status === 'draft'
  const canQuote = rfq.status === 'sent' || rfq.status === 'quoting'
  const canAward = rfq.status === 'quoting' || rfq.status === 'evaluation'

  const doSend = async () => {
    try {
      await client.post(`/rfqs/${id}/send`)
      void message.success(t('message.rfq_sent'))
      load()
    } catch (e) { void message.error(extractError(e).detail || t('error.send_failed')) }
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
      void message.success(t('rfq.quote_entered'))
      setQuoteModal(null)
      setQuotePrice(0)
      setQuoteDays(null)
      load()
    } catch (e) { void message.error(extractError(e).detail || t('rfq.entry_failed')) }
  }

  const doAward = async (quoteIds: string[]) => {
    try {
      await client.post(`/rfqs/${id}/award`, { quote_ids: quoteIds })
      void message.success(t('rfq.awarded_msg'))
      load()
    } catch (e) { void message.error(extractError(e).detail || t('rfq.award_failed')) }
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
          <Button size="small" icon={<PlusOutlined />} onClick={() => setQuoteModal({ rfqItemId: row.key, supplierId: sup.supplier_id })}>{t('rfq.enter_btn')}</Button>
        ) : '-'
      }
      return (
        <Space direction="vertical" size={0}>
          <Typography.Text strong style={q.selected ? { color: '#22C55E' } : undefined}>
            ¥{q.price.toLocaleString()}
          </Typography.Text>
          {q.days && <Typography.Text type="secondary" style={{ fontSize: 11 }}>{q.days} {t('rfq.days_delivery')}</Typography.Text>}
          {q.selected && <Tag color="success" icon={<CheckCircleOutlined />}>{t('rfq.awarded')}</Tag>}
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
          <Button onClick={() => navigate('/rfqs')}>{t('button.back')}</Button>
          {canSend && <Button type="primary" onClick={doSend}>{t('rfq.send')}</Button>}
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
                if (lowestPerItem.length === 0) { void message.warning(t('rfq.no_quotes')); return }
                Modal.confirm({
                  title: t('rfq.award_confirm_title'),
                  content: t('rfq.auto_award_content', { count: lowestPerItem.length }),
                  onOk: () => doAward(lowestPerItem),
                })
              } else {
                doAward(selectedIds)
              }
            }}>{t('rfq.award')}
            </Button>
          )}
        </Space>
      </div>

      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label={t('field.title')}>{rfq.title}</Descriptions.Item>
          <Descriptions.Item label={t('field.deadline')}>{rfq.deadline || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.status')}><Tag color={statusColors[rfq.status]}>{rfq.status}</Tag></Descriptions.Item>
          <Descriptions.Item label={t('field.created_at')}>{rfq.created_at?.slice(0, 10)}</Descriptions.Item>
          {rfq.notes && <Descriptions.Item label={t('field.notes')} span={2}>{rfq.notes}</Descriptions.Item>}
        </Descriptions>
      </Card>

      <Card title={t('rfq.comparison_table')}>
        <Table
          dataSource={comparisonData}
          rowKey="key"
          size="small"
          pagination={false}
          scroll={{ x: 'max-content' }}
          columns={[
            { title: t('rfq.item_col'), dataIndex: 'item_name', fixed: 'left', width: 200 },
             { title: t('rfq.qty_col'), dataIndex: 'qty', width: 80, align: 'right', render: (v: number, r: any) => `${fmtQty(v)} ${r.uom}` },
            ...supplierCols,
          ]}
        />
      </Card>

      <Modal title={t('rfq.enter_quote')} open={!!quoteModal} onCancel={() => setQuoteModal(null)} onOk={doAddQuote} okText={t('button.save')}>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div><Typography.Text>{t('rfq.unit_price')}</Typography.Text><InputNumber style={{ width: '100%' }} min={0} value={quotePrice} onChange={(v) => setQuotePrice(Number(v ?? 0))} prefix="¥" /></div>
          <div><Typography.Text>{t('rfq.delivery_days')}</Typography.Text><InputNumber style={{ width: '100%' }} min={0} value={quoteDays ?? undefined} onChange={(v) => setQuoteDays(v ? Number(v) : null)} /></div>
        </Space>
      </Modal>
    </Space>
  )
}
