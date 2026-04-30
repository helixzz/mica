import { PlusOutlined } from '@ant-design/icons'
import { Button, Card, Col, DatePicker, Input, Progress, Row, Select, Space, Table, Tag, Typography, theme } from 'antd'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, Contract, DeliveryPlan, DeliveryPlanOverview, PurchaseOrder } from '@/api'
import { DeliveryPlanModal } from '@/components/DeliveryPlanModal'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageHeader } from '@/components/ui/PageHeader'
import { StatCard } from '@/components/ui/StatCard'

const { Text } = Typography

export function DeliveryPlansPage() {
  const { t } = useTranslation()
  const { token } = theme.useToken()
  const [loading, setLoading] = useState(false)
  const [overview, setOverview] = useState<DeliveryPlanOverview | null>(null)
  const [pos, setPos] = useState<PurchaseOrder[]>([])
  const [contracts, setContracts] = useState<Contract[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editingPlan, setEditingPlan] = useState<DeliveryPlan | undefined>()

  const [filters, setFilters] = useState<{
    po_id?: string
    contract_id?: string
    status?: string
    dateRange?: [dayjs.Dayjs, dayjs.Dayjs]
    search?: string
  }>({})

  useEffect(() => {
    loadData()
    loadOptions()
  }, [filters])

  const loadOptions = async () => {
    try {
      const [poData, contractData] = await Promise.all([
        api.listPOs(),
        api.listContracts(),
      ])
      setPos(poData as any)
      setContracts(contractData)
    } catch (err) {
      console.error(err)
    }
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await api.getDeliveryPlansOverview()
      
      let filteredPlans = data.plans
      if (filters.po_id) filteredPlans = filteredPlans.filter(p => p.po_id === filters.po_id)
      if (filters.contract_id) filteredPlans = filteredPlans.filter(p => p.contract_id === filters.contract_id)
      if (filters.status) filteredPlans = filteredPlans.filter(p => p.status === filters.status)
      if (filters.search) {
        const q = filters.search.toLowerCase()
        filteredPlans = filteredPlans.filter(p => 
          p.plan_name.toLowerCase().includes(q) || 
          p.item_name.toLowerCase().includes(q)
        )
      }
      if (filters.dateRange) {
        const [start, end] = filters.dateRange
        filteredPlans = filteredPlans.filter(p => {
          const d = dayjs(p.planned_date)
          return d.isAfter(start.subtract(1, 'day')) && d.isBefore(end.add(1, 'day'))
        })
      }

      setOverview({
        ...data,
        plans: filteredPlans
      })
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'planned': return 'blue'
      case 'in_transit': return 'orange'
      case 'partial': return 'gold'
      case 'complete': return 'green'
      default: return 'default'
    }
  }

  const columns = [
    {
      title: t('delivery_plan.planned_date'),
      dataIndex: 'planned_date',
      key: 'planned_date',
      render: (val: string) => dayjs(val).format('YYYY-MM-DD'),
    },
    {
      title: t('nav.purchase_orders'),
      dataIndex: 'po_id',
      key: 'po_id',
      render: (val: string) => pos.find(p => p.id === val)?.po_number || '-',
    },
    {
      title: t('nav.contracts'),
      dataIndex: 'contract_id',
      key: 'contract_id',
      render: (val: string) => contracts.find(c => c.id === val)?.contract_number || '-',
    },
    {
      title: t('nav.items'),
      dataIndex: 'item_name',
      key: 'item_name',
    },
    {
      title: t('delivery_plan.plan_name'),
      dataIndex: 'plan_name',
      key: 'plan_name',
      render: (val: string, record: DeliveryPlan) => (
        <a onClick={() => { setEditingPlan(record); setModalOpen(true) }}>{val}</a>
      )
    },
    {
      title: t('delivery_plan.planned_qty'),
      dataIndex: 'planned_qty',
      key: 'planned_qty',
    },
    {
      title: t('delivery_plan.actual_qty'),
      dataIndex: 'actual_qty',
      key: 'actual_qty',
    },
    {
      title: t('delivery_plan.status'),
      dataIndex: 'status',
      key: 'status',
      render: (val: string) => <Tag color={getStatusColor(val)}>{t(`status.${val}`)}</Tag>,
    },
    {
      title: t('delivery_plan.notes'),
      dataIndex: 'notes',
      key: 'notes',
    },
  ]

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <PageHeader
        title={t('delivery_plan.title')}
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingPlan(undefined); setModalOpen(true) }}>
            {t('delivery_plan.new_plan')}
          </Button>
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <StatCard
            label={t('delivery_plan.total_planned')}
            value={overview?.total_planned || 0}
          />
        </Col>
        <Col xs={24} sm={8}>
          <StatCard
            label={t('delivery_plan.total_actual')}
            value={overview?.total_actual || 0}
          />
        </Col>
        <Col xs={24} sm={8}>
          <StatCard
            label={t('delivery_plan.completion')}
            value={`${overview?.completion_pct || 0}%`}
          />
        </Col>
      </Row>

      <Card>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space wrap>
            <Select
              placeholder={t('nav.purchase_orders')}
              allowClear
              style={{ width: 200 }}
              onChange={(val) => setFilters(f => ({ ...f, po_id: val }))}
            >
              {pos.map(p => <Select.Option key={p.id} value={p.id}>{p.po_number}</Select.Option>)}
            </Select>
            <Select
              placeholder={t('nav.contracts')}
              allowClear
              style={{ width: 200 }}
              onChange={(val) => setFilters(f => ({ ...f, contract_id: val }))}
            >
              {contracts.map(c => <Select.Option key={c.id} value={c.id}>{c.contract_number}</Select.Option>)}
            </Select>
            <Select
              placeholder={t('delivery_plan.status')}
              allowClear
              style={{ width: 150 }}
              onChange={(val) => setFilters(f => ({ ...f, status: val }))}
            >
              <Select.Option value="planned">{t('status.planned')}</Select.Option>
              <Select.Option value="in_transit">{t('status.in_transit')}</Select.Option>
              <Select.Option value="partial">{t('status.partial')}</Select.Option>
              <Select.Option value="complete">{t('status.complete')}</Select.Option>
            </Select>
            <DatePicker.RangePicker
              onChange={(dates) => setFilters(f => ({ ...f, dateRange: dates as any }))}
            />
            <Input.Search
              placeholder={t('common.search')}
              allowClear
              onSearch={(val) => setFilters(f => ({ ...f, search: val }))}
              style={{ width: 200 }}
            />
          </Space>

          {overview?.plans.length === 0 ? (
            <EmptyState title={t('delivery_plan.no_plans')} description={t('delivery_plan.no_plans')} />
          ) : (
            <Table
              columns={columns}
              dataSource={overview?.plans || []}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          )}

          {overview && overview.plans.length > 0 && (
            <div style={{ marginTop: token.marginLG }}>
              <Text type="secondary">{t('delivery_plan.completion')}</Text>
              <Progress percent={overview.completion_pct} status="active" />
            </div>
          )}
        </Space>
      </Card>

      <DeliveryPlanModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={loadData}
        plan={editingPlan}
      />
    </Space>
  )
}
