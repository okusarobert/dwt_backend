import { useState, useEffect, useCallback } from "react";
import { websocketClient, CryptoPrice } from "@/lib/websocket-client";
import { apiClient } from "@/lib/api-client";

export function useCryptoPrices() {
  const [prices, setPrices] = useState<CryptoPrice[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Connect to WebSocket and subscribe to price updates
  useEffect(() => {
    let cleanup: (() => void) | undefined;
    
    const connect = async () => {
      try {
        // Get and set USD to UGX exchange rate
        const exchangeRate = await apiClient.getUsdToUgxRate();
        websocketClient.updateExchangeRate(exchangeRate);
        
        websocketClient.connect();

        // Subscribe to price updates
        const unsubscribePrices = websocketClient.onPriceUpdate((newPrices) => {
          setPrices(newPrices);
          setIsLoading(false);
          setError(null);
        });

        // Subscribe to connection status changes
        const unsubscribeConnection = websocketClient.onConnectionChange(
          (connected) => {
            setIsConnected(connected);
            if (!connected) {
              setError("Connection lost. Reconnecting...");
            } else {
              setError(null);
            }
          }
        );

        // Set cleanup function
        cleanup = () => {
          unsubscribePrices();
          unsubscribeConnection();
          websocketClient.disconnect();
        };
      } catch (err) {
        setError("Failed to connect to price feed");
        setIsLoading(false);
        console.error("WebSocket connection error:", err);
      }
    };

    connect();
    
    return () => {
      if (cleanup) cleanup();
    };
  }, []);

  // Helper functions for price formatting
  const formatPrice = useCallback((price: number): string => {
    // Format as UGX currency
    return new Intl.NumberFormat("en-UG", {
      style: "currency",
      currency: "UGX",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(price);
  }, []);

  const formatChange = useCallback((change: number): string => {
    const sign = change >= 0 ? "+" : "";
    return `${sign}${change.toFixed(2)}%`;
  }, []);

  const isPricePositive = useCallback((crypto: CryptoPrice): boolean => {
    return crypto.changePercent24h >= 0;
  }, []);

  // Get specific crypto by symbol
  const getCryptoBySymbol = useCallback(
    (symbol: string): CryptoPrice | undefined => {
      return prices.find((crypto) => crypto.symbol === symbol);
    },
    [prices]
  );

  // Get top performers (positive change)
  const getTopPerformers = useCallback(
    (limit: number = 5): CryptoPrice[] => {
      return prices
        .filter((crypto) => crypto.changePercent24h > 0)
        .sort((a, b) => b.changePercent24h - a.changePercent24h)
        .slice(0, limit);
    },
    [prices]
  );

  // Get worst performers (negative change)
  const getWorstPerformers = useCallback(
    (limit: number = 5): CryptoPrice[] => {
      return prices
        .filter((crypto) => crypto.changePercent24h < 0)
        .sort((a, b) => a.changePercent24h - b.changePercent24h)
        .slice(0, limit);
    },
    [prices]
  );

  // Get highest volume
  const getHighestVolume = useCallback(
    (limit: number = 5): CryptoPrice[] => {
      return prices.sort((a, b) => b.volume24h - a.volume24h).slice(0, limit);
    },
    [prices]
  );

  // Get highest market cap
  const getHighestMarketCap = useCallback(
    (limit: number = 5): CryptoPrice[] => {
      return prices.sort((a, b) => b.marketCap - a.marketCap).slice(0, limit);
    },
    [prices]
  );

  // Manual refresh function
  const refresh = useCallback(() => {
    if (websocketClient.isConnected()) {
      // Reconnect to refresh prices
      websocketClient.disconnect();
      setTimeout(() => websocketClient.connect(), 1000);
    }
  }, []);

  return {
    prices,
    isConnected,
    isLoading,
    error,
    formatPrice,
    formatChange,
    isPricePositive,
    getCryptoBySymbol,
    getTopPerformers,
    getWorstPerformers,
    getHighestVolume,
    getHighestMarketCap,
    refresh,
  };
}
