import { DeleteOutlined, ExperimentOutlined, InfoCircleOutlined, PlusOutlined, ThunderboltOutlined, AppstoreOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Statistic,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'
import { extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
import {
  createDefaultApprovalRuleForm,
  mapApprovalRuleFormToPayload,
  mapApprovalRuleToForm,
} from './admin/approvalRuleForm'
import { SystemParamsTab } from './admin/SystemParamsTab'

type AIModelRow = {
  id: string
  name: string
  provider: string
  model_string: string
  modality: string
  api_base: string | null
  api_key_masked: string | null
  timeout_s: number
  is_active: boolean
  priority: number
}

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
          { key: 'companies', label: t('admin.companies'), children: <CompaniesTab /> },
          { key: 'departments', label: t('admin.departments'), children: <DepartmentsTab /> },
          { key: 'system_params', label: t('admin.system_params'), children: <SystemParamsTab /> },
          { key: 'approval_rules', label: t('admin.approval_rules'), children: <ApprovalRulesTab /> },
          { key: 'classification', label: t('admin.classification'), children: <ClassificationTab /> },
          { key: 'import', label: '数据导入', children: <ImportTab /> },
          { key: 'models', label: t('admin.llm_models'), children: <AIModelsPanel /> },
          { key: 'routings', label: t('admin.ai_routing'), children: <RoutingsPanel /> },
          { key: 'users', label: t('admin.users'), children: <UsersPanel /> },
          { key: 'ai_logs', label: t('admin.ai_logs'), children: <AILogsPanel /> },
          { key: 'audit', label: t('admin.audit'), children: <AuditPanel /> },
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

function AIModelsPanel() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<AIModelRow[]>([])
  const [loading, setLoading] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [editing, setEditing] = useState<AIModelRow | null>(null)

  const load = () => {
    setLoading(true)
    api.adminListAIModels().then((d) => setRows(d as AIModelRow[])).finally(() => setLoading(false))
  }
  useEffect(load, [])

  const test = async (id: string) => {
    const r = await api.adminTestAIModel(id)
    if (r.success) {
      void message.success(t('admin.connection_ok') + ` (${r.latency_ms}ms): ${r.model_response?.slice(0, 80)}`)
    } else {
      void message.error(t('admin.connection_fail') + `: ${r.error}`)
    }
  }

  const del = async (id: string) => {
    await api.adminDeleteAIModel(id)
    void message.success(t('message.deleted'))
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setEditOpen(true) }}>{t('admin.new_model')}
        </Button>
      </Space>
      <Table
        rowKey="id"
        dataSource={rows}
        loading={loading}
        pagination={false}
        columns={[
          { title: 'Name', dataIndex: 'name' },
          { title: 'Provider', dataIndex: 'provider' },
          { title: 'Model', dataIndex: 'model_string' },
          { title: 'Modality', dataIndex: 'modality', render: (v) => <Tag>{v}</Tag> },
          { title: 'API Base', dataIndex: 'api_base' },
          { title: 'Key', dataIndex: 'api_key_masked' },
          { title: 'Active', dataIndex: 'is_active', render: (v: boolean) => v ? <Tag color="success">ON</Tag> : <Tag>OFF</Tag> },
          {
            title: '',
            render: (_, r) => (
              <Space>
                <Button size="small" icon={<ThunderboltOutlined />} onClick={() => test(r.id)}>{t('admin.test_connection')}
                </Button>
                <Button size="small" onClick={() => { setEditing(r); setEditOpen(true) }}>{t('button.edit')}
                </Button>
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => {
                  Modal.confirm({ title: `${t('button.delete')} ${r.name}?`, onOk: () => del(r.id) })
                }} />
              </Space>
            ),
          },
        ]}
      />
      <AIModelDrawer
        open={editOpen}
        initial={editing}
        onClose={() => setEditOpen(false)}
        onSaved={() => { setEditOpen(false); load() }}
      />
    </>
  )
}

function AIModelDrawer({
  open, initial, onClose, onSaved,
}: {
  open: boolean
  initial: AIModelRow | null
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (open) {
      form.resetFields()
      if (initial) {
        form.setFieldsValue({
          name: initial.name,
          provider: initial.provider,
          model_string: initial.model_string,
          modality: initial.modality,
          api_base: initial.api_base,
          api_key: '',
          timeout_s: initial.timeout_s,
          priority: initial.priority,
          is_active: initial.is_active,
        })
      } else {
        form.setFieldsValue({
          modality: 'text', timeout_s: 60, priority: 100, is_active: true,
        })
      }
    }
  }, [open, initial, form])

  const save = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const body: Record<string, unknown> = {
        name: values.name,
        provider: values.provider,
        model_string: values.model_string,
        modality: values.modality,
        api_base: values.api_base || null,
        timeout_s: values.timeout_s,
        priority: values.priority,
        is_active: values.is_active,
      }
      if (values.api_key) body.api_key = values.api_key
      if (initial) {
        await api.adminUpdateAIModel(initial.id, body)
      } else {
        await api.adminCreateAIModel(body)
      }
      void message.success(t('message.saved'))
      onSaved()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Drawer
      title={initial ? t('admin.edit_model', { name: initial.name }) : t('admin.new_llm_model')}
      open={open}
      onClose={onClose}
      width={520}
      extra={<Button type="primary" onClick={save} loading={busy}>{t('button.save')}</Button>}
    >
      <Form form={form} layout="vertical">
        <Alert
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginBottom: 16 }}
          message={t('admin.openai_guide_title')}
          description={
            <Typography.Text style={{ fontSize: 13 }}>
              {t('admin.openai_guide_body')}
              <br />3. <b>API Base</b> 填 vendor 的 <Typography.Text code>/v1</Typography.Text> 端点（例如 <Typography.Text code>https://api.modelverse.cn/v1</Typography.Text>）

            </Typography.Text>
          }
        />
        <Form.Item label={t('admin.model_name')} name="name" help={t('admin.model_name_help')} rules={[{ required: true }]}>
          <Input placeholder="qwen-max / gpt-4o / glm-4.7 / ..." />
        </Form.Item>
        <Form.Item
          label="Provider"
          name="provider"
          rules={[{ required: true }]}
          help={t('admin.provider_help')}
        >
          <Input placeholder="openai / anthropic / dashscope / volcengine / mock" />
        </Form.Item>
        <Form.Item
          label="Model String"
          name="model_string"
          rules={[{ required: true }]}
          help={t('admin.model_string_help')}
        >
          <Input placeholder="zai-org/glm-4.7 · deepseek-chat · openai/gpt-4o" />
        </Form.Item>
        <Form.Item label="Modality" name="modality" help={t('admin.modality_help')}>
          <Select options={[
            { value: 'text' }, { value: 'vision' }, { value: 'ocr' }, { value: 'embedding' },
          ]} />
        </Form.Item>
        <Form.Item label="API Base" name="api_base" help={t('admin.api_base_help')}>
          <Input placeholder={t('admin.api_base_placeholder')} />
        </Form.Item>
        <Form.Item label="API Key" name="api_key" help={initial ? t('admin.api_key_help_edit') : t('admin.api_key_help_new')}>
          <Input.Password />
        </Form.Item>
        <Space>
          <Form.Item label="Timeout (s)" name="timeout_s" help={t('admin.timeout_help')}>
            <InputNumber min={1} max={300} />
          </Form.Item>
          <Form.Item label="Priority" name="priority" help={t('admin.priority_help')}>
            <InputNumber />
          </Form.Item>
          <Form.Item label={t('common.enabled')} name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Space>
      </Form>
    </Drawer>
  )
}

function RoutingsPanel() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [models, setModels] = useState<AIModelRow[]>([])
  const [loading, setLoading] = useState(false)

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
        { title: 'Enabled', dataIndex: 'enabled', render: (v: boolean) => v ? <Tag color="success">✓</Tag> : <Tag>✗</Tag> },
      ]}
    />
  )
}

function UsersPanel() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<any | null>(null)
  const [resetPwdUser, setResetPwdUser] = useState<any | null>(null)
  const [form] = Form.useForm()
  const [resetForm] = Form.useForm()
  const [companies, setCompanies] = useState<any[]>([])
  const [departments, setDepartments] = useState<any[]>([])

  const load = () => {
    setLoading(true)
    api.adminListUsers().then(setRows).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    api.companies(true).then(setCompanies)
    api.departments().then(setDepartments)
  }, [])

  const openCreate = () => {
    setEditingUser(null)
    form.resetFields()
    form.setFieldsValue({ role: 'requester', preferred_locale: 'zh-CN' })
    setDrawerOpen(true)
  }

  const openEdit = (user: any) => {
    setEditingUser(user)
    form.resetFields()
    form.setFieldsValue({
      username: user.username,
      display_name: user.display_name,
      email: user.email,
      role: user.role,
      company_id: user.company_id,
      department_id: user.department_id,
      preferred_locale: user.preferred_locale,
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingUser) {
        await api.adminUpdateUser(editingUser.id, values)
        void message.success(t('common.updated'))
      } else {
        await api.adminCreateUser(values)
        void message.success(t('message.created'))
      }
      setDrawerOpen(false)
      load()
    } catch (e: any) {
      if (e.errorFields) return // Form validation error
      void message.error(e?.response?.data?.detail || t('error.save_failed'))
    }
  }

  const toggleActive = async (user: any) => {
    try {
      await api.adminUpdateUser(user.id, { is_active: !user.is_active })
      void message.success(user.is_active ? t('admin.deactivated') : t('common.updated'))
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  const handleResetPassword = async () => {
    try {
      const values = await resetForm.validateFields()
      await api.adminResetPassword(resetPwdUser.id, values.new_password)
      void message.success(t('admin.password_reset_ok'))
      setResetPwdUser(null)
    } catch (e: any) {
      if (e.errorFields) return
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Text type="secondary">{rows.length} {t('admin.user_count')}</Typography.Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>{t('admin.new_user')}</Button>
      </div>
      <Table
        rowKey="id"
        dataSource={rows}
        loading={loading}
        pagination={{ pageSize: 20 }}
        size="small"
        columns={[
          { title: t('admin.username_col'), dataIndex: 'username' },
          { title: t('admin.display_name_col'), dataIndex: 'display_name' },
          { title: t('admin.role_col'), dataIndex: 'role', render: (v: string) => <Tag color="orange">{v}</Tag> },
          { title: t('admin.email_col'), dataIndex: 'email' },
          { title: t('admin.department_col'), dataIndex: 'department_id', render: (v: string) => v || '-' },
          { title: t('admin.locale_col'), dataIndex: 'preferred_locale' },
          { title: t('admin.active_col'), dataIndex: 'is_active', render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? t('common.enabled') : t('common.disabled')}</Tag> },
          { title: t('admin.auth_provider_col'), dataIndex: 'auth_provider' },
          { title: t('admin.last_login_col'), dataIndex: 'last_login_at', render: (v?: string) => v ? new Date(v).toLocaleString() : '-' },
          {
            title: t('common.actions'),
            width: 260,
            render: (_: unknown, r: any) => (
              <Space>
                <Button size="small" onClick={() => openEdit(r)}>{t('button.edit')}</Button>
                <Button size="small" onClick={() => { setResetPwdUser(r); resetForm.resetFields() }}>{t('admin.reset_password')}</Button>
                <Button size="small" danger={r.is_active} onClick={() => toggleActive(r)}>
                  {r.is_active ? t('common.disabled') : t('common.enabled')}
                </Button>
              </Space>
            ),
          },
        ]}
      />
      <Drawer
        title={editingUser ? t('admin.edit_user', { name: editingUser.username }) : t('admin.new_user')}
        width={420}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setDrawerOpen(false)}>{t('button.cancel')}</Button>
            <Button type="primary" onClick={handleSave}>{t('button.save')}</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="username" label={t('admin.username_label')} rules={[{ required: true }]}>
            <Input disabled={!!editingUser} />
          </Form.Item>
          <Form.Item name="display_name" label={t('admin.display_name_label')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label={t('admin.email_label')} rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          {!editingUser && (
            <Form.Item name="password" label={t('admin.password_label')} rules={[{ required: true }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="role" label={t('admin.role_label')} rules={[{ required: true }]}>
            <Select options={[
              { value: 'admin', label: 'admin' },
              { value: 'requester', label: 'requester' },
              { value: 'it_buyer', label: 'it_buyer' },
              { value: 'dept_manager', label: 'dept_manager' },
              { value: 'finance_auditor', label: 'finance_auditor' },
              { value: 'procurement_mgr', label: 'procurement_mgr' },
            ]} />
          </Form.Item>
          <Form.Item name="company_id" label={t('admin.company_label')} rules={[{ required: true }]}>
            <Select options={companies.map(c => ({ value: c.id, label: c.name_zh }))} />
          </Form.Item>
          <Form.Item name="department_id" label={t('admin.department_label')}>
            <Select allowClear options={departments.map(d => ({ value: d.id, label: d.name }))} />
          </Form.Item>
          <Form.Item name="preferred_locale" label={t('admin.locale_label')}>
            <Select options={[{ value: 'zh-CN', label: 'zh-CN' }, { value: 'en-US', label: 'en-US' }]} />
          </Form.Item>
        </Form>
      </Drawer>
      <Modal
        title={resetPwdUser ? t('admin.reset_password_title', { name: resetPwdUser.username }) : ''}
        open={!!resetPwdUser}
        onCancel={() => setResetPwdUser(null)}
        onOk={handleResetPassword}
      >
        <Form form={resetForm} layout="vertical">
          <Form.Item name="new_password" label={t('admin.new_password')} rules={[{ required: true, min: 8, message: t('admin.password_min_length') }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}

function AILogsPanel() {
  const [logs, setLogs] = useState<Record<string, unknown>[]>([])
  const [stats, setStats] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([api.adminAICallLogs({ since_days: 7 }), api.adminAICallStats(7)])
      .then(([l, s]) => { setLogs(l); setStats(s) })
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Space wrap>
        {stats.map((s) => (
          <Card key={String(s.feature_code)} size="small" style={{ minWidth: 180 }}>
            <Statistic
              title={String(s.feature_code)}
              value={Number(s.total_calls)}
              suffix={`calls · ${Number(s.total_tokens)} tokens`}
            />
            <Typography.Text type="secondary">
              avg {Number(s.avg_latency_ms).toFixed(0)}ms
            </Typography.Text>
          </Card>
        ))}
      </Space>
      <Table
        rowKey="id"
        dataSource={logs}
        loading={loading}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: 'Time', dataIndex: 'occurred_at', render: (v: string) => new Date(v).toLocaleString() },
          { title: 'Feature', dataIndex: 'feature_code' },
          { title: 'Model', dataIndex: 'model_name' },
          { title: 'Provider', dataIndex: 'provider' },
          { title: 'Tokens', render: (_, r) => `${r.prompt_tokens}/${r.completion_tokens}` },
          { title: 'Latency', dataIndex: 'latency_ms', render: (v: number) => `${v}ms` },
          { title: 'Status', dataIndex: 'status', render: (v: string) => v === 'success' ? <Tag color="success">{v}</Tag> : <Tag color="error">{v}</Tag> },
          { title: 'Error', dataIndex: 'error', ellipsis: true },
        ]}
      />
    </Space>
  )
}

function AuditPanel() {
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.adminAuditLogs({ since_days: 7 }).then(setRows).finally(() => setLoading(false))
  }, [])

  return (
    <Table
      rowKey="id"
      dataSource={rows}
      loading={loading}
      pagination={{ pageSize: 30 }}
      columns={[
        { title: 'Time', dataIndex: 'occurred_at', render: (v: string) => new Date(v).toLocaleString() },
        { title: 'Actor', dataIndex: 'actor_name' },
        { title: 'Event', dataIndex: 'event_type' },
        { title: 'Resource', render: (_, r) => `${r.resource_type ?? ''} ${r.resource_id ?? ''}` },
        { title: 'Comment', dataIndex: 'comment', ellipsis: true },
      ]}
    />
  )
}

function ApprovalRulesTab() {
  const { t } = useTranslation()
  const [rules, setRules] = useState<any[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRule, setEditingRule] = useState<any | null>(null)
  const [form] = Form.useForm()
  const roleOptions = [
    { value: 'dept_manager', label: t('role.dept_manager') },
    { value: 'procurement_mgr', label: t('role.procurement_mgr') },
    { value: 'finance_auditor', label: t('role.finance_auditor') },
    { value: 'it_buyer', label: t('role.it_buyer') },
    { value: 'admin', label: t('role.admin') },
  ]

  useEffect(() => {
    void api.adminListApprovalRules?.()?.then(setRules).catch(() => {})
  }, [])

  const reloadRules = () => {
    void api.adminListApprovalRules?.()?.then(setRules).catch(() => {})
  }

  const openCreate = () => {
    setEditingRule(null)
    form.resetFields()
    form.setFieldsValue(createDefaultApprovalRuleForm(t('admin.default_stage_name')))
    setDrawerOpen(true)
  }

  const openEdit = (rule: any) => {
    setEditingRule(rule)
    form.resetFields()
    form.setFieldsValue(mapApprovalRuleToForm(rule, t('admin.default_stage_name')))
    setDrawerOpen(true)
  }

  const deleteRule = (rule: any) => {
    Modal.confirm({
      title: `${t('button.delete')} ${rule.name}?`,
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.adminDeleteApprovalRule?.(rule.id)
          void message.success(t('message.deleted'))
          reloadRules()
        } catch (e: any) {
          void message.error(e?.response?.data?.detail || t('error.unexpected'))
        }
      },
    })
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      const payload = mapApprovalRuleFormToPayload(values)
      if (editingRule) {
        await api.adminUpdateApprovalRule?.(editingRule.id, payload)
      } else {
        await api.adminCreateApprovalRule?.(payload)
      }
      void message.success(t('message.saved'))
      setDrawerOpen(false)
      form.resetFields()
      setEditingRule(null)
      reloadRules()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('error.save_failed'))
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Text type="secondary">{rules.length} {t('admin.rule_count')}</Typography.Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>{t('admin.new_rule')}</Button>
      </div>
      <Table dataSource={rules} rowKey="id" size="small" pagination={false} columns={[
        { title: t('admin.biz_type'), dataIndex: 'biz_type' },
        { title: t('admin.amount_range'), render: (_: unknown, r: any) => `${r.amount_min ?? 0} - ${r.amount_max ?? '∞'}` },
        {
          title: t('admin.stage_count'),
          render: (_: unknown, r: any) => Array.isArray(r.stages) ? r.stages.length : '-'
        },
        {
          title: t('admin.stages_preview'),
          render: (_: unknown, r: any) => Array.isArray(r.stages)
            ? r.stages.map((stage: any) => stage.stage_name).join(' → ')
            : '-',
        },
        { title: t('admin.priority'), dataIndex: 'priority' },
        { title: t('admin.enabled'), dataIndex: 'is_active', render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? t('common.yes') : t('common.no')}</Tag> },
        {
          title: t('common.actions'),
          render: (_: unknown, r: any) => (
            <Space>
              <Button size="small" onClick={() => openEdit(r)}>{t('button.edit')}</Button>
              <Button size="small" danger onClick={() => deleteRule(r)}>{t('button.delete')}</Button>
            </Space>
          ),
        },
      ]} />
      <Drawer title={editingRule ? t('admin.edit_rule_title_existing', { name: editingRule.name }) : t('admin.edit_rule_title')} width={560} open={drawerOpen} onClose={() => { setDrawerOpen(false); setEditingRule(null) }} footer={
        <Space style={{ float: 'right' }}><Button onClick={() => { setDrawerOpen(false); setEditingRule(null) }}>{t('button.cancel')}</Button><Button type="primary" onClick={handleSave}>{t('button.save')}</Button></Space>
      }>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t('field.title')} help={t('admin.rule_name_help')} rules={[{ required: true }]}>
            <Input placeholder={t('admin.rule_name_placeholder')} />
          </Form.Item>
          <Form.Item name="biz_type" label={t('admin.biz_type')} help={t('admin.biz_type_help')} rules={[{ required: true }]}>
            <Select options={[{ value: 'purchase_requisition', label: t('admin.purchase_requisition_opt') }]} />
          </Form.Item>
          <Form.Item name="amount_min" label={t('admin.min_amount')} help={t('admin.min_amount_help')}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
          <Form.Item name="amount_max" label={t('admin.max_amount')} help={t('admin.max_amount_help')}><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
          <Form.Item name="priority" label={t('admin.priority')} help={t('admin.priority_help')} initialValue={100}><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="is_active" label={t('admin.enabled')} valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
          <Typography.Text strong>{t('admin.stages_editor_title')}</Typography.Text>
          <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            {t('admin.stages_editor_help')}
          </Typography.Text>
          <Form.List name="stages">
            {(fields, { add, remove }) => (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                {fields.map((field, index) => (
                  <Card
                    key={field.key}
                    size="small"
                    title={t('admin.stage_n', { n: index + 1 })}
                    extra={fields.length > 1 ? <Button danger size="small" onClick={() => remove(field.name)}>{t('button.delete')}</Button> : null}
                  >
                    {(() => {
                      const { key: _fieldKey, ...restField } = field
                      return (
                        <>
                    <Form.Item
                      {...restField}
                      name={[field.name, 'stage_name']}
                      label={t('contract.installment_label')}
                      help={t('admin.stage_name_help')}
                      rules={[{ required: true }]}
                    >
                      <Input placeholder={t('admin.stage_name_placeholder')} />
                    </Form.Item>
                    <Form.Item
                      {...restField}
                      name={[field.name, 'approver_role']}
                      label={t('field.role')}
                      help={t('admin.stage_role_help')}
                      rules={[{ required: true }]}
                    >
                      <Select options={roleOptions} />
                    </Form.Item>
                        </>
                      )
                    })()}
                  </Card>
                ))}
                <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ stage_name: '', approver_role: 'dept_manager' })} block>
                  {t('admin.add_stage')}
                </Button>
              </Space>
            )}
          </Form.List>
        </Form>
      </Drawer>
    </Space>
  )
}

function CompaniesTab() {
  const { t } = useTranslation()
  const [companies, setCompanies] = useState<any[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingCompany, setEditingCompany] = useState<any | null>(null)
  const [form] = Form.useForm()

  const load = () => { void api.companies(true).then(setCompanies) }
  useEffect(load, [])

  const openCreate = () => {
    setEditingCompany(null)
    form.resetFields()
    form.setFieldsValue({ default_currency: 'CNY' })
    setDrawerOpen(true)
  }

  const openEdit = (company: any) => {
    setEditingCompany(company)
    form.resetFields()
    form.setFieldsValue({
      name_zh: company.name_zh,
      name_en: company.name_en,
      default_currency: company.default_currency,
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = form.getFieldsValue()
      if (editingCompany) {
        await api.updateCompany(editingCompany.id, values)
        void message.success(t('common.updated'))
      } else {
        await api.createCompany(values)
        void message.success(t('message.created'))
      }
      form.resetFields()
      setDrawerOpen(false)
      setEditingCompany(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('error.save_failed'))
    }
  }

  const toggleActive = async (company: any) => {
    try {
      await api.updateCompany(company.id, { is_enabled: !company.is_enabled })
      void message.success(company.is_enabled ? t('admin.deactivated') : t('common.updated'))
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
    }
  }

  const handleDeleteCompany = (company: any) => {
    Modal.confirm({
      title: `${t('button.delete')} ${company.name_zh}?`,
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteCompany(company.id)
          void message.success(t('message.deleted'))
          load()
        } catch (e: any) {
          void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
        }
      },
    })
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Text type="secondary">{companies.length} {t('admin.company_count')}</Typography.Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>{t('admin.new_company')}</Button>
      </div>
      <Table dataSource={companies} rowKey="id" size="small" pagination={false} columns={[
        { title: t('admin.code_col'), dataIndex: 'code', width: 100 },
        { title: t('admin.name_zh_col'), dataIndex: 'name_zh' },
        { title: t('admin.name_en_col'), dataIndex: 'name_en', render: (v: string | null) => v || '-' },
        { title: t('admin.default_currency'), dataIndex: 'default_currency', width: 80 },
        { title: t('admin.status_col'), dataIndex: 'is_enabled', width: 70, render: (v: boolean) => <Tag color={v !== false ? 'success' : 'default'}>{v !== false ? t('common.enabled') : t('common.disabled')}</Tag> },
        {
          title: t('common.actions'),
          width: 220,
          render: (_: unknown, r: any) => (
            <Space>
              <Button size="small" onClick={() => openEdit(r)}>{t('button.edit')}</Button>
              <Button size="small" danger={r.is_enabled !== false} onClick={() => toggleActive(r)}>
                {r.is_enabled !== false ? t('common.disabled') : t('common.enabled')}
              </Button>
              <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDeleteCompany(r)} />
            </Space>
          ),
        },
      ]} />
      <Drawer title={editingCompany ? t('admin.edit_company', { name: editingCompany.name_zh }) : t('admin.new_company_entity')} width={420} open={drawerOpen} onClose={() => { setDrawerOpen(false); setEditingCompany(null) }} footer={
        <Space style={{ float: 'right' }}><Button onClick={() => { setDrawerOpen(false); setEditingCompany(null) }}>{t('button.cancel')}</Button><Button type="primary" onClick={handleSave}>{t('button.save')}</Button></Space>
      }>
        <Form form={form} layout="vertical">
          {!editingCompany && (
            <Form.Item name="code" label={t('admin.code_label')} help={t('admin.company_code_help')} rules={[{ required: true }]}><Input placeholder="DEMO" /></Form.Item>
          )}
          <Form.Item name="name_zh" label={t('admin.name_zh_label')} help={t('admin.company_name_zh_help')} rules={[{ required: true }]}><Input placeholder="觅采科技有限公司" /></Form.Item>
          <Form.Item name="name_en" label={t('admin.name_en_label')} help={t('admin.company_name_en_help')}><Input placeholder="Mica Technology Co., Ltd." /></Form.Item>
          <Form.Item name="default_currency" label={t('admin.currency_label')} initialValue="CNY">
            <Select options={[{ value: 'CNY' }, { value: 'USD' }, { value: 'EUR' }, { value: 'HKD' }, { value: 'JPY' }]} />
          </Form.Item>
        </Form>
      </Drawer>
    </Space>
  )
}

function DepartmentsTab() {
  const { t } = useTranslation()
  const [departments, setDepartments] = useState<any[]>([])
  const [companies, setCompanies] = useState<any[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingDept, setEditingDept] = useState<any | null>(null)
  const [form] = Form.useForm()

  const load = () => { void api.departments().then(setDepartments) }
  useEffect(() => {
    load()
    void api.companies(true).then(setCompanies)
  }, [])

  const companyMap = Object.fromEntries(companies.map(c => [c.id, c.name_zh]))

  const openCreate = () => {
    setEditingDept(null)
    form.resetFields()
    setDrawerOpen(true)
  }

  const openEdit = (dept: any) => {
    setEditingDept(dept)
    form.resetFields()
    form.setFieldsValue({
      code: dept.code,
      name_zh: dept.name_zh,
      name_en: dept.name_en,
      company_id: dept.company_id,
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = form.getFieldsValue()
      if (editingDept) {
        await api.updateDepartment(editingDept.id, values)
        void message.success(t('common.updated'))
      } else {
        await api.createDepartment(values)
        void message.success(t('message.created'))
      }
      form.resetFields()
      setDrawerOpen(false)
      setEditingDept(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('error.save_failed'))
    }
  }

  const handleDelete = (dept: any) => {
    Modal.confirm({
      title: `${t('button.delete')} ${dept.name_zh}?`,
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.deleteDepartment(dept.id)
          void message.success(t('message.deleted'))
          load()
        } catch (e: any) {
          void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
        }
      },
    })
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Text type="secondary">{departments.length} {t('admin.department_count')}</Typography.Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>{t('admin.new_department')}</Button>
      </div>
      <Table dataSource={departments} rowKey="id" size="small" pagination={false} columns={[
        { title: t('admin.department_code'), dataIndex: 'code', width: 120 },
        { title: t('admin.department_name_zh'), dataIndex: 'name_zh' },
        { title: t('admin.department_name_en'), dataIndex: 'name_en', render: (v: string | null) => v || '-' },
        { title: t('admin.department_company'), dataIndex: 'company_id', render: (v: string) => companyMap[v] || v },
        {
          title: t('common.actions'),
          width: 160,
          render: (_: unknown, r: any) => (
            <Space>
              <Button size="small" onClick={() => openEdit(r)}>{t('button.edit')}</Button>
              <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(r)} />
            </Space>
          ),
        },
      ]} />
      <Drawer
        title={editingDept ? t('admin.edit_department', { name: editingDept.name_zh }) : t('admin.new_department')}
        width={420}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setEditingDept(null) }}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => { setDrawerOpen(false); setEditingDept(null) }}>{t('button.cancel')}</Button>
            <Button type="primary" onClick={handleSave}>{t('button.save')}</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="code" label={t('admin.department_code')} rules={[{ required: true }]}>
            <Input disabled={!!editingDept} />
          </Form.Item>
          <Form.Item name="name_zh" label={t('admin.department_name_zh')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="name_en" label={t('admin.department_name_en')}>
            <Input />
          </Form.Item>
          <Form.Item name="company_id" label={t('admin.department_company')} rules={[{ required: true }]}>
            <Select options={companies.map(c => ({ value: c.id, label: c.name_zh }))} />
          </Form.Item>
        </Form>
      </Drawer>
    </Space>
  )
}

function ImportTab() {
  const { t } = useTranslation()
  const [result, setResult] = useState<{ created?: number; skipped?: number; errors?: string[] } | null>(null)
  const [uploading, setUploading] = useState(false)

  const doImport = async (endpoint: string, file: File) => {
    setUploading(true)
    setResult(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const { data } = await api.adminUploadFile(endpoint, formData)
      setResult(data)
      void message.success(t('admin.import_complete', { created: data.created }) + (data.skipped ? `, ${t('admin.import_skipped', { skipped: data.skipped })}` : ''))
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || t('admin.import_failed'))
    } finally {
      setUploading(false)
    }
  }

  const importConfigs = [
    {
      key: 'suppliers',
      title: t('admin.import_suppliers'),
      desc: t('admin.import_suppliers_desc'),
      endpoint: '/admin/import/suppliers',
      templateKind: 'suppliers',
    },
    {
      key: 'items',
      title: t('admin.import_items_title'),
      desc: t('admin.import_items_desc'),
      endpoint: '/admin/import/items',
      templateKind: 'items',
    },
    {
      key: 'prices',
      title: t('admin.import_prices_title'),
      desc: t('admin.import_prices_desc'),
      endpoint: '/admin/import/prices',
      templateKind: 'prices',
    },
  ]

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {importConfigs.map((cfg) => (
        <Card key={cfg.key} size="small" title={cfg.title}>
          <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 12 }}>{cfg.desc}</Typography.Text>
          <Space>
            <Button href={`/api/v1/admin/import/template/${cfg.templateKind}`} target="_blank">下载模板</Button>
            <Upload
              accept=".xlsx,.xls"
              beforeUpload={(file) => { void doImport(cfg.endpoint, file as unknown as File); return false }}
              showUploadList={false}
              maxCount={1}
            >
              <Button type="primary" icon={<PlusOutlined />} loading={uploading}>{t('admin.upload_data')}</Button>
            </Upload>
          </Space>
        </Card>
      ))}
      {result && result.errors && result.errors.length > 0 && (
        <Alert type="warning" message={t('admin.rows_with_issues', { count: result.errors.length })} description={result.errors.slice(0, 10).join('\n')} showIcon />
      )}
    </Space>
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


void ExperimentOutlined
