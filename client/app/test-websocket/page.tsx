"use client";

import { useCryptoPrices } from "@/hooks/use-crypto-prices";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RefreshCw, Wifi, WifiOff, AlertCircle } from "lucide-react";

export default function TestWebSocketPage() {
  const {
    prices,
    isConnected,
    isLoading,
    error,
    formatPrice,
    formatChange,
    isPricePositive,
    refresh,
  } = useCryptoPrices();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            WebSocket Connection Test
          </h1>
          <p className="text-gray-600 dark:text-gray-300">
            Testing real-time crypto price streaming from the backend
          </p>
        </div>

        {/* Connection Status */}
        <Card className="p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {isConnected ? (
                <Wifi className="w-6 h-6 text-green-500" />
              ) : (
                <WifiOff className="w-6 h-6 text-red-500" />
              )}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Connection Status
                </h3>
                <p className="text-gray-600 dark:text-gray-300">
                  {isConnected ? "Connected to WebSocket" : "Disconnected"}
                </p>
              </div>
            </div>
            <Button onClick={refresh} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </Card>

        {/* Error Display */}
        {error && (
          <Card className="p-6 mb-8 border-red-200 bg-red-50 dark:bg-red-900/20 dark:border-red-800">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-6 h-6 text-red-500" />
              <div>
                <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
                  Connection Error
                </h3>
                <p className="text-red-700 dark:text-red-300">{error}</p>
              </div>
            </div>
          </Card>
        )}

        {/* Loading State */}
        {isLoading && (
          <Card className="p-6 mb-8">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <p className="text-gray-600 dark:text-gray-300">
                Connecting to WebSocket and loading crypto prices...
              </p>
            </div>
          </Card>
        )}

        {/* Price Data */}
        {prices.length > 0 && (
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Live Crypto Prices ({prices.length} assets)
            </h3>
            <div className="space-y-4">
              {prices.map((crypto) => (
                <div
                  key={crypto.symbol}
                  className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center">
                      <span className="font-bold text-gray-700 dark:text-gray-200">
                        {crypto.symbol[0]}
                      </span>
                    </div>
                    <div>
                      <div className="font-semibold text-gray-900 dark:text-white">
                        {crypto.symbol}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-300">
                        {crypto.name}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-gray-900 dark:text-white">
                      {formatPrice(crypto.price)}
                    </div>
                    <div
                      className={`text-sm ${
                        isPricePositive(crypto)
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-600 dark:text-red-400"
                      }`}
                    >
                      {formatChange(crypto.changePercent24h)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Debug Info */}
        <Card className="p-6 mt-8">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Debug Information
          </h3>
          <div className="space-y-2 text-sm text-gray-600 dark:text-gray-300">
            <p>
              WebSocket URL:{" "}
              {process.env.NEXT_PUBLIC_WEBSOCKET_URL || "ws://localhost:5000"}
            </p>
            <p>
              Connection Status: {isConnected ? "Connected" : "Disconnected"}
            </p>
            <p>Loading State: {isLoading ? "Loading" : "Loaded"}</p>
            <p>Error State: {error ? "Error" : "No Errors"}</p>
            <p>Price Count: {prices.length}</p>
            <p>
              Last Update:{" "}
              {prices.length > 0
                ? new Date(prices[0]?.lastUpdated).toLocaleString()
                : "Never"}
            </p>
          </div>
        </Card>
      </div>
    </div>
  );
}
