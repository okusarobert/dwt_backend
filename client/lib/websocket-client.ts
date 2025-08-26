import { io, Socket } from "socket.io-client";

export interface CryptoPrice {
  symbol: string;
  name: string;
  price: number; // Price in UGX
  priceUsd: number; // Original USD price
  change24h: number;
  changePercent24h: number;
  volume24h: number;
  marketCap: number;
  lastUpdated: string;
}

export interface PriceUpdate {
  symbol: string;
  price: number;
  change24h: number;
  changePercent24h: number;
  timestamp: string;
}

export interface TradeStatusUpdate {
  type: string;
  trade_id: string;
  data: {
    status?: string;
    message?: string;
    [key: string]: any;
  };
  timestamp: string;
}

class WebSocketClient {
  private _socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private priceCallbacks: ((prices: CryptoPrice[]) => void)[] = [];
  private connectionCallbacks: ((connected: boolean) => void)[] = [];
  private tradeStatusCallbacks: ((update: TradeStatusUpdate) => void)[] = [];
  private currencyChangeCallbacks: ((data: any) => void)[] = [];
  private usdToUgxRate = 3700; // Default rate, will be updated
  private currentTradeId: string | null = null;
  private connected = false;

  connect() {
    try {
      const wsUrl =
        process.env.NEXT_PUBLIC_WEBSOCKET_URL || "ws://localhost:5000";
      this._socket = io(wsUrl, {
        transports: ["websocket"],
        timeout: 60000,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay,
        forceNew: true,
        upgrade: true,
        rememberUpgrade: false,
        pingTimeout: 60000,
        pingInterval: 25000,
      });

      this.setupEventHandlers();
    } catch (error) {
      console.error("Failed to connect to WebSocket:", error);
      this.scheduleReconnect();
    }
  }

  private setupEventHandlers() {
    if (!this._socket) return;

    this._socket.on('connect', () => {
      console.log('WebSocket connected');
      this.connected = true;
      this.connectionCallbacks.forEach(callback => callback(true));
    });

    this._socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      this.connected = false;
      this.connectionCallbacks.forEach(callback => callback(false));
    });

    this._socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.connected = false;
      this.connectionCallbacks.forEach(callback => callback(false));
    });

    this._socket.on('debug_trade_update', (data) => {
      console.log('🔔 DEBUG: Received debug trade update:', data);
    });

    this._socket.on("crypto-price-update", (data: PriceUpdate[]) => {
      this.handlePriceUpdate(data);
    });

    this._socket.on("crypto-prices", (data: any[]) => {
      // Debug logging to check what we're receiving
      console.log("Raw crypto prices from backend:", data.slice(0, 2)); // Log first 2 items
      console.log("Current USD to UGX rate:", this.usdToUgxRate);
      
      // Backend sends USD prices, convert to UGX for display
      const convertedPrices: CryptoPrice[] = data.map((crypto) => ({
        ...crypto,
        priceUsd: crypto.price, // Store original USD price
        price: crypto.price * this.usdToUgxRate, // Convert to UGX
        change24h: crypto.change24h * this.usdToUgxRate, // Convert absolute change to UGX
        // changePercent24h stays as-is since it's already a percentage
      }));
      
      console.log("Converted prices:", convertedPrices.slice(0, 2)); // Log first 2 converted items
      this.notifyPriceCallbacks(convertedPrices);
    });

    this._socket.on("reconnect", (attemptNumber) => {
      console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
      this.reconnectAttempts = 0;
      this.notifyConnectionChange(true);

      // Resubscribe to crypto price updates
      this._socket?.emit("subscribe", { channel: "crypto-prices" });
    });

    this._socket.on("reconnect_failed", () => {
      console.error("WebSocket reconnection failed");
      this.notifyConnectionChange(false);
    });

    // Trade status update handler
    this._socket.on("trade_status_update", (data: TradeStatusUpdate) => {
      console.log("Trade status update received:", data);
      this.notifyTradeStatusCallbacks(data);
    });

    // Trade room join confirmation
    this._socket.on("joined_trade", (data: any) => {
      console.log("Successfully joined trade room:", data);
    });

    // Currency change handler
    this._socket.on("currency_change", (data: any) => {
      console.log("Currency change received:", data);
      this.notifyCurrencyChangeCallbacks(data);
    });

    // Error handler
    this._socket.on("error", (error: any) => {
      console.error("WebSocket error:", error);
    });
  }

  private handlePriceUpdate(updates: PriceUpdate[]) {
    // Convert updates to full crypto price objects with UGX conversion
    const prices: CryptoPrice[] = updates.map((update) => ({
      symbol: update.symbol,
      name: this.getCryptoName(update.symbol),
      priceUsd: update.price,
      price: update.price * this.usdToUgxRate, // Convert USD to UGX
      change24h: update.change24h * this.usdToUgxRate,
      changePercent24h: update.changePercent24h,
      volume24h: 0, // Will be updated from full price data
      marketCap: 0, // Will be updated from full price data
      lastUpdated: update.timestamp,
    }));

    this.notifyPriceCallbacks(prices);
  }

  private getCryptoName(symbol: string): string {
    const names: { [key: string]: string } = {
      BTC: "Bitcoin",
      ETH: "Ethereum",
      BNB: "Binance Coin",
      ADA: "Cardano",
      SOL: "Solana",
      DOT: "Polkadot",
      USDT: "Tether",
      USDC: "USD Coin",
      XRP: "Ripple",
      MATIC: "Polygon",
    };
    return names[symbol] || symbol;
  }

  private notifyPriceCallbacks(prices: CryptoPrice[]) {
    this.priceCallbacks.forEach((callback) => callback(prices));
  }

  private notifyConnectionChange(connected: boolean) {
    this.connectionCallbacks.forEach((callback) => callback(connected));
  }

  private notifyTradeStatusCallbacks(update: TradeStatusUpdate) {
    this.tradeStatusCallbacks.forEach((callback) => callback(update));
  }

  private notifyCurrencyChangeCallbacks(data: any) {
    this.currencyChangeCallbacks.forEach((callback) => callback(data));
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(
          `Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`
        );
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    }
  }

  onPriceUpdate(callback: (prices: CryptoPrice[]) => void) {
    this.priceCallbacks.push(callback);
    return () => {
      const index = this.priceCallbacks.indexOf(callback);
      if (index > -1) {
        this.priceCallbacks.splice(index, 1);
      }
    };
  }

  onConnectionChange(callback: (connected: boolean) => void) {
    this.connectionCallbacks.push(callback);
    return () => {
      const index = this.connectionCallbacks.indexOf(callback);
      if (index > -1) {
        this.connectionCallbacks.splice(index, 1);
      }
    };
  }

  disconnect() {
    if (this._socket) {
      this._socket.disconnect();
      this._socket = null;
    }
  }

  isConnected(): boolean {
    return this._socket?.connected || false;
  }

  // Update USD to UGX exchange rate
  updateExchangeRate(rate: number) {
    this.usdToUgxRate = rate;
  }

  // Get current exchange rate
  getExchangeRate(): number {
    return this.usdToUgxRate;
  }

  // Trade-specific methods
  joinTradeRoom(tradeId: string) {
    if (this._socket && this._socket.connected) {
      this.currentTradeId = tradeId;
      this._socket.emit('join_trade', { trade_id: tradeId });
      console.log(`🔔 Joining trade room for trade ${tradeId}`);
      
      // Listen for join confirmation
      this._socket.on('joined_trade', (data) => {
        console.log('🔔 Successfully joined trade room:', data);
      });
      
      this._socket.on('error', (error) => {
        console.error('🔔 Error joining trade room:', error);
      });
    } else {
      console.warn('🔔 Cannot join trade room - WebSocket not connected');
    }
  }

  leaveTradeRoom(tradeId?: string) {
    if (this._socket && this._socket.connected) {
      const targetTradeId = tradeId || this.currentTradeId;
      if (targetTradeId) {
        this._socket.emit('leave_trade', { trade_id: targetTradeId });
        console.log(`Leaving trade room: ${targetTradeId}`);
        if (targetTradeId === this.currentTradeId) {
          this.currentTradeId = null;
        }
      }
    }
  }

  onTradeStatusUpdate(callback: (update: TradeStatusUpdate) => void) {
    this.tradeStatusCallbacks.push(callback);
    return () => {
      const index = this.tradeStatusCallbacks.indexOf(callback);
      if (index > -1) {
        this.tradeStatusCallbacks.splice(index, 1);
      }
    };
  }

  getCurrentTradeId(): string | null {
    return this.currentTradeId;
  }

  onCurrencyChange(callback: (data: any) => void) {
    this.currencyChangeCallbacks.push(callback);
    return () => {
      const index = this.currencyChangeCallbacks.indexOf(callback);
      if (index > -1) {
        this.currencyChangeCallbacks.splice(index, 1);
      }
    };
  }

  // Expose socket for direct event handling if needed
  get socket() {
    return this._socket;
  }
}

export const websocketClient = new WebSocketClient();
