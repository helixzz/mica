import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Button,
  Card,
  Divider,
  Form,
  Input,
  message,
  Space,
  Spin,
  Switch,
  Typography,
} from 'antd'
import { client } from '@/api/client'

const { Title, Text } = Typography

interface FeishuSettings {
  enabled: boolean
  app_id: string
  app_secret: string
  approval_code: string
  notify_on_pr: boolean
  notify_on_approval: boolean
  notify_on_po: boolean
  notify_on_payment: boolean
  notify_on_contract_expiry: boolean
  payment_workflow: boolean
}

function ToggleRow({ checked, onChange, label, desc }: { checked?: boolean; onChange?: (v: boolean) => void; label: string; desc: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start' }}>
      <Switch checked={checked} onChange={onChange} style={{ flexShrink: 0, marginTop: 2 }} />
      <div style={{ marginLeft: 8 }}>
        <Text>{label}</Text>
        {desc && <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12 }}>{desc}</div>}
      </div>
    </div>
  )
}

export const FeishuSettingsTab: React.FC = () => {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [initialValues, setInitialValues] = useState<FeishuSettings | null>(null)
  const [formKey, setFormKey] = useState(0)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [enabled, setEnabled] = useState(false)

  useEffect(() => {
    client
      .get<FeishuSettings>('/admin/feishu/settings')
      .then(({ data }) => {
        setInitialValues(data)
        setEnabled(data.enabled)
        setFormKey((k) => k + 1)
      })
      .catch((error) => {
        console.error('Failed to fetch feishu settings', error)
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSave = async () => {
    try {
      setSaving(true)
      const values = await form.validateFields()
      await client.put('/admin/feishu/settings', values)
      message.success(t('feishu.save_success', 'Settings saved successfully'))
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unknown error'
      message.error(`${t('feishu.save_failed', 'Failed to save settings')}: ${detail}`)
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    try {
      setTesting(true)
      await client.post('/admin/feishu/test')
      message.success(t('feishu.test_success', 'Connection successful'))
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || 'Unknown error'
      message.error(`${t('feishu.test_failed', 'Connection failed')}: ${detail}`)
    } finally {
      setTesting(false)
    }
  }

  if (!initialValues) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="feishu-settings-tab">
      <Form key={formKey} form={form} layout="vertical" initialValues={initialValues}>
        <Card
          title={
            <Space>
              <Title level={4} style={{ margin: 0 }}>
                {t('feishu.title', 'Feishu Integration')}
              </Title>
            </Space>
          }
          extra={
            <Space>
              <Text>{t('common.enabled', 'Enabled')}</Text>
              <Form.Item name="enabled" valuePropName="checked" noStyle>
                <Switch />
              </Form.Item>
            </Space>
          }
        >
          <div style={{ opacity: enabled ? 1 : 0.6, pointerEvents: enabled ? 'auto' : 'none' }}>
            <Title level={5}>{t('feishu.credentials', 'Application Credentials')}</Title>
            <Card size="small" style={{ marginBottom: 24 }}>
              <Form.Item
                name="app_id"
                label={t('feishu.app_id', 'App ID')}
                help={t('feishu.app_id_help', 'The App ID from Feishu Developer Console')}
                rules={[{ required: enabled, message: t('common.required', 'Required') }]}
              >
                <Input placeholder="cli_..." />
              </Form.Item>
              <Form.Item
                name="app_secret"
                label={t('feishu.app_secret', 'App Secret')}
                help={t('feishu.app_secret_help', 'The App Secret from Feishu Developer Console')}
              >
                <Input.Password placeholder="••••••••••••••••" />
              </Form.Item>
              <Form.Item
                name="approval_code"
                label={t('feishu.approval_code', 'Approval Code')}
                help={t('feishu.approval_code_help', 'The Approval Definition Code for PRs')}
              >
                <Input placeholder="C2..." />
              </Form.Item>
            </Card>

            <Title level={5}>{t('feishu.notifications', 'Notification Settings')}</Title>
            <Card size="small" style={{ marginBottom: 24 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Form.Item name="notify_on_pr" valuePropName="checked" style={{ marginBottom: 0 }}>
                  <ToggleRow
                    label={t('feishu.notify_on_pr', 'PR Submitted')}
                    desc={t('feishu.notify_on_pr_desc', 'Notify approvers when a PR is submitted')}
                  />
                </Form.Item>
                <Form.Item name="notify_on_approval" valuePropName="checked" style={{ marginBottom: 0 }}>
                  <ToggleRow
                    label={t('feishu.notify_on_approval', 'Approval Decided')}
                    desc={t('feishu.notify_on_approval_desc', 'Notify requester when PR is approved or rejected')}
                  />
                </Form.Item>
                <Form.Item name="notify_on_po" valuePropName="checked" style={{ marginBottom: 0 }}>
                  <ToggleRow
                    label={t('feishu.notify_on_po', 'PO Created')}
                    desc={t('feishu.notify_on_po_desc', 'Notify buyer and requester when PO is created')}
                  />
                </Form.Item>
                <Form.Item name="notify_on_payment" valuePropName="checked" style={{ marginBottom: 0 }}>
                  <ToggleRow
                    label={t('feishu.notify_on_payment', 'Payment Pending')}
                    desc={t('feishu.notify_on_payment_desc', 'Notify finance when payment is pending')}
                  />
                </Form.Item>
                <Form.Item name="notify_on_contract_expiry" valuePropName="checked" style={{ marginBottom: 0 }}>
                  <ToggleRow
                    label={t('feishu.notify_on_contract_expiry', 'Contract Expiring')}
                    desc={t('feishu.notify_on_contract_expiry_desc', 'Notify owner and manager when contract is expiring')}
                  />
                </Form.Item>
              </Space>
            </Card>

            <Title level={5}>{t('feishu.payment_workflow', 'Payment Workflow')}</Title>
            <Card size="small" style={{ marginBottom: 24 }}>
              <Form.Item name="payment_workflow" valuePropName="checked" style={{ marginBottom: 0 }}>
                <ToggleRow
                  label={t('feishu.payment_workflow_desc', 'Enable Feishu Approval Workflow for Payments')}
                  desc=""
                />
              </Form.Item>
            </Card>

            <Divider />
            <Space>
              <Button onClick={handleTest} loading={testing} disabled={!enabled}>
                {t('feishu.test_connection', 'Test Connection')}
              </Button>
              <Button type="primary" onClick={handleSave} loading={saving}>
                {t('feishu.save', 'Save Settings')}
              </Button>
            </Space>
          </div>
        </Card>
      </Form>
    </div>
  )
}
