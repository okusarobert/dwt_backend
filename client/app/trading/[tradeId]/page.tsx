"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth/auth-provider";
import { toast } from "react-hot-toast";
import { 
  Loader2, 
  CheckCircle, 
  XCircle, 
  Clock, 
  ArrowLeft,
  Smartphone,
  CreditCard
} from "lucide-react";
import { apiClient } from "@/lib/api-client";
import { formatUGX, formatNumber } from '@/lib/currency-formatter';
import { websocketClient, TradeStatusUpdate } from '@/lib/websocket-client';

interface Trade {
  id: string;
  type: 'buy' | 'sell';
  crypto_currency: string;
  crypto_amount: number;
  fiat_amount: number;
  status: string;
  created_at: string;
  completed_at?: string;
  payment_url?: string;
  phone_number?: string;
}

interface TradeEvent {
  trade_id: string;
  status: string;
  message: string;
  timestamp: string;
  payment_url?: string;
}

export default function TradeWaitingPage() {
  const { user, isLoading: authLoading } = useAuth();
  const params = useParams();
  const router = useRouter();
  const tradeId = params.tradeId as string;

  const [trade, setTrade] = useState<Trade | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [events, setEvents] = useState<TradeEvent[]>([]);

  // Load trade details
  useEffect(() => {
    const loadTrade = async () => {
      if (!tradeId || tradeId === 'undefined') {
        console.error('Invalid trade ID:', tradeId);
        toast.error('Invalid trade ID');
        router.push('/trading');
        return;
      }
      
      try {
        console.log('Loading trade with ID:', tradeId);
        const tradeData = await apiClient.getTrade(tradeId);
        console.log('Trade data:', tradeData);
        setTrade(tradeData.data);
      } catch (error: any) {
        console.error('Failed to load trade:', error);
        toast.error('Failed to load trade details');
        router.push('/trading');
      } finally {
        setIsLoading(false);
      }
    };

    if (user && tradeId) {
      loadTrade();
    }
  }, [user, tradeId, router]);

  // WebSocket connection for trade updates
  useEffect(() => {
    if (!tradeId || !user) return;

    // Connect to WebSocket if not already connected
    if (!websocketClient.isConnected()) {
      websocketClient.connect();
    }

    // Set up connection status listener
    const unsubscribeConnection = websocketClient.onConnectionChange((connected) => {
      setWsConnected(connected);
      if (connected && tradeId) {
        // Join trade room when connected
        websocketClient.joinTradeRoom(tradeId);
      }
    });

    // Set up trade status update listener
    const unsubscribeTradeStatus = websocketClient.onTradeStatusUpdate((update: TradeStatusUpdate) => {
      try {
        console.log('🔔 Trade status update received:', update);
        
        const tradeEvent: TradeEvent = {
          type: update.type || 'status_update',
          message: update.data?.message || 'Trade status updated',
          timestamp: update.timestamp || new Date().toISOString(),
          status: update.data?.status
        };
        
        setEvents(prev => [...prev, tradeEvent]);
        
        // Update trade status
        if (update.data?.status && trade) {
          console.log('🔔 Updating trade status from', trade.status, 'to', update.data.status);
          setTrade(prev => prev ? { ...prev, status: update.data.status } : null);
        }

        // Show notifications for important status changes
        if (update.data?.status === 'completed') {
          toast.success('Trade completed successfully!');
        } else if (update.data?.status === 'failed') {
          toast.error('Trade failed: ' + (update.data?.message || 'Unknown error'));
        } else if (update.data?.status === 'processing') {
          toast.info('Trade is being processed...');
        }
      } catch (error) {
        console.error('Error processing trade event:', error);
      }
    });

    // Join trade room if already connected
    if (websocketClient.isConnected()) {
      setWsConnected(true);
      websocketClient.joinTradeRoom(tradeId);
    }

    return () => {
      // Leave trade room and cleanup
      websocketClient.leaveTradeRoom(tradeId);
      unsubscribeConnection();
      unsubscribeTradeStatus();
    };
  }, [tradeId, user, trade]);

  // Auto-redirect after completion
  useEffect(() => {
    if (trade?.status === 'completed') {
      // const timer = setTimeout(() => {
      //   router.push('/dashboard/transactions');
      // }, 5000);
      // return () => clearTimeout(timer);
    }
  }, [trade?.status, router]);

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!trade) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <Card className="w-full max-w-md">
          <CardContent className="p-6 text-center">
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Trade Not Found</h2>
            <p className="text-muted-foreground mb-4">
              The trade you're looking for doesn't exist or you don't have access to it.
            </p>
            <Button onClick={() => router.push('/trading')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Trading
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const getStatusIcon = () => {
    const statusStr = String(trade.status).toLowerCase();
    
    switch (statusStr) {
      case 'completed':
        return <CheckCircle className="w-8 h-8 text-green-500" />;
      case 'failed':
        return <XCircle className="w-8 h-8 text-red-500" />;
      case 'processing':
      case 'payment_pending':
        return <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-8 h-8 text-yellow-500" />;
    }
  };

  const getStatusText = () => {
    console.log('Status debug:', { status: trade.status, fullTrade: trade });
    const statusStr = String(trade.status).toLowerCase();
    
    switch (statusStr) {
      case 'completed':
        return 'Trade Completed Successfully';
      case 'failed':
        return 'Trade Failed';
      case 'processing':
        return 'Processing Trade...';
      case 'payment_pending':
        return 'Transaction Pending';
      case 'pending':
        return 'Trade Pending';
      default:
        return `Trade Status: ${trade.status || 'Unknown'}`;
    }
  };

  const getStatusDescription = () => {
    const statusStr = String(trade.status).toLowerCase();
    const tradeType = trade.type || trade.trade_type;
    
    switch (statusStr) {
      case 'completed':
        return 'Your trade has been completed successfully. You will be redirected to your transaction history shortly.';
      case 'failed':
        return 'Your trade could not be completed. Please try again or contact support if the issue persists.';
      case 'processing':
        return tradeType === 'buy' 
          ? 'We are processing your payment. Please complete the mobile money payment if prompted.'
          : 'We are processing your sell order. Your crypto will be debited once payment is confirmed.';
      case 'payment_pending':
        return tradeType === 'buy'
          ? 'Your payment is being processed. Please wait while we confirm your mobile money transaction.'
          : 'Your transaction is pending. We are waiting for payment confirmation.';
      case 'pending':
        return 'Your trade is in queue and will be processed shortly.';
      default:
        return `We are monitoring your trade status (${trade.status}).`;
    }
  };

  return (
    <div className="container mx-auto p-3 sm:p-4 max-w-2xl">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="space-y-4 sm:space-y-6"
      >
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push('/trading')}
            className="self-start"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Trading
          </Button>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-muted-foreground">
              {wsConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {/* Trade Status Card */}
        <Card>
          <CardHeader className="text-center px-4 sm:px-6">
            <div className="flex justify-center mb-4">
              {getStatusIcon()}
            </div>
            <CardTitle className="text-xl sm:text-2xl">{getStatusText()}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 sm:space-y-6 px-4 sm:px-6">
            <p className="text-center text-muted-foreground text-sm sm:text-base">
              {getStatusDescription()}
            </p>

            {/* Trade Details */}
            <div className="bg-muted/50 p-3 sm:p-4 rounded-lg space-y-3">
              <div className="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-0">
                <span className="font-medium text-sm sm:text-base">Type:</span>
                <span className="capitalize text-sm sm:text-base">
                  {(() => {
                    // Check all possible trade type fields
                    const tradeType = trade.type || trade.trade_type || (trade as any).tradeType;
                    console.log('Trade type debug:', { 
                      type: trade.type, 
                      trade_type: trade.trade_type, 
                      tradeType: (trade as any).tradeType,
                      resolved: tradeType,
                      fullTrade: trade 
                    });
                    
                    if (!tradeType) return 'Unknown (no type field)';
                    
                    const typeStr = String(tradeType).toLowerCase();
                    if (typeStr === 'buy') return 'Buy';
                    if (typeStr === 'sell') return 'Sell';
                    return `Unknown (${tradeType})`;
                  })()}
                </span>
              </div>
              <div className="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-0">
                <span className="font-medium text-sm sm:text-base">Crypto Amount:</span>
                <span className="text-sm sm:text-base font-mono">{formatNumber(trade.crypto_amount, 8)} {trade.crypto_currency}</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-0">
                <span className="font-medium text-sm sm:text-base">Fiat Amount:</span>
                <span className="text-sm sm:text-base font-semibold">{formatUGX(trade.fiat_amount)}</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-0">
                <span className="font-medium text-sm sm:text-base">Created:</span>
                <span className="text-sm sm:text-base">{new Date(trade.created_at).toLocaleString()}</span>
              </div>
              {trade.phone_number && (
                <div className="flex flex-col sm:flex-row sm:justify-between gap-1 sm:gap-0">
                  <span className="font-medium text-sm sm:text-base">Phone:</span>
                  <span className="text-sm sm:text-base">{trade.phone_number}</span>
                </div>
              )}
            </div>

            {/* Payment Button for Buy Orders */}
            {trade.type === 'buy' && trade.payment_url && trade.status === 'processing' && (
              <div className="text-center space-y-3 sm:space-y-4">
                <div className="flex items-center justify-center gap-2 text-blue-600">
                  <Smartphone className="w-4 h-4 sm:w-5 sm:h-5" />
                  <span className="font-medium text-sm sm:text-base">Complete Payment</span>
                </div>
                <Button
                  onClick={() => window.open(trade.payment_url, '_blank')}
                  className="w-full"
                  size="lg"
                >
                  <CreditCard className="w-4 h-4 mr-2" />
                  Open Mobile Money App
                </Button>
                <p className="text-xs sm:text-sm text-muted-foreground px-2">
                  Click the button above to complete your payment via mobile money
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
              {trade.status === 'completed' && (
                <Button
                  onClick={() => router.push('/dashboard/transactions')}
                  className="flex-1 text-sm sm:text-base"
                >
                  View Transactions
                </Button>
              )}
              {trade.status === 'failed' && (
                <Button
                  onClick={() => router.push('/trading')}
                  className="flex-1 text-sm sm:text-base"
                >
                  Try Again
                </Button>
              )}
              <Button
                variant="outline"
                onClick={() => router.push('/dashboard')}
                className="flex-1 text-sm sm:text-base"
              >
                Go to Dashboard
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Events Log */}
        {events.length > 0 && (
          <Card>
            <CardHeader className="px-4 sm:px-6">
              <CardTitle className="text-base sm:text-lg">Trade Events</CardTitle>
            </CardHeader>
            <CardContent className="px-4 sm:px-6">
              <div className="space-y-2 sm:space-y-3">
                {events.map((event, index) => (
                  <div key={index} className="flex items-start gap-2 sm:gap-3 p-2 sm:p-3 bg-muted/30 rounded-lg">
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-1 sm:mt-2 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-1 sm:gap-0">
                        <span className="font-medium capitalize text-sm sm:text-base">{event.status}</span>
                        <span className="text-xs text-muted-foreground">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      {event.message && (
                        <p className="text-xs sm:text-sm text-muted-foreground mt-1 break-words">{event.message}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </motion.div>
    </div>
  );
}
