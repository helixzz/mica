import { Button, Card, Descriptions, Space, Spin, Statistic, Tag, Typography } from 'antd'
import { ArrowDownOutlined, ArrowUpOutlined, MinusOutlined } from '@ant-design/icons'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type Item, type SKUForecast } from '@/api'
import { MonoId } from '@/components/ui/Mono'

export default function ItemDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [item, setItem] = useState<Item | null>(null)
  const [forecast, setForecast] = useState<SKUForecast | null>(null)
  const [forecastLoading, setForecastLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    try {
      api.getItem(id)
        .then(setItem)
        .catch(() => setError(t('error.unexpected')))
    } catch {
      setError(t('error.unexpected'))
    }
    try {
      api.getSKUForecast(id)
        .then(setForecast)
        .catch(() => {})
        .finally(() => setForecastLoading(false))
    } catch {
      setForecastLoading(false)
    }
  }, [id, t])

  if (error) return (
    <div style={{ textAlign: 'center', padding: 48 }}>
      <Typography.Text type="danger">{error}</Typography.Text>
      <br />
      <Button onClick={() => { setError(null); window.location.reload() }}>
        {t('error.retry')}
      </Button>
    </div>
  )

  if (!item) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 200 }}>
      <Spin size="large" />
    </div>
  )

  const trendConfig = {
    up: { color: '#cf1322', icon: <ArrowUpOutlined />, label: t('forecast.trend_up') },
    down: { color: '#3f8600', icon: <ArrowDownOutlined />, label: t('forecast.trend_down') },
    flat: { color: '#8c8c8c', icon: <MinusOutlined />, label: t('forecast.trend_flat') },
  }

  const currencyFormatter = (val: number | null) =>
    val != null
      ? new Intl.NumberFormat('zh-CN', {
          style: 'currency',
          currency: 'CNY',
        }).format(val)
      : '-'

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={3} style={{ margin: 0 }}>{item.name}</Typography.Title>
        <Button onClick={() => navigate('/sku')}>{t('supplier.back_to_sku')}</Button>
      </div>
      <Card>
        <Descriptions bordered size="small" column={2}>
          <Descriptions.Item label={t('item.code')}><MonoId>{item.code}</MonoId></Descriptions.Item>
          <Descriptions.Item label={t('field.item_name')}>{item.name}</Descriptions.Item>
          <Descriptions.Item label={t('item.category_label')}>{item.category || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.uom')}>{item.uom}</Descriptions.Item>
          <Descriptions.Item label={t('field.specification')} span={2}>{item.specification || '-'}</Descriptions.Item>
          <Descriptions.Item label={t('field.status')}><Tag color={item.is_enabled !== false ? 'success' : 'default'}>{item.is_enabled !== false ? t('item.active') : t('item.inactive')}</Tag></Descriptions.Item>
        </Descriptions>
      </Card>

      {forecastLoading ? (
        <Card title={t('forecast.title')} size="small">
          <Spin />
        </Card>
      ) : forecast ? (
        <Card title={t('forecast.title')} size="small">
          {forecast.sample_size < 3 ? (
            <Typography.Text type="secondary">
              {t('forecast.insufficient_data')}
            </Typography.Text>
          ) : (
            <Space size="large" wrap>
              <Statistic
                title={t('forecast.trend_up')}
                value={trendConfig[forecast.trend].label}
                prefix={
                  <span style={{ color: trendConfig[forecast.trend].color }}>
                    {trendConfig[forecast.trend].icon}
                  </span>
                }
                valueStyle={{
                  color: trendConfig[forecast.trend].color,
                  fontSize: 16,
                }}
              />
              <Statistic
                title={t('forecast.next_month')}
                value={currencyFormatter(forecast.next_month_prediction)}
                valueStyle={{
                  color:
                    forecast.trend === 'up'
                      ? '#cf1322'
                      : forecast.trend === 'down'
                        ? '#3f8600'
                        : '#666',
                }}
              />
              <Statistic
                title={t('forecast.ma_7d')}
                value={currencyFormatter(forecast.ma_7d)}
              />
              <Statistic
                title={t('forecast.ma_30d')}
                value={currencyFormatter(forecast.ma_30d)}
              />
              <Statistic
                title={t('forecast.recent_avg')}
                value={currencyFormatter(forecast.recent_avg)}
              />
              <Statistic
                title={t('forecast.sample_size')}
                value={forecast.sample_size}
              />
            </Space>
          )}
        </Card>
      ) : null}
    </Space>
  )
}
