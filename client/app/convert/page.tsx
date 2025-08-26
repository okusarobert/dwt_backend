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
import { useAuth } from "@/components/auth/auth-provider";
import { toast } from "react-hot-toast";
import { RefreshCw } from "lucide-react";
import Image from "next/image";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout";

// --- MOCK DATA --- //
const cryptocurrencies: any[] = [];

// --- CURRENCY INPUT COMPONENT (Adapted from TradingPage) --- //
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
      </div>
    </div>
  );
};

// --- MAIN CONVERT PAGE COMPONENT --- //
function ConvertPage() {
  const { user, isLoading } = useAuth();
  const [spendAmount, setSpendAmount] = useState("");
  const [receiveAmount, setReceiveAmount] = useState("");
  const [fromCurrency, setFromCurrency] = useState("");
  const [toCurrency, setToCurrency] = useState("");

  // Mock exchange rate and balances
  const exchangeRate = useMemo(() => {
    // Simulate different rates for crypto-to-crypto
    return 43250 + (fromCurrency.charCodeAt(0) % 10) * 100 - (toCurrency.charCodeAt(0) % 10) * 50;
  }, [fromCurrency, toCurrency]);

  const balances = useMemo(() => ({
    BTC: 0.5,
    ETH: 3,
    SOL: 50,
    BNB: 10,
    USDT: 5000,
  }), []);

  useEffect(() => {
    if (spendAmount) {
      const amount = parseFloat(spendAmount);
      if (!isNaN(amount)) {
        setReceiveAmount((amount * exchangeRate).toFixed(6));
      }
    } else {
      setReceiveAmount("");
    }
  }, [spendAmount, exchangeRate]);

  const handleSwap = () => {
    const newFrom = toCurrency;
    const newTo = fromCurrency;
    setFromCurrency(newFrom);
    setToCurrency(newTo);
    setSpendAmount(receiveAmount);
  };

  const handleConvert = () => {
    if (!spendAmount || !receiveAmount) {
      toast.error("Please enter an amount to convert.");
      return;
    }
    toast.success(
      `Successfully converted ${spendAmount} ${fromCurrency} to ${receiveAmount} ${toCurrency}!`
    );
  };

  if (isLoading || !user) {
    return (
      <AuthenticatedLayout title="Convert">
        <div className="flex items-center justify-center flex-grow">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const fromBalance = (balances as any)[fromCurrency];
  const toBalance = (balances as any)[toCurrency];

  return (
    <AuthenticatedLayout title="Convert">
      <div className="flex-grow container mx-auto p-4 sm:p-6 lg:p-8 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          <Card className="shadow-lg dark:shadow-2xl dark:shadow-primary/10">
            <CardHeader>
              <CardTitle className="text-center text-2xl font-bold">Convert Crypto</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <CurrencyInput
                label="You Spend"
                amount={spendAmount}
                onAmountChange={setSpendAmount}
                selectedCurrency={fromCurrency}
                onCurrencyChange={setFromCurrency}
                currencies={cryptocurrencies}
                balance={fromBalance}
              />

              <div className="flex justify-center -my-2 z-10">
                <Button variant="outline" size="icon" onClick={handleSwap} className="rounded-full bg-background hover:bg-muted">
                  <ArrowDownUp className="w-4 h-4 text-muted-foreground" />
                </Button>
              </div>

              <CurrencyInput
                label="You Receive"
                amount={receiveAmount}
                onAmountChange={setReceiveAmount}
                selectedCurrency={toCurrency}
                onCurrencyChange={setToCurrency}
                currencies={cryptocurrencies}
                balance={toBalance}
                isReadOnly
              />

              <div className="text-sm text-muted-foreground pt-4 space-y-1">
                <div className="flex justify-between">
                  <span>Exchange Rate</span>
                  <span className="font-mono">1 {fromCurrency} ≈ {exchangeRate.toPrecision(6)} {toCurrency}</span>
                </div>
                <div className="flex justify-between">
                  <span>Fee (0.1%)</span>
                  <span className="font-mono">0.1%</span>
                </div>
              </div>

              <Button
                onClick={handleConvert}
                size="lg"
                className="w-full text-lg font-semibold mt-4"
                disabled={!spendAmount || parseFloat(spendAmount) <= 0}
              >
                Convert Now
              </Button>

            </CardContent>
          </Card>
        </motion.div>
      </div>
    </AuthenticatedLayout>
  );
}

export default ConvertPage;
