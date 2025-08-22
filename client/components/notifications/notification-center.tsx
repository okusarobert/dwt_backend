'use client';

import React, { useState } from 'react';
import { Bell, X, Check, CheckCheck, Trash2, ExternalLink } from 'lucide-react';
import { useNotifications, CryptoNotification } from '@/hooks/use-notifications';
import { useTheme } from '@/components/theme/theme-provider';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';

const NotificationCenter: React.FC = () => {
  const { theme } = useTheme();
  const {
    notifications,
    unreadCount,
    isConnected,
    markAsRead,
    markAllAsRead,
    clearNotifications
  } = useNotifications();
  
  const [isOpen, setIsOpen] = useState(false);

  const handleNotificationClick = (notification: CryptoNotification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
    
    if (notification.action_url) {
      // Close popover and navigate
      setIsOpen(false);
    }
  };

  const getNotificationIcon = (type: CryptoNotification['type']) => {
    switch (type) {
      case 'crypto_deposit':
        return '💰';
      case 'crypto_withdrawal':
        return '📤';
      case 'confirmation_update':
        return '🔄';
      default:
        return '📢';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-red-500';
      case 'normal':
        return 'bg-blue-500';
      case 'low':
        return 'bg-gray-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={`relative transition-colors ${
            theme === 'dark'
              ? 'text-[#B7BDC6] hover:text-white hover:bg-[#2B3139]'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
        >
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
            >
              {unreadCount > 99 ? '99+' : unreadCount}
            </Badge>
          )}
          {!isConnected && (
            <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></div>
          )}
        </Button>
      </PopoverTrigger>
      
      <PopoverContent
        className={`w-96 p-0 ${
          theme === 'dark'
            ? 'bg-[#1E2329] border-[#2B3139]'
            : 'bg-white border-gray-200'
        }`}
        align="end"
      >
        {/* Header */}
        <div className={`flex items-center justify-between p-4 border-b ${
          theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'
        }`}>
          <div className="flex items-center gap-2">
            <h3 className={`font-semibold ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Notifications
            </h3>
            {!isConnected && (
              <Badge variant="outline" className="text-xs">
                Offline
              </Badge>
            )}
          </div>
          
          <div className="flex items-center gap-1">
            {notifications.length > 0 && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  className="h-8 px-2"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-4 h-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearNotifications}
                  className="h-8 px-2"
                  title="Clear all"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsOpen(false)}
              className="h-8 px-2"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Notifications List */}
        <div className="max-h-96 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className={`p-8 text-center ${
              theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-500'
            }`}>
              <Bell className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p className="text-sm">No notifications yet</p>
              <p className="text-xs mt-1">You'll see crypto deposit and withdrawal updates here</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-[#2B3139]">
              {notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-4 transition-colors cursor-pointer ${
                    !notification.read
                      ? (theme === 'dark' ? 'bg-[#2B3139]/30' : 'bg-blue-50')
                      : ''
                  } ${
                    theme === 'dark'
                      ? 'hover:bg-[#2B3139]/50'
                      : 'hover:bg-gray-50'
                  }`}
                  onClick={() => handleNotificationClick(notification)}
                >
                  <div className="flex items-start gap-3">
                    {/* Icon and Priority Indicator */}
                    <div className="relative flex-shrink-0">
                      <div className="text-2xl">
                        {getNotificationIcon(notification.type)}
                      </div>
                      <div className={`absolute -top-1 -right-1 w-3 h-3 rounded-full ${
                        getPriorityColor(notification.priority)
                      }`}></div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className={`font-medium text-sm truncate ${
                          theme === 'dark' ? 'text-white' : 'text-gray-900'
                        }`}>
                          {notification.title}
                        </h4>
                        {!notification.read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0 ml-2"></div>
                        )}
                      </div>
                      
                      <p className={`text-xs mb-2 ${
                        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                      }`}>
                        {notification.message}
                      </p>

                      {/* Transaction Details */}
                      {notification.transaction && (
                        <div className={`text-xs space-y-1 mb-2 ${
                          theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-500'
                        }`}>
                          <div className="flex justify-between">
                            <span>Amount:</span>
                            <span className="font-mono">
                              {notification.transaction.amount} {notification.transaction.crypto_symbol}
                            </span>
                          </div>
                          {notification.transaction.confirmations !== undefined && (
                            <div className="flex justify-between">
                              <span>Confirmations:</span>
                              <span>
                                {notification.transaction.confirmations}
                                {notification.transaction.required_confirmations && 
                                  `/${notification.transaction.required_confirmations}`
                                }
                              </span>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Footer */}
                      <div className="flex items-center justify-between">
                        <span className={`text-xs ${
                          theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-400'
                        }`}>
                          {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
                        </span>
                        
                        <div className="flex items-center gap-2">
                          {notification.action_url && (
                            <Link href={notification.action_url}>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 px-2 text-xs"
                              >
                                <ExternalLink className="w-3 h-3 mr-1" />
                                View
                              </Button>
                            </Link>
                          )}
                          
                          {!notification.read && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                markAsRead(notification.id);
                              }}
                              className="h-6 px-2 text-xs"
                            >
                              <Check className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {notifications.length > 0 && (
          <div className={`p-3 border-t text-center ${
            theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'
          }`}>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => setIsOpen(false)}
            >
              View All Notifications
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
};

export default NotificationCenter;
