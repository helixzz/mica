import { PlusOutlined, HolderOutlined } from '@ant-design/icons'
import {
  Button,
  Card,
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
import React, { useEffect, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '@/api'
import {
  createDefaultApprovalRuleForm,
  mapApprovalRuleFormToPayload,
  mapApprovalRuleToForm,
} from './approvalRuleForm'

export function ApprovalRulesTab() {
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

  const bizTypeOptions = [
    { value: 'pr', label: t('admin.biz_type_pr') },
    { value: 'po', label: t('admin.biz_type_po') },
    { value: 'payment', label: t('admin.biz_type_payment') },
    { value: 'contract', label: t('admin.biz_type_contract') },
    { value: 'invoice', label: t('admin.biz_type_invoice') },
    { value: 'rfq', label: t('admin.biz_type_rfq') },
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

  const dragItem = useRef<number | null>(null)
  const dragOverItem = useRef<number | null>(null)

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, index: number) => {
    dragItem.current = index
    e.dataTransfer.effectAllowed = 'move'
    // Optional: set drag image or styling
  }

  const handleDragEnter = (e: React.DragEvent<HTMLDivElement>, index: number) => {
    dragOverItem.current = index
    e.preventDefault()
  }

  const handleDragEnd = () => {
    if (dragItem.current !== null && dragOverItem.current !== null && dragItem.current !== dragOverItem.current) {
      const currentStages = form.getFieldValue('stages') || []
      const newStages = [...currentStages]
      const draggedItemContent = newStages[dragItem.current]
      newStages.splice(dragItem.current, 1)
      newStages.splice(dragOverItem.current, 0, draggedItemContent)
      form.setFieldsValue({ stages: newStages })
    }
    dragItem.current = null
    dragOverItem.current = null
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Text type="secondary">{rules.length} {t('admin.rule_count')}</Typography.Text>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>{t('admin.new_rule')}</Button>
      </div>
      <Table dataSource={rules} rowKey="id" size="small" pagination={false} columns={[
        { title: t('admin.rule_name'), dataIndex: 'name' },
        { title: t('admin.biz_type'), dataIndex: 'biz_type', render: (v: string) => bizTypeOptions.find(o => o.value === v)?.label || v },
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
            <Select options={bizTypeOptions} />
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
                  <div
                    key={field.key}
                    draggable
                    onDragStart={(e) => handleDragStart(e, index)}
                    onDragEnter={(e) => handleDragEnter(e, index)}
                    onDragEnd={handleDragEnd}
                    onDragOver={(e) => e.preventDefault()}
                    style={{ cursor: 'grab' }}
                  >
                    <Card
                      size="small"
                      title={
                        <Space>
                          <HolderOutlined style={{ color: 'var(--color-text-secondary)', cursor: 'grab' }} />
                          {t('admin.stage_n', { n: index + 1 })}
                        </Space>
                      }
                      extra={fields.length > 1 ? <Button danger size="small" onClick={() => remove(field.name)}>{t('button.delete')}</Button> : null}
                      style={{ border: '1px solid var(--color-border)' }}
                    >
                      {(() => {
                        const { key: _fieldKey, ...restField } = field
                        return (
                          <>
                            <Form.Item
                              {...restField}
                              name={[field.name, 'stage_name']}
                              label={t('admin.stage_name')}
                              help={t('admin.stage_name_help')}
                              rules={[{ required: true }]}
                            >
                              <Input placeholder={t('admin.stage_name_placeholder')} />
                            </Form.Item>
                            <Form.Item
                              {...restField}
                              name={[field.name, 'approver_role']}
                              label={t('admin.approver_role')}
                              help={t('admin.stage_role_help')}
                              rules={[{ required: true }]}
                            >
                              <Select options={roleOptions} />
                            </Form.Item>
                          </>
                        )
                      })()}
                    </Card>
                  </div>
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
