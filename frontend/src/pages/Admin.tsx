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
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'
import { extractError } from '@/api/client'
import { useAuth } from '@/auth/useAuth'
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
        <Typography.Text type="secondary">仅管理员可访问此页面 / Admin only.</Typography.Text>
      </Card>
    )
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={3} style={{ margin: 0 }}>
        系统管理 / Admin Console
      </Typography.Title>
      <Tabs
        items={[
          { key: 'system', label: '系统信息', children: <SystemInfoPanel /> },
          { key: 'system_params', label: '系统参数', children: <SystemParamsTab /> },
          { key: 'classification', label: '分类管理', children: <ClassificationTab /> },
          { key: 'models', label: 'LLM 模型', children: <AIModelsPanel /> },
          { key: 'routings', label: 'AI 场景路由', children: <RoutingsPanel /> },
          { key: 'users', label: '用户管理', children: <UsersPanel /> },
          { key: 'ai_logs', label: 'AI 调用日志', children: <AILogsPanel /> },
          { key: 'audit', label: '审计日志', children: <AuditPanel /> },
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
      void message.success(`连接成功 (${r.latency_ms}ms): ${r.model_response?.slice(0, 80)}`)
    } else {
      void message.error(`连接失败: ${r.error}`)
    }
  }

  const del = async (id: string) => {
    await api.adminDeleteAIModel(id)
    void message.success('已删除')
    load()
  }

  return (
    <>
      <Space style={{ marginBottom: 12 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditing(null); setEditOpen(true) }}>
          新增模型
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
                <Button size="small" icon={<ThunderboltOutlined />} onClick={() => test(r.id)}>
                  测试连接
                </Button>
                <Button size="small" onClick={() => { setEditing(r); setEditOpen(true) }}>
                  编辑
                </Button>
                <Button size="small" danger icon={<DeleteOutlined />} onClick={() => {
                  Modal.confirm({ title: `删除 ${r.name}？`, onOk: () => del(r.id) })
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
      void message.success('已保存')
      onSaved()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Drawer
      title={initial ? `编辑模型 ${initial.name}` : '新增 LLM 模型'}
      open={open}
      onClose={onClose}
      width={520}
      extra={<Button type="primary" onClick={save} loading={busy}>保存</Button>}
    >
      <Form form={form} layout="vertical">
        <Alert
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginBottom: 16 }}
          message="OpenAI 兼容 API 填写指南"
          description={
            <Typography.Text style={{ fontSize: 13 }}>
              使用任意 OpenAI 兼容的第三方服务（DeepSeek / 智谱 GLM / Modelverse / 通义兼容接口等）时：
              <br />1. <b>Provider</b> 填 <Typography.Text code>openai</Typography.Text>（或 <Typography.Text code>openai-compatible</Typography.Text>、<Typography.Text code>deepseek</Typography.Text> 等）
              <br />2. <b>Model String</b> 填 vendor 的原始 model id（例如 <Typography.Text code>zai-org/glm-4.7</Typography.Text>）— 后端会自动补 <Typography.Text code>openai/</Typography.Text> 前缀
              <br />3. <b>API Base</b> 填 vendor 的 <Typography.Text code>/v1</Typography.Text> 端点（例如 <Typography.Text code>https://api.modelverse.cn/v1</Typography.Text>）
              <br />4. <b>API Key</b> 填 vendor 发放的密钥
            </Typography.Text>
          }
        />
        <Form.Item label="模型名称 Name" name="name" rules={[{ required: true }]}>
          <Input placeholder="qwen-max / gpt-4o / glm-4.7 / ..." />
        </Form.Item>
        <Form.Item
          label="Provider"
          name="provider"
          rules={[{ required: true }]}
          help="OpenAI 兼容服务统一填 openai（或 openai-compatible / deepseek / modelverse 等别名）"
        >
          <Input placeholder="openai / anthropic / dashscope / volcengine / mock" />
        </Form.Item>
        <Form.Item
          label="Model String"
          name="model_string"
          rules={[{ required: true }]}
          help="填 vendor 的原始 model id（如 zai-org/glm-4.7、deepseek-chat）；已带 openai/ 等前缀则保持不变"
        >
          <Input placeholder="zai-org/glm-4.7 · deepseek-chat · openai/gpt-4o" />
        </Form.Item>
        <Form.Item label="Modality" name="modality">
          <Select options={[
            { value: 'text' }, { value: 'vision' }, { value: 'ocr' }, { value: 'embedding' },
          ]} />
        </Form.Item>
        <Form.Item label="API Base" name="api_base">
          <Input placeholder="可选，留空使用默认" />
        </Form.Item>
        <Form.Item label="API Key" name="api_key" help={initial ? '留空表示不修改' : '保存后仅展示脱敏'}>
          <Input.Password />
        </Form.Item>
        <Space>
          <Form.Item label="Timeout (s)" name="timeout_s">
            <InputNumber min={1} max={300} />
          </Form.Item>
          <Form.Item label="Priority" name="priority">
            <InputNumber />
          </Form.Item>
          <Form.Item label="启用" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Space>
      </Form>
    </Drawer>
  )
}

function RoutingsPanel() {
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

  const modelMap = Object.fromEntries(models.map((m) => [m.id, m.name]))

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
    void message.success('已更新路由')
    load()
  }

  return (
    <Table
      rowKey="feature_code"
      dataSource={rows}
      loading={loading}
      pagination={false}
      columns={[
        { title: '场景 Feature', dataIndex: 'feature_code' },
        {
          title: '主模型',
          dataIndex: 'primary_model_id',
          render: (v: string | null, r) => (
            <Select
              style={{ width: 240 }}
              value={v || undefined}
              onChange={(val) => changePrimary(r.feature_code as string, val, r)}
              allowClear
              options={models.map((m) => ({ value: m.id, label: `${m.name} (${m.modality})` }))}
              placeholder="未配置"
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
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.adminListUsers().then(setRows).finally(() => setLoading(false))
  }, [])

  return (
    <Table
      rowKey="id"
      dataSource={rows}
      loading={loading}
      pagination={{ pageSize: 20 }}
      columns={[
        { title: 'Username', dataIndex: 'username' },
        { title: 'Name', dataIndex: 'display_name' },
        { title: 'Role', dataIndex: 'role', render: (v: string) => <Tag color="orange">{v}</Tag> },
        { title: 'Email', dataIndex: 'email' },
        { title: 'Locale', dataIndex: 'preferred_locale' },
        { title: 'Active', dataIndex: 'is_active', render: (v: boolean) => v ? '✓' : '✗' },
        { title: 'Auth', dataIndex: 'auth_provider' },
        { title: 'Last Login', dataIndex: 'last_login_at', render: (v?: string) => v ? new Date(v).toLocaleString() : '-' },
      ]}
    />
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

function ClassificationTab() {
  const [costCenters, setCostCenters] = useState<any[]>([])
  const [categories, setCategories] = useState<any[]>([])
  const [expenseTypes, setExpenseTypes] = useState<any[]>([])
  const [adding, setAdding] = useState<string | null>(null)
  const [form] = Form.useForm()

  const load = () => {
    void api.listCostCenters().then(setCostCenters)
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
      void message.success('已添加')
      form.resetFields()
      setAdding(null)
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || '创建失败')
    }
  }

  const handleDelete = async (dimension: string, id: string) => {
    try {
      if (dimension === 'cost_center') await api.deleteCostCenter(id)
      else if (dimension === 'category') await api.deleteProcurementCategory(id)
      else await api.deleteLookupValue(id)
      void message.success('已停用')
      load()
    } catch (e: any) {
      void message.error(e?.response?.data?.detail || '操作失败')
    }
  }

  const renderList = (dimension: string, items: any[], title: string) => (
    <Card
      size="small"
      title={<Space><AppstoreOutlined />{title}</Space>}
      extra={<Button size="small" icon={<PlusOutlined />} onClick={() => { setAdding(dimension); form.resetFields() }}>添加</Button>}
      style={{ marginBottom: 16 }}
    >
      <Table
        dataSource={items}
        rowKey="id"
        size="small"
        pagination={false}
        columns={[
          { title: '编码', dataIndex: 'code', width: 120 },
          { title: '中文名称', dataIndex: 'label_zh' },
          { title: '英文名称', dataIndex: 'label_en' },
          { title: '排序', dataIndex: 'sort_order', width: 60 },
          {
            title: '',
            width: 60,
            render: (_: unknown, r: any) => (
              <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(dimension, r.id)} />
            ),
          },
        ]}
      />
    </Card>
  )

  const renderCategoryTree = () => (
    <Card
      size="small"
      title={<Space><AppstoreOutlined />采购种类（2 级层级）</Space>}
      extra={<Button size="small" icon={<PlusOutlined />} onClick={() => { setAdding('category'); form.resetFields() }}>添加</Button>}
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
            <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete('category', cat.id)} />
          </div>
          {(cat.children || []).map((child: any) => (
            <div key={child.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0 4px 32px', borderBottom: '1px solid #fafafa' }}>
              <Space>
                <Tag>L2</Tag>
                <Typography.Text>{child.label_zh}</Typography.Text>
                <Typography.Text type="secondary">{child.code}</Typography.Text>
              </Space>
              <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete('category', child.id)} />
            </div>
          ))}
        </div>
      ))}
      {categories.length === 0 && <Typography.Text type="secondary">暂无分类</Typography.Text>}
    </Card>
  )

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {renderList('cost_center', costCenters, '成本中心')}
      {renderCategoryTree()}
      {renderList('expense_type', expenseTypes, '开支类型')}

      <Modal
        title={adding === 'cost_center' ? '添加成本中心' : adding === 'category' ? '添加采购种类' : '添加开支类型'}
        open={!!adding}
        onCancel={() => setAdding(null)}
        onOk={() => adding && handleAdd(adding)}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="code" label="编码" rules={[{ required: true }]}>
            <Input placeholder="如 CC-IT / laptop / capex" />
          </Form.Item>
          <Form.Item name="label_zh" label="中文名称" rules={[{ required: true }]}>
            <Input placeholder="信息技术部 / 笔记本电脑 / 资本性支出" />
          </Form.Item>
          <Form.Item name="label_en" label="英文名称" rules={[{ required: true }]}>
            <Input placeholder="IT Department / Laptops / CapEx" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序" initialValue={0}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          {adding === 'category' && (
            <Form.Item name="parent_id" label="上级分类（留空为一级）">
              <Select
                allowClear
                placeholder="选择上级分类（一级）"
                options={categories.map((c: any) => ({ value: c.id, label: c.label_zh }))}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </Space>
  )
}


void ExperimentOutlined