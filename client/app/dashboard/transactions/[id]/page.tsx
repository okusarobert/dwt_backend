"use client";

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/components/auth/auth-provider";
import { useTheme } from "@/components/theme/theme-provider";
import { toast } from "react-hot-toast";
import { 
  ArrowLeft,
  ExternalLink,
  Copy,
  Calendar,
  Hash,
  Wallet,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
  RefreshCw
} from 'lucide-react';
import { formatCryptoAmount, formatNumber } from '@/lib/currency-formatter';
import { useTransactionDetails } from '@/hooks/use-transactions';

interface TransactionDetailsPageProps {}

const TransactionDetailsPage: React.FC<TransactionDetailsPageProps> = () => {
  const { user } = useAuth();
  const { theme } = useTheme();
  const router = useRouter();
  const params = useParams();
  const transactionId = parseInt(params.id as string);

  const {
    data: transactionData,
    isLoading,
    error,
    refetch
  } = useTransactionDetails(transactionId);


  const transaction = transactionData?.transaction;

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'bg-green-500/20 text-green-500';
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-500';
      case 'failed':
        return 'bg-red-500/20 text-red-500';
      default:
        return 'bg-gray-500/20 text-gray-500';
    }
  };

  const getTransactionAmount = () => {
    if (!transaction) return { amount: 0, currency: 'UGX' };
    
    const currency = transaction.metadata_json?.currency || transaction.account?.currency || 'UGX';
    let amount = parseFloat(transaction.amount || '0');
    
    if (transaction.metadata_json) {
      switch (currency.toUpperCase()) {
        case 'ETH':
          amount = parseFloat(transaction.metadata_json.amount_eth || transaction.amount || '0');
          break;
        case 'TRX':
          amount = parseFloat(transaction.metadata_json.amount_trx || transaction.amount || '0');
          break;
        case 'BTC':
          amount = parseFloat(transaction.metadata_json.amount_btc || transaction.amount || '0');
          break;
        default:
          amount = parseFloat(transaction.amount || '0');
      }
    }
    
    return { amount, currency };
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  const getBlockchainExplorerUrl = (txid: string, currency: string) => {
    const explorers: Record<string, string> = {
      BTC: `https://blockstream.info/tx/${txid}`,
      ETH: `https://etherscan.io/tx/${txid}`,
      TRX: `https://tronscan.org/#/transaction/${txid}`,
      SOL: `https://solscan.io/tx/${txid}`,
      BNB: `https://bscscan.com/tx/${txid}`,
    };
    
    return explorers[currency.toUpperCase()] || `https://blockstream.info/tx/${txid}`;
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Please log in</h2>
          <p className="text-gray-600">You need to be logged in to view transaction details.</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (error || !transaction) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">
          <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold mb-2">Transaction Not Found</h2>
          <p className="text-gray-600 mb-4">The requested transaction could not be found or you don't have permission to view it.</p>
          <Button onClick={() => router.push('/dashboard/transactions')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Transactions
          </Button>
        </div>
      </div>
    );
  }

  const { amount, currency } = getTransactionAmount();
  const isDeposit = transaction.type?.toLowerCase() === 'deposit';
  const isWithdrawal = transaction.type?.toLowerCase() === 'withdrawal';
  const date = new Date(transaction.created_at);

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => router.push('/dashboard/transactions')}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Transactions
          </Button>
          <div>
            <h1 className={`text-3xl font-bold ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              Transaction Details
            </h1>
            <p className={`text-sm mt-1 ${
              theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
            }`}>
              {transaction.blockchain_txid ? (
                <>Transaction Hash: {transaction.blockchain_txid.slice(0, 16)}...{transaction.blockchain_txid.slice(-8)}</>
              ) : (
                'Internal Transaction'
              )}
            </p>
          </div>
        </div>
        <Button
          onClick={() => refetch()}
          variant="outline"
          size="sm"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Transaction Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Transaction Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {isDeposit ? (
                  <TrendingUp className="h-5 w-5 text-green-500" />
                ) : isWithdrawal ? (
                  <TrendingDown className="h-5 w-5 text-red-500" />
                ) : (
                  <Wallet className="h-5 w-5" />
                )}
                Transaction Overview
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">Type</label>
                  <div className="mt-1">
                    <Badge variant={isDeposit ? 'default' : isWithdrawal ? 'destructive' : 'secondary'}>
                      {transaction.type?.charAt(0).toUpperCase() + transaction.type?.slice(1)}
                    </Badge>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Status</label>
                  <div className="mt-1 flex items-center gap-2">
                    {getStatusIcon(transaction.status)}
                    <Badge className={getStatusColor(transaction.status)}>
                      {transaction.status?.charAt(0).toUpperCase() + transaction.status?.slice(1)}
                    </Badge>
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Amount</label>
                  <div className={`mt-1 text-lg font-semibold ${
                    isDeposit ? 'text-green-500' : isWithdrawal ? 'text-red-500' : ''
                  }`}>
                    {isDeposit ? '+' : isWithdrawal ? '-' : ''}{formatNumber(amount, currency === 'BTC' ? 8 : 6)} {currency}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-500">Currency</label>
                  <div className="mt-1 text-lg font-medium">
                    {currency}
                  </div>
                </div>
              </div>
              
              {transaction.description && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Description</label>
                  <div className="mt-1 text-sm">
                    {transaction.description}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Blockchain Information */}
          {(transaction.blockchain_txid || transaction.address) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Hash className="h-5 w-5" />
                  Blockchain Information
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {transaction.blockchain_txid && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Transaction Hash</label>
                    <div className="mt-1 flex items-center gap-2">
                      <code className="text-sm bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded flex-1 break-all">
                        {transaction.blockchain_txid}
                      </code>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(transaction.blockchain_txid, 'Transaction hash')}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.open(getBlockchainExplorerUrl(transaction.blockchain_txid, currency), '_blank')}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
                
                {transaction.address && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Address</label>
                    <div className="mt-1 flex items-center gap-2">
                      <code className="text-sm bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded flex-1 break-all">
                        {transaction.address}
                      </code>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(transaction.address, 'Address')}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}

                {transaction.confirmations !== undefined && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-500">Confirmations</label>
                      <div className="mt-1 text-lg font-medium">
                        {transaction.confirmations || 0}
                      </div>
                    </div>
                    {transaction.required_confirmations && (
                      <div>
                        <label className="text-sm font-medium text-gray-500">Required Confirmations</label>
                        <div className="mt-1 text-lg font-medium">
                          {transaction.required_confirmations}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Additional Metadata */}
          {transaction.metadata_json && Object.keys(transaction.metadata_json).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Additional Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {transaction.metadata_json.from_address && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">From Address</label>
                      <div className="mt-1">
                        <code className="text-sm bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded break-all">
                          {transaction.metadata_json.from_address}
                        </code>
                      </div>
                    </div>
                  )}
                  {transaction.metadata_json.to_address && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">To Address</label>
                      <div className="mt-1">
                        <code className="text-sm bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded break-all">
                          {transaction.metadata_json.to_address}
                        </code>
                      </div>
                    </div>
                  )}
                  {transaction.metadata_json.block_number && (
                    <div>
                      <label className="text-sm font-medium text-gray-500">Block Number</label>
                      <div className="mt-1 text-lg font-medium">
                        {transaction.metadata_json.block_number}
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                Timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Created</label>
                <div className="mt-1 text-sm">
                  {date.toLocaleString('en-CA', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                  })}
                </div>
              </div>
              
              {transaction.updated_at && transaction.updated_at !== transaction.created_at && (
                <div>
                  <label className="text-sm font-medium text-gray-500">Last Updated</label>
                  <div className="mt-1 text-sm">
                    {new Date(transaction.updated_at).toLocaleString('en-CA', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                      hour12: false
                    })}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Account Information */}
          {transaction.account && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wallet className="h-5 w-5" />
                  Account
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-gray-500">Currency</label>
                  <div className="mt-1 text-sm">
                    {transaction.account.currency}
                  </div>
                </div>
                {transaction.account.account_type && (
                  <div>
                    <label className="text-sm font-medium text-gray-500">Account Type</label>
                    <div className="mt-1 text-sm">
                      {transaction.account.account_type}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Fee Information */}
          {transaction.fee_amount && (
            <Card>
              <CardHeader>
                <CardTitle>Network Fee</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-lg font-medium">
                  {transaction.fee_amount} {currency}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default TransactionDetailsPage;
