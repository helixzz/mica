import React, { useEffect, useState } from 'react';
import { Card, Table, Progress, Typography, Spin, Empty, Badge } from 'antd';
import { api, SupplierScorecardItem } from '@/api';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { fmtAmount } from '@/utils/format';
import { PanelProps } from '../PanelRegistry';

const { Text } = Typography;

export default function SupplierScorecardPanel({ width, height }: PanelProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<SupplierScorecardItem[]>([]);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await api.getInsightsSupplierScorecard();
        setData(result.sort((a, b) => b.score - a.score));
      } catch (error) {
        console.error('Failed to fetch supplier scorecard data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'green';
    if (score >= 60) return 'gold';
    return 'red';
  };

  const columns = [
    {
      title: t('supplier.name', '供应商'),
      dataIndex: 'supplier_name',
      key: 'supplier_name',
      render: (text: string, record: SupplierScorecardItem) => (
        <a onClick={() => navigate(`/suppliers/${record.supplier_id}`)}>{text}</a>
      )
    },
    {
      title: t('insights.score'),
      dataIndex: 'score',
      key: 'score',
      render: (score: number) => (
        <Badge 
          count={score} 
          style={{ backgroundColor: getScoreColor(score), color: '#fff' }} 
          showZero
        />
      )
    },
    {
      title: t('insights.on_time_rate'),
      dataIndex: 'on_time_rate',
      key: 'on_time_rate',
      render: (rate: number) => (
        <Progress 
          percent={rate} 
          size="small" 
          status={rate >= 90 ? 'success' : rate >= 70 ? 'normal' : 'exception'}
        />
      )
    },
    {
      title: t('insights.avg_days'),
      dataIndex: 'avg_delivery_days',
      key: 'avg_delivery_days',
      render: (days: number) => <Text>{days.toFixed(1)}</Text>
    },
    {
      title: t('po.total_amount', '总金额'),
      dataIndex: 'total_amount',
      key: 'total_amount',
      render: (amount: number) => <Text>{fmtAmount(amount)}</Text>
    }
  ];

  if (loading) {
    return (
      <Card title={t('insights.supplier_scorecard')} bordered={false} style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin />
        </div>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card title={t('insights.supplier_scorecard')} bordered={false} style={{ height: '100%' }}>
        <Empty />
      </Card>
    );
  }

  return (
    <Card title={t('insights.supplier_scorecard')} bordered={false} style={{ height: '100%' }} bodyStyle={{ height: 'calc(100% - 58px)', overflow: 'auto', padding: 0 }}>
      <Table 
        columns={columns} 
        dataSource={data} 
        rowKey="supplier_id"
        pagination={false}
        size="small"
      />
    </Card>
  );
}
