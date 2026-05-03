import { DeleteOutlined, InfoCircleOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'
import { extractError } from '@/api/client'

export type AIModelRow = {
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

export function AIModelPanel() {
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