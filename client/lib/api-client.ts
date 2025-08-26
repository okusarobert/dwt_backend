import axios, { AxiosInstance, AxiosResponse } from "axios";
import { cookieAuth } from "./cookie-auth";

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  country?: string;
  phone_number?: string;
  ref_code?: string;
  created_at?: string;
  balance?: number;
  currency?: string;
  locked_amount?: number;
  max_deposit?: number;
  min_deposit?: number;
  // Admin flags (optional on many endpoints)
  blocked?: boolean;
  deleted?: boolean;
}

export interface AuthResponse {
  message?: string;
  user?: User;
  token?: string;
  redirect?: string;
  requires_verification?: boolean;
  // For registration, backend returns user data with verification requirements
  // For login, backend returns user data
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  password: string;
  password_confirm: string;
  sponsor_code?: string;
  country?: string;
}

class ApiClient {
  private authClient: AxiosInstance;
  private walletClient: AxiosInstance;
  private adminClient: AxiosInstance;

  constructor() {
    // Auth service client
    this.authClient = axios.create({
      baseURL: `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1`,
      withCredentials: true,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Wallet service client
    this.walletClient = axios.create({
      baseURL: `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1`,
      withCredentials: true,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Admin routes share same base; endpoints start with /admin
    this.adminClient = this.walletClient;

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Add auth header interceptor
    this.authClient.interceptors.request.use(
      async (config) => {
        // For HTTP-only cookies, we don't need to manually add headers
        // The browser will automatically include cookies
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Reuse same interceptors for admin client if ever separated

    this.walletClient.interceptors.request.use(
      async (config) => {
        // For HTTP-only cookies, we don't need to manually add headers
        // The browser will automatically include cookies
      return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Handle response errors
    this.authClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Clear auth state on 401
          await cookieAuth.removeAuthCookie();
        } else if (error.response?.status === 403 && error.response?.data?.redirect === '/auth/verify-email') {
          // Handle email verification required - but avoid redirect loop
          console.log('Email verification required, redirecting...');
          // Only redirect if we're not already on the verify-email page
          if (typeof window !== 'undefined' && !window.location.pathname.includes('/auth/verify-email')) {
            window.location.href = '/auth/verify-email';
          }
          return Promise.reject(new Error('Email verification required'));
        }
        return Promise.reject(error);
      }
    );

    this.walletClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          // Clear auth state on 401
          await cookieAuth.removeAuthCookie();
        } else if (error.response?.status === 403 && error.response?.data?.redirect === '/auth/verify-email') {
          // Handle email verification required
          console.log('Email verification required, redirecting...');
          window.location.href = '/auth/verify-email';
          return Promise.reject(new Error('Email verification required'));
        }
        return Promise.reject(error);
      }
    );
  }

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.authClient.post(
      "/login",
      credentials
    );
    return response.data;
  }

  async register(userData: RegisterRequest): Promise<AuthResponse> {
    try {
      const response: AxiosResponse<AuthResponse> = await this.authClient.post(
        "/register",
        userData
      );

      // Backend now returns user data with verification requirements
      return response.data;
    } catch (error: any) {
      console.error("Registration failed:", error);
      
      // Handle validation errors
      if (error.response?.status === 400 && error.response?.data) {
        // Convert backend errors to a string for the form to parse
        throw new Error(JSON.stringify(error.response.data));
      }
      
      throw error;
    }
  }

  async logout(): Promise<boolean> {
    try {
      await this.authClient.post("/logout");
      await cookieAuth.removeAuthCookie();
      return true;
    } catch (error) {
      console.error("Logout failed:", error);
      return false;
    }
  }

  async isAuthenticated(): Promise<boolean> {
    return await cookieAuth.isAuthenticated();
  }

  async getCurrentUser(): Promise<User | null> {
    try {
      const decodedToken = await cookieAuth.getDecodedToken();
      if (decodedToken) {
        // Return basic user info from token
        return {
          id: decodedToken.user_id,
          email: "", // Not available in token
          first_name: "", // Not available in token
          last_name: "", // Not available in token
          role: "user", // Default role
        };
      }
      return null;
    } catch (error) {
      console.error("Failed to get current user:", error);
      return null;
    }
  }

  async getUserConfig(): Promise<User | null> {
    try {
      const response: AxiosResponse<{ user: User }> = await this.authClient.get("/user-config");
      return response.data.user;
    } catch (error) {
      console.error("Failed to get user config:", error);
      return null;
    }
  }

  async getVerificationInfo(): Promise<{ email: string; verified: boolean }> {
    const response = await this.authClient.get("/verification-info");
    return response.data;
  }

  async verifyEmail(code: string, email: string): Promise<{ message: string }> {
    const response: AxiosResponse<{ message: string }> = await this.authClient.post(
      "/verify-email",
      { code, email }
    );
    return response.data;
  }

  async resendVerification(email: string): Promise<{ message: string }> {
    const response: AxiosResponse<{ message: string }> = await this.authClient.post(
      "/resend-verification",
      { email }
    );
    return response.data;
  }

  // Wallet-specific methods
  async getDashboardSummary(): Promise<any> {
    const response = await this.walletClient.get("/wallet/dashboard/summary");
    return response.data;
  }

  async getWalletBalance(): Promise<any> {
    const response = await this.walletClient.get("/wallet/balance");
    return response.data;
  }

  async getTransactionHistory(
    limit = 5, 
    offset = 0, 
    filters?: {
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
  ): Promise<any> {
    const params: any = { limit, offset };
    
    if (filters) {
      if (filters.currency) params.currency = filters.currency;
      if (filters.status) params.status = filters.status;
      if (filters.type) params.type = filters.type;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      if (filters.search) params.search = filters.search;
      if (filters.sort_by) params.sort_by = filters.sort_by;
      if (filters.sort_order) params.sort_order = filters.sort_order;
      if (filters.page) params.page = filters.page;
    }
    
    const response = await this.walletClient.get("/wallet/transactions", {
      params,
    });
    return response.data;
  }

  async getTransactionDetails(transactionId: number): Promise<any> {
    const response = await this.walletClient.get(`/wallet/transactions/${transactionId}`);
    return response.data;
  }

  async getUserPnL(currency?: string, periodDays: number = 1): Promise<any> {
    const params = new URLSearchParams();
    if (currency) params.append('currency', currency);
    params.append('period_days', periodDays.toString());
    
    const response = await this.walletClient.get(`/wallet/pnl?${params}`);
    return response.data;
  }

  async getPortfolioSummary(): Promise<any> {
    const response = await this.walletClient.get('/wallet/portfolio-summary');
    return response.data;
  }

  // ------------------------------
  // Admin: Users
  // ------------------------------
  async adminListUsers(params?: {
    q?: string;
    role?: string;
    blocked?: boolean;
    deleted?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<{ success: boolean; data: User[]; pagination: { page: number; page_size: number; total: number } }> {
    // Map UI params to backend params
    const mapped: any = { ...(params || {}) };
    if (mapped.blocked !== undefined) {
      mapped.is_blocked = mapped.blocked;
      delete mapped.blocked;
    }
    if (mapped.deleted !== undefined) {
      mapped.is_deleted = mapped.deleted;
      delete mapped.deleted;
    }

    const response = await this.adminClient.get("/admin/users", {
      params: mapped,
    });
    return response.data;
  }

  async adminUpdateUser(
    userId: number,
    body: {
      first_name?: string;
      last_name?: string;
      email?: string;
      phone?: string;
      role?: string;
      is_blocked?: boolean;
      is_deleted?: boolean;
    }
  ): Promise<{ success: boolean; data: User }> {
    // Convert role to uppercase if provided
    if (body.role) {
      body.role = String(body.role).toUpperCase();
    }
    const response = await this.adminClient.patch(`/admin/users/${userId}`, body);
    return { success: true, data: response.data };
  }

  // =============================
  async getReserveStatus(): Promise<any> {
    const response = await this.walletClient.get("/wallet/reserves/status");
    const data = response.data;
    const reserves = data?.reserves;

    // Always normalize to simple array shape for the UI
    const items: Array<{
      currency: string;
      accounts: Array<{ account_type: string; balance: number; available?: number; locked?: number }>;
    }> = [];

    if (Array.isArray(reserves)) {
      // Backend already returns array; coerce account entries
      for (const entry of reserves) {
        const currency = String((entry as any)?.currency ?? "");
        const accs: any[] = Array.isArray((entry as any)?.accounts) ? (entry as any).accounts : [];
        const simpleAccs = accs.map((acc) => {
          const i: any = acc || {};
          const account_type = String((i.account_type ?? i.type ?? "")).toUpperCase();
          const balance =
            typeof i.total_balance === "number" ? i.total_balance :
            typeof i.available_balance === "number" ? i.available_balance :
            typeof i.balance === "number" ? i.balance : 0;
          const available = typeof i.available_balance === "number" ? i.available_balance : undefined;
          const locked = typeof i.locked_balance === "number" ? i.locked_balance : undefined;
          return { account_type, balance, available, locked };
        });
        items.push({ currency, accounts: simpleAccs });
      }
    } else {
      // Normalize from grouped object shape { crypto: {CUR: info}, fiat: {CUR: info} }
      const pushFromGroup = (group: any, accountType: string) => {
        if (!group || typeof group !== "object") return;
        Object.entries(group).forEach(([currency, info]) => {
          const i: any = info || {};
          const balance =
            typeof i.total_balance === "number" ? i.total_balance :
            typeof i.available_balance === "number" ? i.available_balance :
            typeof i.balance === "number" ? i.balance : 0;
          const available = typeof i.available_balance === "number" ? i.available_balance : undefined;
          const locked = typeof i.locked_balance === "number" ? i.locked_balance : undefined;

          let item = items.find((x) => x.currency === currency);
          if (!item) {
            item = { currency, accounts: [] };
            items.push(item);
          }
          item.accounts.push({ account_type: accountType, balance, available, locked });
        });
      };

      pushFromGroup(reserves?.crypto, "CRYPTO");
      pushFromGroup(reserves?.fiat, "FIAT");
    }

    return { success: data?.success ?? true, reserves: items };
  }

  async getReserveBalance(
    currency: string,
    accountType: string
  ): Promise<any> {
    const response = await this.walletClient.get(
      `/wallet/reserves/${currency}/${accountType}/balance`
    );
    const data = response.data || {};
    const b = (data as any).balance;
    let numeric = 0;
    if (typeof b === "number") {
      numeric = b;
    } else if (b && typeof b === "object") {
      const i: any = b;
      if (typeof i.total_balance === "number") numeric = i.total_balance;
      else if (typeof i.available_balance === "number") numeric = i.available_balance;
      else if (typeof i.balance === "number") numeric = i.balance;
    }
    return { success: Boolean((data as any).success), balance: numeric };
  }

  async topUpReserve(
    currency: string,
    accountType: string,
    amount: number,
    source_reference?: string
  ): Promise<any> {
    const response = await this.walletClient.post(
      `/wallet/reserves/${currency}/${accountType}/topup`,
      { amount, source_reference }
    );
    return response.data;
  }

  async withdrawFromReserve(
    currency: string,
    accountType: string,
    amount: number,
    destination_reference?: string
  ): Promise<any> {
    const response = await this.walletClient.post(
      `/wallet/reserves/${currency}/${accountType}/withdraw`,
      { amount, destination_reference }
    );
    return response.data;
  }

  async getReserveAnalytics(period_days = 30): Promise<any> {
    const response = await this.walletClient.get(
      `/wallet/reserves/analytics`,
      { params: { period_days } }
    );
    return response.data;
  }

  async clearReserveCache(): Promise<any> {
    const response = await this.walletClient.post(
      "/wallet/reserves/cache/clear"
    );
    return response.data;
  }

  // Get crypto balances for user (now with aggregation)
  async getCryptoBalances(): Promise<{
    balances: Record<string, any>;
    total_value_ugx: number;
    total_value_usd: number;
    portfolio_breakdown?: Record<string, any>;
  }> {
    const response = await this.walletClient.get('/wallet/crypto/balances');
    return response.data;
  }

  // Get detailed crypto balances with multi-chain aggregation
  async getDetailedCryptoBalances(): Promise<{
    aggregated_balances: Record<string, {
      total_balance: number;
      addresses: Array<{
        address: string;
        chain: string;
        currency: string;
        memo?: string;
      }>;
      chains: Record<string, {
        balance: number;
        accounts: Array<{
          account_id: number;
          balance: number;
          currency: string;
          parent_currency?: string;
        }>;
      }>;
    }>;
    balance_summary: {
      total_currencies: number;
      currencies: Record<string, {
        balance: number;
        chain_count: number;
      }>;
      multi_chain_tokens: Record<string, {
        total_balance: number;
        chains: Record<string, number>;
      }>;
    };
    portfolio_value: {
      total_value_usd: number;
      total_value_target: number;
      target_currency: string;
      currencies: Record<string, {
        balance: number;
        price_usd: number;
        value_usd: number;
        chains: Record<string, any>;
      }>;
    };
    multi_chain_details: Record<string, any>;
    success: boolean;
  }> {
    const response = await this.walletClient.get('/wallet/crypto/balances/detailed');
    return response.data;
  }

  // Generate deposit address for crypto
  async generateDepositAddress(crypto: string): Promise<{
    address: string;
    memo?: string;
    qr_code?: string;
  }> {
    const response = await this.walletClient.post(`/wallet/crypto/${crypto.toLowerCase()}/deposit/address`);
    return response.data;
  }

  // Withdraw crypto to external address
  async withdrawCrypto(crypto: string, amount: number, address: string): Promise<{
    message: string;
    transaction_id?: string;
  }> {
    const response = await this.walletClient.post(`/wallet/crypto/${crypto.toLowerCase()}/withdraw`, {
      amount,
      address,
    });
    return response.data;
  }

  // Get current crypto prices
  async getCryptoPrices(): Promise<Record<string, {
    price_ugx: number;
    change_24h: number;
    last_updated: string;
  }>> {
    const response = await this.walletClient.get('/api/trading/prices');
    return response.data;
  }

  // Get USD to UGX exchange rate
  async getUsdToUgxRate(): Promise<number> {
    try {
      const response = await this.walletClient.get('/api/trading/exchange-rate/USD/UGX');
      return response.data.rate || 3700; // Fallback rate
    } catch (error) {
      console.warn('Failed to get USD to UGX rate, using fallback');
      return 3700; // Fallback rate ~3700 UGX per USD
    }
  }

  // Trading endpoints
  async calculateTrade(
    tradeType: 'buy' | 'sell',
    cryptoCurrency: string,
    amount: number
  ): Promise<{
    crypto_amount: number;
    fiat_amount: number;
    exchange_rate: number;
    fee_amount: number;
    total_cost?: number;
    net_proceeds?: number;
  }> {
    const response = await this.walletClient.post('/api/trading/calculate', {
      crypto_currency: cryptoCurrency,
      fiat_currency: 'UGX',
      amount: amount,
      trade_type: tradeType,
      payment_method: 'mobile_money'
    });
    return response.data;
  }

  // Get quote for buying specified crypto amount
  async getQuoteForCryptoAmount(
    cryptoCurrency: string,
    cryptoAmount: number,
    paymentMethod: string = 'mobile_money'
  ): Promise<{
    crypto_currency: string;
    crypto_amount: number;
    crypto_amount_smallest_unit: number;
    fiat_currency: string;
    gross_fiat_cost: number;
    gross_fiat_cost_smallest_unit: number;
    fee_amount: number;
    fee_amount_smallest_unit: number;
    total_fiat_cost: number;
    total_fiat_cost_smallest_unit: number;
    exchange_rate: number;
    fee_percentage: number;
    payment_method: string;
  }> {
    const response = await this.walletClient.post('/trading/quote', {
      crypto_currency: cryptoCurrency,
      fiat_currency: 'UGX',
      crypto_amount: cryptoAmount,
      payment_method: paymentMethod
    });
    return response.data.data;
  }

  async executeTrade(
    tradeType: 'buy' | 'sell',
    cryptoCurrency: string,
    amount: number,
    phoneNumber: string,
    amountType: 'fiat' | 'crypto' = 'fiat'
  ): Promise<{
    trade_id: string;
    status: string;
    payment_url?: string;
    message: string;
  }> {
    const response = await this.walletClient.post(`/trading/${tradeType}`, {
      crypto_currency: cryptoCurrency,
      fiat_currency: 'UGX',
      amount: amount,
      amount_type: amountType,
      payment_method: 'mobile_money',
      payment_details: {
        phone_number: phoneNumber
      },
      phone_number: phoneNumber
    });
    return response.data;
  }

  async getTradeHistory(limit = 50, offset = 0): Promise<{
    trades: Array<{
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
    }>;
    total: number;
    pagination: {
      limit: number;
      offset: number;
      total: number;
    };
  }> {
    const response = await this.walletClient.get('/api/trading/history', {
      params: { limit, offset }
    });
    return response.data;
  }

  // Get trade by ID
  async getTrade(tradeId: string): Promise<{
    id: number;
    type?: 'buy' | 'sell';
    trade_type?: 'buy' | 'sell';
    crypto_currency: string;
    crypto_amount: number;
    fiat_amount: number;
    status: string;
    created_at: string;
    completed_at?: string;
    payment_url?: string;
    phone_number?: string;
  }> {
    const response = await this.walletClient.get(`/trading/trades/${tradeId}`);
    return response.data;
  }

  // Multi-network deposit methods
  async getMultiNetworkDepositNetworks(tokenSymbol: string, includeTestnets: boolean = false): Promise<{
    success: boolean;
    networks: Array<{
      network_type: string;
      network_name: string;
      display_name: string;
      currency_code: string;
      confirmation_blocks: number;
      explorer_url: string;
      is_testnet: boolean;
    }>;
    error?: string;
  }> {
    const response = await this.walletClient.get(`/wallet/deposit/networks/${tokenSymbol}`, {
      params: { include_testnets: includeTestnets }
    });
    return response.data;
  }

  async generateMultiNetworkDepositAddress(tokenSymbol: string, networkType: string): Promise<{
    success: boolean;
    address: string;
    currency_code: string;
    network: {
      type: string;
      name: string;
      confirmation_blocks: number;
      explorer_url: string;
    };
    token_info: {
      symbol: string;
      contract_address: string;
      decimals: number;
    };
    error?: string;
  }> {
    const response = await this.walletClient.get(`/wallet/deposit/address/${tokenSymbol}/${networkType}`);
    return response.data;
  }

  // Currency management methods
  async getCurrencies(): Promise<{
    success: boolean;
    currencies: Array<{
      id: string;
      symbol: string;
      name: string;
      is_enabled: boolean;
      is_multi_network: boolean;
      contract_address?: string;
      decimals: number;
      networks: Array<{
        network_type: string;
        network_name: string;
        is_enabled: boolean;
        contract_address?: string;
        confirmation_blocks: number;
        explorer_url: string;
      }>;
      created_at: string;
      updated_at: string;
    }>;
    error?: string;
  }> {
    const response = await this.adminClient.get('/admin/currencies');
    return response.data;
  }

  async createCurrency(currencyData: any): Promise<{
    success: boolean;
    currency?: any;
    error?: string;
  }> {
    const response = await this.adminClient.post('/admin/currencies', currencyData);
    return response.data;
  }

  async updateCurrency(currencyId: string, currencyData: any): Promise<{
    success: boolean;
    currency?: any;
    error?: string;
  }> {
    const response = await this.adminClient.put(`/admin/currencies/${currencyId}`, currencyData);
    return response.data;
  }

  async updateCurrencyStatus(currencyId: string, isEnabled: boolean): Promise<{
    success: boolean;
    error?: string;
  }> {
    const response = await this.adminClient.patch(`/admin/currencies/${currencyId}/status`, {
      is_enabled: isEnabled
    });
    return response.data;
  }

  async deleteCurrency(currencyId: string): Promise<{
    success: boolean;
    error?: string;
  }> {
    const response = await this.adminClient.delete(`/admin/currencies/${currencyId}`);
    return response.data;
  }
}

export const apiClient = new ApiClient();
