import React, { useEffect, useState } from 'react';
import { Table, Tag, Typography, Spin, Empty, Card, Grid } from 'antd';
import { api, PRListItem, PurchaseOrderListItem, Shipment } from '@/api';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { PanelProps } from '../PanelRegistry';

const { Text } = Typography;
const { useBreakpoint } = Grid;

interface DeliveryCalendarPanelProps extends PanelProps {
  maxItems?: number;
}

interface AggregatedDelivery {
  key: string;
  pr: PRListItem;
  po?: PurchaseOrderListItem;
  shipments: Shipment[];
  expectedDate?: string;
  actualDate?: string;
  daysStatus: 'early' | 'close' | 'late' | 'none';
  daysDiff?: number;
}

export default function DeliveryCalendarPanel({ maxItems = 20, width, height }: DeliveryCalendarPanelProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AggregatedDelivery[]>([]);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        // Fetch PRs, POs, and Shipments in parallel
        const [prs, pos, shipments] = await Promise.all([
          api.listPRs().catch(() => [] as PRListItem[]),
          api.listPOs().catch(() => [] as PurchaseOrderListItem[]),
          api.listShipments().catch(() => [] as Shipment[])
        ]);

        // Filter PRs that are not draft/cancelled
        const activePRs = prs
          .filter(pr => !['draft', 'cancelled'].includes(pr.status))
          .sort((a, b) => dayjs(b.created_at).valueOf() - dayjs(a.created_at).valueOf())
          .slice(0, maxItems);

        const aggregated: AggregatedDelivery[] = activePRs.map(pr => {
          const po = pos.find(p => p.pr_id === pr.id);
          const poShipments = po ? shipments.filter(s => s.po_id === po.id) : [];
          
          // Find expected and actual dates from shipments
          let expectedDate: string | undefined;
          let actualDate: string | undefined;
          
          if (poShipments.length > 0) {
            // Get earliest expected date
            const expectedDates = poShipments
              .map(s => s.expected_date)
              .filter(Boolean)
              .sort((a, b) => dayjs(a).valueOf() - dayjs(b).valueOf());
            if (expectedDates.length > 0) expectedDate = expectedDates[0] as string;
            
            // Get latest actual date
            const actualDates = poShipments
              .map(s => s.actual_date)
              .filter(Boolean)
              .sort((a, b) => dayjs(b).valueOf() - dayjs(a).valueOf());
            if (actualDates.length > 0) actualDate = actualDates[0] as string;
          }

          // Calculate days status
          let daysStatus: 'early' | 'close' | 'late' | 'none' = 'none';
          let daysDiff: number | undefined;

          if (expectedDate && !actualDate) {
            daysDiff = dayjs(expectedDate).diff(dayjs(), 'day');
            if (daysDiff < 0) daysStatus = 'late';
            else if (daysDiff <= 3) daysStatus = 'close';
            else daysStatus = 'early';
          }

          return {
            key: pr.id,
            pr,
            po,
            shipments: poShipments,
            expectedDate,
            actualDate,
            daysStatus,
            daysDiff
          };
        });

        setData(aggregated);
      } catch (error) {
        console.error('Failed to fetch delivery calendar data:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [maxItems]);

  const getStatusColor = (status: string) => {
    const map: Record<string, string> = {
      submitted: 'blue',
      approved: 'green',
      rejected: 'red',
      converted: 'cyan',
      confirmed: 'processing',
      in_transit: 'orange',
      arrived: 'success',
      partially_received: 'warning',
      fully_received: 'success',
      closed: 'default'
    };
    return map[status] || 'default';
  };

  const getDaysColor = (status: string) => {
    switch (status) {
      case 'early': return 'success';
      case 'close': return 'warning';
      case 'late': return 'error';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Card title={t('insights.delivery_calendar', '交付日历')} bordered={false} style={{ height: '100%' }}>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin />
        </div>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card title={t('insights.delivery_calendar', '交付日历')} bordered={false} style={{ height: '100%' }}>
        <Empty description={t('insights.no_active_prs', '暂无进行中的采购申请')} />
      </Card>
    );
  }

  const columns = [
    {
      title: t('pr.pr_number', '申请单号'),
      dataIndex: ['pr', 'pr_number'],
      key: 'pr_number',
      render: (text: string, record: AggregatedDelivery) => (
        <a onClick={() => navigate(`/purchase-requisitions/${record.pr.id}`)}>{text}</a>
      )
    },
    {
      title: t('pr.title', '标题'),
      dataIndex: ['pr', 'title'],
      key: 'title',
      ellipsis: true,
    },
    {
      title: t('common.status', '状态'),
      key: 'status',
      render: (_: any, record: AggregatedDelivery) => {
        // Show PO status if PO exists, else PR status
        const status = record.po ? record.po.status : record.pr.status;
        return <Tag color={getStatusColor(status)}>{t(`status.${status}`, status)}</Tag>;
      }
    },
    {
      title: t('po.po_number', '订单号'),
      key: 'po_number',
      render: (_: any, record: AggregatedDelivery) => (
        record.po ? (
          <a onClick={() => navigate(`/purchase-orders/${record.po!.id}`)}>{record.po.po_number}</a>
        ) : <Text type="secondary">-</Text>
      )
    },
    {
      title: t('shipment.expected_date', '预计交货'),
      dataIndex: 'expectedDate',
      key: 'expectedDate',
      render: (text?: string) => text ? dayjs(text).format('YYYY-MM-DD') : <Text type="secondary">-</Text>
    },
    {
      title: t('shipment.actual_date', '实际交货'),
      dataIndex: 'actualDate',
      key: 'actualDate',
      render: (text?: string) => text ? dayjs(text).format('YYYY-MM-DD') : <Text type="secondary">-</Text>
    },
    {
      title: t('insights.days_remaining', '剩余天数'),
      key: 'days',
      render: (_: any, record: AggregatedDelivery) => {
        if (record.actualDate) return <Text type="success">{t('insights.delivered', '已交付')}</Text>;
        if (record.daysStatus === 'none' || record.daysDiff === undefined) return <Text type="secondary">-</Text>;
        
        let text = '';
        if (record.daysDiff < 0) text = t('insights.days_late', '逾期 {{days}} 天', { days: Math.abs(record.daysDiff) });
        else if (record.daysDiff === 0) text = t('insights.today', '今天');
        else text = t('insights.days_left', '剩 {{days}} 天', { days: record.daysDiff });

        return <Text type={getDaysColor(record.daysStatus) as any}>{text}</Text>;
      }
    }
  ];

  return (
    <Card title={t('insights.delivery_calendar', '交付日历')} bordered={false} style={{ height: '100%' }} bodyStyle={{ height: 'calc(100% - 58px)', overflow: 'auto' }}>
      {screens.md ? (
        <Table 
          columns={columns} 
          dataSource={data} 
          pagination={false}
          size="small"
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {data.map(record => (
            <Card key={record.key} size="small" type="inner" bordered>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <a onClick={() => navigate(`/purchase-requisitions/${record.pr.id}`)}>{record.pr.pr_number}</a>
                <Tag color={getStatusColor(record.po ? record.po.status : record.pr.status)}>
                  {t(`status.${record.po ? record.po.status : record.pr.status}`, record.po ? record.po.status : record.pr.status)}
                </Tag>
              </div>
              <div style={{ marginBottom: '8px' }}>
                <Text strong>{record.pr.title}</Text>
              </div>
              {record.po && (
                <div style={{ marginBottom: '8px', fontSize: '12px' }}>
                  <Text type="secondary">{t('po.po_number', '订单号')}: </Text>
                  <a onClick={() => navigate(`/purchase-orders/${record.po!.id}`)}>{record.po.po_number}</a>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <div>
                  <Text type="secondary">{t('shipment.expected_date', '预计')}: </Text>
                  {record.expectedDate ? dayjs(record.expectedDate).format('YYYY-MM-DD') : '-'}
                </div>
                <div>
                  {record.actualDate ? (
                    <Text type="success">{t('insights.delivered', '已交付')}</Text>
                  ) : record.daysDiff !== undefined ? (
                    <Text type={getDaysColor(record.daysStatus) as any}>
                      {record.daysDiff < 0 
                        ? t('insights.days_late', '逾期 {{days}} 天', { days: Math.abs(record.daysDiff) })
                        : record.daysDiff === 0 
                          ? t('insights.today', '今天')
                          : t('insights.days_left', '剩 {{days}} 天', { days: record.daysDiff })
                      }
                    </Text>
                  ) : null}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </Card>
  );
}
