import React, { useEffect, useState, useMemo } from 'react';
import { Card, Typography, Skeleton, Row, Col, Statistic, Table, Empty } from 'antd';
import { useTranslation } from 'react-i18next';
import { api, CashFlowData, CashFlowMonth } from '@/api';
import { PanelProps } from '../PanelRegistry';
import { fmtAmount } from '@/utils/format';

const { Text } = Typography;

const PLANNED_COLOR = 'var(--color-primary-300)';
const CONFIRMED_COLOR = 'var(--color-viz-positive)';

export default function CashFlowForecastPanel({ width, height }: PanelProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<CashFlowData | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await api.getInsightsCashFlow(3);
        setData(result);
      } catch (err) {
        console.error('Failed to fetch cash flow forecast:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const maxValue = useMemo(() => {
    if (!data || !data.months.length) return 0;
    return Math.max(...data.months.map(m => m.planned + m.confirmed));
  }, [data]);

  const columns = [
    {
      title: t('dashboard.forecast_month_col', '月份'),
      dataIndex: 'month',
      key: 'month',
    },
    {
      title: t('insights.planned_amount', '计划付款'),
      dataIndex: 'planned',
      key: 'planned',
      align: 'right' as const,
      render: (val: number) => <Text style={{ color: PLANNED_COLOR }}>{fmtAmount(val, 'CNY')}</Text>,
    },
    {
      title: t('insights.confirmed_amount', '已确认付款'),
      dataIndex: 'confirmed',
      key: 'confirmed',
      align: 'right' as const,
      render: (val: number) => <Text style={{ color: CONFIRMED_COLOR }}>{fmtAmount(val, 'CNY')}</Text>,
    },
    {
      title: t('insights.net_outflow', '净支出'),
      dataIndex: 'net_outflow',
      key: 'net_outflow',
      align: 'right' as const,
      render: (val: number) => <Text strong>{fmtAmount(val, 'CNY')}</Text>,
    },
  ];

  return (
    <Card 
      title={t('insights.cash_flow', '现金流预测')} 
      bordered={false} 
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : !data || data.months.length === 0 ? (
        <Empty style={{ margin: 'auto' }} />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Statistic 
                title={t('insights.planned_amount', '计划付款')} 
                value={data.total_planned} 
                prefix="¥" 
                precision={2}
                valueStyle={{ color: PLANNED_COLOR }}
              />
            </Col>
            <Col span={12}>
              <Statistic 
                title={t('insights.confirmed_amount', '已确认付款')} 
                value={data.total_confirmed} 
                prefix="¥" 
                precision={2}
                valueStyle={{ color: CONFIRMED_COLOR }}
              />
            </Col>
          </Row>

          <div style={{ height: 160, width: '100%' }}>
            <BarChart months={data.months} maxValue={maxValue} />
          </div>

          <Table<CashFlowMonth>
            dataSource={data.months}
            columns={columns}
            rowKey="month"
            pagination={false}
            size="small"
          />
        </div>
      )}
    </Card>
  );
}

function BarChart({ months, maxValue }: { months: CashFlowMonth[], maxValue: number }) {
  const width = 600;
  const height = 160;
  const padTop = 10;
  const padBottom = 30;
  const padLeft = 60;
  const padRight = 10;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;

  const scale = maxValue > 0 ? innerH / maxValue : 0;
  const groupW = innerW / Math.max(months.length, 1);
  const barW = Math.min(40, groupW * 0.6);

  const yTicks = 3;
  const tickValues = Array.from({ length: yTicks + 1 }, (_, i) => (maxValue * i) / yTicks);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      style={{ width: '100%', height: '100%', overflow: 'visible' }}
    >
      {tickValues.map((v, i) => {
        const y = padTop + innerH - v * scale;
        return (
          <g key={i}>
            <line
              x1={padLeft}
              x2={padLeft + innerW}
              y1={y}
              y2={y}
              stroke="var(--color-viz-grid)"
              strokeDasharray={i === 0 ? '' : '4 4'}
            />
            <text
              x={padLeft - 8}
              y={y + 4}
              fontSize={12}
              textAnchor="end"
              fill="var(--color-text-tertiary)"
            >
              {formatCompact(v)}
            </text>
          </g>
        );
      })}

      {months.map((m, i) => {
        const cx = padLeft + groupW * i + groupW / 2;
        const plannedH = m.planned * scale;
        const confirmedH = m.confirmed * scale;
        
        return (
          <g key={m.month}>
            <rect
              x={cx - barW / 2}
              y={padTop + innerH - confirmedH}
              width={barW}
              height={confirmedH}
              fill={CONFIRMED_COLOR}
            />
            <rect
              x={cx - barW / 2}
              y={padTop + innerH - confirmedH - plannedH}
              width={barW}
              height={plannedH}
              fill={PLANNED_COLOR}
            />
            <text
              x={cx}
              y={padTop + innerH + 20}
              fontSize={12}
              textAnchor="middle"
              fill="var(--color-text-secondary)"
            >
              {m.month}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function formatCompact(v: number): string {
  if (v === 0) return '0';
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(0);
}
