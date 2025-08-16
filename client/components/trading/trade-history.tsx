"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowUpRight, ArrowDownLeft } from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { toast } from "react-hot-toast";

interface Trade {
  id: string;
  type: 'buy' | 'sell';
  crypto_currency: string;
  crypto_amount: number;
  fiat_amount: number;
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
      const result = await apiClient.getTradeHistory(limit, 0);
      setTrades(result.trades);
      setTotal(result.total);
    } catch (error: any) {
      console.error('Failed to load trade history:', error);
      toast.error('Failed to load trade history');
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
      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          Trade History
          {total > limit && (
            <span className="text-sm text-muted-foreground">
              Showing {trades.length} of {total}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {trades.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            No trades yet. Start trading to see your history here.
          </div>
        ) : (
          <div className="space-y-4">
            {trades.map((trade) => (
              <motion.div
                key={trade.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-full ${
                    trade.type === 'buy' 
                      ? 'bg-green-100 dark:bg-green-900' 
                      : 'bg-red-100 dark:bg-red-900'
                  }`}>
                    {trade.type === 'buy' ? (
                      <ArrowDownLeft className="w-4 h-4 text-green-600 dark:text-green-400" />
                    ) : (
                      <ArrowUpRight className="w-4 h-4 text-red-600 dark:text-red-400" />
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
                    {trade.type === 'buy' 
                      ? `+${trade.crypto_amount.toFixed(8)} ${trade.crypto_currency}`
                      : `+${trade.fiat_amount.toFixed(2)} UGX`
                    }
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {trade.type === 'buy' 
                      ? `-${trade.fiat_amount.toFixed(2)} UGX`
                      : `-${trade.crypto_amount.toFixed(8)} ${trade.crypto_currency}`
                    }
                  </div>
                </div>

                <Badge className={getStatusColor(trade.status)}>
                  {trade.status}
                </Badge>
              </motion.div>
            ))}
          </div>
        )}
        
        {total > limit && (
          <div className="text-center mt-4">
            <Button variant="outline" onClick={loadTradeHistory}>
              View All Trades
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
