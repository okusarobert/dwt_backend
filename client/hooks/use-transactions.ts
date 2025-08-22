import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface TransactionFilters {
  currency?: string;
  status?: string;
  type?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
}

export interface UseTransactionsOptions {
  limit?: number;
  offset?: number;
  filters?: TransactionFilters;
  enabled?: boolean;
}

// Query key factory for transactions
export const transactionKeys = {
  all: ['transactions'] as const,
  lists: () => [...transactionKeys.all, 'list'] as const,
  list: (filters: TransactionFilters, limit: number, offset: number) => 
    [...transactionKeys.lists(), { filters, limit, offset }] as const,
  details: () => [...transactionKeys.all, 'detail'] as const,
  detail: (id: number) => [...transactionKeys.details(), id] as const,
};

export function useTransactions({
  limit = 20,
  offset = 0,
  filters = {},
  enabled = true,
}: UseTransactionsOptions = {}) {
  return useQuery({
    queryKey: transactionKeys.list(filters, limit, offset),
    queryFn: async () => {
      const response = await apiClient.getTransactionHistory(limit, offset, filters);
      return response;
    },
    enabled,
    staleTime: 1000 * 60 * 2, // 2 minutes for transaction data
  });
}

export function useTransactionsPaginated(
  page: number,
  limit: number,
  filters: TransactionFilters = {}
) {
  const offset = (page - 1) * limit;
  
  return useQuery({
    queryKey: transactionKeys.list({ ...filters, page }, limit, offset),
    queryFn: async () => {
      const response = await apiClient.getTransactionHistory(
        limit, 
        offset, 
        { ...filters, page }
      );
      return response;
    },
    staleTime: 1000 * 60 * 2, // 2 minutes
    placeholderData: (previousData) => previousData, // Keep previous data while loading
  });
}

// Hook for recent transactions (used in wallet page)
export function useRecentTransactions(limit = 5) {
  return useQuery({
    queryKey: transactionKeys.list({}, limit, 0),
    queryFn: async () => {
      const response = await apiClient.getTransactionHistory(limit, 0);
      return response;
    },
    staleTime: 1000 * 30, // 30 seconds for recent transactions
  });
}

// Hook for single transaction details
export function useTransactionDetails(transactionId: number, enabled = true) {
  return useQuery({
    queryKey: transactionKeys.detail(transactionId),
    queryFn: async () => {
      const response = await apiClient.getTransactionDetails(transactionId);
      return response;
    },
    enabled: enabled && !!transactionId,
    staleTime: 1000 * 60 * 5, // 5 minutes for transaction details
  });
}

// Mutation for refreshing transactions
export function useRefreshTransactions() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async () => {
      // Invalidate all transaction queries
      await queryClient.invalidateQueries({
        queryKey: transactionKeys.all,
      });
      return true;
    },
  });
}
