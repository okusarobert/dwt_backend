"use client";

import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Wifi, WifiOff } from "lucide-react";
import { CryptoPrice } from "@/lib/websocket-client";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";
import { useState } from "react";

interface CryptoPriceCardProps {
  crypto: CryptoPrice;
  isConnected: boolean;
  formatPrice: (price: number) => string;
  formatChange: (change: number) => string;
  isPricePositive: (crypto: CryptoPrice) => boolean;
}

export function CryptoPriceCard({
  crypto,
  isConnected,
  formatPrice,
  formatChange,
  isPricePositive,
}: CryptoPriceCardProps) {
  const positive = isPricePositive(crypto);
  const colorClass = positive ? "green" : "red";
  const [logoError, setLogoError] = useState(false);

  // Generate random chart data for demo (in real app, this would come from WebSocket)
  const generateChartData = () => {
    return Array.from({ length: 10 }, () => Math.random() * 20 + 10);
  };

  const chartData = generateChartData();
  const logoPath = getCryptoLogo(crypto.symbol);
  const fallbackLogo = createFallbackLogo(crypto.symbol);

  return (
    <Card className="p-6 shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-transparent hover:border-l-primary-500">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="relative">
            {!logoError ? (
              <Image
                src={logoPath}
                alt={`${crypto.name} logo`}
                width={48}
                height={48}
                className="w-12 h-12 rounded-full"
                onError={() => setLogoError(true)}
              />
            ) : (
              <Image
                src={fallbackLogo}
                alt={`${crypto.name} logo`}
                width={48}
                height={48}
                className="w-12 h-12 rounded-full"
              />
            )}
            {/* Connection indicator */}
            <div className="absolute -top-1 -right-1">
              {isConnected ? (
                <Wifi className="w-3 h-3 text-green-500" />
              ) : (
                <WifiOff className="w-3 h-3 text-red-500" />
              )}
            </div>
          </div>
          <div>
            <div className="font-bold text-foreground">
              {crypto.symbol}
            </div>
            <div className="text-sm text-muted-foreground">
              {crypto.name}
            </div>
          </div>
        </div>
        <div className="text-right">
          <AnimatePresence mode="wait">
            <motion.div
              key={crypto.price}
              initial={{ scale: 1.05, opacity: 0.8 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="font-bold text-foreground"
            >
              {formatPrice(crypto.price)}
            </motion.div>
          </AnimatePresence>
          <div
            className={`flex items-center text-sm ${
              positive
                ? "text-green-600 dark:text-green-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            {positive ? (
              <TrendingUp className="w-4 h-4 mr-1" />
            ) : (
              <TrendingDown className="w-4 h-4 mr-1" />
            )}
            <AnimatePresence mode="wait">
              <motion.span
                key={crypto.changePercent24h}
                initial={{ scale: 1.05, opacity: 0.8 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                {formatChange(crypto.changePercent24h)}
              </motion.span>
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Mini Chart */}
      <div className="flex space-x-1 h-8 items-end">
        {chartData.map((height, i) => (
          <motion.div
            key={i}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: height, opacity: 1 }}
            transition={{ duration: 0.5, delay: i * 0.05 }}
            className={`w-1 rounded-full ${
              positive
                ? "bg-green-500 dark:bg-green-400"
                : "bg-red-500 dark:bg-red-400"
            }`}
            style={{ height: `${height}px` }}
          />
        ))}
      </div>

      {/* Additional Info */}
      <div className="mt-3 pt-3 border-t border-border">
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>24h Vol</span>
          <span>Market Cap</span>
        </div>
        <div className="flex justify-between text-xs font-medium text-foreground">
          <span>
            {crypto.volume24h >= 1e9
              ? `$${(crypto.volume24h / 1e9).toFixed(2)}B`
              : crypto.volume24h >= 1e6
              ? `$${(crypto.volume24h / 1e6).toFixed(2)}M`
              : `$${(crypto.volume24h / 1e3).toFixed(2)}K`}
          </span>
          <span>
            {crypto.marketCap >= 1e9
              ? `$${(crypto.marketCap / 1e9).toFixed(2)}B`
              : crypto.marketCap >= 1e6
              ? `$${(crypto.marketCap / 1e6).toFixed(2)}M`
              : `$${(crypto.marketCap / 1e3).toFixed(2)}K`}
          </span>
        </div>
      </div>

      {/* Last Update */}
      <div className="mt-2 text-xs text-muted-foreground text-center">
        Last updated: {new Date(crypto.lastUpdated).toLocaleTimeString()}
      </div>
    </Card>
  );
}
