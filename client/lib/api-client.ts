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
  // For registration, backend returns {"message": "User registered successfully"}
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

      // Backend returns {"message": "User registered successfully"} with status 201
      // We need to handle this response format
      if (response.status === 201) {
        return {
          message: response.data.message || "User registered successfully",
          user: undefined, // No user data returned on registration
        };
      }

    return response.data;
    } catch (error: any) {
      console.error("Registration failed:", error);

      // Handle different error status codes
      if (error.response?.status === 400) {
        // Validation errors or bad request
        if (error.response?.data && typeof error.response.data === "object") {
          throw new Error(JSON.stringify(error.response.data));
        }
        throw new Error("Invalid registration data");
      } else if (error.response?.status === 500) {
        // Internal server error
        throw new Error("Internal server error. Please try again later.");
      } else {
        // Other errors
        throw new Error("Registration failed. Please try again.");
      }
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

  async getUserConfig(): Promise<{ user: User } | null> {
    try {
      const response: AxiosResponse<{ user: User }> = await this.authClient.get(
        "/user-config"
    );
    return response.data;
    } catch (error) {
      console.error("Failed to get user config:", error);
      return null;
    }
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

  async getTransactionHistory(limit = 5, offset = 0): Promise<any> {
    const response = await this.walletClient.get("/wallet/transactions", {
      params: { limit, offset },
    });
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
    if (mapped.q) {
      mapped.email = mapped.q;
      delete mapped.q;
    }
    if (mapped.role) {
      mapped.role = String(mapped.role).toUpperCase();
    }

    const response = await this.adminClient.get("/admin/users", { params: mapped });
    const data: any = response.data || {};
    const items: User[] = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : [];
    const page = typeof data?.page === "number" ? data.page : (params?.page ?? 1);
    const page_size = typeof data?.page_size === "number" ? data.page_size : (params?.page_size ?? items.length ?? 0);
    const total = typeof data?.total === "number" ? data.total : (Array.isArray(items) ? items.length : 0);
    return { success: true, data: items, pagination: { page, page_size, total } };
  }

  async adminGetUser(userId: number): Promise<{ success: boolean; data: User }> {
    const response = await this.adminClient.get(`/admin/users/${userId}`);
    return { success: true, data: response.data };
  }

  async adminUpdateUser(userId: number, patch: Partial<Pick<User,
    | "first_name"
    | "last_name"
    | "phone_number"
    | "role"
    | "country"
    | "ref_code"
  >> & { blocked?: boolean; deleted?: boolean; default_currency?: string }): Promise<{ success: boolean; data: User }> {
    const body: any = { ...(patch || {}) };
    if (body.default_currency) {
      body.currency = body.default_currency;
      delete body.default_currency;
    }
    if (body.role) {
      body.role = String(body.role).toUpperCase();
    }
    const response = await this.adminClient.patch(`/admin/users/${userId}`, body);
    return { success: true, data: response.data };
  }

  // ===== PORTFOLIO ENDPOINTS =====
  
  /**
   * Get portfolio summary for the authenticated user
   */
  async getPortfolioSummary() {
    try {
      const response = await this.walletClient.get('/wallet/portfolio/summary');
      return response.data;
    } catch (error) {
      console.error('Error fetching portfolio summary:', error);
      throw error;
    }
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
    const response = await this.walletClient.post(`/api/trading/${tradeType}/calculate`, {
      crypto_currency: cryptoCurrency,
      amount: amount
    });
    return response.data;
  }

  async executeTrade(
    tradeType: 'buy' | 'sell',
    cryptoCurrency: string,
    amount: number,
    phoneNumber: string
  ): Promise<{
    trade_id: string;
    status: string;
    payment_url?: string;
    message: string;
  }> {
    const response = await this.walletClient.post(`/api/trading/${tradeType}`, {
      crypto_currency: cryptoCurrency,
      amount: amount,
      phone_number: phoneNumber
    });
    return response.data;
  }

  async getTradeHistory(limit = 50, offset = 0): Promise<{
    trades: Array<{
      id: string;
      type: 'buy' | 'sell';
      crypto_currency: string;
      crypto_amount: number;
      fiat_amount: number;
      status: string;
      created_at: string;
      completed_at?: string;
    }>;
    total: number;
  }> {
    const response = await this.walletClient.get('/api/trading/history', {
      params: { limit, offset }
    });
    return response.data;
  }
}

export const apiClient = new ApiClient();
