import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import {
  Button,
  Drawer,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'
import { useAuth } from '@/auth/useAuth'

export function UsersPanel() {
  const { t } = useTranslation()
  const { user: currentUser } = useAuth()
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<any | null>(null)
  const [resetPwdUser, setResetPwdUser] = useState<any | null>(null)
  const [form] = Form.useForm()
  const [resetForm] = Form.useForm()
  const [companies, setCompanies] = useState<any[]>([])
  const [departments, setDepartments] = useState<any[]>([])
  const [costCenters, setCostCenters] = useState<any[]>([])

  const deptMap = Object.fromEntries(departments.map(d => [d.id, d.name_zh]))

  const load = () => {
    setLoading(true)
    api.adminListUsers().then(setRows).finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    api.companies(true).then(setCompanies)
    api.departments().then(setDepartments)
    api.listCostCenters(true).then(setCostCenters)
  }, [])

  const openCreate = () => {
    setEditingUser(null)
    form.resetFields()
    form.setFieldsValue({ role: 'requester', preferred_locale: 'zh-CN', cost_center_ids: [], department_ids: [] })
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
      cost_center_ids: user.cost_center_ids || [],
      department_ids: user.department_ids || [],
      preferred_locale: user.preferred_locale,
      feishu_open_id: user.feishu_open_id || '',
      feishu_union_id: user.feishu_union_id || '',
      feishu_user_id: user.feishu_user_id || '',
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

  const handleDelete = (user: any) => {
    Modal.confirm({
      title: t('admin.confirm_delete_user_title', { name: user.display_name || user.username }),
      content: t('admin.confirm_delete_user_body'),
      okText: t('button.delete'),
      okType: 'danger',
      cancelText: t('button.cancel'),
      onOk: async () => {
        try {
          await api.adminDeleteUser(user.id)
          void message.success(t('message.deleted'))
          load()
        } catch (e: any) {
          void message.error(e?.response?.data?.detail || t('admin.operation_failed'))
        }
      },
    })
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
          { title: t('admin.department_col'), dataIndex: 'department_id', render: (v: string, r: any) => r?.department_name_zh || deptMap[v] || v || '-' },
          { title: t('admin.locale_col'), dataIndex: 'preferred_locale' },
          { title: t('admin.active_col'), dataIndex: 'is_active', render: (v: boolean) => <Tag color={v ? 'success' : 'default'}>{v ? t('common.enabled') : t('common.disabled')}</Tag> },
          { title: t('admin.auth_provider_col'), dataIndex: 'auth_provider' },
          { title: t('admin.last_login_col'), dataIndex: 'last_login_at', render: (v?: string) => v ? new Date(v).toLocaleString() : '-' },
          {
            title: t('common.actions'),
            width: 340,
            render: (_: unknown, r: any) => (
              <Space>
                <Button size="small" onClick={() => openEdit(r)}>{t('button.edit')}</Button>
                <Button size="small" onClick={() => { setResetPwdUser(r); resetForm.resetFields() }}>{t('admin.reset_password')}</Button>
                <Button size="small" danger={r.is_active} onClick={() => toggleActive(r)}>
                  {r.is_active ? t('common.disabled') : t('common.enabled')}
                </Button>
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  disabled={currentUser?.id === r.id}
                  onClick={() => handleDelete(r)}
                />
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
            <Select allowClear options={departments.map(d => ({ value: d.id, label: d.name_zh }))} />
          </Form.Item>
          <Form.Item name="cost_center_ids" label={t('admin.cost_center_label', 'Cost Centers')}>
            <Select
              allowClear
              mode="multiple"
              options={costCenters.map((c) => ({ value: c.id, label: `${c.code} - ${c.label_zh}` }))}
            />
          </Form.Item>
          <Form.Item name="department_ids" label={t('admin.department_ids_label', 'Departments')}>
            <Select
              allowClear
              mode="multiple"
              options={departments.map((d) => ({ value: d.id, label: `${d.code} - ${d.name_zh}` }))}
            />
          </Form.Item>
          <Form.Item name="preferred_locale" label={t('admin.locale_label')}>
            <Select options={[{ value: 'zh-CN', label: 'zh-CN' }, { value: 'en-US', label: 'en-US' }]} />
          </Form.Item>
          <Form.Item name="feishu_open_id" label={t('admin.feishu_open_id_label', 'Feishu Open ID')} help={t('admin.feishu_open_id_help', 'Optional feishu user ID for notifications')}>
            <Input placeholder="ou_..." />
          </Form.Item>
          <Form.Item name="feishu_union_id" label={t('admin.feishu_union_id_label', 'Feishu Union ID (auto)')} help={t('admin.feishu_union_id_help', 'Auto-populated from SAML SSO login')}>
            <Input disabled />
          </Form.Item>
          <Form.Item name="feishu_user_id" label={t('admin.feishu_user_id_label', 'Feishu User ID (auto)')} help={t('admin.feishu_user_id_help', 'Auto-populated from SAML SSO login')}>
            <Input disabled />
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