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
import { ArrowDownUp, RefreshCw, Loader2 } from "lucide-react";
import Image from "next/image";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";
import { apiClient } from "@/lib/api-client";
import { TradeHistory } from "@/components/trading/trade-history";

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
    <div className="bg-muted/50 p-4 rounded-lg">
      <div className="flex justify-between items-center mb-1">
        <label className="text-sm font-medium text-muted-foreground">
          {label}
        </label>
        {balance !== undefined && (
          <span className="text-xs text-muted-foreground">
            Balance: {balance.toFixed(4)}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <Input
          type="number"
          value={amount}
          onChange={(e) => onAmountChange(e.target.value)}
          placeholder="0.00"
          className="text-2xl font-bold bg-transparent border-none focus-visible:ring-0 focus-visible:ring-offset-0 h-auto p-0"
          readOnly={isReadOnly}
        />
        {currencies.length > 1 ? (
          <Select value={selectedCurrency} onValueChange={onCurrencyChange}>
            <SelectTrigger className="w-auto bg-background border-border rounded-full font-semibold">
              <SelectValue>
                <div className="flex items-center gap-2">
                  {!logoError ? (
                    <Image
                      src={logoPath}
                      alt={`${currency?.name} logo`}
                      width={20}
                      height={20}
                      className="rounded-full"
                      onError={() => setLogoError(true)}
                    />
                  ) : (
                    <Image
                      src={fallbackLogo}
                      alt={`${currency?.name} logo`}
                      width={20}
                      height={20}
                      className="rounded-full"
                    />
                  )}
                  <span>{currency?.code}</span>
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
          <div className="flex items-center gap-2 bg-background border-border rounded-full font-semibold px-3 py-2">
            {!logoError ? (
              <Image
                src={logoPath}
                alt={`${currency?.name} logo`}
                width={20}
                height={20}
                className="rounded-full"
                onError={() => setLogoError(true)}
              />
            ) : (
              <Image
                src={fallbackLogo}
                alt={`${currency?.name} logo`}
                width={20}
                height={20}
                className="rounded-full"
              />
            )}
            <span>{currency?.code}</span>
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

  // Use user's actual balances
  const balances = useMemo(() => {
    if (!user) return {};
    return {
      UGX: user.balance || 0,
      // TODO: Get crypto balances from API
      BTC: 0,
      ETH: 0,
      SOL: 0,
      BNB: 0,
      USDT: 0,
    };
  }, [user]);

  // Calculate trade amounts using real API
  useEffect(() => {
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
  }, [spendAmount, activeTab, cryptoCurrency]);

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
    <div className="flex-grow container mx-auto p-4 sm:p-6 lg:p-8 bg-background">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
        {/* Trading Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex justify-center lg:justify-start"
        >
          <Card className="shadow-lg dark:shadow-2xl dark:shadow-primary/10 w-full max-w-md">
            <CardHeader>
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="buy">Buy</TabsTrigger>
                  <TabsTrigger value="sell">Sell</TabsTrigger>
                </TabsList>
              </Tabs>
            </CardHeader>
            <CardContent className="space-y-2">
              <CurrencyInput
                label="You Spend"
                amount={spendAmount}
                onAmountChange={setSpendAmount}
                selectedCurrency={fromCurrency}
                onCurrencyChange={setCryptoCurrency} // Only crypto can be changed
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
                onAmountChange={setReceiveAmount} // Kept for consistency, but input is read-only
                selectedCurrency={toCurrency}
                onCurrencyChange={setCryptoCurrency} // Only crypto can be changed
                currencies={toCurrencies}
                balance={toBalance}
                isReadOnly
              />

              {/* Phone Number Input */}
              <div className="bg-muted/50 p-4 rounded-lg">
                <label className="text-sm font-medium text-muted-foreground mb-1 block">
                  Mobile Money Phone Number
                </label>
                <Input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="256700000000"
                  className="text-lg"
                />
              </div>

              <div className="text-sm text-muted-foreground pt-4 space-y-1">
                <div className="flex justify-between">
                  <span>Exchange Rate</span>
                  <span className="font-mono">
                    {exchangeRate > 0 ? (
                      activeTab === 'buy' 
                        ? `1 ${fromCurrency} ≈ ${(1 / exchangeRate).toPrecision(6)} ${toCurrency}`
                        : `1 ${fromCurrency} ≈ ${exchangeRate.toFixed(2)} ${toCurrency}`
                    ) : (
                      "--"
                    )}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Fee</span>
                  <span className="font-mono">
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

              <div className="text-center">
                <Button variant="link" className="text-muted-foreground">
                  <RefreshCw className="w-3 h-3 mr-2" />
                  Set up a recurring buy
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Trade History */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <TradeHistory limit={5} />
        </motion.div>
      </div>
    </div>
  );
}

export default TradingPage;
