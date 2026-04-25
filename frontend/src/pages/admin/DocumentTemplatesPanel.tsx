import { EditOutlined, EyeOutlined, UploadOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Drawer,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type DocumentTemplate } from '@/api'
import { extractError } from '@/api/client'

export function DocumentTemplatesPanel() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<DocumentTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [editing, setEditing] = useState<DocumentTemplate | null>(null)
  const [form] = Form.useForm()
  const [placeholderViewer, setPlaceholderViewer] = useState<{
    open: boolean
    template?: DocumentTemplate
    placeholders: string[]
  }>({ open: false, placeholders: [] })

  const load = async () => {
    setLoading(true)
    try {
      const list = await api.adminListDocumentTemplates()
      setRows(list)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const openEdit = (row: DocumentTemplate) => {
    setEditing(row)
    form.setFieldsValue({
      name: row.name,
      description: row.description,
      filename_template: row.filename_template,
      is_enabled: row.is_enabled,
    })
  }

  const handleSave = async () => {
    if (!editing) return
    try {
      const values = await form.validateFields()
      await api.adminUpdateDocumentTemplate(editing.id, values)
      void message.success(t('admin.document_template.saved'))
      setEditing(null)
      void load()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  const handleUpload = async (row: DocumentTemplate, file: File) => {
    try {
      await api.adminUploadDocumentTemplate(row.id, file)
      void message.success(t('admin.document_template.uploaded'))
      void load()
    } catch (e) {
      void message.error(extractError(e).detail)
    }
    return false
  }

  const showPlaceholders = async (row: DocumentTemplate) => {
    try {
      const { placeholders } = await api.previewTemplatePlaceholders(row.id)
      setPlaceholderViewer({ open: true, template: row, placeholders })
    } catch (e) {
      void message.error(extractError(e).detail)
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message={t('admin.document_template.intro_title')}
        description={t('admin.document_template.intro_body')}
      />

      <Table<DocumentTemplate>
        rowKey="id"
        dataSource={rows}
        loading={loading}
        pagination={false}
        columns={[
          {
            title: t('admin.document_template.name'),
            render: (_, r) => (
              <Space direction="vertical" size={0}>
                <Typography.Text strong>{r.name}</Typography.Text>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {r.code}
                </Typography.Text>
              </Space>
            ),
          },
          {
            title: t('admin.document_template.template_file'),
            render: (_, r) =>
              r.template_filename ? (
                <Space direction="vertical" size={0}>
                  <Typography.Text>{r.template_filename}</Typography.Text>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {r.template_size
                      ? `${(r.template_size / 1024).toFixed(1)} KB`
                      : ''}
                  </Typography.Text>
                </Space>
              ) : (
                <Tag color="warning">{t('admin.document_template.no_file')}</Tag>
              ),
          },
          {
            title: t('admin.document_template.filename_template'),
            dataIndex: 'filename_template',
            render: (v: string) => (
              <Typography.Text code style={{ fontSize: 12 }}>
                {v}
              </Typography.Text>
            ),
          },
          {
            title: t('field.status'),
            dataIndex: 'is_enabled',
            width: 80,
            render: (v: boolean) => (
              <Tag color={v ? 'success' : 'default'}>
                {v ? t('common.enabled') : t('common.disabled')}
              </Tag>
            ),
          },
          {
            title: t('common.actions'),
            width: 320,
            render: (_, r) => (
              <Space size="small" wrap>
                <Upload
                  accept=".docx,.xlsx"
                  showUploadList={false}
                  beforeUpload={(file) => handleUpload(r, file)}
                >
                  <Button size="small" icon={<UploadOutlined />}>
                    {t('admin.document_template.upload')}
                  </Button>
                </Upload>
                <Button
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => showPlaceholders(r)}
                >
                  {t('admin.document_template.preview_placeholders')}
                </Button>
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => openEdit(r)}
                >
                  {t('button.edit')}
                </Button>
              </Space>
            ),
          },
        ]}
      />

      <Drawer
        title={t('admin.document_template.edit_title', {
          name: editing?.name ?? '',
        })}
        open={editing !== null}
        onClose={() => setEditing(null)}
        width={560}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setEditing(null)}>{t('button.cancel')}</Button>
            <Button type="primary" onClick={handleSave}>
              {t('button.save')}
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t('admin.document_template.name')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="filename_template"
            label={t('admin.document_template.filename_template')}
            help={t('admin.document_template.filename_template_help')}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="description"
            label={t('admin.document_template.description')}
          >
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item
            name="is_enabled"
            label={t('field.status')}
            valuePropName="checked"
          >
            <Switch
              checkedChildren={t('common.enabled')}
              unCheckedChildren={t('common.disabled')}
            />
          </Form.Item>
        </Form>
      </Drawer>

      <Modal
        title={t('admin.document_template.placeholders_title', {
          name: placeholderViewer.template?.name ?? '',
        })}
        open={placeholderViewer.open}
        onCancel={() => setPlaceholderViewer((s) => ({ ...s, open: false }))}
        footer={[
          <Button
            key="close"
            onClick={() => setPlaceholderViewer((s) => ({ ...s, open: false }))}
          >
            {t('button.close')}
          </Button>,
        ]}
        width={600}
      >
        <Alert
          type="info"
          showIcon
          message={t('admin.document_template.placeholders_hint')}
          style={{ marginBottom: 16 }}
        />
        {placeholderViewer.placeholders.length === 0 ? (
          <Empty description={t('admin.document_template.placeholders_empty')} />
        ) : (
          <List
            size="small"
            bordered
            dataSource={placeholderViewer.placeholders}
            renderItem={(p) => (
              <List.Item>
                <Typography.Text code>[{p}]</Typography.Text>
              </List.Item>
            )}
          />
        )}
      </Modal>

      <Card size="small" title={t('admin.document_template.syntax_title')}>
        <Typography.Paragraph style={{ marginBottom: 4 }}>
          {t('admin.document_template.syntax_body')}
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
          {t('admin.document_template.syntax_examples')}
        </Typography.Paragraph>
      </Card>
    </Space>
  )
}
