import React, { useEffect, useState } from 'react';
import { Card, Typography, Skeleton, Alert, Space, Badge } from 'antd';
import { 
  DollarOutlined, 
  ClockCircleOutlined, 
  ExclamationCircleOutlined, 
  WarningOutlined,
  CheckCircleFilled
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { api, AnomalyItem } from '@/api';
import { PanelProps } from '../PanelRegistry';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Text } = Typography;

const getIconForType = (type: string) => {
  switch (type) {
    case 'price_anomaly': return <DollarOutlined />;
    case 'overdue_delivery': return <ClockCircleOutlined />;
    case 'approval_stale': return <ExclamationCircleOutlined />;
    case 'supplier_concentration': return <WarningOutlined />;
    default: return <WarningOutlined />;
  }
};

export default function AnomalyWallPanel({ width, height }: PanelProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [anomalies, setAnomalies] = useState<AnomalyItem[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const result = await api.getInsightsAnomalyWall();
        
        const sorted = [...result.anomalies].sort((a, b) => {
          if (a.severity === 'critical' && b.severity !== 'critical') return -1;
          if (a.severity !== 'critical' && b.severity === 'critical') return 1;
          return dayjs(b.created_at).valueOf() - dayjs(a.created_at).valueOf();
        });
        
        setAnomalies(sorted);
      } catch (err) {
        console.error('Failed to fetch anomaly wall:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const title = (
    <Space>
      {t('insights.anomaly_wall', '异常红旗')}
      {!loading && anomalies.length > 0 && (
        <Badge count={anomalies.length} style={{ backgroundColor: '#ff4d4f' }} />
      )}
    </Space>
  );

  return (
    <Card 
      title={title} 
      bordered={false} 
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, overflow: 'auto', padding: '16px' }}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : anomalies.length === 0 ? (
        <div style={{ 
          height: '100%', 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: 'var(--color-success, #52c41a)'
        }}>
          <CheckCircleFilled style={{ fontSize: 48, marginBottom: 16 }} />
          <Text strong style={{ fontSize: 16 }}>
            {t('insights.no_anomalies', '暂无异常，一切正常')}
          </Text>
        </div>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {anomalies.map((anomaly, index) => (
            <Alert
              key={`${anomaly.type}-${index}`}
              type={anomaly.severity === 'critical' ? 'error' : 'warning'}
              showIcon
              icon={getIconForType(anomaly.type)}
              message={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Text strong>{anomaly.title}</Text>
                  <Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap', marginLeft: 8 }}>
                    {dayjs(anomaly.created_at).fromNow()}
                  </Text>
                </div>
              }
              description={
                <div style={{ marginTop: 4 }}>
                  <div style={{ marginBottom: anomaly.link ? 8 : 0 }}>{anomaly.description}</div>
                  {anomaly.link && (
                    <a href={anomaly.link} target="_blank" rel="noreferrer">
                      {t('insights.view_details', '查看详情')}
                    </a>
                  )}
                </div>
              }
            />
          ))}
        </Space>
      )}
    </Card>
  );
}
