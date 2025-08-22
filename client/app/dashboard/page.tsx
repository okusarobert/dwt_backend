"use client";

import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";
import { useEffect, useState, ReactNode } from "react";
import { apiClient } from "@/lib/api-client";
import { formatDistanceToNow } from "date-fns";
import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RealTimePrices } from "@/components/crypto/real-time-prices";
import { AuthMiddleware } from "@/components/auth/auth-middleware";
import {
  Wallet,
  TrendingUp,
  ArrowLeftRight,
  Activity,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  LogOut,
} from "lucide-react";

// Type definitions
interface Activity {
  id: string;
  type: string;
  description: string;
  amount: number;
  currency: string;
  created_at: string;
}

interface DashboardData {
  total_portfolio_value: number;
  portfolio_change_24h_pct: number;
  total_assets: number;
  recent_activity: Activity[];
  portfolio_details?: any;
  multi_chain_summary?: {
    total_currencies: number;
    multi_chain_tokens: Record<string, any>;
  };
}

const formatCurrency = (value: number, currency: string = "USD"): string => {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const getActivityIcon = (type: string): ReactNode => {
  switch (type) {
    case "DEPOSIT":
    case "BUY":
      return <ArrowDownRight className="w-4 h-4 text-green-600 dark:text-green-400" />;
    case "WITHDRAWAL":
    case "SELL":
      return <ArrowUpRight className="w-4 h-4 text-red-600 dark:text-red-400" />;
    case "SWAP":
      return <ArrowLeftRight className="w-4 h-4 text-blue-600 dark:text-blue-400" />;
    default:
      return <Activity className="w-4 h-4 text-gray-500" />;
  }
};

function DashboardContent() {
  const { user, logout, isLoading: isAuthLoading } = useAuth();
  const router = useRouter();

  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      if (!user) return;
      try {
        setIsLoadingData(true);
        
        // Fetch both dashboard summary and detailed crypto balances
        const [dashboardResponse, balancesResponse] = await Promise.all([
          apiClient.getDashboardSummary(),
          apiClient.getDetailedCryptoBalances().catch(() => null) // Fallback if detailed balances fail
        ]);
        
        // Enhance dashboard data with portfolio information
        const enhancedData = {
          ...dashboardResponse.data,
          portfolio_details: balancesResponse,
          total_portfolio_value: balancesResponse?.portfolio_value?.total_value_usd || dashboardResponse.data.total_portfolio_value,
          multi_chain_summary: balancesResponse?.balance_summary
        };
        
        setDashboardData(enhancedData);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
        setError("Could not load dashboard data. Please try again later.");
      } finally {
        setIsLoadingData(false);
      }
    };

    fetchDashboardData();
  }, [user]);

  const handleLogout = async () => {
    try {
      await logout();
      router.push("/auth/signin");
    } catch (error) {
      console.error("Logout failed:", error);
      router.push("/auth/signin");
    }
  };

  if (isAuthLoading || (isLoadingData && !dashboardData)) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center">
          <p className="text-lg text-muted-foreground">Loading Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="text-center p-6 bg-card border border-destructive rounded-lg">
          <h2 className="text-xl font-semibold text-destructive-foreground mb-4">Error</h2>
          <p className="text-destructive-foreground">{error}</p>
          <Button onClick={() => window.location.reload()} className="mt-4">Try Again</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container mx-auto p-4 sm:p-6 lg:p-8">
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold">Welcome, {user?.first_name || "User"}</h1>
            <p className="text-muted-foreground">Here is your financial overview.</p>
          </div>
          <Button onClick={handleLogout} variant="outline">
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </header>

        {dashboardData ? (
          <>
            {/* Stat Cards */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
            >
              <Card className="p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-semibold text-foreground">Portfolio Value</h3>
                    <Wallet className="w-6 h-6 text-muted-foreground" />
                  </div>
                  <p className="text-3xl font-bold text-foreground">
                    {formatCurrency(dashboardData.total_portfolio_value)}
                  </p>
                  <div className="flex items-center text-sm mt-4">
                    <span
                      className={`flex items-center ${dashboardData.portfolio_change_24h_pct >= 0
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-600 dark:text-red-400"
                        }`}
                    >
                      {dashboardData.portfolio_change_24h_pct >= 0 ? (
                        <TrendingUp className="w-4 h-4 mr-1" />
                      ) : (
                        <TrendingUp className="w-4 h-4 mr-1 transform -scale-y-100" />
                      )}
                      {dashboardData.portfolio_change_24h_pct.toFixed(2)}% (24h)
                    </span>
                  </div>
                </div>
              </Card>

              <Card className="p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-semibold text-foreground">Total Assets</h3>
                    <DollarSign className="w-6 h-6 text-muted-foreground" />
                  </div>
                  <p className="text-3xl font-bold text-foreground">
                    {dashboardData.multi_chain_summary?.total_currencies || dashboardData.total_assets}
                  </p>
                  <p className="text-sm text-muted-foreground mt-4">
                    {dashboardData.multi_chain_summary ? 
                      `${Object.keys(dashboardData.multi_chain_summary.multi_chain_tokens).length} multi-chain tokens` :
                      'Across all wallets'
                    }
                  </p>
                </div>
              </Card>

              <Card className="p-6 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-semibold text-foreground">Quick Actions</h3>
                    <ArrowLeftRight className="w-6 h-6 text-muted-foreground" />
                  </div>
                  <div className="mt-4 flex flex-col sm:flex-row gap-2">
                    <Button onClick={() => router.push('/trading')} className="flex-1">Trade</Button>
                    <Button onClick={() => router.push('/convert')} variant="outline" className="flex-1">Convert</Button>
                  </div>
                </div>
              </Card>
            </motion.div>

            {/* Portfolio Breakdown */}
            {dashboardData.portfolio_details && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.3 }}
                className="mb-8"
              >
                <h2 className="text-xl font-semibold text-foreground mb-4">
                  Portfolio Breakdown
                </h2>
                <Card className="p-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Object.entries(dashboardData.portfolio_details.portfolio_breakdown || {})
                      .filter(([_, data]: [string, any]) => data.balance > 0)
                      .map(([currency, data]: [string, any]) => (
                        <div key={currency} className="flex items-center justify-between p-4 bg-muted rounded-lg">
                          <div>
                            <div className="font-semibold text-foreground">{currency}</div>
                            <div className="text-sm text-muted-foreground">
                              {data.balance.toFixed(6)} {currency}
                              {data.chains && Object.keys(data.chains).length > 1 && (
                                <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                                  {Object.keys(data.chains).length} chains
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium text-foreground">
                              ${data.value_usd.toFixed(2)}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              ${data.price_usd.toFixed(2)}
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </Card>
              </motion.div>
            )}

            {/* Real-Time Crypto Prices */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
              className="mb-8"
            >
              <RealTimePrices />
            </motion.div>

            {/* Recent Activity */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              <h2 className="text-xl font-semibold text-foreground mb-4">
                Recent Activity
              </h2>
              <Card className="p-6">
                <div className="space-y-4">
                  {dashboardData.recent_activity && dashboardData.recent_activity.length > 0 ? (
                    dashboardData.recent_activity.map((tx: Activity, index: number) => (
                      <div
                        key={tx.id}
                        className={`flex items-center justify-between py-3 ${index < dashboardData.recent_activity.length - 1
                            ? "border-b border-gray-100 dark:border-gray-700"
                            : ""
                          }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center bg-gray-100 dark:bg-gray-800`}>
                            {getActivityIcon(tx.type)}
                          </div>
                          <div>
                            <p className="font-medium text-foreground">{tx.description}</p>
                            <p className="text-sm text-muted-foreground">
                              {formatCurrency(tx.amount, tx.currency)}
                            </p>
                          </div>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {formatDistanceToNow(new Date(tx.created_at), { addSuffix: true })}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="text-muted-foreground text-center">No recent activity.</p>
                  )}
                </div>
              </Card>
            </motion.div>
          </>
        ) : null}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AuthMiddleware>
      <DashboardContent />
    </AuthMiddleware>
  );
}
