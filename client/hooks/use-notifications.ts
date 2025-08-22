import { useState, useEffect, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '@/components/auth/auth-provider';
import { toast } from 'react-hot-toast';

export interface CryptoNotification {
  id: string;
  type: 'crypto_deposit' | 'crypto_withdrawal' | 'confirmation_update';
  title: string;
  message: string;
  priority: 'high' | 'normal' | 'low';
  category: 'deposit' | 'withdrawal' | 'confirmation';
  action_url?: string;
  transaction: {
    hash: string;
    crypto_symbol: string;
    amount: string;
    amount_usd: string;
    amount_ugx: string;
    wallet_address?: string;
    destination_address?: string;
    confirmations?: number;
    required_confirmations?: number;
    status: string;
  };
  timestamp: string;
  read: boolean;
}

export const useNotifications = () => {
  const { user } = useAuth();
  const [socket, setSocket] = useState<Socket | null>(null);
  const [notifications, setNotifications] = useState<CryptoNotification[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Connect to WebSocket
  useEffect(() => {
    if (!user) return;

    const wsUrl = process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:5000';
    const newSocket = io(wsUrl, {
      transports: ['websocket'],
      timeout: 60000,
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 2000,
      forceNew: false,
      auth: {
        token: (user as any).user?.id || user.id // Send user ID for authentication
      }
    });

    newSocket.on('connect', () => {
      console.log('Connected to notification service');
      setIsConnected(true);
      
      // Extract user ID from nested structure
      const userId = (user as any).user?.id || user.id;
      console.log('Sending user ID:', userId);
      
      // Join notifications for this user
      newSocket.emit('join_notifications', { user_id: userId });
    });

    newSocket.on('disconnect', () => {
      console.log('Disconnected from notification service');
      setIsConnected(false);
    });

    newSocket.on('connection_status', (data: any) => {
      console.log('Connection status:', data);
    });

    newSocket.on('notification', (notification: CryptoNotification) => {
      console.log('Received notification:', notification);
      
      // Add to notifications list
      setNotifications(prev => [notification, ...prev]);
      
      // Update unread count
      setUnreadCount(prev => prev + 1);
      
      // Show toast notification
      showToastNotification(notification);
    });

    newSocket.on('notification_read', (data: any) => {
      console.log('Notification marked as read:', data);
      // Update local state if needed
    });

    setSocket(newSocket);

    return () => {
      newSocket.disconnect();
    };
  }, [user]);

  const showToastNotification = useCallback((notification: CryptoNotification) => {
    const { title, message, priority, category } = notification;
    
    const toastOptions = {
      duration: priority === 'high' ? 8000 : 5000,
      position: 'top-right' as const,
      style: {
        background: category === 'deposit' ? '#10B981' : category === 'withdrawal' ? '#F59E0B' : '#6B7280',
        color: 'white',
        fontWeight: '500'
      }
    };

    toast(`${title}: ${message}`, toastOptions);
  }, []);

  const markAsRead = useCallback((notificationId: string) => {
    if (!socket || !user) return;

    // Update local state
    setNotifications(prev => 
      prev.map(notif => 
        notif.id === notificationId 
          ? { ...notif, read: true }
          : notif
      )
    );

    // Update unread count
    setUnreadCount(prev => Math.max(0, prev - 1));

    // Notify server
    socket.emit('mark_notification_read', {
      notification_id: notificationId,
      user_id: (user as any).user?.id || user.id
    });
  }, [socket, user]);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => 
      prev.map(notif => ({ ...notif, read: true }))
    );
    setUnreadCount(0);

    // You could emit a bulk mark as read event here
    notifications.forEach(notif => {
      if (!notif.read && socket && user) {
        socket.emit('mark_notification_read', {
          notification_id: notif.id,
          user_id: (user as any).user?.id || user.id
        });
      }
    });
  }, [notifications, socket, user]);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
    setUnreadCount(0);
  }, []);

  const getNotificationsByType = useCallback((type: CryptoNotification['type']) => {
    return notifications.filter(notif => notif.type === type);
  }, [notifications]);

  const getUnreadNotifications = useCallback(() => {
    return notifications.filter(notif => !notif.read);
  }, [notifications]);

  return {
    notifications,
    unreadCount,
    isConnected,
    markAsRead,
    markAllAsRead,
    clearNotifications,
    getNotificationsByType,
    getUnreadNotifications
  };
};
