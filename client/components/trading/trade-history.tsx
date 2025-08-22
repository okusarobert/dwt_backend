"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { History, RefreshCw } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { formatUGX, formatNumber } from '@/lib/currency-formatter';
import { toast } from "react-hot-toast";

interface Trade {
  id: string;
  type: 'buy' | 'sell';
  crypto_currency: string;
  crypto_amount: number;
  fiat_amount: number;
  total_amount: number;
  status: string;
  created_at: string;
  completed_at?: string;
}

interface TradeHistoryProps {
  limit?: number;
}

export function TradeHistory({ limit = 10 }: TradeHistoryProps) {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadTradeHistory();
  }, []);

  const loadTradeHistory = async () => {
    try {
      setIsLoading(true);
      const response = await apiClient.getTradeHistory(limit, 0);
      // Map the response data to include total_amount if missing
      const mappedTrades = (response.trades || []).map((trade: any) => ({
        ...trade,
        total_amount: trade.total_amount || trade.fiat_amount || 0
      }));
      setTrades(mappedTrades);
      setTotal(response.total || 0);
    } catch (error: any) {
      console.error('Failed to load trade history:', error);
      toast.error('Failed to load trade history');
      setTrades([]);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-base sm:text-lg">Trade History</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <RefreshCw className="w-5 h-5 sm:w-6 sm:h-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <span className="text-base sm:text-lg">Trade History</span>
          {total > limit && (
            <span className="text-xs sm:text-sm text-muted-foreground">
              Showing {trades.length} of {total}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-3 sm:px-6">
        {trades.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No trades yet</p>
            <p className="text-xs mt-1">Start trading to see your history here</p>
          </div>
        ) : (
          <div className="space-y-2 sm:space-y-3">
            {trades.map((trade) => (
              <div
                key={trade.id}
                className="border rounded-lg p-3 sm:p-4"
              >
                {/* Mobile Layout */}
                <div className="sm:hidden">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className={`p-1.5 rounded-full ${
                        trade.type === 'buy' 
                          ? 'bg-green-100 dark:bg-green-900' 
                          : 'bg-red-100 dark:bg-red-900'
                      }`}>
                        {trade.type === 'buy' ? (
                          <History className="w-3 h-3 text-green-600 dark:text-green-400" />
                        ) : (
                          <RefreshCw className="w-3 h-3 text-red-600 dark:text-red-400" />
                        )}
                      </div>
                      <span className="font-medium text-sm">
                        {trade.type === 'buy' ? 'Buy' : 'Sell'} {trade.crypto_currency}
                      </span>
                    </div>
                    <Badge className={`${getStatusColor(trade.status)} text-xs px-2 py-1`}>
                      {trade.status}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-end">
                    <div>
                      <div className="text-xs text-muted-foreground">
                        {formatDate(trade.created_at)}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {formatNumber(trade.crypto_amount, 6)} {trade.crypto_currency}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-sm">
                        {formatUGX(trade.total_amount)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Desktop Layout */}
                <div className="hidden sm:flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-full ${
                      trade.type === 'buy' 
                        ? 'bg-green-100 dark:bg-green-900' 
                        : 'bg-red-100 dark:bg-red-900'
                    }`}>
                      {trade.type === 'buy' ? (
                        <History className="w-4 h-4 text-green-600 dark:text-green-400" />
                      ) : (
                        <RefreshCw className="w-4 h-4 text-red-600 dark:text-red-400" />
                      )}
                    </div>
                    <div>
                      <div className="font-medium">
                        {trade.type === 'buy' ? 'Buy' : 'Sell'} {trade.crypto_currency}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {formatDate(trade.created_at)}
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="font-medium">
                      {formatUGX(trade.total_amount)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {formatNumber(trade.crypto_amount, 8)} {trade.crypto_currency}
                    </div>
                  </div>

                  <Badge className={getStatusColor(trade.status)}>
                    {trade.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {total > limit && (
          <div className="text-center mt-4">
            <Button variant="outline" size="sm" onClick={loadTradeHistory} className="text-sm">
              View All Trades
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
