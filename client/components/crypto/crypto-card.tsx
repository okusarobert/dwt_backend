"use client";

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  formatCurrency,
  formatPercentage,
  formatCryptoAmount,
} from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface CryptoCardProps {
  crypto: {
    id: string;
    symbol: string;
    name: string;
    current_price: number;
    market_cap: number;
    volume_24h: number;
    image: string;
  };
  timeframe: string;
  priceChange: number;
  priceChangeValue: number;
}

export function CryptoCard({
  crypto,
  timeframe,
  priceChange,
  priceChangeValue,
}: CryptoCardProps) {
  const isPositive = priceChange > 0;
  const isNegative = priceChange < 0;

  const getChangeIcon = () => {
    if (isPositive) return <TrendingUp className="w-4 h-4 text-success-600" />;
    if (isNegative) return <TrendingDown className="w-4 h-4 text-danger-600" />;
    return <Minus className="w-4 h-4 text-gray-500" />;
  };

  const getChangeColor = () => {
    if (isPositive) return "text-success-600";
    if (isNegative) return "text-danger-600";
    return "text-gray-600";
  };

  const getChangeBgColor = () => {
    if (isPositive) return "bg-success-50";
    if (isNegative) return "bg-danger-50";
    return "bg-gray-50";
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02, y: -2 }}
      className="card hover:shadow-medium transition-all duration-200 cursor-pointer"
    >
      <div className="flex items-center justify-between">
        {/* Left side - Crypto info */}
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
            <img
              src={crypto.image}
              alt={crypto.name}
              className="w-8 h-8"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = "none";
                target.nextElementSibling?.classList.remove("hidden");
              }}
            />
            <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center text-white font-bold text-sm hidden">
              {crypto.symbol.toUpperCase().charAt(0)}
            </div>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900">{crypto.name}</h3>
            <p className="text-sm text-gray-500 uppercase">{crypto.symbol}</p>
          </div>
        </div>

        {/* Center - Price and change */}
        <div className="flex-1 mx-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-lg font-bold text-gray-900">
                {formatCurrency(crypto.current_price, "USD")}
              </p>
              <div className="flex items-center space-x-2 mt-1">
                {getChangeIcon()}
                <span className={`text-sm font-medium ${getChangeColor()}`}>
                  {formatPercentage(priceChange)}
                </span>
                <span className={`text-sm ${getChangeColor()}`}>
                  ({formatCurrency(Math.abs(priceChangeValue), "USD")})
                </span>
              </div>
            </div>

            <div className="text-right">
              <p className="text-sm text-gray-500">Market Cap</p>
              <p className="text-sm font-medium text-gray-900">
                {formatCurrency(crypto.market_cap, "USD")}
              </p>
            </div>
          </div>
        </div>

        {/* Right side - Actions */}
        <div className="flex items-center space-x-3">
          <Button variant="outline" size="sm">
            Trade
          </Button>
          <Button variant="ghost" size="sm">
            View
          </Button>
        </div>
      </div>

      {/* Additional info row */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-6">
            <div>
              <span className="text-gray-500">24h Volume:</span>
              <span className="ml-2 font-medium text-gray-900">
                {formatCurrency(crypto.volume_24h, "USD")}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Timeframe:</span>
              <span className="ml-2 font-medium text-gray-900">
                {timeframe}
              </span>
            </div>
          </div>

          <div
            className={`px-3 py-1 rounded-full text-xs font-medium ${getChangeBgColor()} ${getChangeColor()}`}
          >
            {timeframe} Change
          </div>
        </div>
      </div>
    </motion.div>
  );
}
