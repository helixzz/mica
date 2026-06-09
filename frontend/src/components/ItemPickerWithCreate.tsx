import { PlusOutlined } from '@ant-design/icons'
import { Button, Divider, Form, Input, Modal, Select, Space, Switch, Typography, message } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type ClassificationItem, type Item } from '@/api'
import { extractError } from '@/api/client'

interface ItemPickerWithCreateProps {
  value?: string | null
  onChange?: (itemId: string | null, item: Item | null) => void
  placeholder?: string
  disabled?: boolean
  allowClear?: boolean
  style?: React.CSSProperties
}

let _itemsCache: Promise<Item[]> | null = null
const _subscribers = new Set<(items: Item[]) => void>()

function loadItems(force = false): Promise<Item[]> {
  if (force || _itemsCache === null) {
    _itemsCache = api.items()
  }
  return _itemsCache
}

function notifyItemListChanged(items: Item[]) {
  _subscribers.forEach((fn) => fn(items))
}

function _generateDefaultCode(name: string): string {
  const slug = name
    .toUpperCase()
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 32)
  if (!slug) return ''
  return slug
}

export function ItemPickerWithCreate({
  value,
  onChange,
  placeholder,
  disabled,
  allowClear = true,
  style,
}: ItemPickerWithCreateProps) {
  const { t } = useTranslation()
  const [items, setItems] = useState<Item[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)

  useEffect(() => {
    let alive = true
    loadItems()
      .then((data) => {
        if (alive) {
          setItems(data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (alive) setLoading(false)
      })

    const handler = (data: Item[]) => {
      if (alive) setItems(data)
    }
    _subscribers.add(handler)
    return () => {
      alive = false
      _subscribers.delete(handler)
    }
  }, [])

  const options = useMemo(
    () =>
      items
        .filter((it) => it.is_enabled !== false && it.is_deleted !== true)
        .map((it) => ({
          value: it.id,
          label: `${it.code} · ${it.name}`,
          item: it,
        })),
    [items],
  )

  const handleChange = (next: string | undefined) => {
    if (!onChange) return
    if (!next) {
      onChange(null, null)
      return
    }
    const found = items.find((it) => it.id === next) ?? null
    onChange(next, found)
  }

  const handleCreated = (item: Item) => {
    loadItems(true).then((fresh) => {
      setItems(fresh)
      notifyItemListChanged(fresh)
    })
    if (onChange) onChange(item.id, item)
    setCreateOpen(false)
  }

  return (
    <>
      <Select
        style={{ width: '100%', ...style }}
        value={value ?? undefined}
        onChange={handleChange}
        placeholder={placeholder ?? t('placeholder.select_item')}
        options={options}
        showSearch
        optionFilterProp="label"
        allowClear={allowClear}
        loading={loading}
        disabled={disabled}
        popupMatchSelectWidth={false}
        dropdownRender={(menu) => (
          <>
            {menu}
            <Divider style={{ margin: '6px 0' }} />
            <div style={{ padding: '0 8px 6px' }}>
              <Button
                type="link"
                icon={<PlusOutlined />}
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setCreateOpen(true)
                }}
                style={{ paddingInline: 4 }}
              >
                {t('item.create_inline')}
              </Button>
            </div>
          </>
        )}
      />
      <CreateItemModal
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onSuccess={handleCreated}
      />
    </>
  )
}

interface CreateItemModalProps {
  open: boolean
  onCancel: () => void
  onSuccess: (item: Item) => void
}

function CreateItemModal({ open, onCancel, onSuccess }: CreateItemModalProps) {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [busy, setBusy] = useState(false)
  const [categories, setCategories] = useState<ClassificationItem[]>([])
  const [codeManuallyEdited, setCodeManuallyEdited] = useState(false)

  useEffect(() => {
    if (!open) return
    void api.listProcurementCategories().then(setCategories).catch(() => setCategories([]))
    form.resetFields()
    setCodeManuallyEdited(false)
  }, [open, form])

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newName = e.target.value
    if (codeManuallyEdited) return
    const proposedCode = _generateDefaultCode(newName)
    form.setFieldValue('code', proposedCode)
  }

  const handleCodeChange = (_e: React.ChangeEvent<HTMLInputElement>) => {
    setCodeManuallyEdited(true)
  }

  const handleOk = async () => {
    try {
      const values = await form.validateFields()
      setBusy(true)
      const created = await api.createItem({
        code: values.code.trim(),
        name: values.name.trim(),
        category_id: values.category_id ?? undefined,
        uom: values.uom || 'EA',
        specification: values.specification?.trim() || undefined,
        requires_serial: Boolean(values.requires_serial),
      })
      void message.success(t('item.create_success', { name: created.name }))
      onSuccess(created)
    } catch (e: any) {
      if (e?.errorFields) return
      void message.error(extractError(e).detail)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      title={t('item.create_modal_title')}
      open={open}
      onCancel={() => {
        if (!busy) onCancel()
      }}
      onOk={handleOk}
      confirmLoading={busy}
      okText={t('button.confirm')}
      cancelText={t('button.cancel')}
      width={560}
      destroyOnClose
    >
      <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
        {t('item.create_modal_hint')}
      </Typography.Paragraph>
      <Form form={form} layout="vertical">
        <Form.Item
          name="name"
          label={t('field.item_name')}
          rules={[{ required: true, max: 255 }]}
        >
          <Input maxLength={255} onChange={handleNameChange} />
        </Form.Item>
        <Form.Item
          name="code"
          label={t('field.item_code')}
          tooltip={t('item.code_tooltip')}
          rules={[
            { required: true, max: 64 },
            {
              pattern: /^[A-Z0-9_-]+$/,
              message: t('item.code_format_error'),
            },
          ]}
        >
          <Input maxLength={64} onChange={handleCodeChange} placeholder="AUTO-FILL-FROM-NAME" />
        </Form.Item>
        <Space.Compact style={{ width: '100%', display: 'flex' }}>
          <Form.Item name="uom" label={t('field.uom')} initialValue="EA" style={{ flex: 1, marginRight: 12 }}>
            <Input maxLength={16} />
          </Form.Item>
          <Form.Item
            name="requires_serial"
            label={t('field.requires_serial')}
            valuePropName="checked"
            style={{ flex: 1 }}
          >
            <Switch />
          </Form.Item>
        </Space.Compact>
        <Form.Item name="category_id" label={t('field.procurement_category')}>
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            options={categories.map((c) => ({
              value: c.id,
              label: `${c.code} · ${c.label_zh || c.label_en}`,
            }))}
            placeholder={t('placeholder.select')}
          />
        </Form.Item>
        <Form.Item name="specification" label={t('field.specification')}>
          <Input.TextArea rows={2} maxLength={1024} />
        </Form.Item>
      </Form>
    </Modal>
  )
}
