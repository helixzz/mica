import { AppstoreOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import {
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'
import { extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import { DocumentTemplatesPanel } from './admin/DocumentTemplatesPanel'
import { ApprovalRulesTab } from './admin/ApprovalRulesTab'
import { SystemParamsTab } from './admin/SystemParamsTab'
import { FeishuSettingsTab } from './admin/FeishuSettingsTab'
import { ImportTab } from './admin/ImportTab'
import { AuditLogsTab } from './admin/AuditLogsTab'
import { UsersPanel } from './admin/UsersPanel'
import { CompaniesPanel } from './admin/CompaniesPanel'
import { DepartmentsPanel } from './admin/DepartmentsPanel'
import { AIModelPanel } from './admin/AIModelPanel'
import type { AIModelRow } from './admin/AIModelPanel'
import { AILogsPanel } from './admin/AILogsPanel'

export function AdminPage() {
  const { t } = useTranslation()
  const { user } = useAuth()

  if (user?.role !== 'admin') {
    return (
      <Card>
        <Typography.Title level={4}>{t('error.permission_denied')}</Typography.Title>
        <Typography.Text type="secondary">{t('admin.admin_only')}</Typography.Text>
      </Card>
    )
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', minWidth: 0 }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        {t('admin.admin_console')}
      </Typography.Title>
      <Tabs
        destroyInactiveTabPane
        tabPosition="top"
        style={{ minWidth: 0 }}
        items={[
          { key: 'system', label: t('admin.system_info'), children: <SystemInfoPanel /> },
          { key: 'companies', label: t('admin.companies'), children: <CompaniesPanel /> },
          { key: 'departments', label: t('admin.departments'), children: <DepartmentsPanel /> },
          { key: 'system_params', label: t('admin.system_params.tab_label'), children: <SystemParamsTab /> },
          { key: 'feishu', label: t('admin.tab.feishu'), children: <FeishuSettingsTab /> },
          { key: 'approval_rules', label: t('admin.approval_rules'), children: <ApprovalRulesTab /> },
          { key: 'classification', label: t('admin.classification'), children: <ClassificationTab /> },
          { key: 'document_templates', label: t('admin.document_templates'), children: <DocumentTemplatesPanel /> },
          { key: 'import', label: t('admin.tab.import'), children: <ImportTab /> },
          { key: 'models', label: t('admin.llm_models'), children: <AIModelPanel /> },
          { key: 'routings', label: t('admin.ai_routing'), children: <RoutingsPanel /> },
          { key: 'users', label: t('admin.users'), children: <UsersPanel /> },
          { key: 'ai_logs', label: t('admin.ai_logs'), children: <AILogsPanel /> },
          { key: 'audit-logs', label: t('admin.tab.audit_logs'), children: <AuditLogsTab /> },
          { key: 'recycle_bin', label: t('admin.recycle_bin'), children: <RecycleBinPanel /> },
        ]}
      />
    </Space>
  )
}

function SystemInfoPanel() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null)
  useEffect(() => {
    void api.adminSystemInfo().then(setInfo)
  }, [])
  if (!info) return null
  return (
    <Card>
      <Descriptions bordered column={2} size="small">
        {Object.entries(info).map(([k, v]) => (
          <Descriptions.Item key={k} label={k}>
            {Array.isArray(v) ? v.join(', ') : String(v)}
          </Descriptions.Item>
        ))}
      </Descriptions>
    </Card>
  )
}

function RoutingsPanel() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [models, setModels] = useState<AIModelRow[]>([])
  const [loading, setLoading] = useState(false)
  const [pendingToggle, setPendingToggle] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    Promise.all([api.adminListRoutings(), api.adminListAIModels()])
      .then(([r, m]) => { setRows(r); setModels(m as AIModelRow[]) })
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const changePrimary = async (feature_code: string, primary_model_id: string | null, current: Record<string, unknown>) => {
    await api.adminUpsertRouting(feature_code, {
      feature_code,
      primary_model_id,
      fallback_model_ids: current.fallback_model_ids,
      prompt_template: current.prompt_template,
      temperature: current.temperature,
      max_tokens: current.max_tokens,
      enabled: current.enabled,
    })
    void message.success(t('admin.routing_updated'))
    load()
  }

  const applyEnabledChange = async (current: Record<string, unknown>, nextEnabled: boolean) => {
    setPendingToggle(current.feature_code as string)
    try {
      await api.adminUpsertRouting(current.feature_code as string, {
        feature_code: current.feature_code,
        primary_model_id: current.primary_model_id,
        fallback_model_ids: current.fallback_model_ids,
        prompt_template: current.prompt_template,
        temperature: current.temperature,
        max_tokens: current.max_tokens,
        enabled: nextEnabled,
      })
      void message.success(
        nextEnabled ? t('admin.routing_enabled_toast') : t('admin.routing_disabled_toast'),
      )
      load()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setPendingToggle(null)
    }
  }

  return (
    <Table
      rowKey="feature_code"
      dataSource={rows}
      loading={loading}
      pagination={false}
      columns={[
        { title: t('admin.feature_col'), dataIndex: 'feature_code' },
        {
          title: t('admin.primary_model'),
          dataIndex: 'primary_model_id',
          render: (v: string | null, r) => (
            <Select
              style={{ width: 240 }}
              value={v || undefined}
              onChange={(val) => changePrimary(r.feature_code as string, val, r)}
              allowClear
              options={models.map((m) => ({ value: m.id, label: `${m.name} (${m.modality})` }))}
              placeholder={t('admin.not_configured')}
            />
          ),
        },
        { title: 'Temperature', dataIndex: 'temperature' },
        { title: 'Max Tokens', dataIndex: 'max_tokens' },
        {
          title: t('admin.enabled_col'),
          dataIndex: 'enabled',
          width: 120,
          render: (v: boolean, r) => {
            const feature = r.feature_code as string
            const loading_ = pendingToggle === feature
            const switchEl = (
              <Switch
                checked={v}
                loading={loading_}
                disabled={loading_}
                onChange={!v ? undefined : (next) => void applyEnabledChange(r, next)}
              />
            )
            if (v) return switchEl
            return (
              <Popconfirm
                title={t('admin.routing_enable_confirm_title')}
                description={t('admin.routing_enable_confirm_desc')}
                okText={t('admin.routing_enable_confirm_ok')}
                cancelText={t('button.cancel')}
                onConfirm={() => void applyEnabledChange(r, true)}
              >
                <Switch checked={false} loading={loading_} disabled={loading_} />
              </Popconfirm>
            )
          },
        },
      ]}
    />
  )
}

function ClassificationTab() {
  const { t } = useTranslation()
  const [costCenters, setCostCenters] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [expenseTypes, setExpenseTypes] = useState<any[]>([])
  const [adding, setAdding] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<any | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    void api.listCostCenters(true).then(setCostCenters)
    void api.getCategoryTree().then(setCategories)
    void api.listLookupValues('expense_type').then(setExpenseTypes)
  }
  useEffect(load, [])

  const handleAdd = async (dimension: string) => {
    try {
      const values = form.getFieldsValue()
      if (dimension === 'cost_center') {
        await api.createCostCenter(values)
      } else if (dimension === 'category') {
        await api.createProcurementCategory(values)
      } else {
        await api.createLookupValue({ ...values, type: 'expense_type' })
      }
      void message.success(t('admin.added'))
      form.resetFields()
      setAdding(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('error.create_failed'))
    }
  }

  const handleUpdate = async () => {
    if (!editingItem) return
    try {
      const values = form.getFieldsValue()
      if (editingItem._dimension === 'category') {
        await api.updateProcurementCategory(editingItem.id, values)
      } else if (editingItem._dimension === 'expense_type') {
        await api.updateLookupValue(editingItem.id, values)
      } else {
        await api.updateCostCenter(editingItem.id, values)
      }
      void message.success(t('common.updated'))
      form.resetFields()
      setEditingItem(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('error.save_failed'))
    }
  }

  const handleDelete = async (dimension: string, id: string) => {
    try {
      if (dimension === 'cost_center') await api.deleteCostCenter(id)
      else if (dimension === 'category') await api.deleteProcurementCategory(id)
      else await api.deleteLookupValue(id)
      void message.success(t('message.deleted'))
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  const handleToggleActive = async (item: any, dimension: string) => {
    try {
      const body = {
        code: item.code,
        label_zh: item.label_zh,
        label_en: item.label_en,
        sort_order: item.sort_order,
        is_enabled: !item.is_enabled,
        annual_budget: item.annual_budget ?? undefined,
        budget_start_date: item.budget_start_date ?? undefined,
        budget_end_date: item.budget_end_date ?? undefined,
      }
      if (dimension === 'category') {
        await api.updateProcurementCategory(item.id, body)
      } else if (dimension === 'expense_type') {
        await api.updateLookupValue(item.id, body)
      } else {
        await api.updateCostCenter(item.id, body)
      }
      void message.success(item.is_enabled ? t('admin.deactivated') : t('common.updated'))
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  const openEdit = (item: any, dimension: string) => {
    setEditingItem({ ...item, _dimension: dimension })
    form.resetFields()
    form.setFieldsValue({
      code: item.code,
      label_zh: item.label_zh,
      label_en: item.label_en,
      sort_order: item.sort_order,
      annual_budget: item.annual_budget ?? undefined,
      budget_start_date: item.budget_start_date ?? undefined,
      budget_end_date: item.budget_end_date ?? undefined,
    })
  }

  const renderList = (dimension: string, items: any[], title: string) => (
    <Card
      size="small"
      title={<Space><AppstoreOutlined />{title}</Space>}
      extra={<Button size="small" icon={<PlusOutlined />} onClick={() => { setAdding(dimension); setEditingItem(null); form.resetFields() }}>{t('common.add')}</Button>}
      style={{ marginBottom: 16 }}
    >
      <Table
        dataSource={items}
        rowKey="id"
        size="small"
        pagination={false}
        columns={[
          { title: t('admin.code_col'), dataIndex: 'code', width: 120 },
          { title: t('admin.label_zh'), dataIndex: 'label_zh' },
          { title: t('admin.label_en'), dataIndex: 'label_en' },
          { title: t('admin.sort_order'), dataIndex: 'sort_order', width: 60 },
          {
            title: t('admin.status_col'),
            dataIndex: 'is_enabled',
            width: 70,
            render: (v: boolean) => (
              <Tag color={v !== false ? 'success' : 'default'}>
                {v !== false ? t('common.enabled') : t('common.disabled')}
              </Tag>
            ),
          },
          {
            title: t('common.actions'),
            width: 240,
            render: (_: unknown, r: any) => (
              <Space>
                <Button size="small" onClick={() => openEdit(r, dimension)}>{t('button.edit')}</Button>
                <Button
                  size="small"
                  danger={r.is_enabled !== false}
                  onClick={() => handleToggleActive(r, dimension)}
                >
                  {r.is_enabled !== false ? t('common.disabled') : t('common.enabled')}
                </Button>
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(dimension, r.id)} />
              </Space>
            ),
          },
        ]}
      />
    </Card>
  )

  const renderCategoryTree = () => (
    <Card
      size="small"
      title={<Space><AppstoreOutlined />{t('admin.category_hierarchy')}</Space>}
      extra={<Button size="small" icon={<PlusOutlined />} onClick={() => { setAdding('category'); form.resetFields() }}>{t('common.add')}</Button>}
      style={{ marginBottom: 16 }}
    >
      {categories.map((cat: any) => (
        <div key={cat.id}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
            <Space>
              <Tag color="blue">L1</Tag>
              <Typography.Text strong>{cat.label_zh}</Typography.Text>
              <Typography.Text type="secondary">{cat.code}</Typography.Text>
            </Space>
            <Space>
              <Button size="small" onClick={() => openEdit(cat, 'category')}>{t('button.edit')}</Button>
              <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete('category', cat.id)} />
            </Space>
          </div>
          {(cat.children || []).map((child: any) => (
            <div key={child.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0 4px 32px', borderBottom: '1px solid #fafafa' }}>
              <Space>
                <Tag>L2</Tag>
                <Typography.Text>{child.label_zh}</Typography.Text>
                <Typography.Text type="secondary">{child.code}</Typography.Text>
              </Space>
              <Space>
                <Button size="small" onClick={() => openEdit(child, 'category')}>{t('button.edit')}</Button>
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete('category', child.id)} />
              </Space>
            </div>
          ))}
        </div>
      ))}
      {categories.length === 0 && <Typography.Text type="secondary">{t('admin.no_categories')}</Typography.Text>}
    </Card>
  )

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {renderList('cost_center', costCenters, t('admin.cost_center_title'))}
      {renderCategoryTree()}
      {renderList('expense_type', expenseTypes, t('admin.expense_type_title'))}

      <Modal
        title={editingItem
          ? t('admin.edit_cost_center')
          : adding === 'cost_center' ? t('admin.add_cost_center') : adding === 'category' ? t('admin.add_category') : t('admin.add_expense_type')}
        open={!!adding || !!editingItem}
        onCancel={() => { setAdding(null); setEditingItem(null) }}
        onOk={() => editingItem ? handleUpdate() : adding && handleAdd(adding)}
        okText={t('button.save')}
        cancelText={t('button.cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="code" label={t('admin.code_label')} rules={[{ required: true }]}>
            <Input placeholder={t('admin.code_placeholder')} />
          </Form.Item>
          <Form.Item name="label_zh" label={t('admin.label_zh')} rules={[{ required: true }]}>
            <Input placeholder={t('admin.label_zh_placeholder')} />
          </Form.Item>
          <Form.Item name="label_en" label={t('admin.label_en')} rules={[{ required: true }]}>
            <Input placeholder="IT Department / Laptops / CapEx" />
          </Form.Item>
          <Form.Item name="sort_order" label={t('admin.sort_order')} initialValue={0}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          {(adding === 'cost_center' || editingItem?._dimension === 'cost_center') && (
            <>
              <Form.Item name="annual_budget" label={t('dashboard.annual_budget')}>
                <InputNumber style={{ width: '100%' }} min={0} precision={2} placeholder="0.00" />
              </Form.Item>
              <Form.Item name="budget_start_date" label={t('dashboard.budget_start_date')}>
                <Input placeholder="YYYY-MM-DD" />
              </Form.Item>
              <Form.Item name="budget_end_date" label={t('dashboard.budget_end_date')}>
                <Input placeholder="YYYY-MM-DD" />
              </Form.Item>
            </>
          )}
          {adding === 'category' && (
            <Form.Item name="parent_id" label={t('admin.parent_category')}>
              <Select
                allowClear
                placeholder={t('admin.select_parent')}
                options={categories.map((c: any) => ({ value: c.id, label: c.label_zh }))}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </Space>
  )
}


function RecycleBinPanel() {
  const { t } = useTranslation()
  const [items, setItems] = useState<{ entity_type: string; entity_id: string; code: string; label: string; deleted_at: string | null }[]>([])
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    api.listRecycleBin().then(setItems).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const entityTypeLabels: Record<string, string> = {
    company: t('field.company'),
    department: t('field.department'),
    cost_center: t('field.cost_center'),
    procurement_category: t('field.procurement_category'),
    lookup_value: t('field.expense_type'),
    supplier: t('field.supplier'),
    item: t('field.item_name'),
  }

  const restore = async (entityType: string, entityId: string) => {
    try {
      await api.restoreFromRecycleBin(entityType, entityId)
      void message.success(t('admin.restored'))
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Text type="secondary">
        {t('admin.recycle_bin_hint')}
      </Typography.Text>
      <Table
        rowKey={(r) => `${r.entity_type}-${r.entity_id}`}
        dataSource={items}
        loading={loading}
        pagination={{ pageSize: 20 }}
        locale={{ emptyText: t('admin.recycle_bin_empty') }}
        columns={[
          {
            title: t('admin.entity_type'),
            dataIndex: 'entity_type',
            width: 120,
            render: (v: string) => <Tag>{entityTypeLabels[v] || v}</Tag>,
            filters: Object.entries(entityTypeLabels).map(([k, v]) => ({ text: v, value: k })),
            onFilter: (value: any, record: any) => record.entity_type === value,
          },
          { title: t('admin.code_col'), dataIndex: 'code', width: 140 },
          { title: t('field.title'), dataIndex: 'label' },
          {
            title: t('admin.deleted_at'),
            dataIndex: 'deleted_at',
            width: 180,
            render: (v: string | null) => v ? new Date(v).toLocaleString() : '-',
          },
          {
            title: t('common.actions'),
            width: 100,
            render: (_: unknown, r: any) => (
              <Button size="small" type="primary" onClick={() => restore(r.entity_type, r.entity_id)}>
                {t('admin.restore')}
              </Button>
            ),
          },
        ]}
      />
    </Space>
  )
}