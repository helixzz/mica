import React, { useEffect, useState } from 'react';
import { Card, Typography, Skeleton, Select, Button, Space } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import { api } from '@/api';
import { PanelProps } from '../PanelRegistry';
import dayjs from 'dayjs';

const { Text, Paragraph } = Typography;

export default function QuarterlySummaryPanel({ width, height }: PanelProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [data, setData] = useState<{ quarter: string; summary_text: string; generated_at: string } | null>(null);
  
  // Generate current and previous quarter strings (e.g., "2026-Q2")
  const currentQuarter = `${dayjs().year()}-Q${Math.ceil((dayjs().month() + 1) / 3)}`;
  const prevQuarterDate = dayjs().subtract(3, 'month');
  const prevQuarter = `${prevQuarterDate.year()}-Q${Math.ceil((prevQuarterDate.month() + 1) / 3)}`;
  
  const [selectedQuarter, setSelectedQuarter] = useState(currentQuarter);

  const fetchData = async (quarter: string) => {
    try {
      setLoading(true);
      setError(false);
      const result = await api.getInsightsQuarterlySummary(quarter);
      setData(result);
    } catch (err) {
      console.error('Failed to fetch quarterly summary:', err);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(selectedQuarter);
  }, [selectedQuarter]);

  const extra = (
    <Select
      value={selectedQuarter}
      onChange={setSelectedQuarter}
      style={{ width: 120 }}
      size="small"
      options={[
        { value: currentQuarter, label: currentQuarter },
        { value: prevQuarter, label: prevQuarter },
      ]}
    />
  );

  return (
    <Card 
      title={t('insights.quarterly_summary', '季度摘要')} 
      extra={extra}
      bordered={false} 
      style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
      bodyStyle={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}
    >
      {loading ? (
        <div style={{ flex: 1 }}>
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            {t('insights.summary_loading', '正在生成季度摘要...')}
          </Text>
          <Skeleton active paragraph={{ rows: 4 }} />
        </div>
      ) : error || !data ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <Text type="secondary" style={{ marginBottom: 16 }}>
            {t('insights.summary_failed', '摘要生成失败，请稍后重试')}
          </Text>
          <Button icon={<ReloadOutlined />} onClick={() => fetchData(selectedQuarter)}>
            {t('common.refresh', '刷新')}
          </Button>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1 }}>
            <Paragraph style={{ fontSize: 14, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
              {data.summary_text}
            </Paragraph>
          </div>
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--color-border-subtle, #f0f0f0)' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              Generated at: {dayjs(data.generated_at).format('YYYY-MM-DD HH:mm:ss')}
            </Text>
          </div>
        </div>
      )}
    </Card>
  );
}
