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
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAuth } from "@/components/auth/auth-provider";
import { useTheme } from "@/components/theme/theme-provider";
import { toast } from "react-hot-toast";
import { Eye, EyeOff, Plus, Minus, Copy, ChevronDown, QrCode, Wallet, TrendingUp, TrendingDown, ArrowDownToLine, ArrowUpFromLine, RefreshCw, Search, Loader2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Image from "next/image";
import { QRCodeSVG } from "qrcode.react";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";
import { apiClient } from "@/lib/api-client";
import { useCryptoPrices } from '@/hooks/use-crypto-prices';
import { formatUGX, formatNumber, formatCryptoAmount } from '@/lib/currency-formatter';
import NotificationCenter from '@/components/notifications/notification-center';
import { MultiChainBalance } from '@/components/crypto/multi-chain-balance';
import { useRecentTransactions } from '@/hooks/use-transactions';
import PnLDisplay from '@/components/wallet/pnl-display';

// Supported cryptocurrencies
const supportedCryptos = [
  { symbol: "BTC", name: "Bitcoin", decimals: 8 },
  { symbol: "ETH", name: "Ethereum", decimals: 18 },
  { symbol: "SOL", name: "Solana", decimals: 9 },
  { symbol: "BNB", name: "BNB", decimals: 18 },
  { symbol: "USDT", name: "Tether", decimals: 6 },
  { symbol: "TRX", name: "Tron", decimals: 6 },
  { symbol: "LTC", name: "Litecoin", decimals: 8 },
];

interface CryptoBalance {
  symbol: string;
  balance: number;
  balance_usd: number;
  balance_ugx: number;
  address?: string;
  memo?: string;
  chains?: Record<string, any>;
  all_addresses?: Array<{
    chain: string;
    address: string;
    memo?: string;
  }>;
}

interface DepositAddress {
  address: string;
  memo?: string;
  qr_code?: string;
}

export default function WalletPage() {
  const { user } = useAuth();
  const { theme } = useTheme();
  const router = useRouter();
  const [balances, setBalances] = useState<CryptoBalance[]>([]);
  const [detailedBalances, setDetailedBalances] = useState<any>(null);
  const [totalValueUGX, setTotalValueUGX] = useState(0);
  const [totalValueUSD, setTotalValueUSD] = useState(0);
  const [isLoadingBalances, setIsLoadingBalances] = useState(true);
  const [showBalances, setShowBalances] = useState(true);
  const [selectedCrypto, setSelectedCrypto] = useState("BTC");
  const [isGeneratingAddress, setIsGeneratingAddress] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [withdrawAddress, setWithdrawAddress] = useState("");
  const [isWithdrawing, setIsWithdrawing] = useState(false);
  const [logoErrors, setLogoErrors] = useState<Record<string, boolean>>({});
  const [showDepositDialog, setShowDepositDialog] = useState(false);
  const [showWithdrawDialog, setShowWithdrawDialog] = useState(false);
  const [viewMode, setViewMode] = useState<'coin' | 'wallet' | 'enhanced'>('coin');

  const { prices, getCryptoBySymbol } = useCryptoPrices();
  
  // Use TanStack Query for recent transactions
  const { 
    data: recentTransactionsData, 
    isLoading: isLoadingRecentTransactions 
  } = useRecentTransactions(5);

  // Extract recent transactions from TanStack Query
  const recentTransactions = recentTransactionsData?.transactions || [];

  // Real-time optimistic price updates
  useEffect(() => {
    if (balances.length > 0 && prices.length > 0) {
      setBalances(prevBalances => {
        let hasChanges = false;
        const updatedBalances = prevBalances.map(balance => {
          const priceData = getCryptoBySymbol(balance.symbol);
          if (priceData) {
            const newBalanceUsd = balance.balance * priceData.priceUsd;
            const newBalanceUgx = balance.balance * priceData.price;
            
            // Only update if prices have actually changed
            if (balance.balance_usd !== newBalanceUsd || balance.balance_ugx !== newBalanceUgx) {
              hasChanges = true;
              return {
                ...balance,
                balance_usd: newBalanceUsd,
                balance_ugx: newBalanceUgx,
              };
            }
          }
          return balance;
        });
        
        // Only trigger re-render if there are actual changes
        return hasChanges ? updatedBalances : prevBalances;
      });
      
      // Update total value in real-time
      const newTotalUgx = balances.reduce((total, balance) => {
        const priceData = getCryptoBySymbol(balance.symbol);
        if (priceData) {
          return total + (balance.balance * priceData.price);
        }
        return total + balance.balance_ugx;
      }, 0);
      
      setTotalValueUGX(newTotalUgx);
    }
  }, [prices, getCryptoBySymbol, balances]); // Real-time updates when prices change

  // Load crypto balances
  const loadBalances = async () => {
    try {
      setIsLoadingBalances(true);
      
      if (viewMode === 'enhanced') {
        // Use detailed aggregated balances API
        const result = await apiClient.getDetailedCryptoBalances();
        console.log('Detailed balances result:', result);
        
        if (!result || !result.aggregated_balances) {
          console.error('Invalid detailed balances response:', result);
          toast.error('Invalid response from detailed balances API');
          return;
        }
        
        setDetailedBalances(result);
        setTotalValueUGX(result.portfolio_value?.total_value_target || 0);
        setTotalValueUSD(result.portfolio_value?.total_value_usd || 0);
        
        // Transform detailed balances for backward compatibility
        const balanceList: CryptoBalance[] = supportedCryptos.map(crypto => {
          const balanceData = result.aggregated_balances[crypto.symbol];
          if (!balanceData) {
            return {
              symbol: crypto.symbol,
              balance: 0,
              balance_usd: 0,
              balance_ugx: 0,
            };
          }
          
          const portfolioData = result.portfolio_value?.currencies[crypto.symbol];
          const balance_usd = portfolioData?.value_usd || 0;
          const balance_ugx = balance_usd * 3700; // Approximate UGX conversion
          
          return {
            symbol: crypto.symbol,
            balance: balanceData.total_balance,
            balance_usd,
            balance_ugx,
            chains: balanceData.chains,
            all_addresses: balanceData.addresses,
          };
        });
        
        setBalances(balanceList);
      } else {
        // Use legacy API for backward compatibility
        const result = await apiClient.getCryptoBalances();
        
        // Transform balances data
        const balanceList: CryptoBalance[] = supportedCryptos.map(crypto => {
          const balanceData = result.balances[crypto.symbol];
          const balance = typeof balanceData === 'object' ? balanceData.balance : (balanceData || 0);
          const address = typeof balanceData === 'object' ? balanceData.address : undefined;
          const memo = typeof balanceData === 'object' ? balanceData.memo : undefined;
          
          // Use existing price data from current balances state if available to prevent UI flicker
          const existingBalance = balances.find(b => b.symbol === crypto.symbol);
          const priceData = getCryptoBySymbol(crypto.symbol);
          const balance_ugx = balance * (priceData?.price || (existingBalance ? existingBalance.balance_ugx / existingBalance.balance : 0) || 0);
          
          return {
            symbol: crypto.symbol,
            balance,
            balance_usd: balance * (priceData?.priceUsd || (existingBalance ? existingBalance.balance_usd / existingBalance.balance : 0) || 0),
            balance_ugx,
            address,
            memo,
          };
        });
        
        setBalances(balanceList);
        setTotalValueUGX(result.total_value_ugx || 0);
        setTotalValueUSD(result.total_value_usd || 0);
      }
    } catch (error) {
      console.error('Failed to load balances:', error);
      toast.error('Failed to load wallet balances');
    } finally {
      setIsLoadingBalances(false);
    }
  };



  // Generate deposit address (fallback for cryptos without existing addresses)
  const generateDepositAddress = async (crypto: string) => {
    try {
      setIsGeneratingAddress(true);
      const response = await apiClient.generateDepositAddress(crypto);
      
      // Update the balance with the new address
      setBalances(prevBalances => 
        prevBalances.map(balance => 
          balance.symbol === crypto 
            ? { ...balance, address: response.address, memo: response.memo }
            : balance
        )
      );
      
      toast.success('Deposit address generated successfully');
    } catch (error: any) {
      console.error('Failed to generate deposit address:', error);
      toast.error(error.response?.data?.error || 'Failed to generate deposit address');
    } finally {
      setIsGeneratingAddress(false);
    }
  };

  // Execute withdrawal
  const executeWithdrawal = async () => {
    if (!withdrawAmount || !withdrawAddress) {
      toast.error('Please enter amount and address');
      return;
    }

    try {
      setIsWithdrawing(true);
      const response = await apiClient.withdrawCrypto(selectedCrypto, parseFloat(withdrawAmount), withdrawAddress);
      
      toast.success(response.message || 'Withdrawal initiated successfully');
      setWithdrawAmount("");
      setWithdrawAddress("");
      loadBalances(); // Refresh balances
    } catch (error: any) {
      console.error('Withdrawal failed:', error);
      toast.error(error.response?.data?.error || 'Withdrawal failed');
    } finally {
      setIsWithdrawing(false);
    }
  };

  // Copy to clipboard
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const handleLogoError = (symbol: string) => {
    setLogoErrors(prev => ({ ...prev, [symbol]: true }));
  };

  useEffect(() => {
    if (user) {
      loadBalances();
    }
  }, [user]); // Removed prices dependency to prevent UI distortion

  if (isLoadingBalances || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen p-6 transition-colors ${
      theme === 'dark' 
        ? 'bg-[#0B0E11] text-white' 
        : 'bg-gray-50 text-gray-900'
    }`}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-8">
          <div>
            <h1 className={`text-2xl sm:text-3xl font-bold mb-2 ${
              theme === 'dark' ? 'text-white' : 'text-black'
            }`}>
              My Assets
            </h1>
            <div className="flex items-center gap-4">
              <Dialog open={showDepositDialog} onOpenChange={setShowDepositDialog}>
                <DialogTrigger asChild>
                  <Button className={`font-medium px-6 transition-colors ${
                    theme === 'dark'
                      ? 'bg-[#F0B90B] hover:bg-[#F0B90B]/90 text-black'
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}>Deposit</Button>
                </DialogTrigger>
                <DialogContent className={`max-w-md ${
                  theme === 'dark' ? 'bg-[#1E2329] border-[#2B3139]' : 'bg-white border-gray-200'
                }`}>
                  <DialogHeader>
                    <DialogTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
                      Deposit Cryptocurrency
                    </DialogTitle>
                    <DialogDescription className={theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'}>
                      Select a cryptocurrency to generate a deposit address
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <label className={`block text-sm font-medium mb-2 ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>
                        Select Cryptocurrency
                      </label>
                      <select
                        value={selectedCrypto}
                        onChange={(e) => setSelectedCrypto(e.target.value)}
                        className={`w-full p-3 rounded-md border transition-colors ${
                          theme === 'dark'
                            ? 'bg-[#2B3139] border-[#2B3139] text-white focus:border-[#F0B90B]'
                            : 'bg-gray-50 border-gray-300 text-gray-900 focus:border-blue-500'
                        }`}
                      >
                        {supportedCryptos.map((crypto) => (
                          <option key={crypto.symbol} value={crypto.symbol}>
                            {crypto.name} ({crypto.symbol})
                          </option>
                        ))}
                      </select>
                    </div>
                    
                    {(() => {
                      const selectedBalance = balances.find(b => b.symbol === selectedCrypto);
                      return selectedBalance?.address && (
                        <div className="space-y-3">
                          <div>
                            <label className={`block text-sm font-medium mb-2 ${
                              theme === 'dark' ? 'text-white' : 'text-gray-900'
                            }`}>
                              Deposit Address
                            </label>
                            <div className={`p-3 rounded-md border break-all text-sm ${
                              theme === 'dark'
                                ? 'bg-[#2B3139] border-[#2B3139] text-white'
                                : 'bg-gray-50 border-gray-300 text-gray-900'
                            }`}>
                              {selectedBalance.address}
                            </div>
                            <Button
                              onClick={() => copyToClipboard(selectedBalance.address!)}
                              variant="outline"
                              size="sm"
                              className={`mt-2 ${
                                theme === 'dark'
                                  ? 'border-[#2B3139] text-white hover:bg-[#2B3139]'
                                  : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                              }`}
                            >
                              <Copy className="w-4 h-4 mr-2" />
                              Copy Address
                            </Button>
                          </div>
                          
                          {selectedBalance.memo && (
                            <div>
                              <label className={`block text-sm font-medium mb-2 ${
                                theme === 'dark' ? 'text-white' : 'text-gray-900'
                              }`}>
                                Memo/Tag
                              </label>
                              <div className={`p-3 rounded-md border break-all text-sm ${
                                theme === 'dark'
                                  ? 'bg-[#2B3139] border-[#2B3139] text-white'
                                  : 'bg-gray-50 border-gray-300 text-gray-900'
                              }`}>
                                {selectedBalance.memo}
                              </div>
                              <Button
                                onClick={() => copyToClipboard(selectedBalance.memo!)}
                                variant="outline"
                                size="sm"
                                className={`mt-2 ${
                                  theme === 'dark'
                                    ? 'border-[#2B3139] text-white hover:bg-[#2B3139]'
                                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                                }`}
                              >
                                <Copy className="w-4 h-4 mr-2" />
                                Copy Memo
                              </Button>
                            </div>
                          )}
                          
                          <div className="flex justify-center">
                            <QRCodeSVG value={selectedBalance.address} size={200} />
                          </div>
                        </div>
                      );
                    })()}
                    
                    {(() => {
                      const selectedBalance = balances.find(b => b.symbol === selectedCrypto);
                      return !selectedBalance?.address && (
                        <Button
                          onClick={() => generateDepositAddress(selectedCrypto)}
                          disabled={isGeneratingAddress}
                          className={`w-full ${
                            theme === 'dark'
                              ? 'bg-[#F0B90B] hover:bg-[#F0B90B]/90 text-black'
                              : 'bg-blue-600 hover:bg-blue-700 text-white'
                          }`}
                        >
                          {isGeneratingAddress ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                              Generating...
                            </>
                          ) : (
                            'Generate Deposit Address'
                          )}
                        </Button>
                      );
                    })()}
                  </div>
                </DialogContent>
              </Dialog>
              
              <Dialog open={showWithdrawDialog} onOpenChange={setShowWithdrawDialog}>
                <DialogTrigger asChild>
                  <Button variant="outline" className={`px-6 transition-colors ${
                    theme === 'dark'
                      ? 'border-[#2B3139] text-white hover:bg-[#2B3139]'
                      : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}>
                    Withdraw
                  </Button>
                </DialogTrigger>
                <DialogContent className={`max-w-md ${
                  theme === 'dark' ? 'bg-[#1E2329] border-[#2B3139]' : 'bg-white border-gray-200'
                }`}>
                  <DialogHeader>
                    <DialogTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
                      Withdraw Cryptocurrency
                    </DialogTitle>
                    <DialogDescription className={theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'}>
                      Send cryptocurrency to an external wallet
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div>
                      <label className={`block text-sm font-medium mb-2 ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>
                        Select Cryptocurrency
                      </label>
                      <select
                        value={selectedCrypto}
                        onChange={(e) => setSelectedCrypto(e.target.value)}
                        className={`w-full p-3 rounded-md border transition-colors ${
                          theme === 'dark'
                            ? 'bg-[#2B3139] border-[#2B3139] text-white focus:border-[#F0B90B]'
                            : 'bg-gray-50 border-gray-300 text-gray-900 focus:border-blue-500'
                        }`}
                      >
                        {supportedCryptos.map((crypto) => {
                          const balance = balances.find(b => b.symbol === crypto.symbol);
                          return (
                            <option key={crypto.symbol} value={crypto.symbol}>
                              {crypto.name} ({crypto.symbol}) - Balance: {balance ? formatNumber(balance.balance, 6) : '0'}
                            </option>
                          );
                        })}
                      </select>
                    </div>
                    
                    <div>
                      <label className={`block text-sm font-medium mb-2 ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>
                        Withdrawal Address
                      </label>
                      <Input
                        value={withdrawAddress}
                        onChange={(e) => setWithdrawAddress(e.target.value)}
                        placeholder="Enter destination address"
                        className={`transition-colors ${
                          theme === 'dark'
                            ? 'bg-[#2B3139] border-[#2B3139] text-white placeholder-[#848E9C] focus:border-[#F0B90B]'
                            : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400 focus:border-blue-500'
                        }`}
                      />
                    </div>
                    
                    <div>
                      <label className={`block text-sm font-medium mb-2 ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>
                        Amount
                      </label>
                      <Input
                        type="number"
                        value={withdrawAmount}
                        onChange={(e) => setWithdrawAmount(e.target.value)}
                        placeholder="Enter amount"
                        step="0.000001"
                        min="0"
                        className={`transition-colors ${
                          theme === 'dark'
                            ? 'bg-[#2B3139] border-[#2B3139] text-white placeholder-[#848E9C] focus:border-[#F0B90B]'
                            : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-400 focus:border-blue-500'
                        }`}
                      />
                      {(() => {
                        const balance = balances.find(b => b.symbol === selectedCrypto);
                        return balance && (
                          <p className={`text-sm mt-1 ${
                            theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                          }`}>
                            Available: {formatNumber(balance.balance, 6)} {selectedCrypto}
                          </p>
                        );
                      })()}
                    </div>
                    
                    <Button
                      onClick={executeWithdrawal}
                      disabled={isWithdrawing || !withdrawAmount || !withdrawAddress}
                      className={`w-full ${
                        theme === 'dark'
                          ? 'bg-[#F0B90B] hover:bg-[#F0B90B]/90 text-black'
                          : 'bg-blue-600 hover:bg-blue-700 text-white'
                      }`}
                    >
                      {isWithdrawing ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        'Withdraw'
                      )}
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
              
              <Button variant="outline" className={`px-6 transition-colors ${
                theme === 'dark'
                  ? 'border-[#2B3139] text-white hover:bg-[#2B3139]'
                  : 'border-gray-400 text-black hover:bg-gray-50'
              }`}>
                Cash In
              </Button>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className={`text-sm mb-1 ${
                theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-700'
              }`}>Estimated Balance</div>
              <div className={`text-2xl font-bold mb-2 transition-all duration-500 ${
                theme === 'dark' ? 'text-white' : 'text-black'
              }`}>
                <span className="tabular-nums">
                  {showBalances ? formatUGX(totalValueUGX) : "••••••••••"}
                </span>
                <span className={`text-sm ml-2 ${
                  theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-700'
                }`}>UGX</span>
              </div>
              <PnLDisplay theme={theme} />
            </div>
            <div className="flex items-center gap-2">
              <NotificationCenter />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowBalances(!showBalances)}
                className={`transition-colors ${
                  theme === 'dark'
                    ? 'text-[#B7BDC6] hover:text-white hover:bg-[#2B3139]'
                    : 'text-gray-700 hover:text-black hover:bg-gray-100'
                }`}
              >
                {showBalances ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        </div>

        {/* Assets Table */}
        <div className={`rounded-lg overflow-hidden transition-colors ${
          theme === 'dark' 
            ? 'bg-[#1E2329]' 
            : 'bg-white border border-gray-200 shadow-sm'
        }`}>
          <div className={`flex items-center justify-between p-6 border-b transition-colors ${
            theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'
          }`}>
            <div className="flex items-center gap-4">
              <h1 className={`text-2xl font-bold mb-2 ${
              theme === 'dark' ? 'text-white' : 'text-black'
            }`}>My Assets</h1>
              <div className={`flex rounded-md ${
                theme === 'dark' ? 'bg-[#2B3139]' : 'bg-gray-100'
              }`}>
                <button 
                  onClick={() => setViewMode('coin')}
                  className={`px-4 py-2 text-sm font-medium rounded-l-md border-b-2 transition-colors ${
                    viewMode === 'coin'
                      ? (theme === 'dark'
                          ? 'text-[#F0B90B] bg-[#2B3139] border-[#F0B90B]'
                          : 'text-blue-600 bg-gray-100 border-blue-600')
                      : (theme === 'dark'
                          ? 'text-[#B7BDC6] hover:text-white bg-transparent border-transparent'
                          : 'text-gray-600 hover:text-gray-900 bg-transparent border-transparent')
                  }`}>
                  Coin View
                </button>
                <button 
                  onClick={() => setViewMode('wallet')}
                  className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    viewMode === 'wallet'
                      ? (theme === 'dark'
                          ? 'text-[#F0B90B] bg-[#2B3139] border-[#F0B90B]'
                          : 'text-blue-600 bg-gray-100 border-blue-600')
                      : (theme === 'dark'
                          ? 'text-[#B7BDC6] hover:text-white bg-transparent border-transparent'
                          : 'text-gray-600 hover:text-gray-900 bg-transparent border-transparent')
                  }`}>
                  Multi-Chain
                </button>
                <button 
                  onClick={() => setViewMode('enhanced')}
                  className={`px-4 py-2 text-sm font-medium rounded-r-md border-b-2 transition-colors ${
                    viewMode === 'enhanced'
                      ? (theme === 'dark'
                          ? 'text-[#F0B90B] bg-[#2B3139] border-[#F0B90B]'
                          : 'text-blue-600 bg-gray-100 border-blue-600')
                      : (theme === 'dark'
                          ? 'text-[#B7BDC6] hover:text-white bg-transparent border-transparent'
                          : 'text-gray-600 hover:text-gray-900 bg-transparent border-transparent')
                  }`}>
                  Enhanced
                </button>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="relative">
                <Search className={`absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 ${
                  theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-500'
                }`} />
                <Input
                  placeholder="Search..."
                  className={`pl-10 w-64 transition-colors ${
                    theme === 'dark'
                      ? 'bg-[#2B3139] border-[#2B3139] text-white placeholder-[#B7BDC6] focus:border-[#F0B90B]'
                      : 'bg-gray-50 border-gray-300 text-gray-900 placeholder-gray-500 focus:border-blue-500'
                  }`}
                />
                <Search className="w-4 h-4 text-[#B7BDC6] absolute right-3 top-1/2 transform -translate-y-1/2" />
              </div>
              <button className={`text-sm font-medium transition-colors ${
                theme === 'dark'
                  ? 'text-[#F0B90B] hover:text-[#F0B90B]/80'
                  : 'text-blue-600 hover:text-blue-700'
              }`}>
                View All &gt;
              </button>
            </div>
          </div>
          
          {isLoadingBalances ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#F0B90B]"></div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              {viewMode === 'enhanced' && detailedBalances ? (
                // Multi-chain aggregated view
                <div className="p-6 space-y-4">
                  {Object.entries(detailedBalances.aggregated_balances)
                    .filter(([_, data]: [string, any]) => data.total_balance > 0)
                    .map(([currency, data]: [string, any]) => {
                      // Use API portfolio data for accurate USD prices
                      const portfolioData = detailedBalances.portfolio_value?.currencies[currency];
                      const priceUsd = portfolioData?.price_usd || 0;
                      
                      return (
                        <MultiChainBalance
                          key={currency}
                          currency={currency}
                          data={data}
                          priceUsd={priceUsd}
                          theme={theme}
                        />
                      );
                    })}
                  
                  {/* Portfolio Summary */}
                  {detailedBalances.aggregation_summary && (
                    <div className={`mt-8 p-6 rounded-lg ${
                      theme === 'dark' ? 'bg-[#2B3139]' : 'bg-gray-50'
                    }`}>
                      <h3 className={`text-lg font-semibold mb-4 ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>
                        Portfolio Summary
                      </h3>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className={`p-4 rounded-lg ${
                          theme === 'dark' ? 'bg-[#1E2329]' : 'bg-white'
                        }`}>
                          <div className={`text-sm ${
                            theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                          }`}>
                            Total Currencies
                          </div>
                          <div className={`text-2xl font-bold ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>
                            {detailedBalances.aggregation_summary.total_currencies}
                          </div>
                        </div>
                        
                        <div className={`p-4 rounded-lg ${
                          theme === 'dark' ? 'bg-[#1E2329]' : 'bg-white'
                        }`}>
                          <div className={`text-sm ${
                            theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                          }`}>
                            Multi-Chain Tokens
                          </div>
                          <div className={`text-2xl font-bold ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>
                            {Object.keys(detailedBalances.aggregation_summary.multi_chain_tokens).length}
                          </div>
                        </div>
                        
                        <div className={`p-4 rounded-lg ${
                          theme === 'dark' ? 'bg-[#1E2329]' : 'bg-white'
                        }`}>
                          <div className={`text-sm ${
                            theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                          }`}>
                            Total Value (USD)
                          </div>
                          <div className={`text-2xl font-bold ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>
                            ${formatNumber(detailedBalances.total_value_usd, 2)}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : viewMode === 'coin' ? (
                <table className="w-full">
                  <thead className={theme === 'dark' ? 'bg-[#2B3139]' : 'bg-gray-50'}>
                    <tr>
                      <th className={`text-left py-4 px-6 text-sm font-medium ${
                        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                      }`}>Coin</th>
                      <th className={`text-right py-4 px-6 text-sm font-medium ${
                        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                      }`}>Amount</th>
                      <th className={`text-right py-4 px-6 text-sm font-medium ${
                        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                      }`}>Coin Price</th>
                      <th className={`text-right py-4 px-6 text-sm font-medium ${
                        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                      }`}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                  {balances.map((asset, index) => {
                    const logoPath = getCryptoLogo(asset.symbol);
                    const fallbackLogo = createFallbackLogo(asset.symbol);
                    const priceData = getCryptoBySymbol(asset.symbol);
                    
                    return (
                      <motion.tr
                        key={asset.symbol}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.05 }}
                        className={`border-b transition-colors ${
                          theme === 'dark' 
                            ? 'border-[#2B3139] hover:bg-[#2B3139]/50' 
                            : 'border-gray-200 hover:bg-gray-50'
                        }`}
                      >
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-3">
                            <div className="relative">
                              {!logoErrors[asset.symbol] ? (
                                <Image
                                  src={logoPath}
                                  alt={`${asset.symbol} logo`}
                                  width={32}
                                  height={32}
                                  className="rounded-full"
                                  onError={() => handleLogoError(asset.symbol)}
                                />
                              ) : (
                                <Image
                                  src={fallbackLogo}
                                  alt={`${asset.symbol} logo`}
                                  width={32}
                                  height={32}
                                  className="rounded-full"
                                />
                              )}
                              {asset.balance > 0 && (
                                <div className={`absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 ${
                                  theme === 'dark' ? 'border-[#1E2329]' : 'border-white'
                                }`}></div>
                              )}
                            </div>
                            <div>
                              <div className={`font-semibold ${
                                theme === 'dark' ? 'text-white' : 'text-gray-900'
                              }`}>{supportedCryptos.find(c => c.symbol === asset.symbol)?.name || asset.symbol}</div>
                              <div className={`text-sm flex items-center gap-2 ${
                                theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                              }`}>
                                {asset.symbol}
                                {priceData && (
                                  <span className={`text-xs px-1.5 py-0.5 rounded transition-all duration-300 ${
                                    priceData.changePercent24h >= 0 
                                      ? 'bg-green-500/20 text-green-500' 
                                      : 'bg-red-500/20 text-red-500'
                                  }`}>
                                    {priceData.changePercent24h >= 0 ? '+' : ''}{priceData.changePercent24h.toFixed(2)}%
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className={`font-medium transition-all duration-300 ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>
                            {showBalances ? (
                              <div className="flex flex-col items-end">
                                <span>{formatNumber(asset.balance, 6)}</span>
                                <span className={`text-xs ${
                                  theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                                }`}>
                                  ≈ ${formatNumber(asset.balance_usd, 2)}
                                </span>
                              </div>
                            ) : "••••••"}
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className={`font-medium transition-all duration-300 ${
                            theme === 'dark' ? 'text-white' : 'text-gray-900'
                          }`}>
                            {priceData ? (
                              <div className="flex flex-col items-end">
                                <span>${priceData.priceUsd.toFixed(2)}</span>
                                <span className={`text-xs transition-colors ${
                                  priceData.changePercent24h >= 0 ? 'text-green-500' : 'text-red-500'
                                }`}>
                                  {priceData.changePercent24h >= 0 ? '+' : ''}{priceData.changePercent24h.toFixed(2)}%
                                </span>
                              </div>
                            ) : (
                              <div className="flex flex-col items-end">
                                <span>--</span>
                                <span className="text-xs text-gray-500">--</span>
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className="relative">
                            <select 
                              className={`rounded text-sm px-3 py-1 focus:outline-none appearance-none cursor-pointer min-w-[100px] transition-colors ${
                                theme === 'dark'
                                  ? 'bg-[#2B3139] border border-[#2B3139] text-white focus:border-[#F0B90B]'
                                  : 'bg-gray-50 border border-gray-300 text-gray-900 focus:border-blue-500'
                              }`}
                              defaultValue="Cash In"
                              onChange={(e) => {
                                const action = e.target.value;
                                if (action === 'Deposit') {
                                  setSelectedCrypto(asset.symbol);
                                  setShowDepositDialog(true);
                                } else if (action === 'Withdraw') {
                                  setSelectedCrypto(asset.symbol);
                                  setShowWithdrawDialog(true);
                                }
                                // Reset the select to default
                                e.target.value = 'Cash In';
                              }}
                            >
                              <option value="Cash In">Cash In</option>
                              <option value="Deposit">Deposit</option>
                              <option value="Withdraw">Withdraw</option>
                            </select>
                            <ChevronDown className={`w-4 h-4 absolute right-2 top-1/2 transform -translate-y-1/2 pointer-events-none ${
                              theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-500'
                            }`} />
                          </div>
                        </td>
                      </motion.tr>
                    );
                  })}

                  </tbody>
                </table>
              ) : (
                <div className="space-y-4">
                  {/* Wallet View - Group by wallet addresses */}
                  {(() => {
                    // Group balances by wallet address
                    const walletGroups = balances.reduce((groups, balance) => {
                      const walletKey = balance.address || 'No Address';
                      if (!groups[walletKey]) {
                        groups[walletKey] = [];
                      }
                      groups[walletKey].push(balance);
                      return groups;
                    }, {} as Record<string, typeof balances>);

                    return Object.entries(walletGroups).map(([address, walletBalances]) => {
                      const totalWalletValue = walletBalances.reduce((sum, balance) => sum + balance.balance_ugx, 0);
                      const hasAddress = address !== 'No Address';
                      
                      return (
                        <div key={address} className={`rounded-lg border transition-colors ${
                          theme === 'dark' 
                            ? 'bg-[#2B3139] border-[#2B3139]' 
                            : 'bg-gray-50 border-gray-200'
                        }`}>
                          <div className="p-4 border-b border-inherit">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                                  hasAddress 
                                    ? 'bg-green-500/20 text-green-500' 
                                    : 'bg-gray-500/20 text-gray-500'
                                }`}>
                                  <Wallet className="w-5 h-5" />
                                </div>
                                <div>
                                  <div className={`font-semibold ${
                                    theme === 'dark' ? 'text-white' : 'text-gray-900'
                                  }`}>
                                    {hasAddress ? 'Main Wallet' : 'Pending Setup'}
                                  </div>
                                  <div className={`text-sm ${
                                    theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                                  }`}>
                                    {hasAddress 
                                      ? `${address.slice(0, 8)}...${address.slice(-8)}`
                                      : 'Address not generated'
                                    }
                                  </div>
                                </div>
                              </div>
                              <div className="text-right">
                                <div className={`font-semibold ${
                                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                                }`}>
                                  {showBalances ? formatUGX(totalWalletValue) : '••••••'}
                                </div>
                                <div className={`text-sm ${
                                  theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                                }`}>
                                  {walletBalances.length} assets
                                </div>
                              </div>
                            </div>
                          </div>
                          <div className="p-4">
                            <div className="grid gap-3">
                              {walletBalances.map((asset) => {
                                const logoPath = getCryptoLogo(asset.symbol);
                                const fallbackLogo = createFallbackLogo(asset.symbol);
                                const priceData = getCryptoBySymbol(asset.symbol);
                                
                                return (
                                  <div key={asset.symbol} className={`flex items-center justify-between p-3 rounded-md transition-colors ${
                                    theme === 'dark' 
                                      ? 'hover:bg-[#1E2329]' 
                                      : 'hover:bg-white'
                                  }`}>
                                    <div className="flex items-center gap-3">
                                      <div className="relative">
                                        {!logoErrors[asset.symbol] ? (
                                          <Image
                                            src={logoPath}
                                            alt={`${asset.symbol} logo`}
                                            width={24}
                                            height={24}
                                            className="rounded-full"
                                            onError={() => handleLogoError(asset.symbol)}
                                          />
                                        ) : (
                                          <Image
                                            src={fallbackLogo}
                                            alt={`${asset.symbol} logo`}
                                            width={24}
                                            height={24}
                                            className="rounded-full"
                                          />
                                        )}
                                        {asset.balance > 0 && (
                                          <div className={`absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full border ${
                                            theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-50'
                                          }`}></div>
                                        )}
                                      </div>
                                      <div>
                                        <div className={`font-medium text-sm ${
                                          theme === 'dark' ? 'text-white' : 'text-gray-900'
                                        }`}>
                                          {supportedCryptos.find(c => c.symbol === asset.symbol)?.name || asset.symbol}
                                        </div>
                                        <div className={`text-xs ${
                                          theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                                        }`}>
                                          {showBalances ? formatNumber(asset.balance, 6) : '••••••'} {asset.symbol}
                                        </div>
                                      </div>
                                    </div>
                                    <div className="text-right">
                                      <div className={`font-medium text-sm ${
                                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                                      }`}>
                                        {showBalances ? `$${formatNumber(asset.balance_usd, 2)}` : '••••••'}
                                      </div>
                                      {priceData && (
                                        <div className={`text-xs ${
                                          priceData.changePercent24h >= 0 ? 'text-green-500' : 'text-red-500'
                                        }`}>
                                          {priceData.changePercent24h >= 0 ? '+' : ''}{priceData.changePercent24h.toFixed(2)}%
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      );
                    });
                  })()}
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Recent Transactions Section */}
        <div className={`rounded-lg overflow-hidden mt-8 transition-colors ${
          theme === 'dark' 
            ? 'bg-[#1E2329]' 
            : 'bg-white border border-gray-200 shadow-sm'
        }`}>
          <div className={`flex items-center justify-between p-6 border-b transition-colors ${
            theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'
          }`}>
            <h2 className={`text-lg font-semibold ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>Recent Transactions</h2>
            <button 
              onClick={() => router.push('/dashboard/transactions')}
              className={`text-sm font-medium transition-colors ${
                theme === 'dark'
                  ? 'text-[#F0B90B] hover:text-[#F0B90B]/80'
                  : 'text-blue-600 hover:text-blue-700'
              }`}
            >
              View All &gt;
            </button>
          </div>
          <div className="p-6">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className={`border-b ${
                    theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'
                  }`}>
                    <th className={`text-left py-3 px-4 text-sm font-medium ${
                      theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                    }`}>Transactions</th>
                    <th className={`text-right py-3 px-4 text-sm font-medium ${
                      theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                    }`}>Amount</th>
                    <th className={`text-right py-3 px-4 text-sm font-medium ${
                      theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                    }`}>Date</th>
                    <th className={`text-right py-3 px-4 text-sm font-medium ${
                      theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                    }`}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoadingRecentTransactions ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span className={`text-sm ${
                            theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                          }`}>Loading transactions...</span>
                        </div>
                      </td>
                    </tr>
                  ) : recentTransactions.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center">
                        <div className={`text-sm ${
                          theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                        }`}>No recent transactions</div>
                      </td>
                    </tr>
                  ) : (
                    recentTransactions.map((transaction) => {
                      const isDeposit = transaction.type?.toLowerCase() === 'deposit';
                      const isWithdrawal = transaction.type?.toLowerCase() === 'withdrawal';
                      const currency = transaction.metadata_json?.currency || transaction.currency || 'UGX';
                      
                      // Get the correct amount based on currency type
                      let amount = transaction.amount || 0;
                      if (transaction.metadata_json) {
                        switch (currency.toUpperCase()) {
                          case 'ETH':
                            amount = parseFloat(transaction.metadata_json.amount_eth || transaction.amount || 0);
                            break;
                          case 'TRX':
                            amount = parseFloat(transaction.metadata_json.amount_trx || transaction.amount || 0);
                            break;
                          case 'BTC':
                            amount = parseFloat(transaction.metadata_json.amount_btc || transaction.amount || 0);
                            break;
                          default:
                            amount = parseFloat(transaction.amount || 0);
                        }
                      }
                      
                      const date = new Date(transaction.created_at);
                      
                      // Get status color
                      const getStatusColor = (status: string) => {
                        switch (status?.toLowerCase()) {
                          case 'completed':
                            return 'bg-green-500/20 text-green-500';
                          case 'pending':
                          case 'awaiting_confirmation':
                            return 'bg-yellow-500/20 text-yellow-500';
                          case 'failed':
                          case 'cancelled':
                            return 'bg-red-500/20 text-red-500';
                          default:
                            return 'bg-gray-500/20 text-gray-500';
                        }
                      };
                      
                      return (
                        <tr 
                          key={transaction.id} 
                          onClick={() => router.push(`/dashboard/transactions/${transaction.id}`)}
                          className={`border-b transition-colors cursor-pointer ${
                            theme === 'dark'
                              ? 'border-[#2B3139] hover:bg-[#2B3139]/30'
                              : 'border-gray-200 hover:bg-gray-100'
                          }`}
                        >
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-3">
                              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                isDeposit ? 'bg-green-500/20' : isWithdrawal ? 'bg-red-500/20' : 'bg-blue-500/20'
                              }`}>
                                {isDeposit ? (
                                  <ArrowDownToLine className="w-4 h-4 text-green-500" />
                                ) : isWithdrawal ? (
                                  <ArrowUpFromLine className="w-4 h-4 text-red-500" />
                                ) : (
                                  <RefreshCw className="w-4 h-4 text-blue-500" />
                                )}
                              </div>
                              <div>
                                <div className={`font-medium ${
                                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                                }`}>
                                  {transaction.type?.charAt(0).toUpperCase() + transaction.type?.slice(1).toLowerCase() || 'Transaction'} {currency}
                                </div>
                                <div className={`text-sm ${
                                  theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                                }`}>
                                  {transaction.description || (isDeposit ? 'From External Wallet' : isWithdrawal ? 'To External Wallet' : 'Transaction')}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className={`font-medium tabular-nums transition-all duration-300 ${
                              isDeposit ? 'text-green-500' : isWithdrawal ? 'text-red-500' : theme === 'dark' ? 'text-white' : 'text-gray-900'
                            }`}>
                              {isDeposit ? '+' : isWithdrawal ? '-' : ''}{formatCryptoAmount(amount, currency)} {currency}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className={`text-sm ${
                              theme === 'dark' ? 'text-[#848E9C]' : 'text-gray-500'
                            }`}>
                              {date.toLocaleString('en-CA', {
                                year: 'numeric',
                                month: '2-digit',
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                                hour12: false
                              })}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span className={`px-2 py-1 text-xs rounded-full ${getStatusColor(transaction.status)}`}>
                              {transaction.status?.charAt(0).toUpperCase() + transaction.status?.slice(1).toLowerCase().replace('_', ' ') || 'Unknown'}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
