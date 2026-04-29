import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Typography,
  Switch,
  Input,
  Button,
  Space,
  Divider,
  message,
  Spin,
  Form,
} from 'antd';
import { client } from '@/api/client';

const { Title, Text } = Typography;

interface FeishuSettings {
  enabled: boolean;
  app_id: string;
  app_secret: string;
  approval_code: string;
  notify_on_pr: boolean;
  notify_on_approval: boolean;
  notify_on_po: boolean;
  notify_on_payment: boolean;
  notify_on_contract_expiry: boolean;
  payment_workflow: boolean;
}

const FEISHU_INITIAL_VALUES: FeishuSettings = {
  enabled: false,
  app_id: '',
  app_secret: '',
  approval_code: '',
  notify_on_pr: false,
  notify_on_approval: false,
  notify_on_po: false,
  notify_on_payment: false,
  notify_on_contract_expiry: false,
  payment_workflow: false,
};

export const FeishuSettingsTab: React.FC = () => {
  const { t } = useTranslation();
  const [form] = Form.useForm<FeishuSettings>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [enabled, setEnabled] = useState(false);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const { data } = await client.get<FeishuSettings>('/admin/feishu/settings');
      form.setFieldsValue(data);
      setEnabled(data.enabled);
    } catch (error) {
      console.error('Failed to fetch feishu settings', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await client.put('/admin/feishu/settings', values);
      message.success(t('feishu.save_success', 'Settings saved successfully'));
    } catch (error) {
      message.error(t('feishu.save_failed', 'Failed to save settings'));
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      await client.post('/admin/feishu/test');
      message.success(t('feishu.test_success', 'Connection successful'));
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error.message;
      message.error(`${t('feishu.test_failed', 'Connection failed')}: ${detail}`);
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  const FEISHU_INITIAL = {
    enabled: false,
    notify_on_pr: false,
    notify_on_approval: false,
    notify_on_po: false,
    notify_on_payment: false,
    notify_on_contract_expiry: false,
    payment_workflow: false,
  };

  return (
    <div className="feishu-settings-tab">
      <Form
        form={form}
        layout="vertical"
        initialValues={FEISHU_INITIAL_VALUES}
        onValuesChange={(changedValues) => {
          if ('enabled' in changedValues) {
            setEnabled(changedValues.enabled);
          }
        }}
      >
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
                rules={[{ required: enabled, message: t('common.required', 'Required') }]}
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
                <Form.Item name="notify_on_pr" valuePropName="checked" style={{ marginBottom: 8 }}>
                  <Switch /> <Text style={{ marginLeft: 8 }}>{t('feishu.notify_on_pr', 'PR Submitted')}</Text>
                  <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12, marginLeft: 52 }}>
                    {t('feishu.notify_on_pr_desc', 'Notify approvers when a PR is submitted')}
                  </div>
                </Form.Item>
                <Form.Item name="notify_on_approval" valuePropName="checked" style={{ marginBottom: 8 }}>
                  <Switch /> <Text style={{ marginLeft: 8 }}>{t('feishu.notify_on_approval', 'Approval Decided')}</Text>
                  <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12, marginLeft: 52 }}>
                    {t('feishu.notify_on_approval_desc', 'Notify requester when PR is approved or rejected')}
                  </div>
                </Form.Item>
                <Form.Item name="notify_on_po" valuePropName="checked" style={{ marginBottom: 8 }}>
                  <Switch /> <Text style={{ marginLeft: 8 }}>{t('feishu.notify_on_po', 'PO Created')}</Text>
                  <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12, marginLeft: 52 }}>
                    {t('feishu.notify_on_po_desc', 'Notify buyer and requester when PO is created')}
                  </div>
                </Form.Item>
                <Form.Item name="notify_on_payment" valuePropName="checked" style={{ marginBottom: 8 }}>
                  <Switch /> <Text style={{ marginLeft: 8 }}>{t('feishu.notify_on_payment', 'Payment Pending')}</Text>
                  <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12, marginLeft: 52 }}>
                    {t('feishu.notify_on_payment_desc', 'Notify finance when payment is pending')}
                  </div>
                </Form.Item>
                <Form.Item name="notify_on_contract_expiry" valuePropName="checked" style={{ marginBottom: 0 }}>
                  <Switch /> <Text style={{ marginLeft: 8 }}>{t('feishu.notify_on_contract_expiry', 'Contract Expiring')}</Text>
                  <div style={{ color: 'var(--color-text-tertiary)', fontSize: 12, marginLeft: 52 }}>
                    {t('feishu.notify_on_contract_expiry_desc', 'Notify owner and manager when contract is expiring')}
                  </div>
                </Form.Item>
              </Space>
            </Card>

            <Title level={5}>{t('feishu.payment_workflow', 'Payment Workflow')}</Title>
            <Card size="small" style={{ marginBottom: 24 }}>
              <Form.Item name="payment_workflow" valuePropName="checked" style={{ marginBottom: 0 }}>
                <Switch /> <Text style={{ marginLeft: 8 }}>{t('feishu.payment_workflow_desc', 'Enable Feishu Approval Workflow for Payments')}</Text>
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
  );
};
