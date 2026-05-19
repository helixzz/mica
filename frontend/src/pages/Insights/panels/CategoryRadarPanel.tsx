import React, { useEffect, useState } from 'react';
import { Card, Table, Typography, Spin, Empty } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { api, CategoryTrendItem } from '@/api';
import { useTranslation } from 'react-i18next';
import { fmtAmount } from '@/utils/format';
import { PanelProps } from '../PanelRegistry';

const { Text } = Typography;

export default function CategoryRadarPanel({ width, height }: PanelProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<CategoryTrendItem[]>([]);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await api.getInsightsCategoryTrends();
        setData(result.sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct)));
      } catch (error) {
        console.error('Failed to fetch category trends data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const columns = [
    {
      title: t('item.category', '品类'),
      dataIndex: 'category_name',
      key: 'category_name',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: t('insights.change_pct'),
      dataIndex: 'change_pct',
      key: 'change_pct',
      render: (pct: number) => {
        if (pct > 0) {
          return <Text type="danger"><ArrowUpOutlined /> {pct.toFixed(1)}%</Text>;
        }
        if (pct < 0) {
          return <Text type="success"><ArrowDownOutlined /> {Math.abs(pct).toFixed(1)}%</Text>;
        }
        return <Text type="secondary">-</Text>;
      }
    },
    {
      title: t('insights.current_price', '当前均价'),
      dataIndex: 'avg_price_current',
      key: 'avg_price_current',
      render: (price: number) => <Text>{fmtAmount(price)}</Text>
    },
    {
      title: t('insights.prev_price', '上期均价'),
      dataIndex: 'avg_price_prev',
      key: 'avg_price_prev',
      render: (price: number) => <Text type="secondary">{fmtAmount(price)}</Text>
    },
    {
      title: t('insights.volume', '采购量'),
      dataIndex: 'volume_current',
      key: 'volume_current',
      render: (vol: number) => <Text>{vol}</Text>
    }
  ];

  if (loading) {
    return (
      <Card title={t('insights.category_radar')} bordered={false} style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin />
        </div>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card title={t('insights.category_radar')} bordered={false} style={{ height: '100%' }}>
        <Empty />
      </Card>
    );
  }

  return (
    <Card title={t('insights.category_radar')} bordered={false} style={{ height: '100%' }} bodyStyle={{ height: 'calc(100% - 58px)', overflow: 'auto', padding: 0 }}>
      <Table 
        columns={columns} 
        dataSource={data} 
        rowKey="category_id"
        pagination={false}
        size="small"
      />
    </Card>
  );
}
