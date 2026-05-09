import {
  Alert,
  Card,
  Descriptions,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'

interface PortalPO {
  po_number: string
  status: string
  currency: string
  total_amount: string
  qty_received: string
  amount_paid: string
  created_at: string
}

interface PortalContract {
  contract_number: string
  title: string
  status: string
  currency: string
  total_amount: string
  signed_date: string | null
  effective_date: string | null
  expiry_date: string | null
}

interface PortalPayment {
  payment_number: string
  amount: string
  currency: string
  status: string
  due_date: string | null
  payment_date: string | null
  payment_method: string
}

interface PortalShipment {
  shipment_number: string
  batch_no: number
  status: string
  carrier: string | null
  tracking_number: string | null
  expected_date: string | null
  actual_date: string | null
}

interface PortalData {
  name: string
  code: string
  contact_name: string | null
  contact_phone: string | null
  contact_email: string | null
  purchase_orders: PortalPO[]
  contracts: PortalContract[]
  payments: PortalPayment[]
  shipments: PortalShipment[]
}

const statusColors: Record<string, string> = {
  confirmed: 'blue',
  draft: 'default',
  partially_received: 'orange',
  fully_received: 'green',
  closed: 'default',
  cancelled: 'red',
  active: 'green',
  superseded: 'orange',
  terminated: 'red',
  expired: 'default',
  pending: 'gold',
  in_transit: 'blue',
  arrived: 'cyan',
  accepted: 'green',
  partially_accepted: 'orange',
  rejected: 'red',
}

function formatDate(d: string | null) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString()
}

function formatAmount(amount: string, currency: string) {
  const n = parseFloat(amount)
  if (isNaN(n)) return '-'
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: currency || 'CNY',
  }).format(n)
}

export default function SupplierPortalPage() {
  const { t } = useTranslation()
  const { token } = useParams<{ token: string }>()
  const [data, setData] = useState<PortalData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    fetch(`/api/v1/supplier-portal/${token}`)
      .then((res) => {
        if (!res.ok) throw new Error('supplier_portal.invalid_token')
        return res.json()
      })
      .then((json: PortalData) => setData(json))
      .catch(() => setError(t('supplier_portal.invalid_token')))
      .finally(() => setLoading(false))
  }, [token, t])

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--color-bg-layout, #f5f5f5)',
        }}
      >
        <Spin size="large" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          background: 'var(--color-bg-layout, #f5f5f5)',
        }}
      >
        <Alert
          type="error"
          message={error || t('supplier_portal.invalid_token')}
          showIcon
          style={{ maxWidth: 480 }}
        />
      </div>
    )
  }

  const poColumns = [
    {
      title: t('field.po_number'),
      dataIndex: 'po_number',
      key: 'po_number',
    },
    {
      title: t('field.status'),
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>{s}</Tag>
      ),
    },
    {
      title: t('field.amount'),
      dataIndex: 'total_amount',
      key: 'total_amount',
      render: (_: string, r: PortalPO) => formatAmount(r.total_amount, r.currency),
    },
    {
      title: t('supplier_portal.qty_received'),
      dataIndex: 'qty_received',
      key: 'qty_received',
    },
    {
      title: t('supplier_portal.amount_paid'),
      dataIndex: 'amount_paid',
      key: 'amount_paid',
      render: (_: string, r: PortalPO) => formatAmount(r.amount_paid, r.currency),
    },
    {
      title: t('field.created_at'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (d: string) => formatDate(d),
    },
  ]

  const contractColumns = [
    {
      title: t('field.contract_number'),
      dataIndex: 'contract_number',
      key: 'contract_number',
    },
    {
      title: t('supplier_portal.contract_title'),
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: t('field.status'),
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>{s}</Tag>
      ),
    },
    {
      title: t('field.amount'),
      dataIndex: 'total_amount',
      key: 'total_amount',
      render: (_: string, r: PortalContract) =>
        formatAmount(r.total_amount, r.currency),
    },
    {
      title: t('supplier_portal.signed_date'),
      dataIndex: 'signed_date',
      key: 'signed_date',
      render: (d: string | null) => formatDate(d),
    },
    {
      title: t('supplier_portal.expiry_date'),
      dataIndex: 'expiry_date',
      key: 'expiry_date',
      render: (d: string | null) => formatDate(d),
    },
  ]

  const paymentColumns = [
    {
      title: t('field.payment_number'),
      dataIndex: 'payment_number',
      key: 'payment_number',
    },
    {
      title: t('field.status'),
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>{s}</Tag>
      ),
    },
    {
      title: t('field.amount'),
      dataIndex: 'amount',
      key: 'amount',
      render: (_: string, r: PortalPayment) =>
        formatAmount(r.amount, r.currency),
    },
    {
      title: t('field.due_date'),
      dataIndex: 'due_date',
      key: 'due_date',
      render: (d: string | null) => formatDate(d),
    },
    {
      title: t('field.payment_date'),
      dataIndex: 'payment_date',
      key: 'payment_date',
      render: (d: string | null) => formatDate(d),
    },
    {
      title: t('field.payment_method'),
      dataIndex: 'payment_method',
      key: 'payment_method',
    },
  ]

  const shipmentColumns = [
    {
      title: t('field.shipment_number'),
      dataIndex: 'shipment_number',
      key: 'shipment_number',
    },
    {
      title: t('supplier_portal.batch_no'),
      dataIndex: 'batch_no',
      key: 'batch_no',
    },
    {
      title: t('field.status'),
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => (
        <Tag color={statusColors[s] || 'default'}>{s}</Tag>
      ),
    },
    {
      title: t('field.carrier'),
      dataIndex: 'carrier',
      key: 'carrier',
      render: (v: string | null) => v || '-',
    },
    {
      title: t('field.tracking_number'),
      dataIndex: 'tracking_number',
      key: 'tracking_number',
      render: (v: string | null) => v || '-',
    },
    {
      title: t('field.expected_date'),
      dataIndex: 'expected_date',
      key: 'expected_date',
      render: (d: string | null) => formatDate(d),
    },
    {
      title: t('field.actual_date'),
      dataIndex: 'actual_date',
      key: 'actual_date',
      render: (d: string | null) => formatDate(d),
    },
  ]

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-bg-layout, #F7F6F5)',
        padding: '24px',
      }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div
          style={{
            background: '#8B5E3C',
            borderRadius: 12,
            padding: '24px 32px',
            marginBottom: 24,
            color: '#fff',
          }}
        >
          <Typography.Title
            level={2}
            style={{ color: '#fff', margin: 0, marginBottom: 4 }}
          >
            {data.name}
          </Typography.Title>
          <Typography.Text style={{ color: 'rgba(255,255,255,0.8)' }}>
            {data.code}
          </Typography.Text>
          {(data.contact_name || data.contact_phone || data.contact_email) && (
            <Descriptions
              size="small"
              column={3}
              style={{ marginTop: 16 }}
              labelStyle={{ color: 'rgba(255,255,255,0.7)' }}
              contentStyle={{ color: '#fff' }}
            >
              {data.contact_name && (
                <Descriptions.Item label={t('field.contact_name')}>
                  {data.contact_name}
                </Descriptions.Item>
              )}
              {data.contact_phone && (
                <Descriptions.Item label={t('field.contact_phone')}>
                  {data.contact_phone}
                </Descriptions.Item>
              )}
              {data.contact_email && (
                <Descriptions.Item label={t('field.contact_email')}>
                  {data.contact_email}
                </Descriptions.Item>
              )}
            </Descriptions>
          )}
        </div>

        <Card
          title={t('supplier_portal.purchase_orders')}
          style={{ marginBottom: 16 }}
        >
          <Table
            columns={poColumns}
            dataSource={data.purchase_orders}
            rowKey="po_number"
            size="small"
            pagination={false}
            locale={{ emptyText: t('supplier_portal.no_data') }}
          />
        </Card>

        <Card
          title={t('supplier_portal.contracts')}
          style={{ marginBottom: 16 }}
        >
          <Table
            columns={contractColumns}
            dataSource={data.contracts}
            rowKey="contract_number"
            size="small"
            pagination={false}
            locale={{ emptyText: t('supplier_portal.no_data') }}
          />
        </Card>

        <Card
          title={t('supplier_portal.payments')}
          style={{ marginBottom: 16 }}
        >
          <Table
            columns={paymentColumns}
            dataSource={data.payments}
            rowKey="payment_number"
            size="small"
            pagination={false}
            locale={{ emptyText: t('supplier_portal.no_data') }}
          />
        </Card>

        <Card title={t('supplier_portal.shipments')}>
          <Table
            columns={shipmentColumns}
            dataSource={data.shipments}
            rowKey="shipment_number"
            size="small"
            pagination={false}
            locale={{ emptyText: t('supplier_portal.no_data') }}
          />
        </Card>
      </div>
    </div>
  )
}
