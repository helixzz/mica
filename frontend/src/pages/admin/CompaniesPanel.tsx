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

export function CompaniesPanel() {
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