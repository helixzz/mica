import React, { useEffect, useState } from 'react';
import { Card, Progress, Typography, Spin, Empty, Space } from 'antd';
import { api, BudgetExecutionItem } from '@/api';
import { useTranslation } from 'react-i18next';
import { fmtAmount } from '@/utils/format';
import { PanelProps } from '../PanelRegistry';

const { Text } = Typography;

export default function BudgetGaugePanel({ width, height }: PanelProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<BudgetExecutionItem[]>([]);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await api.getInsightsBudgetExecution();
        // Sort by execution_pct descending (most at-risk first)
        setData(result.sort((a, b) => b.execution_pct - a.execution_pct));
      } catch (error) {
        console.error('Failed to fetch budget execution data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const getProgressColor = (pct: number) => {
    if (pct >= 90) return '#B85450'; // viz-critical
    if (pct >= 70) return '#C97B3F'; // viz-attention
    return '#2F8F69'; // viz-positive
  };

  if (loading) {
    return (
      <Card title={t('insights.budget_gauge')} bordered={false} style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin />
        </div>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card title={t('insights.budget_gauge')} bordered={false} style={{ height: '100%' }}>
        <Empty description={t('insights.no_budgets')} />
      </Card>
    );
  }

  return (
    <Card title={t('insights.budget_gauge')} bordered={false} style={{ height: '100%' }} bodyStyle={{ height: 'calc(100% - 58px)', overflow: 'auto' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {data.map(item => (
          <div key={item.budget_id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text strong>{item.scope_name}</Text>
              <Text type="secondary">
                {fmtAmount(item.actual_spend)} / {fmtAmount(item.budget_amount)} ({item.execution_pct.toFixed(1)}%)
              </Text>
            </div>
            <Progress 
              percent={item.execution_pct} 
              strokeColor={getProgressColor(item.execution_pct)}
              showInfo={false}
              status={item.execution_pct >= 100 ? 'exception' : 'normal'}
            />
          </div>
        ))}
      </Space>
    </Card>
  );
}
