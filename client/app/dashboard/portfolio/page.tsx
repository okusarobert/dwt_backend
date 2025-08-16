"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Coins,
  BarChart3,
} from "lucide-react";

interface PortfolioAsset {
  account_id: number;
  balance: number;
  last_updated: string;
  ledger_entry_id: number | null;
  percentage: number;
  price_usd: number;
  type: "crypto" | "fiat";
  value_usd: number;
}

interface PortfolioData {
  assets: Record<string, PortfolioAsset>;
  currency_count: number;
  historical_data: any[];
  last_updated: string;
  performance: {
    all_time_high: number;
    all_time_low: number;
    daily_change: number;
    monthly_change: number;
    volatility_30d: number;
    weekly_change: number;
  };
  total_value_usd: number;
}

export default function PortfolioPage() {
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPortfolioData = async () => {
      try {
        setLoading(true);
        const response = await fetch("/api/wallet/portfolio/summary", {
          credentials: "include",
        });

        if (!response.ok) {
          throw new Error("Failed to fetch portfolio data");
        }

        const data = await response.json();
        setPortfolioData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolioData();
  }, []);

  const formatCurrency = (value: number, currency: string = "USD") => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
  };

  const formatBalance = (balance: number, type: string) => {
    if (type === "crypto") {
      return balance.toFixed(8);
    }
    return balance.toLocaleString();
  };

  const getChangeIcon = (change: number) => {
    if (change > 0) return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (change < 0) return <TrendingDown className="h-4 w-4 text-red-500" />;
    return null;
  };

  const getChangeColor = (change: number) => {
    if (change > 0) return "text-green-500";
    if (change < 0) return "text-red-500";
    return "text-muted-foreground";
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold text-foreground">Portfolio</h1>
        <div className="grid gap-4">
          <Card>
            <CardContent className="p-6">
              <div className="animate-pulse space-y-4">
                <div className="h-4 bg-muted rounded w-1/4"></div>
                <div className="h-8 bg-muted rounded w-1/2"></div>
                <div className="h-4 bg-muted rounded w-1/3"></div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold text-foreground">Portfolio</h1>
        <Card>
          <CardContent className="p-6">
            <p className="text-red-500">Error: {error}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!portfolioData) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-semibold text-foreground">Portfolio</h1>
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">
              No portfolio data available.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const assets = Object.entries(portfolioData.assets);
  const cryptoAssets = assets.filter(([_, asset]) => asset.type === "crypto");
  const fiatAssets = assets.filter(([_, asset]) => asset.type === "fiat");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-foreground">Portfolio</h1>
        <p className="text-sm text-muted-foreground">
          Last updated: {new Date(portfolioData.last_updated).toLocaleString()}
        </p>
      </div>

      {/* Portfolio Overview */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Value</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(portfolioData.total_value_usd)}
            </div>
            <p className="text-xs text-muted-foreground">
              {portfolioData.currency_count} currencies
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">24h Change</CardTitle>
            {getChangeIcon(portfolioData.performance.daily_change)}
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold ${getChangeColor(
                portfolioData.performance.daily_change
              )}`}
            >
              {formatPercentage(portfolioData.performance.daily_change)}
            </div>
            <p className="text-xs text-muted-foreground">vs yesterday</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">7d Change</CardTitle>
            {getChangeIcon(portfolioData.performance.weekly_change)}
          </CardHeader>
          <CardContent>
            <div
              className={`text-2xl font-bold ${getChangeColor(
                portfolioData.performance.weekly_change
              )}`}
            >
              {formatPercentage(portfolioData.performance.weekly_change)}
            </div>
            <p className="text-xs text-muted-foreground">vs last week</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              30d Volatility
            </CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {portfolioData.performance.volatility_30d.toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground">
              30-day standard deviation
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Asset Allocation */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Crypto Assets */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Coins className="h-5 w-5" />
              Crypto Assets
            </CardTitle>
            <CardDescription>
              {cryptoAssets.length} cryptocurrency
              {cryptoAssets.length !== 1 ? "s" : ""}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {cryptoAssets.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">
                No crypto assets
              </p>
            ) : (
              cryptoAssets.map(([currency, asset]) => (
                <div key={currency} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{currency}</span>
                      <Badge variant="secondary">{asset.type}</Badge>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        {formatCurrency(asset.value_usd)}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {formatBalance(asset.balance, asset.type)} {currency}
                      </div>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>Allocation</span>
                      <span>{asset.percentage.toFixed(2)}%</span>
                    </div>
                    <Progress value={asset.percentage} className="h-2" />
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Price: {formatCurrency(asset.price_usd)} per {currency}
                  </div>
                  <Separator />
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Fiat Assets */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Fiat Assets
            </CardTitle>
            <CardDescription>
              {fiatAssets.length} fiat currenc
              {fiatAssets.length !== 1 ? "ies" : "y"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {fiatAssets.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">
                No fiat assets
              </p>
            ) : (
              fiatAssets.map(([currency, asset]) => (
                <div key={currency} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{currency}</span>
                      <Badge variant="outline">{asset.type}</Badge>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">
                        {formatCurrency(asset.value_usd)}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {formatBalance(asset.balance, asset.type)} {currency}
                      </div>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>Allocation</span>
                      <span>{asset.percentage.toFixed(2)}%</span>
                    </div>
                    <Progress value={asset.percentage} className="h-2" />
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Exchange Rate: {formatCurrency(asset.price_usd)} per{" "}
                    {currency}
                  </div>
                  <Separator />
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Performance Metrics */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Metrics</CardTitle>
          <CardDescription>
            Portfolio performance over different time periods
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-2">
              <p className="text-sm font-medium">All-Time High</p>
              <p className="text-2xl font-bold">
                {formatCurrency(portfolioData.performance.all_time_high)}
              </p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">All-Time Low</p>
              <p className="text-2xl font-bold">
                {formatCurrency(portfolioData.performance.all_time_low)}
              </p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">30-Day Change</p>
              <p
                className={`text-2xl font-bold ${getChangeColor(
                  portfolioData.performance.monthly_change
                )}`}
              >
                {formatPercentage(portfolioData.performance.monthly_change)}
              </p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium">30-Day Volatility</p>
              <p className="text-2xl font-bold">
                {portfolioData.performance.volatility_30d.toFixed(2)}%
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
