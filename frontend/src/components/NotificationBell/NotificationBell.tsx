import React, { useEffect, useMemo } from 'react';
import { Badge, Button, Popover, List, Typography, Space, theme, Empty } from 'antd';
import { 
  BellOutlined, 
  AuditOutlined, 
  FileTextOutlined, 
  DollarOutlined, 
  CalendarOutlined, 
  AlertOutlined, 
  NotificationOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import { useNotificationStore } from '../../stores/notification';
import { NotificationOut } from '../../api/notifications';

dayjs.extend(relativeTime);

const { Text, Link } = Typography;

export const getCategoryIconAndColor = (category: string, token: any) => {
  switch (category) {
    case 'approval':
      return { icon: <AuditOutlined />, color: token.colorPrimary };
    case 'po_created':
      return { icon: <FileTextOutlined />, color: token.colorInfo };
    case 'payment_pending':
      return { icon: <DollarOutlined />, color: token.colorWarning };
    case 'contract_expiring':
      return { icon: <CalendarOutlined />, color: token.colorWarning };
    case 'price_anomaly':
      return { icon: <AlertOutlined />, color: token.colorError };
    case 'system':
    default:
      return { icon: <NotificationOutlined />, color: token.colorTextSecondary };
  }
};

export const NotificationBell: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { unreadCount, recentItems, refresh, markRead, markAllRead } = useNotificationStore();

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 60000);
    
    const handleFocus = () => refresh();
    window.addEventListener('focus', handleFocus);
    
    return () => {
      clearInterval(interval);
      window.removeEventListener('focus', handleFocus);
    };
  }, [refresh]);

  const handleItemClick = async (item: NotificationOut) => {
    if (!item.read_at) {
      await markRead([item.id]);
    }
    if (item.link_url) {
      navigate(item.link_url);
    }
  };

  const content = (
    <div style={{ width: 320 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: 12, borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
        <Text strong>{t('notification.title', '通知')} ({unreadCount} {t('notification.unread', '未读')})</Text>
        <Space>
          <Button type="link" size="small" onClick={() => markAllRead()} disabled={unreadCount === 0}>
            {t('notification.markAllRead', '全部标记已读')}
          </Button>
          <Button type="text" size="small" icon={<SettingOutlined />} onClick={() => navigate('/notifications?tab=subscriptions')} />
        </Space>
      </div>
      
      <div style={{ maxHeight: 400, overflowY: 'auto', margin: '12px -16px' }}>
        {recentItems.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('notification.empty', '暂无通知')} />
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={recentItems.slice(0, 10)}
            renderItem={(item) => {
              const { icon, color } = getCategoryIconAndColor(item.category, token);
              const isUnread = !item.read_at;
              return (
                <List.Item 
                  style={{ 
                    padding: '12px 16px', 
                    cursor: 'pointer',
                    backgroundColor: isUnread ? token.controlItemBgActive : 'transparent',
                    transition: 'background-color 0.3s'
                  }}
                  onClick={() => handleItemClick(item)}
                  className="notification-item"
                >
                  <List.Item.Meta
                    avatar={<div style={{ color, fontSize: 20, marginTop: 4 }}>{icon}</div>}
                    title={
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <Text strong={isUnread} ellipsis style={{ maxWidth: 200 }}>{item.title}</Text>
                        <Text type="secondary" style={{ fontSize: 12, whiteSpace: 'nowrap', marginLeft: 8 }}>
                          {dayjs(item.created_at).fromNow()}
                        </Text>
                      </div>
                    }
                    description={<Text type="secondary" ellipsis={{ tooltip: item.body }}>{item.body}</Text>}
                  />
                </List.Item>
              );
            }}
          />
        )}
      </div>
      
      <div style={{ textAlign: 'center', paddingTop: 12, borderTop: `1px solid ${token.colorBorderSecondary}` }}>
        <Button type="link" block onClick={() => navigate('/notifications')}>
          {t('notification.viewAll', '查看全部')}
        </Button>
      </div>
    </div>
  );

  return (
    <Popover content={content} trigger="click" placement="bottomRight" arrow={false}>
      <Badge count={unreadCount} size="small" offset={[-4, 4]}>
        <Button type="text" icon={<BellOutlined style={{ fontSize: 18 }} />} />
      </Badge>
    </Popover>
  );
};
