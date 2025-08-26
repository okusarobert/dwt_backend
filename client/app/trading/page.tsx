"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
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
import { websocketClient } from '@/lib/websocket-client';
import { MarketData } from '@/components/trading/market-data';
import { TradeHistory } from '@/components/trading/trade-history';
import { formatUGX, formatNumber } from '@/lib/currency-formatter';

// --- FIAT DATA --- //
const fiatCurrencies = [
  { code: "UGX", name: "Uganda Shilling", symbol: "USh", logo: "/logos/fiat/ugx.svg" },
];

// --- TYPES --- //
interface Currency {
  code: string;
  name: string;
  symbol: string;
  is_enabled?: boolean;
}

// --- CURRENCY INPUT COMPONENT --- //
interface CurrencyInputProps {
  label: string;
  amount: string;
  onAmountChange: (value: string) => void;
  selectedCurrency: string;
  onCurrencyChange: (value: string) => void;
  currencies: Currency[];
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
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <label className="text-sm font-medium text-muted-foreground">
          {label}
        </label>
        {balance !== undefined && (
          <span className="text-xs text-muted-foreground">
            Balance: {formatNumber(balance, 8)} {selectedCurrency}
          </span>
        )}
      </div>
      
      <div className="relative">
        <Input
          type="number"
          value={amount}
          onChange={(e) => {
            const value = e.target.value;
            // Prevent negative values
            if (value === '' || (!isNaN(Number(value)) && Number(value) >= 0)) {
              onAmountChange(value);
            }
          }}
          placeholder="0.00"
          min="0"
          step="any"
          className="text-xl sm:text-2xl font-bold h-14 sm:h-16 pr-20 sm:pr-28 text-right bg-background border-2 focus:border-primary"
          readOnly={isReadOnly}
        />
        
        {currencies.length > 1 ? (
          <Select value={selectedCurrency} onValueChange={onCurrencyChange}>
            <SelectTrigger className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 w-16 sm:w-24 h-8 sm:h-10 border-0 bg-muted/50 hover:bg-muted focus:ring-0 focus:ring-offset-0">
              <SelectValue>
                <div className="flex items-center gap-1 sm:gap-2">
                  {!logoError ? (
                    <Image
                      src={logoPath}
                      alt={`${currency?.name} logo`}
                      width={16}
                      height={16}
                      className="rounded-full sm:w-5 sm:h-5"
                      onError={() => setLogoError(true)}
                    />
                  ) : (
                    <Image
                      src={fallbackLogo}
                      alt={`${currency?.name} logo`}
                      width={16}
                      height={16}
                      className="rounded-full sm:w-5 sm:h-5"
                    />
                  )}
                  <span className="text-xs sm:text-sm font-semibold">
                    {selectedCurrency}
                  </span>
                </div>
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {currencies.map((curr) => (
                <SelectItem 
                  key={curr.code} 
                  value={curr.code}
                  disabled={curr.is_enabled === false}
                >
                  <div className={`flex items-center gap-2 ${
                    curr.is_enabled === false ? 'opacity-50 cursor-not-allowed' : ''
                  }`}>
                    <Image
                      src={getCryptoLogo(curr.symbol)}
                      alt={`${curr.name} logo`}
                      width={20}
                      height={20}
                      className="rounded-full"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = createFallbackLogo(curr.symbol);
                      }}
                    />
                    <span className="font-medium">{curr.code}</span>
                    <span className="text-muted-foreground text-sm hidden sm:inline">
                      {curr.name}
                      {curr.is_enabled === false && ' (Disabled)'}
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <div className="absolute right-2 sm:right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 sm:py-2 bg-muted/50 rounded-lg">
            {!logoError ? (
              <Image
                src={logoPath}
                alt={`${currency?.name} logo`}
                width={16}
                height={16}
                className="rounded-full sm:w-5 sm:h-5"
                onError={() => setLogoError(true)}
              />
            ) : (
              <Image
                src={fallbackLogo}
                alt={`${currency?.name} logo`}
                width={16}
                height={16}
                className="rounded-full sm:w-5 sm:h-5"
              />
            )}
            <span className="font-semibold text-xs sm:text-sm">{selectedCurrency}</span>
          </div>
        )}
      </div>
    </div>
  );
};

// --- MAIN TRADING PAGE COMPONENT --- //
function TradingPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
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
  const [cryptoCurrency, setCryptoCurrency] = useState("");
  const fiatCurrency = "UGX"; // Hardcoded as it's the only fiat option

  // Cryptocurrencies state (moved before usage)
  const [cryptocurrencies, setCryptocurrencies] = useState<Currency[]>([]);
  const [isLoadingCurrencies, setIsLoadingCurrencies] = useState(true);

  const fromCurrency = activeTab === "buy" ? fiatCurrency : cryptoCurrency;
  const toCurrency = activeTab === "buy" ? cryptoCurrency : fiatCurrency;

  const fromCurrencies = activeTab === "buy" ? fiatCurrencies : cryptocurrencies;
  const toCurrencies = activeTab === "buy" ? cryptocurrencies : fiatCurrencies;

  // Real-time crypto prices
  const { prices, isConnected: isPriceConnected, getCryptoBySymbol } = useCryptoPrices();
  
  // WebSocket connection for real-time updates
  const [socket, setSocket] = useState<any>(null);
  
  useEffect(() => {
    setSocket(websocketClient);
  }, []);
  
  // Crypto balances state
  const [cryptoBalances, setCryptoBalances] = useState<Record<string, number>>({});
  const [isLoadingBalances, setIsLoadingBalances] = useState(true);

  // Load cryptocurrencies from admin API
  const loadCryptocurrencies = async () => {
    try {
      const result = await apiClient.getCurrencies();
      if (result.success) {
        // Convert admin currency format to trading page format
        const cryptoList: Currency[] = result.currencies.map(currency => ({
          code: currency.symbol,
          name: currency.name,
          symbol: currency.symbol,
          is_enabled: currency.is_enabled
        }));
        setCryptocurrencies(cryptoList);
        
        // Set default cryptocurrency to first enabled one
        const enabledCrypto = cryptoList.find(crypto => crypto.is_enabled !== false);
        if (enabledCrypto && !cryptoCurrency) {
          setCryptoCurrency(enabledCrypto.code);
        }
      }
    } catch (error) {
      console.error('Failed to load cryptocurrencies:', error);
      // Fallback to empty array
      setCryptocurrencies([]);
    } finally {
      setIsLoadingCurrencies(false);
    }
  };

  useEffect(() => {
    loadCryptocurrencies();
  }, [cryptoCurrency]);

  // Listen for currency change events from websocket
  useEffect(() => {
    const handleCurrencyChange = (data: any) => {
      console.log('Currency change received:', data);
      // Refresh currencies when admin makes changes
      loadCryptocurrencies();
    };
    
    // Use websocket client's currency change handler
    const unsubscribe = websocketClient.onCurrencyChange(handleCurrencyChange);
    
    return unsubscribe;
  }, []);

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
  const [lastEditedField, setLastEditedField] = useState<'spend' | 'receive'>('receive');
  const [quoteData, setQuoteData] = useState<any>(null);

  // Calculate quote when user enters crypto amount (for buy orders)
  useEffect(() => {
    if (activeTab !== 'buy' || lastEditedField !== 'receive') return;

    const getQuote = async () => {
      if (!receiveAmount || isNaN(parseFloat(receiveAmount))) {
        setSpendAmount("");
        setExchangeRate(0);
        setFeeAmount(0);
        setQuoteData(null);
        return;
      }

      setIsCalculating(true);
      try {
        const cryptoAmount = parseFloat(receiveAmount);
        const quote = await apiClient.getQuoteForCryptoAmount(
          cryptoCurrency,
          cryptoAmount,
          'mobile_money'
        );

        setSpendAmount(quote.total_fiat_cost.toFixed(2));
        setExchangeRate(quote.exchange_rate);
        setFeeAmount(quote.fee_amount);
        setQuoteData(quote);
      } catch (error: any) {
        console.error('Quote calculation error:', error);
        // Don't show error toast for zero amounts - just silently clear the form
        const cryptoAmount = parseFloat(receiveAmount) || 0;
        if (cryptoAmount > 0) {
          toast.error(error.response?.data?.error || 'Failed to get quote');
        }
        setSpendAmount("");
        setExchangeRate(0);
        setFeeAmount(0);
        setQuoteData(null);
      } finally {
        setIsCalculating(false);
      }
    };

    const timeoutId = setTimeout(getQuote, 500); // Debounce API calls
    return () => clearTimeout(timeoutId);
  }, [receiveAmount, activeTab, cryptoCurrency, lastEditedField]);

  // Calculate trade amounts using real API (forward calculation: spend -> receive)
  useEffect(() => {
    // For buy tab: only calculate when user edits spend amount (UGX)
    // For sell tab: calculate when user edits either field
    if (activeTab === 'buy' && lastEditedField !== 'spend') return;
    if (activeTab === 'sell' && !spendAmount && !receiveAmount) return;

    const calculateTrade = async () => {
      // Determine which amount to use based on tab and what user entered
      let amount: number = 0;
      let hasValidInput = false;

      if (activeTab === 'buy') {
        // Buy: user enters UGX amount to spend
        if (spendAmount && !isNaN(parseFloat(spendAmount))) {
          amount = parseFloat(spendAmount);
          hasValidInput = true;
        }
      } else {
        // Sell: determine which field has input
        if (lastEditedField === 'spend' && spendAmount && !isNaN(parseFloat(spendAmount))) {
          amount = parseFloat(spendAmount); // Crypto amount to sell
          hasValidInput = true;
        } else if (lastEditedField === 'receive' && receiveAmount && !isNaN(parseFloat(receiveAmount))) {
          amount = parseFloat(receiveAmount); // UGX amount desired
          hasValidInput = true;
        }
      }

      if (!hasValidInput) {
        setReceiveAmount("");
        setSpendAmount("");
        setExchangeRate(0);
        setFeeAmount(0);
        setQuoteData(null);
        return;
      }

      setIsCalculating(true);
      try {
        if (activeTab === 'buy') {
          // For buy: user spends UGX, gets crypto
          const result = await apiClient.calculateTrade(
            'buy',
            cryptoCurrency,
            amount
          );
          setReceiveAmount(result.crypto_amount.toFixed(8));
          setExchangeRate(result.exchange_rate);
          setFeeAmount(result.fee_amount);
        } else {
          // For sell: handle based on which field user edited
          if (lastEditedField === 'spend') {
            // User entered crypto amount to sell -> calculate UGX received
            const result = await apiClient.calculateTrade(
              'sell',
              cryptoCurrency,
              amount
            );
            console.log("Sell crypto result: ", result);
            setReceiveAmount(result.fiat_amount.toFixed(2)); // Show UGX they'll receive
            setExchangeRate(result.exchange_rate);
            setFeeAmount(result.fee_amount);
          } else {
            // User entered UGX amount desired -> calculate crypto needed
            // Need to reverse calculate using market price
            const cryptoData = getCryptoBySymbol(cryptoCurrency);
            if (!cryptoData?.price) {
              throw new Error('Unable to get current market price');
            }
            
            // Estimate crypto needed: UGX / price (with fee buffer)
            const estimatedCrypto = (amount * 1.02) / cryptoData.price;
            
            setSpendAmount(estimatedCrypto.toFixed(8)); // Show crypto they need to sell
            setExchangeRate(cryptoData.price);
            setFeeAmount(amount * 0.02); // Rough 2% fee estimate
          }
        }
        
        setQuoteData(null);
      } catch (error: any) {
        console.error('Trade calculation error:', error);
        toast.error(error.response?.data?.error || 'Failed to calculate trade');
        setReceiveAmount("");
        setSpendAmount("");
        setExchangeRate(0);
        setFeeAmount(0);
        setQuoteData(null);
      } finally {
        setIsCalculating(false);
      }
    };

    const timeoutId = setTimeout(calculateTrade, 500); // Debounce API calls
    return () => clearTimeout(timeoutId);
  }, [spendAmount, receiveAmount, activeTab, cryptoCurrency, lastEditedField]);

  // Effect to reset amounts when tab changes
  useEffect(() => {
    setSpendAmount("");
    setReceiveAmount("");
  }, [activeTab]);

  // Check if amounts are valid (> 0)
  const areAmountsValid = () => {
    const spendValue = parseFloat(spendAmount) || 0;
    const receiveValue = parseFloat(receiveAmount) || 0;
    return spendValue > 0 && receiveValue > 0;
  };

  // Check if trade is valid (amounts > 0, phone number provided, and currency enabled)
  const isTradeValid = () => {
    const selectedCrypto = cryptocurrencies.find(crypto => crypto.code === cryptoCurrency);
    const isCurrencyEnabled = selectedCrypto?.is_enabled !== false;
    return areAmountsValid() && phoneNumber.trim() !== '' && isCurrencyEnabled;
  };

  const handleTrade = async () => {
    // Check if currency is disabled
    const selectedCrypto = cryptocurrencies.find(crypto => crypto.code === cryptoCurrency);
    if (selectedCrypto?.is_enabled === false) {
      toast.error(`${cryptoCurrency} trading is currently disabled. Please select a different cryptocurrency.`);
      return;
    }

    // Only show phone number error if amounts are valid (> 0)
    if (!phoneNumber && areAmountsValid()) {
      toast.error("Please enter your phone number for mobile money.");
      return;
    }

    setIsExecuting(true);
    try {
      // Determine amount type and value based on user input
      let amountToUse: number;
      let amountType: 'fiat' | 'crypto' = 'fiat';
      
      if (activeTab === 'buy' && quoteData && lastEditedField === 'receive') {
        // User entered crypto amount, use that for the trade
        amountToUse = parseFloat(receiveAmount);
        amountType = 'crypto';
      } else {
        // User entered fiat amount or it's a sell order
        amountToUse = parseFloat(spendAmount);
        amountType = 'fiat';
      }
      
      const result = await apiClient.executeTrade(
        activeTab as 'buy' | 'sell',
        cryptoCurrency,
        amountToUse,
        phoneNumber,
        amountType
      );

      console.log("Result: ", result);

      toast.success("Trade initiated successfully");
      
      // Redirect to waiting page
      router.push(`/trading/${result.data.trade_id}`);

      // Reset form (in case user navigates back)
      setSpendAmount("");
      setReceiveAmount("");
      setPhoneNumber("");
      setQuoteData(null);
    } catch (error: any) {
      console.error('Trade execution error:', error);
      toast.error(error.response?.data?.error || 'Failed to execute trade');
    } finally {
      setIsExecuting(false);
    }
  };

  if (isLoading || !user || isLoadingCurrencies) {
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
                    label={activeTab === "buy" ? "You Spend" : "You Want to Receive"}
                    amount={spendAmount}
                    onAmountChange={(value) => {
                      setSpendAmount(value);
                      setLastEditedField('spend');
                    }}
                    selectedCurrency={activeTab === "buy" ? fromCurrency : toCurrency}
                    onCurrencyChange={setCryptoCurrency}
                    currencies={activeTab === "buy" ? fromCurrencies : toCurrencies}
                    balance={activeTab === "buy" ? fromBalance : toBalance}
                  />

                  <div className="flex justify-center py-2">
                    <div className="p-2 rounded-full bg-muted/50">
                      <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
                    </div>
                  </div>

                  <CurrencyInput
                    label={activeTab === "buy" ? "You Receive" : "You Need to Sell"}
                    amount={isCalculating ? "Calculating..." : receiveAmount}
                    onAmountChange={(value) => {
                      setReceiveAmount(value);
                      setLastEditedField('receive');
                    }}
                    selectedCurrency={activeTab === "buy" ? toCurrency : fromCurrency}
                    onCurrencyChange={setCryptoCurrency}
                    currencies={activeTab === "buy" ? toCurrencies : fromCurrencies}
                    balance={activeTab === "buy" ? toBalance : fromBalance}
                    isReadOnly={false}
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

              {/* Quote Breakdown Section (for crypto amount input) */}
              {quoteData && activeTab === 'buy' && (
                <Card className="shadow-sm border-blue-200 bg-blue-50/50 dark:border-blue-800 dark:bg-blue-950/20">
                  <CardContent className="p-3">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-2 h-2 rounded-full bg-blue-500" />
                      <span className="text-sm font-semibold text-blue-700 dark:text-blue-300">
                        Quote Breakdown
                      </span>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">Base Cost</span>
                        <span className="text-sm font-mono text-foreground">
                          {formatUGX(quoteData.gross_fiat_cost)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">
                          Trading Fee ({(quoteData.fee_percentage * 100).toFixed(1)}%)
                        </span>
                        <span className="text-sm font-mono text-foreground">
                          {formatUGX(quoteData.fee_amount)}
                        </span>
                      </div>
                      <div className="border-t pt-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-semibold text-foreground">Total Cost</span>
                          <span className="text-sm font-bold text-foreground">
                            {formatUGX(quoteData.total_fiat_cost)}
                          </span>
                        </div>
                      </div>
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
                    disabled={!isTradeValid() || isCalculating || isExecuting}
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
                currencies={cryptocurrencies} 
                onCurrenciesUpdate={loadCryptocurrencies} 
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
            currencies={cryptocurrencies}
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
                isReadOnly={false}
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
                disabled={!isTradeValid() || isCalculating || isExecuting}
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
