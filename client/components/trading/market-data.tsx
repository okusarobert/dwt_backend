"use client";

import { useState, useEffect } from "react";
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Activity, TrendingUp, TrendingDown, Wifi, WifiOff } from 'lucide-react';
import { useCryptoPrices } from '@/hooks/use-crypto-prices';
import { websocketClient } from '@/lib/websocket-client';
import { formatUGX, formatPercentage } from '@/lib/currency-formatter';
import { useTheme } from '@/components/theme/theme-provider';
import { motion } from 'framer-motion';
import Image from "next/image";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";

interface Currency {
  code: string;
  name: string;
  symbol: string;
  is_enabled?: boolean;
}

interface MarketDataProps {
  currencies: Currency[];
  onCurrenciesUpdate?: () => void;
  selectedCrypto?: string;
  onSelectCrypto?: (symbol: string) => void;
}

export function MarketData({ currencies, onCurrenciesUpdate, selectedCrypto, onSelectCrypto }: MarketDataProps) {
  const { theme } = useTheme();
  const { 
    prices, 
    getCryptoBySymbol, 
    isConnected, 
    isLoading, 
    error, 
    formatPrice, 
    formatChange, 
    isPricePositive, 
    getTopPerformers, 
    getWorstPerformers, 
    refresh 
  } = useCryptoPrices();
  // Listen for currency change events
  useEffect(() => {
    if (!onCurrenciesUpdate) return;
    
    const handleCurrencyChange = (data: any) => {
      console.log('Currency change received in MarketData:', data);
      // Notify parent component to refresh currencies
      onCurrenciesUpdate();
    };
    
    // Use websocket client's currency change handler
    const unsubscribe = websocketClient.onCurrencyChange(handleCurrencyChange);
    
    return unsubscribe;
  }, [onCurrenciesUpdate]);

  const [logoErrors, setLogoErrors] = useState<Record<string, boolean>>({});

  const handleLogoError = (symbol: string) => {
    setLogoErrors(prev => ({ ...prev, [symbol]: true }));
  };

  if (isLoading) {
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Activity className="w-4 h-4 sm:w-5 sm:h-5" />
            Market Data
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 sm:h-8 sm:w-8 border-b-2 border-primary"></div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Activity className="w-4 h-4 sm:w-5 sm:h-5" />
            Market Data
            <WifiOff className="w-3 h-3 sm:w-4 sm:h-4 text-red-500" />
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center py-8">
          <p className="text-sm text-muted-foreground mb-4">{error}</p>
          <Button onClick={refresh} variant="outline" size="sm">
            Retry Connection
          </Button>
        </CardContent>
      </Card>
    );
  }

  // Filter prices to only show enabled currencies
  const enabledPrices = prices.filter(crypto => {
    const currency = currencies.find(c => c.symbol === crypto.symbol);
    return currency?.is_enabled !== false;
  });

  const topPerformers = getTopPerformers(5).filter(crypto => {
    const currency = currencies.find(c => c.symbol === crypto.symbol);
    return currency?.is_enabled !== false;
  });
  
  const worstPerformers = getWorstPerformers(5).filter(crypto => {
    const currency = currencies.find(c => c.symbol === crypto.symbol);
    return currency?.is_enabled !== false;
  });

  return (
    <Card className="shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 sm:w-5 sm:h-5" />
            <span className="text-base sm:text-lg">Market Data</span>
          </div>
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Wifi className="w-3 h-3 sm:w-4 sm:h-4 text-green-500" />
            ) : (
              <WifiOff className="w-3 h-3 sm:w-4 sm:h-4 text-red-500" />
            )}
            <Badge variant={isConnected ? "default" : "destructive"} className="text-xs">
              {isConnected ? "Live" : "Offline"}
            </Badge>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-3 sm:px-6">
        <Tabs defaultValue="all" className="w-full">
          <TabsList className="grid w-full grid-cols-3 h-9 sm:h-10">
            <TabsTrigger value="all" className="text-xs sm:text-sm">All</TabsTrigger>
            <TabsTrigger value="gainers" className="text-xs sm:text-sm">Gainers</TabsTrigger>
            <TabsTrigger value="losers" className="text-xs sm:text-sm">Losers</TabsTrigger>
          </TabsList>

          <TabsContent value="all" className="space-y-1 sm:space-y-2 mt-3">
            {enabledPrices.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No market data available</p>
              </div>
            ) : (
              enabledPrices.map((crypto) => (
                <CryptoRow
                  key={crypto.symbol}
                  crypto={crypto}
                  isSelected={selectedCrypto === crypto.symbol}
                  onSelect={() => onSelectCrypto?.(crypto.symbol)}
                  logoError={logoErrors[crypto.symbol]}
                  onLogoError={() => handleLogoError(crypto.symbol)}
                />
              ))
            )}
          </TabsContent>

          <TabsContent value="gainers" className="space-y-1 sm:space-y-2 mt-3">
            {topPerformers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <TrendingUp className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No gainers today</p>
              </div>
            ) : (
              topPerformers.map((crypto) => (
                <CryptoRow
                  key={crypto.symbol}
                  crypto={crypto}
                  isSelected={selectedCrypto === crypto.symbol}
                  onSelect={() => onSelectCrypto?.(crypto.symbol)}
                  logoError={logoErrors[crypto.symbol]}
                  onLogoError={() => handleLogoError(crypto.symbol)}
                />
              ))
            )}
          </TabsContent>

          <TabsContent value="losers" className="space-y-1 sm:space-y-2 mt-3">
            {worstPerformers.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <TrendingDown className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No losers today</p>
              </div>
            ) : (
              worstPerformers.map((crypto) => (
                <CryptoRow
                  key={crypto.symbol}
                  crypto={crypto}
                  isSelected={selectedCrypto === crypto.symbol}
                  onSelect={() => onSelectCrypto?.(crypto.symbol)}
                  logoError={logoErrors[crypto.symbol]}
                  onLogoError={() => handleLogoError(crypto.symbol)}
                />
              ))
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

interface CryptoRowProps {
  crypto: any;
  isSelected: boolean;
  onSelect: () => void;
  logoError: boolean;
  onLogoError: () => void;
}

function CryptoRow({ crypto, isSelected, onSelect, logoError, onLogoError }: CryptoRowProps) {
  const logoPath = getCryptoLogo(crypto.symbol);
  const fallbackLogo = createFallbackLogo(crypto.symbol);

  return (
    <div
      className={`border rounded-lg cursor-pointer transition-colors hover:bg-muted/50 ${
        isSelected ? 'bg-primary/10 border-primary' : ''
      }`}
      onClick={onSelect}
    >
      {/* Mobile Layout */}
      <div className="sm:hidden p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            {!logoError ? (
              <Image
                src={logoPath}
                alt={`${crypto.name} logo`}
                width={24}
                height={24}
                className="rounded-full"
                onError={onLogoError}
              />
            ) : (
              <Image
                src={fallbackLogo}
                alt={`${crypto.name} logo`}
                width={24}
                height={24}
                className="rounded-full"
              />
            )}
            <div>
              <div className="font-medium text-xs">{crypto.symbol}</div>
              <div className="text-xs text-muted-foreground truncate max-w-[120px]">{crypto.name}</div>
            </div>
          </div>
          <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
            crypto.changePercent24h >= 0 
              ? 'text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30' 
              : 'text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30'
          }`}>
            {crypto.changePercent24h >= 0 ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )}
            {formatPercentage(crypto.changePercent24h)}
          </div>
        </div>
        <div className="text-right">
          <div className="font-semibold text-xs">
            {formatUGX(crypto.price)}
          </div>
        </div>
      </div>

      {/* Desktop Layout */}
      <div className="hidden sm:flex items-center justify-between p-3">
        <div className="flex items-center gap-3">
          {!logoError ? (
            <Image
              src={logoPath}
              alt={`${crypto.name} logo`}
              width={32}
              height={32}
              className="rounded-full"
              onError={onLogoError}
            />
          ) : (
            <Image
              src={fallbackLogo}
              alt={`${crypto.name} logo`}
              width={32}
              height={32}
              className="rounded-full"
            />
          )}
          <div>
            <div className="font-medium text-xs">{crypto.symbol}</div>
            <div className="text-xs text-muted-foreground">{crypto.name}</div>
          </div>
        </div>

        <div className="text-right">
          <div className="font-medium text-xs">
            {formatUGX(crypto.price)}
          </div>
          <div className={`text-xs flex items-center gap-1 ${
            crypto.changePercent24h >= 0 ? 'text-green-600' : 'text-red-600'
          }`}>
            {crypto.changePercent24h >= 0 ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )}
            {formatPercentage(crypto.changePercent24h)}
          </div>
        </div>
      </div>
    </div>
  );
}
