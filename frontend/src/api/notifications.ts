import { client } from './client';

export interface NotificationOut {
  id: string;
  category: string;
  title: string;
  body: string;
  link_url?: string;
  biz_type?: string;
  biz_id?: string;
  meta?: Record<string, any>;
  read_at?: string | null;
  sent_via?: string[];
  created_at: string;
}

export interface NotificationSubscription {
  category: string;
  in_app_enabled: boolean;
  email_enabled: boolean;
}

export interface ListNotificationsParams {
  unread_only?: boolean;
  category?: string;
  limit?: number;
  before_id?: string;
}

export async function listNotifications(opts: ListNotificationsParams = {}): Promise<{ items: NotificationOut[]; has_more: boolean }> {
  const params = new URLSearchParams();
  if (opts.unread_only !== undefined) params.append('unread_only', String(opts.unread_only));
  if (opts.category) params.append('category', opts.category);
  if (opts.limit) params.append('limit', String(opts.limit));
  if (opts.before_id) params.append('before_id', opts.before_id);

  const qs = params.toString();
  const url = `/api/v1/notifications${qs ? `?${qs}` : ''}`;
  const res = await client.get(url);
  return res.data;
}

export async function getUnreadCount(): Promise<{ total: number; by_category: Record<string, number> }> {
  const res = await client.get('/api/v1/notifications/unread-count');
  return res.data;
}

export async function markRead(params: { ids?: string[]; all?: boolean }): Promise<{ updated: number }> {
  const res = await client.post('/api/v1/notifications/mark-read', params);
  return res.data;
}

export async function getSubscriptions(): Promise<NotificationSubscription[]> {
  const res = await client.get('/api/v1/notifications/subscriptions');
  return res.data;
}

export async function updateSubscription(category: string, payload: { in_app_enabled: boolean; email_enabled: boolean }): Promise<NotificationSubscription> {
  const res = await client.put(`/api/v1/notifications/subscriptions/${category}`, payload);
  return res.data;
}
