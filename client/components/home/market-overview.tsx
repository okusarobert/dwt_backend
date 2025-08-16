"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import {
  formatCurrency,
  formatPercentage,
  formatCryptoAmount,
} from "@/lib/utils";
import { CryptoCard } from "@/components/crypto/crypto-card";

interface CryptoData {
  id: string;
  symbol: string;
  name: string;
  current_price: number;
  price_change_24h: number;
  price_change_percentage_24h: number;
  price_change_percentage_7d: number;
  price_change_percentage_30d: number;
  market_cap: number;
  volume_24h: number;
  image: string;
}

const mockCryptoData: CryptoData[] = [
  {
    id: "bitcoin",
    symbol: "btc",
    name: "Bitcoin",
    current_price: 43250.67,
    price_change_24h: 1250.45,
    price_change_percentage_24h: 2.98,
    price_change_percentage_7d: 8.45,
    price_change_percentage_30d: 15.67,
    market_cap: 850000000000,
    volume_24h: 28000000000,
    image: "/images/btc.svg",
  },
  {
    id: "ethereum",
    symbol: "eth",
    name: "Ethereum",
    current_price: 2650.89,
    price_change_24h: -45.67,
    price_change_percentage_24h: -1.69,
    price_change_percentage_7d: 12.34,
    price_change_percentage_30d: 28.91,
    market_cap: 320000000000,
    volume_24h: 15000000000,
    image: "/images/eth.svg",
  },
  {
    id: "binancecoin",
    symbol: "bnb",
    name: "BNB",
    current_price: 312.45,
    price_change_24h: 8.92,
    price_change_percentage_24h: 2.94,
    price_change_percentage_7d: 5.67,
    price_change_percentage_30d: 18.23,
    market_cap: 48000000000,
    volume_24h: 1200000000,
    image: "/images/bnb.svg",
  },
  {
    id: "solana",
    symbol: "sol",
    name: "Solana",
    current_price: 98.76,
    price_change_24h: -2.34,
    price_change_percentage_24h: -2.31,
    price_change_percentage_7d: 25.67,
    price_change_percentage_30d: 45.89,
    market_cap: 42000000000,
    volume_24h: 2800000000,
    image: "/images/sol.svg",
  },
  {
    id: "cardano",
    symbol: "ada",
    name: "Cardano",
    current_price: 0.567,
    price_change_24h: 0.023,
    price_change_percentage_24h: 4.23,
    price_change_percentage_7d: 18.45,
    price_change_percentage_30d: 32.67,
    market_cap: 20000000000,
    volume_24h: 890000000,
    image: "/images/ada.svg",
  },
  {
    id: "polkadot",
    symbol: "dot",
    name: "Polkadot",
    current_price: 7.89,
    price_change_24h: -0.12,
    price_change_percentage_24h: -1.5,
    price_change_percentage_7d: 8.9,
    price_change_percentage_30d: 22.34,
    market_cap: 9500000000,
    volume_24h: 450000000,
    image: "/images/dot.svg",
  },
];

export function MarketOverview() {
  const [cryptoData, setCryptoData] = useState<CryptoData[]>(mockCryptoData);
  const [timeframe, setTimeframe] = useState<"24h" | "7d" | "30d">("24h");
  const [sortBy, setSortBy] = useState<"market_cap" | "volume" | "change">(
    "market_cap"
  );

  const getPriceChange = (crypto: CryptoData) => {
    switch (timeframe) {
      case "24h":
        return crypto.price_change_percentage_24h;
      case "7d":
        return crypto.price_change_percentage_7d;
      case "30d":
        return crypto.price_change_percentage_30d;
      default:
        return crypto.price_change_percentage_24h;
    }
  };

  const getPriceChangeValue = (crypto: CryptoData) => {
    switch (timeframe) {
      case "24h":
        return crypto.price_change_24h;
      case "7d":
        return (
          crypto.current_price -
          crypto.current_price / (1 + crypto.price_change_percentage_7d / 100)
        );
      case "30d":
        return (
          crypto.current_price -
          crypto.current_price / (1 + crypto.price_change_percentage_30d / 100)
        );
      default:
        return crypto.price_change_24h;
    }
  };

  const sortedCryptoData = [...cryptoData].sort((a, b) => {
    switch (sortBy) {
      case "market_cap":
        return b.market_cap - a.market_cap;
      case "volume":
        return b.volume_24h - a.volume_24h;
      case "change":
        return getPriceChange(b) - getPriceChange(a);
      default:
        return b.market_cap - a.market_cap;
    }
  });

  return (
    <section className="py-16 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Market Overview
          </h2>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Track real-time cryptocurrency prices and market performance across
            different timeframes
          </p>
        </motion.div>

        {/* Controls */}
        <div className="flex flex-col sm:flex-row justify-between items-center mb-8 gap-4">
          <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
            {(["24h", "7d", "30d"] as const).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  timeframe === tf
                    ? "bg-white text-primary-600 shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-600">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="market_cap">Market Cap</option>
              <option value="volume">Volume</option>
              <option value="change">Price Change</option>
            </select>
          </div>
        </div>

        {/* Market Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="card text-center">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              Total Market Cap
            </h3>
            <p className="text-2xl font-bold text-gray-900">
              {formatCurrency(1300000000000, "USD")}
            </p>
            <p className="text-sm text-success-600 mt-1">+2.45%</p>
          </div>

          <div className="card text-center">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              24h Volume
            </h3>
            <p className="text-2xl font-bold text-gray-900">
              {formatCurrency(85000000000, "USD")}
            </p>
            <p className="text-sm text-danger-600 mt-1">-1.23%</p>
          </div>

          <div className="card text-center">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              Active Coins
            </h3>
            <p className="text-2xl font-bold text-gray-900">2,295</p>
            <p className="text-sm text-success-600 mt-1">+12</p>
          </div>

          <div className="card text-center">
            <h3 className="text-sm font-medium text-gray-500 mb-2">
              BTC Dominance
            </h3>
            <p className="text-2xl font-bold text-gray-900">48.2%</p>
            <p className="text-sm text-danger-600 mt-1">-0.8%</p>
          </div>
        </div>

        {/* Crypto List */}
        <div className="space-y-4">
          {sortedCryptoData.map((crypto, index) => (
            <motion.div
              key={crypto.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
            >
              <CryptoCard
                crypto={crypto}
                timeframe={timeframe}
                priceChange={getPriceChange(crypto)}
                priceChangeValue={getPriceChangeValue(crypto)}
              />
            </motion.div>
          ))}
        </div>

        {/* View All Button */}
        <div className="text-center mt-12">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="btn-primary px-8 py-3 text-lg"
          >
            View All Markets
          </motion.button>
        </div>
      </div>
    </section>
  );
}
