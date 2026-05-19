import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress, Typography, Spin, Empty, Table } from 'antd';
import { api, ApprovalBottleneckData } from '@/api';
import { useTranslation } from 'react-i18next';
import { PanelProps } from '../PanelRegistry';

const { Text, Title } = Typography;

export default function ApprovalBottleneckPanel({ width, height }: PanelProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<ApprovalBottleneckData | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        const result = await api.getInsightsApprovalBottleneck();
        setData(result);
      } catch (error) {
        console.error('Failed to fetch approval bottleneck data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <Card title={t('insights.approval_bottleneck')} bordered={false} style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin />
        </div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card title={t('insights.approval_bottleneck')} bordered={false} style={{ height: '100%' }}>
        <Empty />
      </Card>
    );
  }

  const maxStageHours = Math.max(...data.stages.map(s => s.avg_hours), 1);

  const columns = [
    {
      title: t('user.name', '姓名'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('insights.pending_approvals'),
      dataIndex: 'pending_count',
      key: 'pending_count',
    },
    {
      title: t('insights.avg_hours'),
      dataIndex: 'avg_age_hours',
      key: 'avg_age_hours',
      render: (hours: number) => (
        <Text type={hours > 48 ? 'danger' : undefined}>{hours.toFixed(1)}</Text>
      )
    }
  ];

  return (
    <Card title={t('insights.approval_bottleneck')} bordered={false} style={{ height: '100%' }} bodyStyle={{ height: 'calc(100% - 58px)', overflow: 'auto' }}>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Statistic title={t('insights.pending_approvals')} value={data.total_pending} />
        </Col>
        <Col span={8}>
          <Statistic title={t('insights.approved_30d')} value={data.total_approved_30d} valueStyle={{ color: '#3f8600' }} />
        </Col>
        <Col span={8}>
          <Statistic 
            title={t('insights.avg_hours')} 
            value={data.avg_time_to_approve.toFixed(1)} 
            valueStyle={{ color: data.avg_time_to_approve > 48 ? '#cf1322' : undefined }}
          />
        </Col>
      </Row>

      <div style={{ marginBottom: 24 }}>
        <Title level={5} style={{ fontSize: 14, marginBottom: 16 }}>{t('insights.stages_analysis', '各节点平均耗时')}</Title>
        {data.stages.map(stage => (
          <div key={stage.stage_label} style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <Text>{stage.stage_label}</Text>
              <Text type={stage.avg_hours > 48 ? 'danger' : 'secondary'}>{stage.avg_hours.toFixed(1)}h</Text>
            </div>
            <Progress 
              percent={(stage.avg_hours / maxStageHours) * 100} 
              showInfo={false} 
              strokeColor={stage.avg_hours > 48 ? '#ff4d4f' : '#1890ff'}
            />
          </div>
        ))}
      </div>

      <div>
        <Title level={5} style={{ fontSize: 14, marginBottom: 16 }}>{t('insights.top_pending', '待审批积压排行')}</Title>
        <Table 
          columns={columns} 
          dataSource={data.top_pending_approvers} 
          rowKey="name"
          pagination={false}
          size="small"
        />
      </div>
    </Card>
  );
}
