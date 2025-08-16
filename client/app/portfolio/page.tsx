"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout";
import { useAuth } from "@/components/auth/auth-provider";
import { toast } from "react-hot-toast";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Download,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  Loader2,
  AlertCircle,
  Wallet,
  ArrowUp,
  ArrowDown
} from "lucide-react";
import Link from "next/link";
import { apiClient } from "@/lib/api-client";
import { useCryptoPrices } from "@/hooks/use-crypto-prices";

// --- TYPE DEFINITIONS ---
interface Asset {
  account_id: number;
  balance: number;
  last_updated: string;
  ledger_entry_id: number | null;
  percentage: number;
  price_usd: number;
  type: 'crypto' | 'fiat';
  value_usd: number;
}

interface PortfolioData {
  assets: Record<string, Asset>;
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

interface PriceData {
  symbol: string;
  price: number;
  change_24h: number;
}

// Helper function to format currency
const formatCurrency = (value: number, currency: string = 'USD'): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

// Helper function to format percentage
const formatPercentage = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value / 100);
};

// --- COMPONENT ---
const PortfolioPage = () => {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [timeRange, setTimeRange] = useState<string>('1M');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [portfolioData, setPortfolioData] = useState<PortfolioData | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<string | null>(null);
  
  // Initialize with empty transactions array
  const { prices: cryptoPrices, getCryptoBySymbol } = useCryptoPrices();
  const [transactions] = useState<Array<{
    id: number;
    type: 'buy' | 'sell';
    asset: string;
    amount: number;
    value: number;
    date: string;
    status: 'completed' | 'pending' | 'failed';
  }>>([]);


  // Chart colors
  const PIE_CHART_COLORS = [
    'hsl(var(--chart-1))',
    'hsl(var(--chart-2))',
    'hsl(var(--chart-3))',
    'hsl(var(--chart-4))',
    'hsl(var(--chart-5))',
    'hsl(var(--chart-6))',
  ];

  // Fetch portfolio data
  useEffect(() => {
    const fetchPortfolioData = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const data = await apiClient.getPortfolioSummary();
        setPortfolioData(data);
        
        // Select the first asset by default
        const firstAsset = Object.keys(data.assets || {})[0];
        if (firstAsset) {
          setSelectedAsset(firstAsset);
        }
      } catch (err) {
        console.error('Failed to fetch portfolio data:', err);
        setError('Failed to load portfolio data. Please try again later.');
        toast.error('Failed to load portfolio data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPortfolioData();
  }, []);


  // Handle refresh
  const handleRefresh = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const data = await apiClient.getPortfolioSummary();
      setPortfolioData(data);
      toast.success('Portfolio data refreshed');
    } catch (err) {
      console.error('Failed to refresh portfolio data:', err);
      setError('Failed to refresh portfolio data');
      toast.error('Failed to refresh data');
    } finally {
      setIsLoading(false);
    }
  };

  // Loading state
  if (isLoading && !portfolioData) {
    return (
      <AuthenticatedLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="w-12 h-12 animate-spin text-primary" />
            <p className="text-muted-foreground">Loading portfolio data...</p>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <AuthenticatedLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4 max-w-md">
            <div className="text-destructive">
              <AlertCircle className="w-12 h-12 mx-auto mb-4" />
              <h3 className="text-lg font-medium">Error loading portfolio</h3>
              <p className="text-sm text-muted-foreground mt-2">{error}</p>
            </div>
            <Button onClick={handleRefresh}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  // No data state
  if (!portfolioData || Object.keys(portfolioData.assets || {}).length === 0) {
    return (
      <AuthenticatedLayout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center space-y-4 max-w-md">
            <div className="text-muted-foreground">
              <Wallet className="w-12 h-12 mx-auto mb-4" />
              <h3 className="text-lg font-medium">No assets found</h3>
              <p className="text-sm text-muted-foreground mt-2">
                You don't have any assets in your portfolio yet.
              </p>
            </div>
            <Button asChild>
              <Link href="/trade">Start Trading</Link>
            </Button>
          </div>
        </div>
      </AuthenticatedLayout>
    );
  }

  // Get asset icon path
  const getAssetIcon = (symbol: string) => {
    // Map of common crypto symbols to their icon paths
    const iconMap: { [key: string]: string } = {
      'BTC': '/crypto-logos/btc.svg',
      'ETH': '/crypto-logos/eth.svg',
      'USDT': '/crypto-logos/usdt.svg',
      'USDC': '/crypto-logos/usdc.svg',
      'BNB': '/crypto-logos/bnb.svg',
      'XRP': '/crypto-logos/xrp.svg',
      'SOL': '/crypto-logos/sol.svg',
      'ADA': '/crypto-logos/ada.svg',
      'DOT': '/crypto-logos/dot.svg',
      'DOGE': '/crypto-logos/doge.svg',
      // Add more mappings as needed
    };

    return iconMap[symbol] || '/crypto-logos/generic.svg';
  };

  // Prepare data for charts, using real-time prices from the hook
  const assets = Object.entries(portfolioData.assets || {}).map(([symbol, asset]) => {
    const livePriceData = getCryptoBySymbol(symbol.toUpperCase());
    const currentPrice = livePriceData?.price ?? asset.price_usd;
    const value = asset.balance * currentPrice;
    const changePercent = livePriceData?.changePercent24h ?? 0;

    return {
      ...asset,
      symbol,
      name: symbol,
      icon: getAssetIcon(symbol),
      value_usd: value, // Use real-time value
      balance: asset.balance,
      changePercent: changePercent, // Use real-time 24h change
      price_usd: currentPrice, // Use real-time price
    };
  });

  const totalPortfolioValue = assets.reduce((acc, asset) => acc + asset.value_usd, 0);

  const historicalData = portfolioData.historical_data || [];
  // Transform historical data for the chart
  const chartData = historicalData.map(item => ({
    date: item.date,
    value: item.total_value_usd
  }));
  const performance = portfolioData.performance || {
    all_time_high: 0,
    all_time_low: 0,
    daily_change: 0,
    monthly_change: 0,
    volatility_30d: 0,
    weekly_change: 0,
  };

  // Performance data for the performance chart
  const performanceData = [
    { asset: 'BTC', portfolio: 1.86, market: 2.1, benchmark: 1.5 },
    { asset: 'ETH', portfolio: 1.82, market: 1.9, benchmark: 1.3 },
    { asset: 'SOL', portfolio: 8.47, market: 7.2, benchmark: 5.8 },
    { asset: 'ADA', portfolio: -3.85, market: -2.5, benchmark: -1.8 },
    { asset: 'DOT', portfolio: 3.45, market: 2.8, benchmark: 2.1 },
    { asset: 'USDT', portfolio: 0, market: 0.1, benchmark: 0 },
  ];

  // Handle export
  const handleExport = () => {
    toast.success('Exporting portfolio data...');
    // TODO: Implement export functionality
  };

  return (
    <AuthenticatedLayout title="Portfolio">
      <div className="min-h-screen bg-background text-foreground p-4 sm:p-6">
        <div className="container mx-auto max-w-7xl">
        <header className="bg-card border-b border-border px-6 py-4 shadow-sm rounded-lg mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-foreground">Portfolio</h1>
              <p className="text-muted-foreground mt-1">Track your crypto investments and performance</p>
            </div>
            <div className="flex items-center space-x-2">
              <Button variant="ghost" size="icon" onClick={handleRefresh} disabled={isLoading}>
                <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleExport}>
                <Download className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </header>

        <main className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Total Portfolio Value</CardTitle>
                  <CardDescription>The current estimated value of all your assets.</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-4xl font-bold">{formatCurrency(totalPortfolioValue)}</p>
                  <div className={`flex items-center font-semibold ${performance.daily_change >= 0 ? "text-success" : "text-destructive"}`}>
                    {performance.daily_change >= 0 ? <TrendingUp className="w-5 h-5 mr-1" /> : <TrendingDown className="w-5 h-5 mr-1" />}
                    <span>{formatPercentage(performance.daily_change)}</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Historical Performance</CardTitle>
                    <CardDescription>Portfolio value over time.</CardDescription>
                  </div>
                  <Select value={timeRange} onValueChange={setTimeRange}>
                    <SelectTrigger className="w-24"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1M">1M</SelectItem>
                      <SelectItem value="3M">3M</SelectItem>
                      <SelectItem value="6M">6M</SelectItem>
                      <SelectItem value="1Y">1Y</SelectItem>
                      <SelectItem value="ALL">All</SelectItem>
                    </SelectContent>
                  </Select>
                </CardHeader>
                <CardContent className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey="date" tickFormatter={(str) => new Date(str).toLocaleDateString("en-US", { month: "short" })} axisLine={false} tickLine={false} stroke="hsl(var(--muted-foreground))" />
                      <YAxis tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`} axisLine={false} tickLine={false} width={40} stroke="hsl(var(--muted-foreground))" />
                      <Tooltip contentStyle={{ backgroundColor: "hsl(var(--background))", borderColor: "hsl(var(--border))", color: "hsl(var(--foreground))" }} />
                      <Line type="monotone" dataKey="value" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-1 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Asset Allocation</CardTitle>
                  <CardDescription>Your portfolio diversification.</CardDescription>
                </CardHeader>
                <CardContent className="h-80 flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={assets} dataKey="value_usd" nameKey="name" cx="50%" cy="50%" outerRadius={80} labelLine={false} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                          {assets.map((entry, index) => <Cell key={`cell-${index}`} fill={PIE_CHART_COLORS[index % PIE_CHART_COLORS.length]} />)}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: "hsl(var(--background))", borderColor: "hsl(var(--border))", color: "hsl(var(--foreground))" }} formatter={(value, name) => [formatCurrency(value as number), name]} />
                      </PieChart>
                    </ResponsiveContainer>
                </CardContent>
              </Card>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Your Assets</CardTitle>
              <CardDescription>A detailed look at your holdings.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {assets.map((asset) => (
                  <div key={asset.symbol} className="flex items-center justify-between p-3 rounded-md hover:bg-muted/50">
                    <div className="flex items-center space-x-4">
                      <img src={asset.icon} alt={asset.name} className="w-10 h-10" />
                      <div>
                        <p className="font-semibold text-foreground">{asset.name} ({asset.symbol})</p>
                        <p className="text-sm text-muted-foreground">{asset.balance} {asset.symbol}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-foreground">{formatCurrency(asset.value_usd)}</p>
                      <div className={`flex items-center justify-end text-sm ${asset.changePercent >= 0 ? "text-success" : "text-destructive"}`}>
                        {asset.changePercent >= 0 ? <ArrowUp className="w-4 h-4 mr-1" /> : <ArrowDown className="w-4 h-4 mr-1" />}
                        {formatPercentage(asset.changePercent)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Transactions</CardTitle>
              <CardDescription>Your latest trading activity.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {transactions.map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between p-3 rounded-md hover:bg-muted/50">
                    <div className="flex items-center space-x-4">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center ${tx.type === 'buy' ? 'bg-success/20 text-success' : 'bg-destructive/20 text-destructive'}`}>
                        {tx.type === 'buy' ? <ArrowUpRight className="w-5 h-5" /> : <ArrowDownRight className="w-5 h-5" />}
                      </div>
                      <div>
                        <p className="font-semibold text-foreground">{tx.type === "buy" ? "Bought" : "Sold"} {tx.asset}</p>
                        <p className="text-sm text-muted-foreground">{new Date(tx.date).toLocaleDateString()}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-foreground">{formatCurrency(tx.value)}</p>
                      <p className="text-sm text-muted-foreground">{tx.amount} {tx.asset}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <Button variant="outline" className="w-full">View All Transactions</Button>
              </div>
            </CardContent>
          </Card>
        </main>
        </div>
      </div>
    </AuthenticatedLayout>
  );
}

export default PortfolioPage;
