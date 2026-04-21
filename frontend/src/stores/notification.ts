import { create } from 'zustand';
import { NotificationOut, getUnreadCount, listNotifications, markRead } from '../api/notifications';

interface NotificationState {
  unreadCount: number;
  unreadByCategory: Record<string, number>;
  recentItems: NotificationOut[];
  loading: boolean;
  refresh: () => Promise<void>;
  markRead: (ids: string[]) => Promise<void>;
  markAllRead: () => Promise<void>;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  unreadCount: 0,
  unreadByCategory: {},
  recentItems: [],
  loading: false,

  refresh: async () => {
    set({ loading: true });
    try {
      const [countRes, listRes] = await Promise.all([
        getUnreadCount(),
        listNotifications({ limit: 20 })
      ]);
      set({
        unreadCount: countRes.total,
        unreadByCategory: countRes.by_category,
        recentItems: listRes.items,
        loading: false
      });
    } catch (error) {
      console.error('Failed to refresh notifications', error);
      set({ loading: false });
    }
  },

  markRead: async (ids: string[]) => {
    if (!ids.length) return;
    try {
      await markRead({ ids });
      // Optimistic update
      const { recentItems, unreadCount } = get();
      const newItems = recentItems.map(item => 
        ids.includes(item.id) ? { ...item, read_at: new Date().toISOString() } : item
      );
      set({ 
        recentItems: newItems,
        unreadCount: Math.max(0, unreadCount - ids.length)
      });
      // Refresh to get accurate counts
      get().refresh();
    } catch (error) {
      console.error('Failed to mark notifications as read', error);
    }
  },

  markAllRead: async () => {
    try {
      await markRead({ all: true });
      // Optimistic update
      const { recentItems } = get();
      const newItems = recentItems.map(item => ({ ...item, read_at: item.read_at || new Date().toISOString() }));
      set({ 
        recentItems: newItems,
        unreadCount: 0,
        unreadByCategory: {}
      });
      get().refresh();
    } catch (error) {
      console.error('Failed to mark all notifications as read', error);
    }
  }
}));
