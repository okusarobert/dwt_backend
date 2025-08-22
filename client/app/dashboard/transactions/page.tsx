"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/components/auth/auth-provider";
import { useTheme } from "@/components/theme/theme-provider";
import { toast } from "react-hot-toast";
import { useRouter, useSearchParams } from 'next/navigation';
import { 
  Search, 
  Filter, 
  Download, 
  Calendar,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Eye,
  ExternalLink,
  ArrowUp,
  ArrowDown
} from 'lucide-react';
import { formatCryptoAmount } from '@/lib/currency-formatter';
import { useTransactionsPaginated, useRefreshTransactions, type TransactionFilters } from '@/hooks/use-transactions';

interface Transaction {
  id: number;
  type: string;
  amount: string;
  amount_smallest_unit: string;
  currency?: string;
  status: string;
  created_at: string;
  updated_at: string;
  description?: string;
  blockchain_txid?: string;
  address?: string;
  metadata_json?: {
    currency?: string;
    amount_eth?: string;
    amount_trx?: string;
    amount_btc?: string;
    from_address?: string;
    to_address?: string;
    block_number?: number;
  };
}

interface TransactionFiltersState {
  currency: string;
  status: string;
  type: string;
  dateFrom: string;
  dateTo: string;
  search: string;
}

const TransactionHistoryPage = () => {
  const { user } = useAuth();
  const { theme } = useTheme();
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Initialize state from URL parameters
  const [currentPage, setCurrentPage] = useState(() => 
    parseInt(searchParams.get('page') || '1')
  );
  const [limit, setLimit] = useState(() => 
    parseInt(searchParams.get('limit') || '20')
  );
  const [filters, setFilters] = useState<TransactionFiltersState>(() => ({
    currency: searchParams.get('currency') || 'all',
    status: searchParams.get('status') || 'all',
    type: searchParams.get('type') || 'all',
    dateFrom: searchParams.get('date_from') || '',
    dateTo: searchParams.get('date_to') || '',
    search: searchParams.get('search') || ''
  }));
  
  const [sortBy, setSortBy] = useState<'created_at' | 'amount' | 'status'>(() => 
    (searchParams.get('sort_by') as 'created_at' | 'amount' | 'status') || 'created_at'
  );
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(() => 
    (searchParams.get('sort_order') as 'asc' | 'desc') || 'desc'
  );

  // Convert filters to TanStack Query format
  const queryFilters: TransactionFilters = {
    ...(filters.currency !== 'all' && { currency: filters.currency }),
    ...(filters.status !== 'all' && { status: filters.status }),
    ...(filters.type !== 'all' && { type: filters.type }),
    ...(filters.dateFrom && { date_from: filters.dateFrom }),
    ...(filters.dateTo && { date_to: filters.dateTo }),
    ...(filters.search && { search: filters.search }),
    sort_by: sortBy,
    sort_order: sortOrder,
  };

  // Use TanStack Query for data fetching
  const {
    data: transactionData,
    isLoading,
    error,
    refetch
  } = useTransactionsPaginated(currentPage, limit, queryFilters);

  const refreshMutation = useRefreshTransactions();

  // Update URL when state changes
  const updateURL = (newState: {
    page?: number;
    limit?: number;
    filters?: Partial<TransactionFiltersState>;
    sortBy?: string;
    sortOrder?: string;
  }) => {
    const params = new URLSearchParams();
    
    // Set pagination
    params.set('page', (newState.page || currentPage).toString());
    params.set('limit', (newState.limit || limit).toString());
    
    // Set filters
    const currentFilters = { ...filters, ...newState.filters };
    if (currentFilters.currency !== 'all') params.set('currency', currentFilters.currency);
    if (currentFilters.status !== 'all') params.set('status', currentFilters.status);
    if (currentFilters.type !== 'all') params.set('type', currentFilters.type);
    if (currentFilters.dateFrom) params.set('date_from', currentFilters.dateFrom);
    if (currentFilters.dateTo) params.set('date_to', currentFilters.dateTo);
    if (currentFilters.search) params.set('search', currentFilters.search);
    
    // Set sorting
    params.set('sort_by', newState.sortBy || sortBy);
    params.set('sort_order', newState.sortOrder || sortOrder);
    
    router.push(`/dashboard/transactions?${params.toString()}`, { scroll: false });
  };

  // Supported currencies for filter
  const currencies = ['BTC', 'ETH', 'SOL', 'BNB', 'USDT', 'USDC', 'TRX', 'UGX'];
  const statuses = ['completed', 'pending', 'failed'];
  const types = ['deposit', 'withdrawal', 'transfer'];

  // Extract data from TanStack Query response
  const transactions = transactionData?.transactions || [];
  const pagination = transactionData?.pagination || {
    page: currentPage,
    limit,
    total_count: 0,
    total_pages: 0,
    has_next: false,
    has_prev: false
  };

  const handleFilterChange = (key: keyof TransactionFiltersState, value: string) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    setCurrentPage(1);
    updateURL({ page: 1, filters: { [key]: value } });
  };

  const handlePageSizeChange = (newLimit: number) => {
    setLimit(newLimit);
    setCurrentPage(1);
    updateURL({ page: 1, limit: newLimit });
  };

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    updateURL({ page: newPage });
  };

  const applyFilters = () => {
    setCurrentPage(1);
    updateURL({ page: 1 });
  };

  const clearFilters = () => {
    const clearedFilters = {
      currency: 'all',
      status: 'all',
      type: 'all',
      dateFrom: '',
      dateTo: '',
      search: ''
    };
    setFilters(clearedFilters);
    setCurrentPage(1);
    updateURL({ page: 1, filters: clearedFilters });
  };

  const handleSort = (column: 'created_at' | 'amount' | 'status') => {
    let newSortOrder: 'asc' | 'desc';
    if (sortBy === column) {
      newSortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      newSortOrder = 'desc';
    }
    setSortBy(column);
    setSortOrder(newSortOrder);
    updateURL({ sortBy: column, sortOrder: newSortOrder });
  };

  const getTransactionAmount = (transaction: Transaction) => {
    const currency = transaction.metadata_json?.currency || transaction.currency || 'UGX';
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

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'bg-green-500/20 text-green-500';
      case 'pending':
      case 'awaiting_confirmation':
        return 'bg-yellow-500/20 text-yellow-500';
      case 'failed':
        return 'bg-red-500/20 text-red-500';
      default:
        return 'bg-gray-500/20 text-gray-500';
    }
  };

  const handleRefresh = async () => {
    try {
      await refreshMutation.mutateAsync();
      toast.success('Transactions refreshed');
    } catch (error) {
      toast.error('Failed to refresh transactions');
    }
  };

  const exportTransactions = () => {
    // TODO: Implement CSV export
    toast.success('Export feature coming soon!');
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold mb-2">Please log in</h2>
          <p className="text-gray-600">You need to be logged in to view transaction history.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className={`text-3xl font-bold ${
            theme === 'dark' ? 'text-white' : 'text-gray-900'
          }`}>
            Transaction History
          </h1>
          <p className={`text-sm mt-1 ${
            theme === 'dark' ? 'text-gray-400' : 'text-gray-600'
          }`}>
            View and manage all your transactions
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={isLoading || refreshMutation.isPending}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading || refreshMutation.isPending ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={exportTransactions}
            variant="outline"
            size="sm"
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Currency</label>
              <Select value={filters.currency} onValueChange={(value) => handleFilterChange('currency', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="All currencies" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All currencies</SelectItem>
                  {currencies.map(currency => (
                    <SelectItem key={currency} value={currency}>{currency}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <Select value={filters.status} onValueChange={(value) => handleFilterChange('status', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {statuses.map(status => (
                    <SelectItem key={status} value={status}>
                      {status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ')}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Type</label>
              <Select value={filters.type} onValueChange={(value) => handleFilterChange('type', value)}>
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  {types.map(type => (
                    <SelectItem key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <label className="text-sm font-medium mb-2 block">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search transactions..."
                  value={filters.search}
                  onChange={(e) => handleFilterChange('search', e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-sm font-medium mb-2 block">From Date</label>
              <Input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange('dateFrom', e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">To Date</label>
              <Input
                type="date"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange('dateTo', e.target.value)}
              />
            </div>
          </div>
          
          <div className="flex gap-2">
            <Button onClick={applyFilters} disabled={isLoading}>
              Apply Filters
            </Button>
            <Button onClick={clearFilters} variant="outline">
              Clear All
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Transactions Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              Transactions ({pagination.total_count})
            </CardTitle>
            <div className="text-sm text-gray-500">
              Page {pagination.page} of {pagination.total_pages}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : transactions.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No transactions found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className={theme === 'dark' ? 'bg-gray-800' : 'bg-gray-50'}>
                  <tr>
                    <th className="text-left py-3 px-4 font-medium">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSort('created_at')}
                        className="h-auto p-0 font-medium"
                      >
                        Date & Time
                        <ArrowUpDown className="ml-2 h-4 w-4" />
                      </Button>
                    </th>
                    <th className="text-left py-3 px-4 font-medium">Type</th>
                    <th className="text-right py-3 px-4 font-medium">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSort('amount')}
                        className="h-auto p-0 font-medium"
                      >
                        Amount
                        <ArrowUpDown className="ml-2 h-4 w-4" />
                      </Button>
                    </th>
                    <th className="text-center py-3 px-4 font-medium">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSort('status')}
                        className="h-auto p-0 font-medium"
                      >
                        Status
                        <ArrowUpDown className="ml-2 h-4 w-4" />
                      </Button>
                    </th>
                    <th className="text-left py-3 px-4 font-medium">Description</th>
                    <th className="text-center py-3 px-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((transaction, index) => {
                    const { amount, currency } = getTransactionAmount(transaction);
                    const isDeposit = transaction.type?.toLowerCase() === 'deposit';
                    const isWithdrawal = transaction.type?.toLowerCase() === 'withdrawal';
                    const date = new Date(transaction.created_at);
                    
                    return (
                      <tr 
                        key={transaction.id} 
                        className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors"
                        onClick={() => router.push(`/dashboard/transactions/${transaction.id}`)}
                      >
                        <td className="py-4 px-4 text-sm">
                          {date.toLocaleDateString('en-CA')} {date.toLocaleTimeString('en-CA', { hour12: false, hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="py-4 px-4">
                          <Badge variant={
                            isDeposit ? 'default' : 
                            isWithdrawal ? 'destructive' : 
                            'secondary'
                          }>
                            {transaction.type?.charAt(0).toUpperCase() + transaction.type?.slice(1)}
                          </Badge>
                        </td>
                        <td className="py-4 px-4 text-sm font-medium text-center">
                          <span className={isDeposit ? 'text-green-600' : isWithdrawal ? 'text-red-600' : ''}>
                            {isDeposit ? '+' : isWithdrawal ? '-' : ''}{formatCryptoAmount(amount, currency)} {currency}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-center">
                          <Badge className={
                            transaction.status === 'completed' ? 'bg-green-500/20 text-green-500' :
                            transaction.status === 'pending' ? 'bg-yellow-500/20 text-yellow-500' :
                            transaction.status === 'failed' ? 'bg-red-500/20 text-red-500' :
                            'bg-gray-500/20 text-gray-500'
                          }>
                            {transaction.status?.charAt(0).toUpperCase() + transaction.status?.slice(1)}
                          </Badge>
                        </td>
                        <td className="py-4 px-4 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">
                          {transaction.description || '-'}
                        </td>
                        <td className="py-4 px-4 text-center">
                          <div className="flex items-center justify-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/dashboard/transactions/${transaction.id}`);
                              }}
                              className="h-8 w-8 p-0"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            {transaction.blockchain_txid && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  const explorers: Record<string, string> = {
                                    BTC: `https://blockstream.info/tx/${transaction.blockchain_txid}`,
                                    ETH: `https://etherscan.io/tx/${transaction.blockchain_txid}`,
                                    TRX: `https://tronscan.org/#/transaction/${transaction.blockchain_txid}`,
                                    SOL: `https://solscan.io/tx/${transaction.blockchain_txid}`,
                                    BNB: `https://bscscan.com/tx/${transaction.blockchain_txid}`,
                                  };
                                  const url = explorers[currency.toUpperCase()] || `https://blockstream.info/tx/${transaction.blockchain_txid}`;
                                  window.open(url, '_blank');
                                }}
                                className="h-8 w-8 p-0"
                              >
                                <ExternalLink className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          
          {/* Enhanced Pagination */}
          <div className="flex flex-col sm:flex-row items-center justify-between mt-6 gap-4">
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-500">
                Showing {((pagination.page - 1) * pagination.limit) + 1} to {Math.min(pagination.page * pagination.limit, pagination.total_count)} of {pagination.total_count} transactions
              </div>
              
              {/* Page Size Selector */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">Show:</span>
                <Select value={limit.toString()} onValueChange={(value) => handlePageSizeChange(parseInt(value))}>
                  <SelectTrigger className="w-20">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="20">20</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                    <SelectItem value="100">100</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Pagination Controls */}
            {pagination.total_pages > 1 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(1)}
                  disabled={pagination.page === 1 || isLoading}
                >
                  First
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={!pagination.has_prev || isLoading}
                >
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Previous
                </Button>
                
                {/* Page Numbers */}
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(5, pagination.total_pages) }, (_, i) => {
                    let pageNum;
                    if (pagination.total_pages <= 5) {
                      pageNum = i + 1;
                    } else if (pagination.page <= 3) {
                      pageNum = i + 1;
                    } else if (pagination.page >= pagination.total_pages - 2) {
                      pageNum = pagination.total_pages - 4 + i;
                    } else {
                      pageNum = pagination.page - 2 + i;
                    }
                    
                    return (
                      <Button
                        key={pageNum}
                        variant={pageNum === pagination.page ? "default" : "outline"}
                        size="sm"
                        className="w-8 h-8 p-0"
                        onClick={() => handlePageChange(pageNum)}
                        disabled={isLoading}
                      >
                        {pageNum}
                      </Button>
                    );
                  })}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={!pagination.has_next || isLoading}
                >
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePageChange(pagination.total_pages)}
                  disabled={pagination.page === pagination.total_pages || isLoading}
                >
                  Last
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default TransactionHistoryPage;
