"use client";

import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/components/auth/auth-provider";
import { toast } from "react-hot-toast";
import { ArrowDownUp, RefreshCw, Loader2, TrendingUp, History, BarChart3 } from "lucide-react";
import Image from "next/image";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";
import { apiClient } from "@/lib/api-client";
import { useCryptoPrices } from '@/hooks/use-crypto-prices';
import { MarketData } from '@/components/trading/market-data';
import { TradeHistory } from '@/components/trading/trade-history';
import { formatUGX, formatNumber } from '@/lib/currency-formatter';

// --- MOCK DATA --- //
const fiatCurrencies = [
  { code: "UGX", name: "Uganda Shilling", symbol: "USh", logo: "/logos/fiat/ugx.svg" },
];

const cryptocurrencies = [
  { code: "BTC", name: "Bitcoin", symbol: "BTC" },
  { code: "ETH", name: "Ethereum", symbol: "ETH" },
  { code: "SOL", name: "Solana", symbol: "SOL" },
  { code: "BNB", name: "BNB", symbol: "BNB" },
  { code: "USDT", name: "Tether", symbol: "USDT" },
];

// --- CURRENCY INPUT COMPONENT --- //
interface CurrencyInputProps {
  label: string;
  amount: string;
  onAmountChange: (value: string) => void;
  selectedCurrency: string;
  onCurrencyChange: (value: string) => void;
  currencies: { code: string; name: string; symbol: string }[];
  balance?: number;
  isReadOnly?: boolean;
}

const CurrencyInput: React.FC<CurrencyInputProps> = ({
  label,
  amount,
  onAmountChange,
  selectedCurrency,
  onCurrencyChange,
  currencies,
  balance,
  isReadOnly = false,
}) => {
  const [logoError, setLogoError] = useState(false);
  const currency = currencies.find((c) => c.code === selectedCurrency);
  const logoPath = currency ? getCryptoLogo(currency.symbol) : "";
  const fallbackLogo = currency ? createFallbackLogo(currency.symbol) : "";

  return (
    <div className="border rounded-lg p-4">
      <div className="flex justify-between items-center mb-3">
        <label className="text-sm font-medium text-foreground">
          {label}
        </label>
        {balance !== undefined && (
          <span className="text-xs text-muted-foreground">
            Balance: {formatNumber(balance, 8)} {selectedCurrency}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <Input
          type="number"
          value={amount}
          onChange={(e) => onAmountChange(e.target.value)}
          placeholder="0.00"
          className="text-xl font-bold bg-transparent border-none focus-visible:ring-0 focus-visible:ring-offset-0 h-auto p-0 min-w-0 flex-1"
          readOnly={isReadOnly}
        />
        {currencies.length > 1 ? (
          <Select value={selectedCurrency} onValueChange={onCurrencyChange}>
            <SelectTrigger className="min-w-[70px] sm:min-w-[90px] bg-background border-border rounded-full font-semibold flex-shrink-0 h-8 sm:h-10 px-2 sm:px-3">
              <SelectValue>
                <div className="flex items-center gap-1">
                  {!logoError ? (
                    <Image
                      src={logoPath}
                      alt={`${currency?.name} logo`}
                      width={14}
                      height={14}
                      className="rounded-full sm:w-4 sm:h-4"
                      onError={() => setLogoError(true)}
                    />
                  ) : (
                    <Image
                      src={fallbackLogo}
                      alt={`${currency?.name} logo`}
                      width={14}
                      height={14}
                      className="rounded-full sm:w-4 sm:h-4"
                    />
                  )}
                  <span className="whitespace-nowrap text-xs sm:text-sm font-medium">{currency?.code}</span>
                </div>
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {currencies.map((c) => (
                <SelectItem key={c.code} value={c.code}>
                  {c.code} - {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <div className="flex items-center gap-1 bg-background border-border rounded-full font-semibold px-2 sm:px-3 py-1.5 sm:py-2 min-w-[70px] sm:min-w-[90px] flex-shrink-0">
            {!logoError ? (
              <Image
                src={logoPath}
                alt={`${currency?.name} logo`}
                width={14}
                height={14}
                className="rounded-full sm:w-4 sm:h-4"
                onError={() => setLogoError(true)}
              />
            ) : (
              <Image
                src={fallbackLogo}
                alt={`${currency?.name} logo`}
                width={14}
                height={14}
                className="rounded-full sm:w-4 sm:h-4"
              />
            )}
            <span className="whitespace-nowrap text-xs sm:text-sm font-medium">{currency?.code}</span>
          </div>
        )}
      </div>
    </div>
  );
};

// --- MAIN TRADING PAGE COMPONENT --- //
function TradingPage() {
  const { user, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState("buy");
  const [spendAmount, setSpendAmount] = useState("");
  const [receiveAmount, setReceiveAmount] = useState("");
  const [isCalculating, setIsCalculating] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);
  const [exchangeRate, setExchangeRate] = useState(0);
  const [feeAmount, setFeeAmount] = useState(0);
  const [phoneNumber, setPhoneNumber] = useState("");

  // When buying, you spend UGX to get crypto.
  // When selling, you spend crypto to get UGX.
  const [cryptoCurrency, setCryptoCurrency] = useState("BTC");
  const fiatCurrency = "UGX"; // Hardcoded as it's the only fiat option

  const fromCurrency = activeTab === "buy" ? fiatCurrency : cryptoCurrency;
  const toCurrency = activeTab === "buy" ? cryptoCurrency : fiatCurrency;

  const fromCurrencies = activeTab === "buy" ? fiatCurrencies : cryptocurrencies;
  const toCurrencies = activeTab === "buy" ? cryptocurrencies : fiatCurrencies;

  // Real-time crypto prices
  const { prices, isConnected: isPriceConnected, getCryptoBySymbol } = useCryptoPrices();
  
  // Crypto balances state
  const [cryptoBalances, setCryptoBalances] = useState<Record<string, number>>({});
  const [isLoadingBalances, setIsLoadingBalances] = useState(true);

  // Load crypto balances
  useEffect(() => {
    const loadCryptoBalances = async () => {
      try {
        const result = await apiClient.getCryptoBalances();
        // Extract balance values from the nested objects
        const extractedBalances: Record<string, number> = {};
        Object.entries(result.balances).forEach(([crypto, balanceData]: [string, any]) => {
          extractedBalances[crypto] = balanceData?.balance || 0;
        });
        setCryptoBalances(extractedBalances);
      } catch (error) {
        console.error('Failed to load crypto balances:', error);
        // Set empty balances on error to prevent NaN
        setCryptoBalances({});
      } finally {
        setIsLoadingBalances(false);
      }
    };

    if (user) {
      loadCryptoBalances();
    }
  }, [user]);

  // Use user's actual balances
  const balances = useMemo(() => {
    if (!user) return {};
    return {
      UGX: user.balance || 0,
      ...cryptoBalances,
    };
  }, [user, cryptoBalances]);

  // Track which field was last edited to determine calculation direction
  const [lastEditedField, setLastEditedField] = useState<'spend' | 'receive'>('spend');

  // Calculate trade amounts using real API (forward calculation: spend -> receive)
  useEffect(() => {
    if (lastEditedField !== 'spend') return;

    const calculateTrade = async () => {
      if (!spendAmount || isNaN(parseFloat(spendAmount))) {
        setReceiveAmount("");
        setExchangeRate(0);
        setFeeAmount(0);
        return;
      }

      setIsCalculating(true);
      try {
        const amount = parseFloat(spendAmount);
        const result = await apiClient.calculateTrade(
          activeTab as 'buy' | 'sell',
          cryptoCurrency,
          amount
        );

        if (activeTab === 'buy') {
          setReceiveAmount(result.crypto_amount.toFixed(8));
        } else {
          setReceiveAmount(result.fiat_amount.toFixed(2));
        }
        
        setExchangeRate(result.exchange_rate);
        setFeeAmount(result.fee_amount);
      } catch (error: any) {
        console.error('Trade calculation error:', error);
        toast.error(error.response?.data?.error || 'Failed to calculate trade');
        setReceiveAmount("");
        setExchangeRate(0);
        setFeeAmount(0);
      } finally {
        setIsCalculating(false);
      }
    };

    const timeoutId = setTimeout(calculateTrade, 500); // Debounce API calls
    return () => clearTimeout(timeoutId);
  }, [spendAmount, activeTab, cryptoCurrency, lastEditedField]);

  // Reverse calculation: receive -> spend
  useEffect(() => {
    if (lastEditedField !== 'receive') return;

    const calculateReverse = async () => {
      if (!receiveAmount || isNaN(parseFloat(receiveAmount))) {
        setSpendAmount("");
        setExchangeRate(0);
        setFeeAmount(0);
        return;
      }

      setIsCalculating(true);
      try {
        const amount = parseFloat(receiveAmount);
        // For reverse calculation, we need to swap the logic
        const reverseTab = activeTab === 'buy' ? 'sell' : 'buy';
        const result = await apiClient.calculateTrade(
          reverseTab as 'buy' | 'sell',
          cryptoCurrency,
          amount
        );

        if (activeTab === 'buy') {
          // User entered crypto amount, calculate required fiat
          setSpendAmount(result.fiat_amount.toFixed(2));
        } else {
          // User entered fiat amount, calculate required crypto
          setSpendAmount(result.crypto_amount.toFixed(8));
        }
        
        setExchangeRate(result.exchange_rate);
        setFeeAmount(result.fee_amount);
      } catch (error: any) {
        console.error('Reverse calculation error:', error);
        toast.error(error.response?.data?.error || 'Failed to calculate trade');
        setSpendAmount("");
        setExchangeRate(0);
        setFeeAmount(0);
      } finally {
        setIsCalculating(false);
      }
    };

    const timeoutId = setTimeout(calculateReverse, 500); // Debounce API calls
    return () => clearTimeout(timeoutId);
  }, [receiveAmount, activeTab, cryptoCurrency, lastEditedField]);

  // Effect to reset amounts when tab changes
  useEffect(() => {
    setSpendAmount("");
    setReceiveAmount("");
  }, [activeTab]);

  const handleTrade = async () => {
    if (!spendAmount || !receiveAmount) {
      toast.error("Please enter an amount to trade.");
      return;
    }

    if (!phoneNumber) {
      toast.error("Please enter your phone number for mobile money.");
      return;
    }

    setIsExecuting(true);
    try {
      const amount = parseFloat(spendAmount);
      const result = await apiClient.executeTrade(
        activeTab as 'buy' | 'sell',
        cryptoCurrency,
        amount,
        phoneNumber
      );

      toast.success(result.message);
      
      if (activeTab === 'buy' && result.payment_url) {
        toast.success('Please complete payment on your mobile money app.');
      }

      // Reset form
      setSpendAmount("");
      setReceiveAmount("");
      setPhoneNumber("");
    } catch (error: any) {
      console.error('Trade execution error:', error);
      toast.error(error.response?.data?.error || 'Failed to execute trade');
    } finally {
      setIsExecuting(false);
    }
  };

  if (isLoading || !user) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  const fromBalance = (balances as any)[fromCurrency];
  const toBalance = (balances as any)[toCurrency];

  return (
    <div className="flex-grow container mx-auto p-2 sm:p-4 lg:p-8 bg-background">
      {/* Mobile Layout - Tabbed Interface */}
      <div className="lg:hidden">
        <Tabs defaultValue="trade" className="w-full">
          <TabsList className="grid w-full grid-cols-3 mb-4">
            <TabsTrigger value="trade" className="text-xs">
              <TrendingUp className="w-4 h-4 mr-1" />
              Trade
            </TabsTrigger>
            <TabsTrigger value="history" className="text-xs">
              <History className="w-4 h-4 mr-1" />
              History
            </TabsTrigger>
            <TabsTrigger value="markets" className="text-xs">
              <BarChart3 className="w-4 h-4 mr-1" />
              Markets
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="trade" className="mt-0">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-3"
            >
              {/* Buy/Sell Toggle */}
              <Card className="shadow-sm">
                <CardContent className="p-3">
                  <Tabs value={activeTab} onValueChange={setActiveTab}>
                    <TabsList className="grid w-full grid-cols-2 h-10">
                      <TabsTrigger value="buy" className="text-sm font-medium">Buy Crypto</TabsTrigger>
                      <TabsTrigger value="sell" className="text-sm font-medium">Sell Crypto</TabsTrigger>
                    </TabsList>
                  </Tabs>
                </CardContent>
              </Card>

              {/* Amount Input Section */}
              <Card className="shadow-sm">
                <CardContent className="p-3 space-y-3">
                  <CurrencyInput
                    label="You Spend"
                    amount={spendAmount}
                    onAmountChange={(value) => {
                      setSpendAmount(value);
                      setLastEditedField('spend');
                    }}
                    selectedCurrency={fromCurrency}
                    onCurrencyChange={setCryptoCurrency}
                    currencies={fromCurrencies}
                    balance={fromBalance}
                  />

                  <div className="flex justify-center py-2">
                    <div className="p-2 rounded-full bg-muted/50">
                      <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </div>

                  <CurrencyInput
                    label="You Receive"
                    amount={isCalculating ? "Calculating..." : receiveAmount}
                    onAmountChange={(value) => {
                      setReceiveAmount(value);
                      setLastEditedField('receive');
                    }}
                    selectedCurrency={toCurrency}
                    onCurrencyChange={setCryptoCurrency}
                    currencies={toCurrencies}
                    balance={toBalance}
                    isReadOnly={isCalculating}
                  />
                </CardContent>
              </Card>

              {/* Phone Number Section */}
              <Card className="shadow-sm">
                <CardContent className="p-3">

                  <div>
                    <label className="text-sm font-medium text-foreground mb-2 block">
                      Mobile Money Phone Number
                    </label>
                    <Input
                      type="tel"
                      value={phoneNumber}
                      onChange={(e) => setPhoneNumber(e.target.value)}
                      placeholder="256700000000"
                      className="text-base h-11"
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Market Price Section */}
              {cryptoCurrency && getCryptoBySymbol(cryptoCurrency) && (
                <Card className="shadow-sm">
                  <CardContent className="p-3">

                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-foreground">Current Market Price</span>
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${
                          isPriceConnected ? 'bg-green-500' : 'bg-red-500'
                        }`} />
                        <span className="text-xs text-muted-foreground">
                          {isPriceConnected ? 'Live' : 'Offline'}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-lg font-bold text-foreground">
                        {formatUGX(getCryptoBySymbol(cryptoCurrency)?.price || 0)}
                      </span>
                      <span className={`text-sm font-medium px-2 py-1 rounded-full ${
                        (getCryptoBySymbol(cryptoCurrency)?.changePercent24h || 0) >= 0 
                          ? 'text-green-700 bg-green-100 dark:text-green-400 dark:bg-green-900/30' 
                          : 'text-red-700 bg-red-100 dark:text-red-400 dark:bg-red-900/30'
                      }`}>
                        {(getCryptoBySymbol(cryptoCurrency)?.changePercent24h || 0) >= 0 ? '+' : ''}
                        {getCryptoBySymbol(cryptoCurrency)?.changePercent24h.toFixed(2)}%
                      </span>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Trade Details Section */}
              <Card className="shadow-sm">
                <CardContent className="p-3">

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-muted-foreground">Exchange Rate</span>
                      <span className="text-sm font-mono text-foreground">
                        {exchangeRate > 0 ? (
                          activeTab === 'buy' 
                            ? `1 ${fromCurrency} ≈ ${(1 / exchangeRate).toPrecision(4)} ${toCurrency}`
                            : `1 ${fromCurrency} ≈ ${exchangeRate.toFixed(0)} ${toCurrency}`
                        ) : (
                          "--"
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-muted-foreground">Trading Fee</span>
                      <span className="text-sm font-mono text-foreground">
                        {feeAmount > 0 ? `${feeAmount.toFixed(0)} UGX` : "--"}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Action Button Section */}
              <Card className="shadow-sm">
                <CardContent className="p-3">

                  <Button
                    onClick={handleTrade}
                    size="lg"
                    className="w-full text-base font-semibold h-12"
                    disabled={
                      !spendAmount || 
                      parseFloat(spendAmount) <= 0 || 
                      !phoneNumber || 
                      isCalculating || 
                      isExecuting
                    }
                  >
                    {isExecuting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Processing Trade...
                      </>
                    ) : (
                      `${activeTab === "buy" ? `Buy ${toCurrency}` : `Sell ${fromCurrency}`}`
                    )}
                  </Button>

                  <div className="text-center pt-3">
                    <Button variant="ghost" size="sm" className="text-muted-foreground">
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Set up recurring trades
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </TabsContent>
          
          <TabsContent value="history" className="mt-0">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <TradeHistory limit={20} />
            </motion.div>
          </TabsContent>
          
          <TabsContent value="markets" className="mt-0">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <MarketData 
                selectedCrypto={cryptoCurrency}
                onSelectCrypto={setCryptoCurrency}
              />
            </motion.div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Desktop Layout - Grid */}
      <div className="hidden lg:grid grid-cols-3 gap-6 max-w-7xl mx-auto">
        {/* Market Data */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="col-span-1"
        >
          <MarketData 
            selectedCrypto={cryptoCurrency}
            onSelectCrypto={setCryptoCurrency}
          />
        </motion.div>

        {/* Trading Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="col-span-1"
        >
          <Card className="shadow-lg dark:shadow-2xl dark:shadow-primary/10 w-full">
            <CardHeader className="pb-6">
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-2 h-10">
                  <TabsTrigger value="buy" className="text-base">Buy</TabsTrigger>
                  <TabsTrigger value="sell" className="text-base">Sell</TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>
            <CardContent className="space-y-4 px-6">
              <CurrencyInput
                label="You Spend"
                amount={spendAmount}
                onAmountChange={(value) => {
                  setSpendAmount(value);
                  setLastEditedField('spend');
                }}
                selectedCurrency={fromCurrency}
                onCurrencyChange={setCryptoCurrency}
                currencies={fromCurrencies}
                balance={fromBalance}
              />

              <div className="flex justify-center py-2">
                <div className="p-2 rounded-full bg-muted">
                  <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
                </div>
              </div>

              <CurrencyInput
                label="You Receive"
                amount={isCalculating ? "Calculating..." : receiveAmount}
                onAmountChange={(value) => {
                  setReceiveAmount(value);
                  setLastEditedField('receive');
                }}
                selectedCurrency={toCurrency}
                onCurrencyChange={setCryptoCurrency}
                currencies={toCurrencies}
                balance={toBalance}
                isReadOnly={isCalculating}
              />

              <div className="bg-muted/50 p-4 rounded-lg">
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Mobile Money Phone Number
                </label>
                <Input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="256700000000"
                  className="text-base h-10"
                />
              </div>

              {cryptoCurrency && getCryptoBySymbol(cryptoCurrency) && (
                <div className="bg-muted/30 p-3 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">Market Price</span>
                    <div className="flex items-center gap-1">
                      <div className={`w-2 h-2 rounded-full ${
                        isPriceConnected ? 'bg-green-500' : 'bg-red-500'
                      }`} />
                      <span className="text-xs text-muted-foreground">
                        {isPriceConnected ? 'Live' : 'Offline'}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-base font-bold truncate">
                      {formatUGX(getCryptoBySymbol(cryptoCurrency)?.price || 0)}
                    </span>
                    <span className={`text-sm font-medium ml-2 ${
                      (getCryptoBySymbol(cryptoCurrency)?.changePercent24h || 0) >= 0 
                        ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {(getCryptoBySymbol(cryptoCurrency)?.changePercent24h || 0) >= 0 ? '+' : ''}
                      {getCryptoBySymbol(cryptoCurrency)?.changePercent24h.toFixed(2)}%
                    </span>
                  </div>
                </div>
              )}

              <div className="text-sm text-muted-foreground pt-4 space-y-2">
                <div className="flex justify-between items-start gap-2">
                  <span className="font-medium flex-shrink-0">Exchange Rate</span>
                  <span className="font-mono text-sm text-right break-all">
                    {exchangeRate > 0 ? (
                      activeTab === 'buy' 
                        ? `1 ${fromCurrency} ≈ ${(1 / exchangeRate).toPrecision(6)} ${toCurrency}`
                        : `1 ${fromCurrency} ≈ ${exchangeRate.toFixed(2)} ${toCurrency}`
                    ) : (
                      "--"
                    )}
                  </span>
                </div>
                <div className="flex justify-between items-center gap-2">
                  <span className="font-medium flex-shrink-0">Fee</span>
                  <span className="font-mono text-sm">
                    {feeAmount > 0 ? `${feeAmount.toFixed(2)} UGX` : "--"}
                  </span>
                </div>
              </div>

              <Button
                onClick={handleTrade}
                size="lg"
                className="w-full text-lg font-semibold mt-4"
                disabled={
                  !spendAmount || 
                  parseFloat(spendAmount) <= 0 || 
                  !phoneNumber || 
                  isCalculating || 
                  isExecuting
                }
              >
                {isExecuting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  `${activeTab === "buy" ? `Buy ${toCurrency}` : `Sell ${fromCurrency}`}`
                )}
              </Button>

              <div className="text-center pt-2">
                <Button variant="link" className="text-muted-foreground text-sm">
                  <RefreshCw className="w-3 h-3 mr-2" />
                  Set up a recurring buy
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Trade History */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="col-span-1"
        >
          <TradeHistory limit={8} />
        </motion.div>
      </div>
    </div>
  );
}

export default TradingPage;
