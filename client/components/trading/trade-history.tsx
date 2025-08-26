"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, ArrowUpRight, ArrowDownLeft, RefreshCw, History, CheckCircle, Clock, XCircle, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { formatUGX, formatNumber } from '@/lib/currency-formatter';
import { toast } from "react-hot-toast";

interface Trade {
  id: string;
  type: 'buy' | 'sell';
  trade_type: string;
  crypto_currency: string;
  fiat_currency: string;
  crypto_amount: number;
  fiat_amount: number;
  total_amount: number;
  exchange_rate: number;
  fee_amount: number;
  status: string;
  payment_method: string;
  created_at: string;
  updated_at: string;
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
      // Map the response data to ensure all fields are present
      const mappedTrades = (response.trades || []).map((trade: any) => ({
        ...trade,
        // Ensure total_amount is available, fallback to fiat_amount
        total_amount: trade.total_amount || trade.fiat_amount || 0,
        // Ensure type is lowercase for consistency
        type: (trade.type || trade.trade_type || '').toLowerCase()
      }));
      setTrades(mappedTrades);
      setTotal(response.pagination?.total || response.total || mappedTrades.length);
    } catch (error: any) {
      console.error('Failed to load trade history:', error);
      toast.error('Failed to load trade history');
      setTrades([]);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />;
      case 'pending':
      case 'payment_pending':
        return <Clock className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-600 dark:text-red-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-600 dark:text-gray-400" />;
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
          <div className="space-y-4">
            {trades.map((trade) => (
              <div
                key={trade.id}
                className="border rounded-xl p-4 sm:p-6 hover:shadow-md transition-shadow bg-white dark:bg-gray-800"
              >
                {/* Mobile Layout */}
                <div className="sm:hidden">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3 flex-1">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                        trade.type === 'buy' 
                          ? 'bg-green-50 dark:bg-green-900/20' 
                          : 'bg-red-50 dark:bg-red-900/20'
                      }`}>
                        {trade.type === 'buy' ? (
                          <ArrowUpRight className="w-4 h-4 text-green-600 dark:text-green-400" />
                        ) : (
                          <ArrowDownLeft className="w-4 h-4 text-red-600 dark:text-red-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-xs truncate">
                          {trade.type === 'buy' ? 'Bought' : 'Sold'} {formatNumber(trade.crypto_amount, trade.crypto_currency === 'BTC' ? 8 : 6)} {trade.crypto_currency}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatDate(trade.created_at)}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-muted/30">
                      {getStatusIcon(trade.status)}
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-baseline">
                    <div className={`font-semibold text-xs ${
                      trade.type === 'buy' ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                    }`}>
                      {trade.type === 'buy' ? '-' : '+'}{formatUGX(trade.total_amount)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Rate: {formatUGX(trade.exchange_rate)}/{trade.crypto_currency}
                    </div>
                  </div>
                </div>

                {/* Desktop Layout */}
                <div className="hidden sm:block">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-4 flex-1">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${
                        trade.type === 'buy' 
                          ? 'bg-green-50 dark:bg-green-900/20' 
                          : 'bg-red-50 dark:bg-red-900/20'
                      }`}>
                        {trade.type === 'buy' ? (
                          <ArrowUpRight className="w-5 h-5 text-green-600 dark:text-green-400" />
                        ) : (
                          <ArrowDownLeft className="w-5 h-5 text-red-600 dark:text-red-400" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-xs truncate">
                          {trade.type === 'buy' ? 'Bought' : 'Sold'} {formatNumber(trade.crypto_amount, trade.crypto_currency === 'BTC' ? 8 : 6)} {trade.crypto_currency}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {formatDate(trade.created_at)}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-muted/30">
                      {getStatusIcon(trade.status)}
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-baseline">
                    <div className={`font-semibold text-xs ${
                      trade.type === 'buy' ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                    }`}>
                      {trade.type === 'buy' ? '-' : '+'}{formatUGX(trade.total_amount)}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Rate: {formatUGX(trade.exchange_rate)}/{trade.crypto_currency}
                    </div>
                  </div>
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
