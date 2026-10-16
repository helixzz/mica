import { ApiOutlined, CopyOutlined, PlusOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
  theme,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type ApiToken, type ApiTokenCreated, type ApiTokenScope } from '@/api'
import { extractError } from '@/api/client'
import { EmptyState, MonoId, MonoNum, PageHeader, Section } from '@/components/ui'

const { Text } = Typography

const EXPIRY_DAY_OPTIONS = [30, 90, 180, 365]
const DEFAULT_EXPIRY_DAYS = 90
const NAME_MAX_LENGTH = 64

const SCOPE_LABEL_KEYS: Record<string, string> = {
  read: 'apiTokens.scope_read',
  write: 'apiTokens.scope_write',
}

const isScope = (value: unknown): value is ApiTokenScope =>
  value === 'read' || value === 'write'

/** "write" implies "read": a read & write token always carries both scopes. */
function normalizeScopes(values: ApiTokenScope[]): ApiTokenScope[] {
  return values.includes('write') ? ['read', 'write'] : ['read']
}

function formatStamp(value: string | null | undefined): string | null {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : null
}

async function writeClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // The Clipboard API needs a secure context; fall back to the legacy path.
  }
  const area = document.createElement('textarea')
  area.value = text
  area.style.position = 'fixed'
  area.style.top = '-1000px'
  area.style.opacity = '0'
  document.body.appendChild(area)
  area.select()
  let copied = false
  try {
    copied = document.execCommand('copy')
  } catch {
    copied = false
  }
  area.remove()
  return copied
}

interface CreateFormValues {
  name: string
  scopes?: unknown
  expires_in_days?: number
}

export function ApiTokensPage() {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  const [tokens, setTokens] = useState<ApiToken[]>([])
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [createdToken, setCreatedToken] = useState<ApiTokenCreated | null>(null)
  const [form] = Form.useForm<CreateFormValues>()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setTokens(await api.listMyApiTokens())
    } catch (e) {
      void message.error(`${t('apiTokens.loading_error')}: ${extractError(e).detail}`)
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  // The create modal is destroyed on close, so its ``initialValues`` (read-only,
  // 90 days) apply to every fresh open without touching the form instance.
  const openCreate = useCallback(() => {
    setCreateOpen(true)
  }, [])

  const handleCreate = useCallback(async () => {
    let values: CreateFormValues
    try {
      values = await form.validateFields()
    } catch {
      return // field errors are rendered inline by the form
    }
    const scopes = (Array.isArray(values.scopes) ? values.scopes : []).filter(isScope)
    setSaving(true)
    try {
      const created = await api.createApiToken({
        name: values.name.trim(),
        scopes: normalizeScopes(scopes),
        ...(values.expires_in_days ? { expires_in_days: values.expires_in_days } : {}),
      })
      setCreateOpen(false)
      setCreatedToken(created)
      await load()
    } catch (e) {
      void message.error(`${t('error.create_failed')}: ${extractError(e).detail}`)
    } finally {
      setSaving(false)
    }
  }, [form, load, t])

  const handleRotate = useCallback(
    async (record: ApiToken) => {
      try {
        setCreatedToken(await api.rotateApiToken(record.id))
        await load()
      } catch (e) {
        void message.error(`${t('error.unexpected')}: ${extractError(e).detail}`)
      }
    },
    [load, t],
  )

  const handleRevoke = useCallback(
    async (record: ApiToken) => {
      try {
        await api.revokeApiToken(record.id)
        void message.success(t('message.deleted'))
        await load()
      } catch (e) {
        void message.error(`${t('error.delete_failed')}: ${extractError(e).detail}`)
      }
    },
    [load, t],
  )

  const handleCopy = useCallback(async () => {
    if (!createdToken) return
    if (await writeClipboard(createdToken.token)) {
      void message.success(t('apiTokens.copied'))
    } else {
      void message.error(t('error.unexpected'))
    }
  }, [createdToken, t])

  const columns: ColumnsType<ApiToken> = useMemo(
    () => [
      {
        title: t('apiTokens.name'),
        dataIndex: 'name',
        width: 180,
        render: (value: string) => <Text strong>{value}</Text>,
      },
      {
        title: t('apiTokens.prefix'),
        dataIndex: 'prefix',
        width: 150,
        render: (value: string) => <MonoId>{value}</MonoId>,
      },
      {
        title: t('apiTokens.scopes'),
        dataIndex: 'scopes',
        width: 160,
        render: (scopes: string[] | null) => (
          <Space size={4} wrap>
            {(scopes ?? []).map((scope) => (
              <Tag key={scope} color={scope === 'write' ? 'blue' : 'default'}>
                {t(SCOPE_LABEL_KEYS[scope] ?? scope)}
              </Tag>
            ))}
          </Space>
        ),
      },
      {
        title: t('apiTokens.status'),
        key: 'status',
        width: 110,
        render: (_: unknown, record: ApiToken) => {
          if (record.revoked_at) return <Tag color="default">{t('apiTokens.status_revoked')}</Tag>
          if (record.is_expired) return <Tag color="warning">{t('apiTokens.status_expired')}</Tag>
          return <Tag color="success">{t('apiTokens.status_active')}</Tag>
        },
      },
      {
        title: t('apiTokens.expires_in'),
        dataIndex: 'expires_at',
        width: 170,
        render: (value: string | null) => {
          const stamp = formatStamp(value)
          return stamp ? (
            <MonoNum>{stamp}</MonoNum>
          ) : (
            <Text type="secondary">{t('apiTokens.never_expires')}</Text>
          )
        },
      },
      {
        title: t('apiTokens.last_used'),
        dataIndex: 'last_used_at',
        width: 210,
        render: (value: string | null, record: ApiToken) => {
          const stamp = formatStamp(value)
          if (!stamp) return <Text type="secondary">{t('apiTokens.never_used')}</Text>
          return (
            <Space size={6} wrap>
              <MonoNum>{stamp}</MonoNum>
              {record.last_used_ip && (
                <MonoId style={{ fontSize: 12, color: token.colorTextTertiary }}>
                  {record.last_used_ip}
                </MonoId>
              )}
            </Space>
          )
        },
      },
      {
        title: t('apiTokens.actions'),
        key: 'actions',
        width: 170,
        fixed: 'right',
        render: (_: unknown, record: ApiToken) => {
          const revoked = Boolean(record.revoked_at)
          return (
            <Space size={4}>
              <Popconfirm
                title={t('apiTokens.rotate_confirm')}
                okText={t('button.confirm')}
                cancelText={t('button.cancel')}
                disabled={revoked}
                onConfirm={() => handleRotate(record)}
              >
                <Button size="small" disabled={revoked}>
                  {t('apiTokens.rotate')}
                </Button>
              </Popconfirm>
              <Popconfirm
                title={t('apiTokens.revoke_confirm')}
                okText={t('button.confirm')}
                cancelText={t('button.cancel')}
                okButtonProps={{ danger: true }}
                disabled={revoked}
                onConfirm={() => handleRevoke(record)}
              >
                <Button size="small" danger disabled={revoked}>
                  {t('apiTokens.revoke')}
                </Button>
              </Popconfirm>
            </Space>
          )
        },
      },
    ],
    [handleRevoke, handleRotate, t, token.colorTextTertiary],
  )

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <PageHeader
        title={t('apiTokens.title')}
        subtitle={t('apiTokens.subtitle')}
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            {t('apiTokens.create')}
          </Button>
        }
      />

      <Alert
        type="info"
        showIcon
        message={t('apiTokens.usage_title')}
        description={
          <Space direction="vertical" size={4}>
            <Text>{t('apiTokens.usage_hint')}</Text>
            <Typography.Link href="/api/docs" target="_blank" rel="noreferrer">
              <ApiOutlined /> /api/docs
            </Typography.Link>
          </Space>
        }
      />

      <Section density="compact">
        <Table<ApiToken>
          rowKey="id"
          dataSource={tokens}
          columns={columns}
          loading={loading}
          size="small"
          scroll={{ x: 1160 }}
          locale={{ emptyText: <EmptyState size="compact" title={t('apiTokens.empty')} /> }}
          pagination={{
            pageSize: 10,
            hideOnSinglePage: true,
            showSizeChanger: false,
            showTotal: (count) => t('common.total_count', { count }),
          }}
        />
      </Section>

      <Modal
        title={t('apiTokens.create')}
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        confirmLoading={saving}
        okText={t('button.create')}
        cancelText={t('button.cancel')}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ scopes: ['read'], expires_in_days: DEFAULT_EXPIRY_DAYS }}
        >
          <Form.Item
            name="name"
            label={t('apiTokens.name')}
            rules={[
              { required: true, whitespace: true, message: t('validation.required') },
              { max: NAME_MAX_LENGTH },
            ]}
          >
            <Input placeholder={t('apiTokens.name_placeholder')} maxLength={NAME_MAX_LENGTH} />
          </Form.Item>
          <Form.Item
            name="scopes"
            label={t('apiTokens.scopes')}
            normalize={(value: ApiTokenScope[] | undefined) =>
              normalizeScopes((Array.isArray(value) ? value : []).filter(isScope))
            }
          >
            <Checkbox.Group
              options={[
                { value: 'read', label: t('apiTokens.scope_read') },
                { value: 'write', label: t('apiTokens.scope_write') },
              ]}
            />
          </Form.Item>
          <Form.Item name="expires_in_days" label={t('apiTokens.expires_in')}>
            <Select
              options={EXPIRY_DAY_OPTIONS.map((days) => ({
                value: days,
                label: t('apiTokens.days', { count: days }),
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={t('apiTokens.created_title')}
        open={Boolean(createdToken)}
        onCancel={() => setCreatedToken(null)}
        width={560}
        footer={
          <Button type="primary" onClick={() => setCreatedToken(null)}>
            {t('button.close')}
          </Button>
        }
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Alert type="error" showIcon message={t('apiTokens.created_warning')} />
          {createdToken && (
            <>
              <Space size="middle" wrap>
                <MonoId>{createdToken.prefix}</MonoId>
                <Text type="secondary">{createdToken.name}</Text>
                <Text type="secondary">
                  {formatStamp(createdToken.expires_at) ?? t('apiTokens.never_expires')}
                </Text>
              </Space>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: token.marginSM,
                  padding: token.paddingSM,
                  background: token.colorFillAlter,
                  border: `1px solid ${token.colorBorderSecondary}`,
                  borderRadius: token.borderRadiusSM,
                }}
              >
                <MonoId style={{ flex: 1, minWidth: 0, wordBreak: 'break-all', whiteSpace: 'normal' }}>
                  {createdToken.token}
                </MonoId>
                <Button icon={<CopyOutlined />} onClick={handleCopy}>
                  {t('apiTokens.copy')}
                </Button>
              </div>
            </>
          )}
        </Space>
      </Modal>
    </Space>
  )
}
