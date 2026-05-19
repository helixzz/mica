import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Typography, Tag, Spin, Empty, Badge, Space } from 'antd';
import { api, PRListItem, PurchaseOrderListItem, ApprovalTask } from '@/api';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { FileTextOutlined, ShoppingCartOutlined, CheckSquareOutlined } from '@ant-design/icons';
import { PanelProps } from '../PanelRegistry';

dayjs.extend(relativeTime);

const { Text, Title } = Typography;

interface WorkflowKanbanPanelProps extends PanelProps {
  maxItemsPerColumn?: number;
}

interface KanbanItem {
  id: string;
  type: 'pr' | 'po' | 'approval';
  number: string;
  title: string;
  date: string;
  status: string;
  url: string;
}

export default function WorkflowKanbanPanel({ maxItemsPerColumn = 10, width, height }: WorkflowKanbanPanelProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [columns, setColumns] = useState<{
    todo: KanbanItem[];
    inProgress: KanbanItem[];
    waiting: KanbanItem[];
    done: KanbanItem[];
  }>({
    todo: [],
    inProgress: [],
    waiting: [],
    done: []
  });

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        
        // Fetch data in parallel
        const [prs, pos, approvals] = await Promise.all([
          api.listPRs().catch(() => [] as PRListItem[]),
          api.listPOs().catch(() => [] as PurchaseOrderListItem[]),
          api.myPendingApprovals ? api.myPendingApprovals().catch(() => [] as ApprovalTask[]) : Promise.resolve([] as ApprovalTask[])
        ]);

        const todo: KanbanItem[] = [];
        const inProgress: KanbanItem[] = [];
        const waiting: KanbanItem[] = [];
        const done: KanbanItem[] = [];

        const sevenDaysAgo = dayjs().subtract(7, 'day');

        // Process PRs
        prs.forEach(pr => {
          const item: KanbanItem = {
            id: `pr-${pr.id}`,
            type: 'pr',
            number: pr.pr_number,
            title: pr.title,
            date: pr.created_at,
            status: pr.status,
            url: `/purchase-requisitions/${pr.id}`
          };

          if (pr.status === 'draft' || pr.status === 'returned') {
            todo.push(item);
          } else if (pr.status === 'submitted') {
            inProgress.push(item);
          } else if (['approved', 'converted'].includes(pr.status) && dayjs(pr.created_at).isAfter(sevenDaysAgo)) {
            // Only show recently approved/converted PRs in done if they don't have POs yet
            // (Simplified logic for kanban display)
            done.push(item);
          }
        });

        // Process POs
        pos.forEach(po => {
          const item: KanbanItem = {
            id: `po-${po.id}`,
            type: 'po',
            number: po.po_number,
            title: po.pr_title || po.po_number,
            date: po.created_at || new Date().toISOString(),
            status: po.status,
            url: `/purchase-orders/${po.id}`
          };

          if (po.status === 'confirmed') {
            inProgress.push(item);
          } else if (['pending', 'in_transit'].includes(po.status)) {
            waiting.push(item);
          } else if (['fully_received', 'paid', 'closed'].includes(po.status) && dayjs(po.created_at).isAfter(sevenDaysAgo)) {
            done.push(item);
          }
        });

        // Process Approvals
        approvals.forEach(app => {
          if (app.status === 'pending') {
            todo.push({
              id: `app-${app.id}`,
              type: 'approval',
              number: t('insights.approval_task', '审批任务'),
              title: app.stage_name,
              date: app.assigned_at,
              status: 'pending',
              url: `/approvals/${app.id}` // Assuming this route exists, adjust if needed
            });
          }
        });

        // Sort columns by date (newest first) and slice
        const sortByDate = (a: KanbanItem, b: KanbanItem) => dayjs(b.date).valueOf() - dayjs(a.date).valueOf();
        
        setColumns({
          todo: todo.sort(sortByDate).slice(0, maxItemsPerColumn),
          inProgress: inProgress.sort(sortByDate).slice(0, maxItemsPerColumn),
          waiting: waiting.sort(sortByDate).slice(0, maxItemsPerColumn),
          done: done.sort(sortByDate).slice(0, maxItemsPerColumn)
        });

      } catch (error) {
        console.error('Failed to fetch kanban data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [maxItemsPerColumn, t]);

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'pr': return <FileTextOutlined style={{ color: '#1890ff' }} />;
      case 'po': return <ShoppingCartOutlined style={{ color: '#722ed1' }} />;
      case 'approval': return <CheckSquareOutlined style={{ color: '#fa8c16' }} />;
      default: return null;
    }
  };

  const getStatusColor = (status: string) => {
    const map: Record<string, string> = {
      draft: 'default',
      submitted: 'blue',
      approved: 'green',
      returned: 'red',
      confirmed: 'processing',
      pending: 'warning',
      in_transit: 'orange',
      fully_received: 'success',
      paid: 'success',
      closed: 'default'
    };
    return map[status] || 'default';
  };

  const renderColumn = (title: string, items: KanbanItem[], color: string) => (
    <Col xs={24} md={12} xl={6} style={{ height: '100%' }}>
      <div style={{ 
        backgroundColor: '#f5f5f5', 
        padding: '12px', 
        borderRadius: '8px',
        height: '100%',
        minHeight: '300px',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <Title level={5} style={{ margin: 0 }}>{title}</Title>
          <Badge count={items.length} style={{ backgroundColor: color }} />
        </div>
        
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {items.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('common.no_data', '暂无数据')} />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {items.map(item => (
                <Card 
                  key={item.id} 
                  size="small" 
                  hoverable 
                  onClick={() => navigate(item.url)}
                  style={{ cursor: 'pointer' }}
                  bodyStyle={{ padding: '12px' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <Space>
                      {getTypeIcon(item.type)}
                      <Text strong style={{ fontSize: '13px' }}>{item.number}</Text>
                    </Space>
                    <Tag color={getStatusColor(item.status)} style={{ margin: 0 }}>
                      {t(`status.${item.status}`, item.status)}
                    </Tag>
                  </div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text ellipsis style={{ width: '100%', fontSize: '13px' }}>{item.title}</Text>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {dayjs(item.date).fromNow()}
                    </Text>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </Col>
  );

  if (loading) {
    return (
      <Card title={t('insights.workflow_kanban', '工作流看板')} bordered={false} style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  return (
    <Card title={t('insights.workflow_kanban', '工作流看板')} bordered={false} style={{ height: '100%', display: 'flex', flexDirection: 'column' }} bodyStyle={{ flex: 1, padding: '16px', overflow: 'hidden' }}>
      <Row gutter={[16, 16]} style={{ height: '100%' }}>
        {renderColumn(t('insights.todo', '待我处理'), columns.todo, '#1890ff')}
        {renderColumn(t('insights.in_progress', '进行中'), columns.inProgress, '#fa8c16')}
        {renderColumn(t('insights.waiting', '待对方回复'), columns.waiting, '#d9d9d9')}
        {renderColumn(t('insights.done_recently', '近期完成'), columns.done, '#52c41a')}
      </Row>
    </Card>
  );
}
