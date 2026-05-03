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
  Typography,
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'

export function DepartmentsPanel() {
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