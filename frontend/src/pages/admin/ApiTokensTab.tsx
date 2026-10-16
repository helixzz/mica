import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import {
  Button,
  Input,
  Popconfirm,
  Space,
  Switch,
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

import { api, type AdminApiToken } from '@/api'
import { extractError } from '@/api/client'
import { EmptyState, MonoId, MonoNum } from '@/components/ui'

const { Text } = Typography

const SCOPE_LABEL_KEYS: Record<string, string> = {
  read: 'apiTokens.scope_read',
  write: 'apiTokens.scope_write',
}

function formatStamp(value: string | null | undefined): string | null {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : null
}

/** Shape check only: it keeps a typo from turning into a backend 422. */
const isValidUserId = (value: string) =>
  value === '' || /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)

export function ApiTokensTab() {
  const { t } = useTranslation()
  const { token } = theme.useToken()

  const [rows, setRows] = useState<AdminApiToken[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [userIdInput, setUserIdInput] = useState('')
  const [userId, setUserId] = useState('')
  const [includeRevoked, setIncludeRevoked] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await api.listAdminApiTokens({
        limit: pageSize,
        offset: (page - 1) * pageSize,
        ...(userId ? { user_id: userId } : {}),
        ...(includeRevoked ? { include_revoked: true } : {}),
      })
      setRows(result.items)
      setTotal(result.total)
    } catch (e) {
      void message.error(`${t('apiTokens.loading_error')}: ${extractError(e).detail}`)
    } finally {
      setLoading(false)
    }
  }, [includeRevoked, page, pageSize, t, userId])

  useEffect(() => {
    void fetchData()
  }, [fetchData])

  const handleSearch = useCallback(() => {
    const next = userIdInput.trim()
    if (!isValidUserId(next)) return
    setUserId(next)
    setPage(1)
  }, [userIdInput])

  const handleReset = useCallback(() => {
    setUserIdInput('')
    setUserId('')
    setIncludeRevoked(false)
    setPage(1)
  }, [])

  const handleRevoke = useCallback(
    async (record: AdminApiToken) => {
      try {
        await api.revokeAdminApiToken(record.id)
        void message.success(t('message.deleted'))
        await fetchData()
      } catch (e) {
        void message.error(`${t('error.delete_failed')}: ${extractError(e).detail}`)
      }
    },
    [fetchData, t],
  )

  const columns: ColumnsType<AdminApiToken> = useMemo(
    () => [
      {
        title: t('apiTokens.owner'),
        key: 'owner',
        width: 180,
        render: (_: unknown, record: AdminApiToken) => (
          <Space direction="vertical" size={0}>
            <Text>{record.user_display_name || record.username}</Text>
            {record.user_display_name && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.username}
              </Text>
            )}
          </Space>
        ),
      },
      {
        title: t('apiTokens.name'),
        dataIndex: 'name',
        width: 160,
        render: (value: string) => <Text strong>{value}</Text>,
      },
      {
        title: t('apiTokens.prefix'),
        dataIndex: 'prefix',
        width: 140,
        render: (value: string) => <MonoId>{value}</MonoId>,
      },
      {
        title: t('apiTokens.scopes'),
        dataIndex: 'scopes',
        width: 150,
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
        render: (_: unknown, record: AdminApiToken) => {
          if (record.revoked_at) return <Tag color="default">{t('apiTokens.status_revoked')}</Tag>
          if (record.is_expired) return <Tag color="warning">{t('apiTokens.status_expired')}</Tag>
          return <Tag color="success">{t('apiTokens.status_active')}</Tag>
        },
      },
      {
        title: t('apiTokens.last_used'),
        dataIndex: 'last_used_at',
        width: 200,
        render: (value: string | null, record: AdminApiToken) => {
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
        title: t('apiTokens.created_at'),
        dataIndex: 'created_at',
        width: 170,
        render: (value: string) => <MonoNum>{formatStamp(value)}</MonoNum>,
      },
      {
        title: t('apiTokens.actions'),
        key: 'actions',
        width: 110,
        fixed: 'right',
        render: (_: unknown, record: AdminApiToken) => {
          const revoked = Boolean(record.revoked_at)
          return (
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
          )
        },
      },
    ],
    [handleRevoke, t, token.colorTextTertiary],
  )

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Input
          style={{ width: 280 }}
          allowClear
          value={userIdInput}
          status={isValidUserId(userIdInput) ? undefined : 'error'}
          placeholder={t('apiTokens.user_id')}
          onChange={(e) => setUserIdInput(e.target.value)}
          onPressEnter={handleSearch}
        />
        <Button
          type="primary"
          icon={<SearchOutlined />}
          disabled={!isValidUserId(userIdInput)}
          onClick={handleSearch}
        >
          {t('button.search')}
        </Button>
        <Button onClick={handleReset}>{t('button.reset')}</Button>
        <Button icon={<ReloadOutlined />} onClick={() => void fetchData()}>
          {t('common.refresh')}
        </Button>
        <Space size={8}>
          <Switch checked={includeRevoked} onChange={(checked) => { setIncludeRevoked(checked); setPage(1) }} />
          <Text type="secondary">{t('apiTokens.show_revoked')}</Text>
        </Space>
      </Space>

      <Table<AdminApiToken>
        rowKey="id"
        dataSource={rows}
        columns={columns}
        loading={loading}
        size="small"
        scroll={{ x: 1220 }}
        locale={{ emptyText: <EmptyState size="compact" title={t('apiTokens.empty')} /> }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (count) => t('common.total_count', { count }),
          onChange: (nextPage, nextPageSize) => {
            setPage(nextPage)
            setPageSize(nextPageSize)
          },
        }}
      />
    </Space>
  )
}
