import React, { useState, useEffect } from 'react';
import { Tabs, Card, List, Typography, Button, Space, Tag, Switch, Table, theme, message, Badge } from 'antd';
import { useTranslation } from 'react-i18next';
import { useSearchParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { useNotificationStore } from '../stores/notification';
import { listNotifications, getSubscriptions, updateSubscription, NotificationOut, NotificationSubscription } from '../api/notifications';
import { getCategoryIconAndColor } from '../components/NotificationBell';

dayjs.extend(relativeTime);

const { Title, Text } = Typography;

const ALL_CATEGORIES = ['approval', 'po_created', 'payment_pending', 'contract_expiring', 'price_anomaly', 'system'];

export const NotificationCenter: React.FC = () => {
  const { t } = useTranslation();
  const CATEGORIES = [
    { key: 'all', label: t('notification.filters.all') },
    { key: 'unread', label: t('notification.filters.unread') },
    { key: 'approval', label: t('notification.filters.approval') },
    { key: 'contract_expiring', label: t('notification.filters.contract_expiring') },
    { key: 'price_anomaly', label: t('notification.filters.price_anomaly') },
    { key: 'system', label: t('notification.filters.system') }
  ];
  const { token } = theme.useToken();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const activeTab = searchParams.get('tab') || 'inbox';
  const activeFilter = searchParams.get('filter') || 'all';
  
  const { markRead, markAllRead, refresh } = useNotificationStore();
  
  const [items, setItems] = useState<NotificationOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  
  const [subscriptions, setSubscriptions] = useState<NotificationSubscription[]>([]);
  const [subsLoading, setSubsLoading] = useState(false);

  const fetchNotifications = async (loadMore = false) => {
    setLoading(true);
    try {
      const beforeId = loadMore && items.length > 0 ? items[items.length - 1].id : undefined;
      const opts: any = { limit: 20, before_id: beforeId };
      
      if (activeFilter === 'unread') {
        opts.unread_only = true;
      } else if (activeFilter !== 'all') {
        opts.category = activeFilter;
      }
      
      const res = await listNotifications(opts);
      setItems(prev => loadMore ? [...prev, ...res.items] : res.items);
      setHasMore(res.has_more);
    } catch (error) {
      message.error(t('notification.fetchError'));
    } finally {
      setLoading(false);
    }
  };

  const fetchSubscriptions = async () => {
    setSubsLoading(true);
    try {
      const res = await getSubscriptions();
      setSubscriptions(res);
    } catch (error) {
      message.error(t('notification.fetchSubsError'));
    } finally {
      setSubsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'inbox') {
      fetchNotifications();
    } else if (activeTab === 'subscriptions') {
      fetchSubscriptions();
    }
  }, [activeTab, activeFilter]);

  const handleTabChange = (key: string) => {
    setSearchParams(prev => {
      prev.set('tab', key);
      return prev;
    });
  };

  const handleFilterChange = (key: string) => {
    setSearchParams(prev => {
      prev.set('filter', key);
      return prev;
    });
  };

  const handleMarkRead = async (id: string) => {
    await markRead([id]);
    setItems(prev => prev.map(item => item.id === id ? { ...item, read_at: new Date().toISOString() } : item));
  };

  const handleMarkAllRead = async () => {
    await markAllRead();
    setItems(prev => prev.map(item => ({ ...item, read_at: item.read_at || new Date().toISOString() })));
  };

  const handleItemClick = async (item: NotificationOut) => {
    if (!item.read_at) {
      await handleMarkRead(item.id);
    }
    if (item.link_url) {
      navigate(item.link_url);
    }
  };

  const handleToggleSubscription = async (category: string, field: 'in_app_enabled' | 'email_enabled', checked: boolean) => {
    const sub = subscriptions.find(s => s.category === category) || { category, in_app_enabled: true, email_enabled: false };
    const payload = { ...sub, [field]: checked };
    
    try {
      await updateSubscription(category, payload);
      setSubscriptions(prev => {
        const exists = prev.find(s => s.category === category);
        if (exists) {
          return prev.map(s => s.category === category ? { ...s, [field]: checked } : s);
        }
        return [...prev, payload];
      });
      message.success(t('notification.saveSuccess'));
    } catch (error) {
      message.error(t('notification.saveError'));
    }
  };

  const columns = [
    {
      title: t('notification.category'),
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => {
        const { icon, color } = getCategoryIconAndColor(category, token);
        return (
          <Space>
            <span style={{ color }}>{icon}</span>
            {t(`notification.categories.${category}`, category)}
          </Space>
        );
      }
    },
    {
      title: t('notification.inApp'),
      dataIndex: 'in_app_enabled',
      key: 'in_app_enabled',
      render: (enabled: boolean, record: any) => (
        <Switch 
          checked={enabled !== false} 
          onChange={(checked) => handleToggleSubscription(record.category, 'in_app_enabled', checked)} 
        />
      )
    },
    {
      title: t('notification.email'),
      dataIndex: 'email_enabled',
      key: 'email_enabled',
      render: (enabled: boolean, record: any) => (
        <Switch 
          checked={enabled === true} 
          onChange={(checked) => handleToggleSubscription(record.category, 'email_enabled', checked)} 
        />
      )
    }
  ];

  const tableData = ALL_CATEGORIES.map(cat => {
    const sub = subscriptions.find(s => s.category === cat);
    return {
      key: cat,
      category: cat,
      in_app_enabled: sub ? sub.in_app_enabled : true,
      email_enabled: sub ? sub.email_enabled : false
    };
  });

  return (
    <div style={{ padding: 24, maxWidth: 1000, margin: '0 auto' }}>
      <Title level={3} style={{ marginBottom: 24 }}>{t('notification.center')}</Title>
      
      <Card bodyStyle={{ padding: 0 }}>
        <Tabs 
          activeKey={activeTab} 
          onChange={handleTabChange}
          style={{ padding: '0 24px' }}
          items={[
            {
              key: 'inbox',
              label: t('notification.inbox'),
              children: (
                <div style={{ padding: '16px 0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                    <Space wrap>
                      {CATEGORIES.map(cat => (
                        <Tag.CheckableTag
                          key={cat.key}
                          checked={activeFilter === cat.key}
                          onChange={() => handleFilterChange(cat.key)}
                        >
                          {t(`notification.filters.${cat.key}`, cat.label)}
                        </Tag.CheckableTag>
                      ))}
                    </Space>
                    <Button onClick={handleMarkAllRead}>{t('notification.markAllRead')}</Button>
                  </div>
                  
                  <List
                    loading={loading && items.length === 0}
                    dataSource={items}
                    renderItem={(item) => {
                      const { icon, color } = getCategoryIconAndColor(item.category, token);
                      const isUnread = !item.read_at;
                      return (
                        <List.Item
                          style={{ 
                            padding: '16px 24px',
                            backgroundColor: isUnread ? token.controlItemBgActive : 'transparent',
                            cursor: item.link_url ? 'pointer' : 'default'
                          }}
                          onClick={() => item.link_url && handleItemClick(item)}
                          actions={[
                            isUnread && (
                              <Button 
                                type="link" 
                                onClick={(e) => { e.stopPropagation(); handleMarkRead(item.id); }}
                              >
                                {t('notification.markRead')}
                              </Button>
                            )
                          ].filter(Boolean)}
                        >
                          <List.Item.Meta
                            avatar={<div style={{ color, fontSize: 24, marginTop: 4 }}>{icon}</div>}
                            title={
                              <Space>
                                <Text strong={isUnread}>{item.title}</Text>
                                {isUnread && <Badge status="processing" />}
                              </Space>
                            }
                            description={
                              <div>
                                <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>{item.body}</Text>
                                <Text type="secondary" style={{ fontSize: 12 }}>{dayjs(item.created_at).fromNow()}</Text>
                              </div>
                            }
                          />
                        </List.Item>
                      );
                    }}
                  />
                  
                  {hasMore && (
                    <div style={{ textAlign: 'center', marginTop: 16, marginBottom: 16 }}>
                      <Button loading={loading} onClick={() => fetchNotifications(true)}>
                        {t('notification.loadMore')}
                      </Button>
                    </div>
                  )}
                </div>
              )
            },
            {
              key: 'subscriptions',
              label: t('notification.subscriptions'),
              children: (
                <div style={{ padding: '16px 0 24px' }}>
                  <Table 
                    columns={columns} 
                    dataSource={tableData} 
                    pagination={false}
                    loading={subsLoading}
                  />
                </div>
              )
            }
          ]}
        />
      </Card>
    </div>
  );
};

export default NotificationCenter;
