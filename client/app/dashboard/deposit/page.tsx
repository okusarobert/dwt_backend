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
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useTheme } from "@/components/theme/theme-provider";
import { toast } from "react-hot-toast";
import { Copy, QrCode, Loader2, AlertCircle, ExternalLink, ArrowLeft } from 'lucide-react';
import { QRCodeSVG } from "qrcode.react";
import { apiClient } from "@/lib/api-client";
import Image from "next/image";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";
import { useRouter } from "next/navigation";
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout";
import { useSearchParams } from "next/navigation";
import { websocketClient } from '@/lib/websocket-client';

interface SupportedCrypto {
  symbol: string;
  name: string;
  isMultiNetwork: boolean;
  is_enabled?: boolean;
}

interface NetworkOption {
  network_type: string;
  network_name: string;
  display_name: string;
  currency_code: string;
  confirmation_blocks: number;
  explorer_url: string;
  is_testnet: boolean;
}

interface DepositAddress {
  success: boolean;
  address: string;
  currency_code: string;
  network: {
    type: string;
    name: string;
    confirmation_blocks: number;
    explorer_url: string;
  };
  token_info: {
    symbol: string;
    contract_address: string;
    decimals: number;
  };
}

export default function DepositPage() {
  const { theme } = useTheme();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [selectedCrypto, setSelectedCrypto] = useState<string>("");
  const [selectedNetwork, setSelectedNetwork] = useState<NetworkOption | null>(null);
  const [networks, setNetworks] = useState<NetworkOption[]>([]);
  const [depositAddress, setDepositAddress] = useState<DepositAddress | null>(null);
  const [isLoadingNetworks, setIsLoadingNetworks] = useState(false);
  const [isLoadingAddress, setIsLoadingAddress] = useState(false);
  const [supportedCryptos, setSupportedCryptos] = useState<SupportedCrypto[]>([]);
  const [isLoadingCurrencies, setIsLoadingCurrencies] = useState(true);

  // Load currencies from admin API
  const loadCurrencies = async () => {
    try {
      setIsLoadingCurrencies(true);
      const result = await apiClient.getCurrencies();
      if (result.success) {
        // Convert admin currency format to deposit page format
        const cryptoList: SupportedCrypto[] = result.currencies
          .filter((currency: any) => currency.is_enabled) // Only show enabled currencies
          .map((currency: any) => {
            return {
              symbol: currency.symbol,
              name: currency.name,
              isMultiNetwork: currency.is_multi_network, // Use admin-configured multi-network setting
              is_enabled: currency.is_enabled
            };
          });
        setSupportedCryptos(cryptoList);
      }
    } catch (error) {
      console.error('Failed to load currencies:', error);
      toast.error('Failed to load available currencies');
    } finally {
      setIsLoadingCurrencies(false);
    }
  };

  // Initialize currencies and selected crypto from URL parameter
  useEffect(() => {
    loadCurrencies();
  }, []);

  useEffect(() => {
    const cryptoParam = searchParams.get('crypto');
    if (cryptoParam && supportedCryptos.find(c => c.symbol === cryptoParam.toUpperCase())) {
      setSelectedCrypto(cryptoParam.toUpperCase());
    }
  }, [searchParams, supportedCryptos]);

  // Listen for currency change events from websocket
  useEffect(() => {
    const handleCurrencyChange = (data: any) => {
      console.log('Currency change received in deposit page:', data);
      // Refresh currencies when admin makes changes
      loadCurrencies();
    };
    
    // Use websocket client's currency change handler
    const unsubscribe = websocketClient.onCurrencyChange(handleCurrencyChange);
    
    return unsubscribe;
  }, []);

  // Clear selection if selected crypto becomes disabled
  useEffect(() => {
    if (selectedCrypto && supportedCryptos.length > 0) {
      const selectedCurrency = supportedCryptos.find(c => c.symbol === selectedCrypto);
      if (!selectedCurrency) {
        // Selected crypto is no longer available (disabled), clear selection
        setSelectedCrypto('');
        setSelectedNetwork(null);
        setDepositAddress(null);
        toast.error(`${selectedCrypto} has been disabled and is no longer available for deposits`);
      }
    }
  }, [selectedCrypto, supportedCryptos]);

  // Load networks when crypto is selected
  useEffect(() => {
    if (selectedCrypto) {
      loadNetworks();
      setSelectedNetwork(null);
      setDepositAddress(null);
    }
  }, [selectedCrypto]);

  // Load deposit address when network is selected
  useEffect(() => {
    if (selectedNetwork && selectedCrypto) {
      loadDepositAddress(selectedNetwork);
    }
  }, [selectedNetwork, selectedCrypto]);

  const loadNetworks = async () => {
    try {
      setIsLoadingNetworks(true);
      const crypto = supportedCryptos.find(c => c.symbol === selectedCrypto);
      
      // Load networks from admin API for all currencies (both single and multi-network)
      const includeTestnets = process.env.NODE_ENV === 'development';
      const data = await apiClient.getMultiNetworkDepositNetworks(selectedCrypto, includeTestnets);
      
      if (data.success) {
        setNetworks(data.networks);
        // Auto-select first mainnet network
        const mainnetNetwork = data.networks.find((n: NetworkOption) => !n.is_testnet);
        if (mainnetNetwork) {
          setSelectedNetwork(mainnetNetwork);
        } else if (data.networks.length > 0) {
          // If no mainnet available, select first network
          setSelectedNetwork(data.networks[0]);
        }
      } else {
        throw new Error(data.error || 'Failed to load networks');
      }
    } catch (error: any) {
      console.error('Failed to load networks:', error);
      toast.error(error.message || 'Failed to load available networks');
    } finally {
      setIsLoadingNetworks(false);
    }
  };

  const getDefaultConfirmations = (symbol: string): number => {
    const confirmationMap: Record<string, number> = {
      'BTC': 3,
      'ETH': 12,
      'BNB': 3,
      'SOL': 32,
      'TRX': 19,
      'LTC': 6,
      'MATIC': 128
    };
    return confirmationMap[symbol] || 3;
  };

  const getDefaultExplorer = (symbol: string): string => {
    const explorerMap: Record<string, string> = {
      'BTC': 'https://blockstream.info',
      'ETH': 'https://etherscan.io',
      'BNB': 'https://bscscan.com',
      'SOL': 'https://solscan.io',
      'TRX': 'https://tronscan.org',
      'LTC': 'https://blockchair.com/litecoin',
      'MATIC': 'https://polygonscan.com'
    };
    return explorerMap[symbol] || '';
  };

  const getDefaultDecimals = (symbol: string): number => {
    const decimalsMap: Record<string, number> = {
      'BTC': 8,
      'ETH': 18,
      'BNB': 18,
      'SOL': 9,
      'TRX': 6,
      'LTC': 8,
      'MATIC': 18
    };
    return decimalsMap[symbol] || 8;
  };

  const loadDepositAddress = async (network: NetworkOption) => {
    try {
      setIsLoadingAddress(true);
      const crypto = supportedCryptos.find(c => c.symbol === selectedCrypto);
      
      if (crypto?.isMultiNetwork) {
        // Multi-network crypto - use multi-network API
        const data = await apiClient.generateMultiNetworkDepositAddress(selectedCrypto, network.network_type);
        
        if (data.success) {
          setDepositAddress(data);
        } else {
          throw new Error(data.error || 'Failed to generate deposit address');
        }
      } else {
        // Single-network crypto - use regular deposit address API
        const data = await apiClient.generateDepositAddress(selectedCrypto);
        
        if (data.success && data.address) {
          // Convert to multi-network format for consistent UI
          const convertedData: DepositAddress = {
            success: true,
            address: data.address,
            currency_code: selectedCrypto,
            network: {
              type: network.network_type,
              name: network.display_name,
              confirmation_blocks: network.confirmation_blocks,
              explorer_url: network.explorer_url
            },
            token_info: {
              symbol: selectedCrypto,
              contract_address: '', // No contract for native tokens
              decimals: getDefaultDecimals(selectedCrypto)
            }
          };
          setDepositAddress(convertedData);
        } else {
          throw new Error(data.error || 'Failed to generate deposit address');
        }
      }
    } catch (error: any) {
      console.error('Failed to load deposit address:', error);
      // Don't show toast for 400 errors (bad request/validation errors)
      if (error.status !== 400) {
        toast.error(error.message || 'Failed to generate deposit address');
      }
    } finally {
      setIsLoadingAddress(false);
    }
  };

  const handleNetworkSelect = (networkType: string) => {
    const network = networks.find(n => n.network_type === networkType);
    if (network) {
      setSelectedNetwork(network);
    }
  };

  const getNetworkLogo = (networkType: string) => {
    const networkLogoMap: Record<string, string> = {
      'ethereum': 'ETH',
      'ethereum_sepolia': 'ETH',
      'ethereum_goerli': 'ETH',
      'base': 'BASE',
      'base_sepolia': 'BASE',
      'arbitrum': 'ARB',
      'arbitrum_sepolia': 'ARB',
      'optimism': 'OP',
      'optimism_sepolia': 'OP',
      'bsc': 'BNB',
      'bsc_testnet': 'BNB',
      'tron': 'TRX',
      'tron_shasta': 'TRX',
      'polygon': 'MATIC',
      'polygon_mumbai': 'MATIC',
      'bitcoin': 'BTC',
      'bitcoin_testnet': 'BTC',
      'litecoin': 'LTC',
      'litecoin_testnet': 'LTC',
      'xrp': 'XRP',
      'xrp_testnet': 'XRP',
      'solana': 'SOL',
      'solana_devnet': 'SOL',
      'solana_testnet': 'SOL'
    };
    // Extract symbol from network type if not in mapping (e.g., 'bitcoin' -> 'BTC')
    const symbol = networkLogoMap[networkType] || networkType.split('_')[0].toUpperCase();
    return getCryptoLogo(symbol);
  };

  const getNetworkFallbackLogo = (networkType: string) => {
    const networkLogoMap: Record<string, string> = {
      'ethereum': 'ETH',
      'ethereum_sepolia': 'ETH',
      'ethereum_goerli': 'ETH',
      'base': 'BASE',
      'base_sepolia': 'BASE',
      'arbitrum': 'ARB',
      'arbitrum_sepolia': 'ARB',
      'optimism': 'OP',
      'optimism_sepolia': 'OP',
      'bsc': 'BNB',
      'bsc_testnet': 'BNB',
      'tron': 'TRX',
      'tron_shasta': 'TRX',
      'polygon': 'MATIC',
      'polygon_mumbai': 'MATIC',
      'bitcoin': 'BTC',
      'bitcoin_testnet': 'BTC',
      'litecoin': 'LTC',
      'litecoin_testnet': 'LTC',
      'xrp': 'XRP',
      'xrp_testnet': 'XRP',
      'solana': 'SOL',
      'solana_devnet': 'SOL',
      'solana_testnet': 'SOL'
    };
    // Extract symbol from network type if not in mapping (e.g., 'bitcoin' -> 'BTC')
    const symbol = networkLogoMap[networkType] || networkType.split('_')[0].toUpperCase();
    return createFallbackLogo(symbol);
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Header */}
      <div className="flex items-center space-x-4 mb-8">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.back()}
            className="flex items-center space-x-2"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back</span>
          </Button>
          <div>
            <h1 className={`text-3xl font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
              Deposit Cryptocurrency
            </h1>
            <p className={`text-lg ${theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}`}>
              Select a cryptocurrency and network to generate your deposit address
            </p>
          </div>
        </div>

      <div className="grid gap-8 lg:grid-cols-2">
          {/* Left Column - Selection */}
          <div className="space-y-6">
            {/* Cryptocurrency Selection */}
            <Card className={theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'}>
              <CardHeader>
                <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
                  Select Cryptocurrency
                </CardTitle>
                <CardDescription className={theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}>
                  Choose the cryptocurrency you want to deposit
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isLoadingCurrencies ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <span className="ml-2">Loading currencies...</span>
                  </div>
                ) : (
                  <Select value={selectedCrypto} onValueChange={setSelectedCrypto}>
                    <SelectTrigger className={`w-full ${theme === 'dark' ? 'bg-[#2B3139] border-[#2B3139] text-white' : 'bg-white border-gray-200'}`}>
                      <SelectValue placeholder="Select a cryptocurrency">
                      {selectedCrypto && (
                        <div className="flex items-center space-x-2">
                          <div className="relative w-5 h-5">
                            <Image
                              src={getCryptoLogo(selectedCrypto)}
                              alt={selectedCrypto}
                              width={20}
                              height={20}
                              className="rounded-full"
                              onError={(e) => {
                                const target = e.target as HTMLImageElement;
                                target.src = createFallbackLogo(selectedCrypto);
                              }}
                            />
                          </div>
                          <span>{supportedCryptos.find(c => c.symbol === selectedCrypto)?.name}</span>
                        </div>
                      )}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent className={theme === 'dark' ? 'bg-[#2B3139] border-[#2B3139]' : 'bg-white border-gray-200'}>
                    {supportedCryptos.length === 0 ? (
                      <div className={`p-4 text-center ${theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}`}>
                        No currencies available for deposit
                      </div>
                    ) : (
                      supportedCryptos.map((crypto) => (
                        <SelectItem
                          key={crypto.symbol}
                          value={crypto.symbol}
                          className={`cursor-pointer ${theme === 'dark' ? 'text-white hover:bg-[#F0B90B]/10 focus:bg-[#F0B90B]/10' : 'text-gray-900 hover:bg-blue-50 focus:bg-blue-50'}`}
                        >
                          <div className="flex items-center space-x-3">
                            <div className="relative w-5 h-5">
                              <Image
                                src={getCryptoLogo(crypto.symbol)}
                                alt={crypto.name}
                                width={20}
                                height={20}
                                className="rounded-full"
                                onError={(e) => {
                                  const target = e.target as HTMLImageElement;
                                  target.src = createFallbackLogo(crypto.symbol);
                                }}
                              />
                            </div>
                            <div>
                              <div className="font-medium">{crypto.name}</div>
                              <div className={`text-xs ${theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}`}>
                                {crypto.symbol}
                              </div>
                            </div>
                          </div>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              )}
            </CardContent>
          </Card>

            {/* Network Selection */}
            {selectedCrypto && (
              <Card className={theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'}>
                <CardHeader>
                  <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
                    Select Network
                  </CardTitle>
                  <CardDescription className={theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}>
                    Choose the blockchain network for your deposit
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {isLoadingNetworks ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin" />
                      <span className="ml-2">Loading networks...</span>
                    </div>
                  ) : (
                    <Select
                      value={selectedNetwork?.network_type || ""}
                      onValueChange={handleNetworkSelect}
                    >
                      <SelectTrigger className={`w-full ${theme === 'dark' ? 'bg-[#2B3139] border-[#2B3139] text-white' : 'bg-white border-gray-200'}`}>
                        <SelectValue placeholder="Select a network">
                          {selectedNetwork && (
                            <div className="flex items-center space-x-2">
                              <div className="relative w-5 h-5">
                                <Image
                                  src={getNetworkLogo(selectedNetwork.network_type)}
                                  alt={selectedNetwork.display_name}
                                  width={20}
                                  height={20}
                                  className="rounded-full"
                                  onError={(e) => {
                                    const target = e.target as HTMLImageElement;
                                    target.src = getNetworkFallbackLogo(selectedNetwork.network_type);
                                  }}
                                />
                              </div>
                              <span>{selectedNetwork.display_name}</span>
                              {selectedNetwork.is_testnet && (
                                <Badge variant="outline" className="text-xs ml-2">
                                  Testnet
                                </Badge>
                              )}
                            </div>
                          )}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent className={theme === 'dark' ? 'bg-[#2B3139] border-[#2B3139]' : 'bg-white border-gray-200'}>
                        {networks.map((network) => (
                          <SelectItem
                            key={network.network_type}
                            value={network.network_type}
                            className={`cursor-pointer ${theme === 'dark' ? 'text-white hover:bg-[#F0B90B]/10 focus:bg-[#F0B90B]/10' : 'text-gray-900 hover:bg-blue-50 focus:bg-blue-50'}`}
                          >
                            <div className="flex items-center justify-between w-full">
                              <div className="flex items-center space-x-3">
                                <div className="relative w-5 h-5">
                                  <Image
                                    src={getNetworkLogo(network.network_type)}
                                    alt={network.display_name}
                                    width={20}
                                    height={20}
                                    className="rounded-full"
                                    onError={(e) => {
                                      const target = e.target as HTMLImageElement;
                                      target.src = getNetworkFallbackLogo(network.network_type);
                                    }}
                                  />
                                </div>
                                <div>
                                  <div className="font-medium">{network.display_name}</div>
                                  <div className={`text-xs ${theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}`}>
                                    {network.confirmation_blocks} confirmation{network.confirmation_blocks !== 1 ? 's' : ''}
                                  </div>
                                </div>
                              </div>
                              {network.is_testnet && (
                                <Badge variant="outline" className="text-xs">
                                  Testnet
                                </Badge>
                              )}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column - Deposit Address */}
          {selectedNetwork && (
            <div>
              <Card className={theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'}>
                <CardHeader>
                  <CardTitle className={theme === 'dark' ? 'text-white' : 'text-gray-900'}>
                    Deposit Address
                  </CardTitle>
                  <CardDescription className={theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}>
                    Send {selectedCrypto} to this address on {selectedNetwork.display_name}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {isLoadingAddress ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="h-8 w-8 animate-spin" />
                      <span className="ml-3">Generating address...</span>
                    </div>
                  ) : depositAddress ? (
                    <>
                      {/* QR Code */}
                      <div className="flex justify-center">
                        <motion.div
                          initial={{ opacity: 0, scale: 0.9 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="p-4 bg-white rounded-lg shadow-sm"
                        >
                          <QRCodeSVG value={depositAddress.address} size={200} />
                        </motion.div>
                      </div>

                      {/* Address */}
                      <div>
                        <label className={`text-sm font-medium ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                          Address
                        </label>
                        <div className="flex items-center space-x-2 mt-1">
                          <div className={`flex-1 p-3 rounded-lg font-mono text-sm break-all ${
                            theme === 'dark' ? 'bg-[#2B3139] text-white' : 'bg-gray-50 text-gray-900'
                          }`}>
                            {depositAddress.address}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => copyToClipboard(depositAddress.address, 'Address')}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      {/* Contract Address */}
                      {depositAddress.token_info.contract_address && (
                        <div>
                          <label className={`text-sm font-medium ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                            Token Contract
                          </label>
                          <div className="flex items-center space-x-2 mt-1">
                            <div className={`flex-1 p-3 rounded-lg font-mono text-sm break-all ${
                              theme === 'dark' ? 'bg-[#2B3139] text-white' : 'bg-gray-50 text-gray-900'
                            }`}>
                              {depositAddress.token_info.contract_address}
                            </div>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => copyToClipboard(depositAddress.token_info.contract_address, 'Contract')}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* Important Information */}
                      <div className={`p-4 rounded-lg ${theme === 'dark' ? 'bg-[#2B3139]' : 'bg-gray-50'}`}>
                        <div className="flex items-center space-x-2 mb-3">
                          <AlertCircle className="h-5 w-5 text-yellow-500" />
                          <span className={`text-sm font-medium ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                            Important Information
                          </span>
                        </div>
                        <ul className={`text-sm space-y-2 ${theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}`}>
                          <li>• Only send {selectedCrypto} to this address on {selectedNetwork.display_name}</li>
                          <li>• Minimum confirmations: {depositAddress.network.confirmation_blocks}</li>
                          <li>• Sending other tokens may result in permanent loss</li>
                          {selectedNetwork.is_testnet && (
                            <li className="text-yellow-500">• This is a testnet address for development only</li>
                          )}
                        </ul>
                      </div>

                      {/* Explorer Link */}
                      {/* {depositAddress.network.explorer_url && (
                        <div className="flex justify-center">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => window.open(`${depositAddress.network.explorer_url}/address/${depositAddress.address}`, '_blank')}
                            className="flex items-center space-x-2"
                          >
                            <ExternalLink className="h-4 w-4" />
                            <span>View on Explorer</span>
                          </Button>
                        </div>
                      )} */}
                    </>
                  ) : null}
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>
  );
}
