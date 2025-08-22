"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, ExternalLink, Copy } from "lucide-react";
import Image from "next/image";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";
import { formatNumber, formatUGX, formatCryptoAmount } from "@/lib/currency-formatter";
import { toast } from "react-hot-toast";

interface ChainBalance {
  balance: number;
  accounts: Array<{
    account_id: number;
    balance: number;
    currency: string;
    parent_currency: string | null;
  }>;
}

interface MultiChainBalanceData {
  total_balance: number;
  chains: Record<string, ChainBalance>;
  addresses: Array<{
    chain: string;
    address: string;
    memo?: string;
  }>;
}

interface MultiChainBalanceProps {
  currency: string;
  data: MultiChainBalanceData;
  priceUsd?: number;
  theme?: 'light' | 'dark';
}

export function MultiChainBalance({ currency, data, priceUsd = 0, theme = 'dark' }: MultiChainBalanceProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [logoError, setLogoError] = useState(false);

  const isMultiChain = Object.keys(data.chains).length > 1;
  const totalValueUsd = data.total_balance * priceUsd;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const logoPath = getCryptoLogo(currency);
  const fallbackLogo = createFallbackLogo(currency);

  return (
    <Card className={`overflow-hidden transition-all duration-200 ${
      theme === 'dark' 
        ? 'bg-[#1E2329] border-[#2B3139] hover:bg-[#2B3139]/50' 
        : 'bg-white border-gray-200 hover:bg-gray-50'
    }`}>
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              {!logoError ? (
                <Image
                  src={logoPath}
                  alt={`${currency} logo`}
                  width={40}
                  height={40}
                  className="rounded-full"
                  onError={() => setLogoError(true)}
                />
              ) : (
                <Image
                  src={fallbackLogo}
                  alt={`${currency} logo`}
                  width={40}
                  height={40}
                  className="rounded-full"
                />
              )}
              {isMultiChain && (
                <div className={`absolute -top-1 -right-1 w-4 h-4 bg-blue-500 rounded-full border-2 flex items-center justify-center ${
                  theme === 'dark' ? 'border-[#1E2329]' : 'border-white'
                }`}>
                  <span className="text-xs text-white font-bold">{Object.keys(data.chains).length}</span>
                </div>
              )}
            </div>
            
            <div>
              <div className="flex items-center gap-2">
                <h3 className={`font-semibold text-lg ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  {currency}
                </h3>
                {isMultiChain && (
                  <Badge variant="secondary" className={`text-xs ${
                    theme === 'dark' 
                      ? 'bg-blue-500/20 text-blue-400 border-blue-500/30' 
                      : 'bg-blue-100 text-blue-700 border-blue-200'
                  }`}>
                    Multi-Chain
                  </Badge>
                )}
              </div>
              <div className="text-2xl font-bold">
                {formatCryptoAmount(data.total_balance, currency)} {currency}
              </div>
            </div>
          </div>

          <div className="text-right">
            <div className={`font-semibold ${
              theme === 'dark' ? 'text-white' : 'text-gray-900'
            }`}>
              ${formatNumber(totalValueUsd, 2)}
            </div>
            <div className={`text-sm ${
              theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
            }`}>
              ≈ ${formatNumber(totalValueUsd, 2)}
            </div>
          </div>

          {isMultiChain && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className={`ml-2 ${
                theme === 'dark'
                  ? 'text-[#B7BDC6] hover:text-white hover:bg-[#2B3139]'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </Button>
          )}
        </div>

        {/* Multi-chain breakdown */}
        {isMultiChain && isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-4 space-y-3"
          >
            <div className={`border-t pt-3 ${
              theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'
            }`}>
              <h4 className={`text-sm font-medium mb-3 ${
                theme === 'dark' ? 'text-white' : 'text-gray-900'
              }`}>
                Chain Distribution
              </h4>
              
              {Object.entries(data.chains).map(([chain, chainData]) => {
                const percentage = (chainData.balance / data.total_balance) * 100;
                const chainValueUsd = chainData.balance * priceUsd;
                
                return (
                  <div key={chain} className="flex items-center justify-between py-2">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${
                        chain === 'ETH' ? 'bg-blue-500' :
                        chain === 'TRX' ? 'bg-red-500' :
                        chain === 'BNB' ? 'bg-yellow-500' :
                        chain === 'SOL' ? 'bg-purple-500' :
                        'bg-gray-500'
                      }`} />
                      <span className={`text-sm font-medium ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>
                        {chain}
                      </span>
                      <Badge variant="outline" className={`text-xs ${
                        theme === 'dark' 
                          ? 'border-[#2B3139] text-[#B7BDC6]' 
                          : 'border-gray-300 text-gray-600'
                      }`}>
                        {percentage.toFixed(1)}%
                      </Badge>
                    </div>
                    
                    <div className="text-right">
                      <div className={`text-sm font-medium ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>
                        {formatNumber(chainData.balance, 6)}
                      </div>
                      <div className={`text-xs ${
                        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                      }`}>
                        ${formatNumber(chainValueUsd, 2)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Addresses */}
            {data.addresses && data.addresses.length > 0 && (
              <div className={`border-t pt-3 ${
                theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'
              }`}>
                <h4 className={`text-sm font-medium mb-3 ${
                  theme === 'dark' ? 'text-white' : 'text-gray-900'
                }`}>
                  Deposit Addresses
                </h4>
                
                {data.addresses.map((addr, index) => (
                  <div key={index} className={`flex items-center justify-between py-2 px-3 rounded-md ${
                    theme === 'dark' ? 'bg-[#2B3139]' : 'bg-gray-50'
                  }`}>
                    <div>
                      <div className={`text-sm font-medium ${
                        theme === 'dark' ? 'text-white' : 'text-gray-900'
                      }`}>
                        {addr.chain}
                      </div>
                      <div className={`text-xs font-mono break-all ${
                        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                      }`}>
                        {addr.address.slice(0, 20)}...{addr.address.slice(-10)}
                      </div>
                      {addr.memo && (
                        <div className={`text-xs ${
                          theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'
                        }`}>
                          Memo: {addr.memo}
                        </div>
                      )}
                    </div>
                    
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(addr.address)}
                        className={`h-8 w-8 p-0 ${
                          theme === 'dark'
                            ? 'text-[#B7BDC6] hover:text-white hover:bg-[#1E2329]'
                            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
                        }`}
                      >
                        <Copy className="w-3 h-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          const explorerUrl = 
                            addr.chain === 'ETH' ? `https://etherscan.io/address/${addr.address}` :
                            addr.chain === 'TRX' ? `https://tronscan.org/#/address/${addr.address}` :
                            addr.chain === 'BNB' ? `https://bscscan.com/address/${addr.address}` :
                            addr.chain === 'SOL' ? `https://solscan.io/account/${addr.address}` :
                            '#';
                          if (explorerUrl !== '#') {
                            window.open(explorerUrl, '_blank');
                          }
                        }}
                        className={`h-8 w-8 p-0 ${
                          theme === 'dark'
                            ? 'text-[#B7BDC6] hover:text-white hover:bg-[#1E2329]'
                            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200'
                        }`}
                      >
                        <ExternalLink className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </div>
    </Card>
  );
}
