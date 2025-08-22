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

class WebSocketClient {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private priceCallbacks: ((prices: CryptoPrice[]) => void)[] = [];
  private connectionCallbacks: ((connected: boolean) => void)[] = [];
  private usdToUgxRate = 3700; // Default rate, will be updated

  connect() {
    try {
      const wsUrl =
        process.env.NEXT_PUBLIC_WEBSOCKET_URL || "ws://localhost:5000";
      this.socket = io(wsUrl, {
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
    if (!this.socket) return;

    this.socket.on("connect", () => {
      console.log("WebSocket connected");
      this.reconnectAttempts = 0;
      this.notifyConnectionChange(true);

      // Subscribe to crypto price updates
      this.socket?.emit("subscribe", { channel: "crypto-prices" });
    });

    this.socket.on("disconnect", () => {
      console.log("WebSocket disconnected");
      this.notifyConnectionChange(false);
    });

    this.socket.on("connect_error", (error) => {
      console.error("WebSocket connection error:", error);
      this.notifyConnectionChange(false);
    });

    this.socket.on("crypto-price-update", (data: PriceUpdate[]) => {
      this.handlePriceUpdate(data);
    });

    this.socket.on("crypto-prices", (data: any[]) => {
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

    this.socket.on("reconnect", (attemptNumber) => {
      console.log(`WebSocket reconnected after ${attemptNumber} attempts`);
      this.reconnectAttempts = 0;
      this.notifyConnectionChange(true);

      // Resubscribe to crypto price updates
      this.socket?.emit("subscribe", { channel: "crypto-prices" });
    });

    this.socket.on("reconnect_failed", () => {
      console.error("WebSocket reconnection failed");
      this.notifyConnectionChange(false);
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
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  // Update USD to UGX exchange rate
  updateExchangeRate(rate: number) {
    this.usdToUgxRate = rate;
  }

  // Get current exchange rate
  getExchangeRate(): number {
    return this.usdToUgxRate;
  }
}

export const websocketClient = new WebSocketClient();
