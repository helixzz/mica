import React, { useEffect, useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Card,
  Typography,
  Collapse,
  Badge,
  Button,
  Input,
  InputNumber,
  Switch,
  Space,
  Modal,
  Form,
  message,
  Tooltip,
  Tag,
  Row,
  Col,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  UndoOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import {
  SystemParameter,
  listSystemParams,
  updateSystemParam,
  resetSystemParam,
} from '../../api/admin-system-params';

const { Title, Text } = Typography;
const { Panel } = Collapse;

export const SystemParamsTab: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [params, setParams] = useState<SystemParameter[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingParam, setEditingParam] = useState<SystemParameter | null>(null);
  const [form] = Form.useForm();

  const fetchParams = async () => {
    setLoading(true);
    try {
      const data = await listSystemParams();
      setParams(data);
    } catch (error) {
      message.error(t('admin.system_params.fetch_error', 'Failed to fetch system parameters'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchParams();
  }, []);

  const handleEdit = (param: SystemParameter) => {
    setEditingParam(param);
    form.setFieldsValue({ value: param.value });
    setEditModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (!editingParam) return;

      await updateSystemParam(editingParam.key, values.value);
      message.success(t('admin.system_params.update_success', 'Parameter updated successfully'));
      setEditModalVisible(false);
      fetchParams();
    } catch (error) {
      message.error(t('admin.system_params.update_error', 'Failed to update parameter'));
    }
  };

  const handleReset = async (param: SystemParameter) => {
    try {
      await resetSystemParam(param.key);
      message.success(t('admin.system_params.reset_success', 'Parameter reset to default'));
      fetchParams();
    } catch (error) {
      message.error(t('admin.system_params.reset_error', 'Failed to reset parameter'));
    }
  };

  const filteredParams = useMemo(() => {
    if (!searchText) return params;
    const lowerSearch = searchText.toLowerCase();
    return params.filter(
      (p) =>
        p.key.toLowerCase().includes(lowerSearch) ||
        p.description_zh.toLowerCase().includes(lowerSearch) ||
        p.description_en.toLowerCase().includes(lowerSearch)
    );
  }, [params, searchText]);

  const groupedParams = useMemo(() => {
    const groups: Record<string, SystemParameter[]> = {};
    filteredParams.forEach((p) => {
      if (!groups[p.category]) {
        groups[p.category] = [];
      }
      groups[p.category].push(p);
    });
    return groups;
  }, [filteredParams]);

  const nonDefaultCount = useMemo(() => {
    return params.filter((p) => p.value !== p.default_value).length;
  }, [params]);

  const renderValue = (param: SystemParameter) => {
    if (param.is_sensitive) {
      return '••••••••';
    }
    if (param.data_type === 'bool') {
      return param.value ? t('common.yes', 'Yes') : t('common.no', 'No');
    }
    return `${param.value} ${param.unit || ''}`.trim();
  };

  const renderInputWidget = (param: SystemParameter) => {
    switch (param.data_type) {
      case 'int':
      case 'float':
      case 'decimal':
        return (
          <InputNumber
            style={{ width: '100%' }}
            min={param.min_value ?? undefined}
            max={param.max_value ?? undefined}
            step={param.data_type === 'int' ? 1 : 0.1}
            placeholder={String(param.default_value)}
          />
        );
      case 'bool':
        return <Switch />;
      case 'string':
      default:
        return <Input placeholder={String(param.default_value)} />;
    }
  };

  return (
    <div className="system-params-tab">
      <Card
        title={
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              {t('admin.system_params.title', 'System Parameters')}
            </Title>
            <Tag color="blue">
              {t('admin.system_params.summary', '{{total}} params ({{modified}} modified)', {
                total: params.length,
                modified: nonDefaultCount,
              })}
            </Tag>
          </Space>
        }
        extra={
          <Space>
            <Input
              placeholder={t('admin.system_params.search', 'Search params...')}
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
            <Button icon={<ReloadOutlined />} onClick={fetchParams} loading={loading}>
              {t('common.refresh', 'Refresh')}
            </Button>
          </Space>
        }
      >
        <Collapse defaultActiveKey={Object.keys(groupedParams)}>
          {Object.entries(groupedParams).map(([category, categoryParams]) => (
            <Panel
              key={category}
              header={
                <Space>
                  <Text strong>{category.toUpperCase()}</Text>
                  <Badge count={categoryParams.length} style={{ backgroundColor: '#52c41a' }} />
                </Space>
              }
            >
              {categoryParams.map((param) => (
                <Card
                  key={param.key}
                  size="small"
                  style={{ marginBottom: 8 }}
                  bodyStyle={{ padding: '12px 16px' }}
                >
                  <Row align="middle" justify="space-between">
                    <Col span={12}>
                      <Space direction="vertical" size={0}>
                        <Space>
                          <Text strong>
                            {i18n.language === 'zh-CN' ? param.description_zh : param.description_en}
                          </Text>
                          {param.value !== param.default_value && (
                            <Tag color="warning">{t('admin.system_params.modified', 'Modified')}</Tag>
                          )}
                        </Space>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {i18n.language === 'zh-CN' ? param.description_en : param.description_zh}
                        </Text>
                        <Text code style={{ fontSize: '12px' }}>
                          {param.key}
                        </Text>
                      </Space>
                    </Col>
                    <Col span={8} style={{ textAlign: 'right' }}>
                      <Text style={{ fontSize: '16px', fontWeight: 500 }}>
                        {renderValue(param)}
                      </Text>
                    </Col>
                    <Col span={4} style={{ textAlign: 'right' }}>
                      <Space>
                        <Button
                          type="text"
                          icon={<EditOutlined />}
                          onClick={() => handleEdit(param)}
                        />
                        <Tooltip title={t('admin.system_params.reset', 'Reset to default')}>
                          <Button
                            type="text"
                            danger
                            icon={<UndoOutlined />}
                            onClick={() => handleReset(param)}
                            disabled={param.value === param.default_value}
                          />
                        </Tooltip>
                      </Space>
                    </Col>
                  </Row>
                </Card>
              ))}
            </Panel>
          ))}
        </Collapse>
      </Card>

      <Modal
        title={t('admin.system_params.edit_title', 'Edit Parameter')}
        open={editModalVisible}
        onOk={handleSave}
        onCancel={() => setEditModalVisible(false)}
        destroyOnClose
      >
        {editingParam && (
          <Form form={form} layout="vertical">
            <div style={{ marginBottom: 16 }}>
              <Text strong>{editingParam.key}</Text>
              <br />
              <Text type="secondary">
                {i18n.language === 'zh-CN'
                  ? editingParam.description_zh
                  : editingParam.description_en}
              </Text>
            </div>
            <Form.Item
              name="value"
              label={t('admin.system_params.value', 'Value')}
              rules={[{ required: true, message: t('common.required', 'Required') }]}
              valuePropName={editingParam.data_type === 'bool' ? 'checked' : 'value'}
            >
              {renderInputWidget(editingParam)}
            </Form.Item>
            <div style={{ marginTop: 8 }}>
              <Text type="secondary">
                <InfoCircleOutlined style={{ marginRight: 4 }} />
                {t('admin.system_params.default_hint', 'Default value:')}{' '}
                {String(editingParam.default_value)} {editingParam.unit || ''}
              </Text>
            </div>
          </Form>
        )}
      </Modal>
    </div>
  );
};
