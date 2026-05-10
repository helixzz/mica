import { useEffect, useState } from 'react'
import { Popconfirm, Select, Switch, Table, message } from 'antd'
import type { AIModelRow } from './AIModelPanel'
import { useTranslation } from 'react-i18next'
import { api } from '@/api'
import { extractError } from '@/api/client'

const TOKEN_PRESET_VALUES = [256, 512, 1024, 2048, 4096, 8192, 16384]

const TOKEN_PRESET_LABELS: Record<number, string> = {
  256: 'admin.token_preset_short',
  512: 'admin.token_preset_brief',
  1024: 'admin.token_preset_normal',
  2048: 'admin.token_preset_medium',
  4096: 'admin.token_preset_long',
  8192: 'admin.token_preset_extended',
  16384: 'admin.token_preset_full',
}

export function RoutingsPanel() {
  const { t } = useTranslation()
  const [rows, setRows] = useState<Record<string, unknown>[]>([])
  const [models, setModels] = useState<AIModelRow[]>([])
  const [loading, setLoading] = useState(false)
  const [pendingToggle, setPendingToggle] = useState<string | null>(null)

  const tokenOptions = TOKEN_PRESET_VALUES.map((v) => ({
    value: v,
    label: t(TOKEN_PRESET_LABELS[v]),
  }))

  const load = () => {
    setLoading(true)
    Promise.all([api.adminListRoutings(), api.adminListAIModels()])
      .then(([r, m]) => { setRows(r); setModels(m as AIModelRow[]) })
      .finally(() => setLoading(false))
  }
  useEffect(() => { void load() }, [])

  const changePrimary = async (feature_code: string, primary_model_id: string | null, current: Record<string, unknown>) => {
    await api.adminUpsertRouting(feature_code, {
      feature_code, primary_model_id,
      fallback_model_ids: current.fallback_model_ids as string[] | undefined,
      prompt_template: current.prompt_template as string | undefined,
      temperature: current.temperature as number | undefined,
      max_tokens: current.max_tokens as number | undefined,
      enabled: current.enabled as boolean | undefined,
    })
    void message.success(t('admin.routing_updated'))
    void load()
  }

  const applyEnabledChange = async (current: Record<string, unknown>, nextEnabled: boolean) => {
    setPendingToggle(current.feature_code as string)
    try {
      await api.adminUpsertRouting(current.feature_code as string, {
        feature_code: current.feature_code as string,
        primary_model_id: (current.primary_model_id as string) || null,
        fallback_model_ids: current.fallback_model_ids as string[] | undefined,
        prompt_template: current.prompt_template as string | undefined,
        temperature: current.temperature as number | undefined,
        max_tokens: current.max_tokens as number | undefined,
        enabled: nextEnabled,
      })
      void message.success(nextEnabled ? t('admin.routing_enabled_toast') : t('admin.routing_disabled_toast'))
      void load()
    } catch (e) {
      void message.error(extractError(e).detail)
    } finally {
      setPendingToggle(null)
    }
  }

  return (
    <Table
      rowKey="feature_code"
      dataSource={rows}
      loading={loading}
      pagination={false}
      columns={[
        { title: t('admin.feature_col'), dataIndex: 'feature_code' },
        {
          title: t('admin.primary_model'), dataIndex: 'primary_model_id',
          render: (v: string | null, r) => (
            <Select style={{ width: 240 }} value={v || undefined}
              onChange={async (val) => {
              try {
                await changePrimary(r.feature_code as string, val ?? null, r)
              } catch (e) {
                void message.error(extractError(e).detail)
              }
            }}
              allowClear
              options={models.map((m) => ({ value: m.id, label: `${m.name} (${m.modality})` }))}
              placeholder={t('admin.not_configured')}
            />
          ),
        },
        { title: t('admin.temperature_col'), dataIndex: 'temperature' },
        {
          title: t('admin.max_tokens_col'), dataIndex: 'max_tokens',
          render: (v: number | null, r) => (
            <Select
              style={{ width: 220 }}
              value={v ?? 1024}
              onChange={async (val) => {
                try {
                  await api.adminUpsertRouting(r.feature_code as string, {
                    feature_code: r.feature_code as string,
                    primary_model_id: (r.primary_model_id as string) || null,
                    fallback_model_ids: r.fallback_model_ids as string[] | undefined,
                    prompt_template: r.prompt_template as string | undefined,
                    temperature: r.temperature as number | undefined,
                    max_tokens: val,
                    enabled: r.enabled as boolean | undefined,
                  })
                  void message.success(t('admin.routing_updated'))
                  void load()
                } catch (e) {
                  void message.error(extractError(e).detail)
                }
              }}
              options={tokenOptions}
            />
          ),
        },
        {
          title: t('admin.enabled_col'), dataIndex: 'enabled', width: 120,
          render: (v: boolean, r) => {
            const loading_ = pendingToggle === (r.feature_code as string)
            if (v) return <Switch checked={v} loading={loading_} disabled={loading_}
              onChange={!v ? undefined : (next) => void applyEnabledChange(r, next)} />
            return (
              <Popconfirm title={t('admin.routing_enable_confirm_title')}
                description={t('admin.routing_enable_confirm_desc')}
                okText={t('admin.routing_enable_confirm_ok')} cancelText={t('button.cancel')}
                onConfirm={() => void applyEnabledChange(r, true)}>
                <Switch checked={false} loading={loading_} disabled={loading_} />
              </Popconfirm>
            )
          },
        },
      ]}
    />
  )
}
