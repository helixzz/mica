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
  Select,
  Alert,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  UndoOutlined,
  InfoCircleOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import {
  SystemParameter,
  listSystemParams,
  updateSystemParam,
  resetSystemParam,
} from '../../api/admin-system-params';
import { api, type Company, type Department } from '@/api';

const { Title, Text } = Typography;
const { Panel } = Collapse;

export const SystemParamsTab: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [params, setParams] = useState<SystemParameter[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingParam, setEditingParam] = useState<SystemParameter | null>(null);
  const [refreshingMetadata, setRefreshingMetadata] = useState(false);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
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
    void api.companies(true).then(setCompanies).catch(() => setCompanies([]));
    void api.departments().then(setDepartments).catch(() => setDepartments([]));
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
      const err = error as { response?: { data?: { detail?: string } } };
      const detail = err?.response?.data?.detail;
      if (detail === 'saml.company_code_not_found') {
        message.error(t('admin.system_params.company_code_not_found', '指定的公司编码不存在或已被禁用'));
      } else if (detail === 'saml.department_code_not_found') {
        message.error(t('admin.system_params.department_code_not_found', '指定的部门编码不存在或已被禁用'));
      } else if (detail) {
        message.error(detail);
      } else {
        message.error(t('admin.system_params.update_error', 'Failed to update parameter'));
      }
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

  const handleRefreshMetadata = async () => {
    setRefreshingMetadata(true);
    try {
      const result = await api.refreshSamlMetadata();
      const certChanged = result.cert_changed === 'True';
      const certsFound = Number(result.signing_certs_found ?? '0');
      Modal.success({
        title: t(
          'admin.saml_metadata.refresh_ok_title',
          'IdP metadata refreshed successfully',
        ),
        content: (
          <div>
            <p>
              {certChanged
                ? t(
                    'admin.saml_metadata.cert_updated',
                    'Signing certificate was updated.',
                  )
                : t(
                    'admin.saml_metadata.cert_unchanged',
                    'Signing certificate is already current — no change needed.',
                  )}
            </p>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('admin.saml_metadata.certs_found', 'Certificates found: {{count}}', {
                count: certsFound,
              })}
              {result.sso_url_in_metadata && (
                <>
                  <br />
                  {t('admin.saml_metadata.sso_url_in_metadata', 'SSO URL in metadata: {{url}}', {
                    url: result.sso_url_in_metadata,
                  })}
                </>
              )}
              {result.entity_id_in_metadata && (
                <>
                  <br />
                  {t(
                    'admin.saml_metadata.entity_id_mismatch',
                    'Metadata entityId differs from current: {{metadata}} vs {{current}}',
                    {
                      metadata: result.entity_id_in_metadata,
                      current: result.entity_id_current,
                    },
                  )}
                </>
              )}
            </Text>
          </div>
        ),
      });
      fetchParams();
    } catch (error: unknown) {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (error as Error)?.message ||
        'Unknown error';
      Modal.error({
        title: t('admin.saml_metadata.refresh_error_title', 'Failed to refresh IdP metadata'),
        content: String(detail),
      });
    } finally {
      setRefreshingMetadata(false);
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
    if (param.key === 'auth.saml.group_mapping' || param.key === 'auth.saml.idp.x509_cert') {
      return <Input.TextArea rows={8} placeholder={String(param.default_value)} />;
    }
    if (param.key === 'auth.saml.jit.default_role') {
      return (
        <Select
          options={[
            { value: 'requester', label: t('role.requester', 'Requester') },
            { value: 'it_buyer', label: t('role.it_buyer') },
            { value: 'dept_manager', label: t('role.dept_manager') },
            { value: 'finance_auditor', label: t('role.finance_auditor') },
            { value: 'procurement_mgr', label: t('role.procurement_mgr') },
            { value: 'admin', label: t('role.admin') },
          ]}
        />
      );
    }
    if (param.key === 'auth.saml.jit.default_company_code') {
      const enabled = companies.filter((c) => c.is_enabled && !c.is_deleted);
      return (
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder={t('admin.system_params.select_company', '选择默认公司（留空将自动使用唯一启用的公司）')}
          options={enabled.map((c) => ({
            value: c.code,
            label: `${c.code} — ${c.name_zh}`,
          }))}
          notFoundContent={t('admin.system_params.no_companies', '暂无可选公司')}
        />
      );
    }
    if (param.key === 'auth.saml.jit.default_department_code') {
      return (
        <Select
          allowClear
          showSearch
          optionFilterProp="label"
          placeholder={t('admin.system_params.select_department', '选择默认部门（可留空，由管理员后续指定）')}
          options={departments.map((d) => ({
            value: d.code,
            label: `${d.code} — ${d.name_zh}`,
          }))}
          notFoundContent={t('admin.system_params.no_departments', '暂无可选部门')}
        />
      );
    }
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
                          {param.key.startsWith('auth.saml.') && (
                            <Tooltip
                              title={t(
                                `admin.saml_help.${param.key}`,
                                i18n.language === 'zh-CN' ? param.description_zh : param.description_en
                              )}
                            >
                              <InfoCircleOutlined />
                            </Tooltip>
                          )}
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
                        {param.key === 'auth.saml.idp.metadata_url' && (
                          <Tooltip
                            title={t(
                              'admin.saml_metadata.refresh_tooltip',
                              'Fetch IdP metadata now and update signing certificate',
                            )}
                          >
                            <Button
                              type="text"
                              icon={<SyncOutlined spin={refreshingMetadata} />}
                              onClick={handleRefreshMetadata}
                              loading={refreshingMetadata}
                              disabled={!param.value}
                            />
                          </Tooltip>
                        )}
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
            {editingParam.key.startsWith('auth.saml.') && (
              <Alert
                style={{ marginTop: 12 }}
                type="info"
                showIcon
                message={t(
                  `admin.saml_help.${editingParam.key}`,
                  i18n.language === 'zh-CN' ? editingParam.description_zh : editingParam.description_en
                )}
              />
            )}
          </Form>
        )}
      </Modal>
    </div>
  );
};
