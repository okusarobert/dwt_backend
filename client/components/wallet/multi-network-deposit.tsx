"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { Copy, QrCode, Loader2, AlertCircle, CheckCircle2, Network, ExternalLink } from 'lucide-react';
import { QRCodeSVG } from "qrcode.react";
import { apiClient } from "@/lib/api-client";
import Image from "next/image";
import { getCryptoLogo, createFallbackLogo } from "@/lib/crypto-logos";

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

interface MultiNetworkDepositProps {
  isOpen: boolean;
  onClose: () => void;
  tokenSymbol: string;
  tokenName: string;
}

export function MultiNetworkDeposit({ isOpen, onClose, tokenSymbol, tokenName }: MultiNetworkDepositProps) {
  const { theme } = useTheme();
  const [networks, setNetworks] = useState<NetworkOption[]>([]);
  const [selectedNetwork, setSelectedNetwork] = useState<NetworkOption | null>(null);
  const [depositAddress, setDepositAddress] = useState<DepositAddress | null>(null);
  const [isLoadingNetworks, setIsLoadingNetworks] = useState(false);
  const [isLoadingAddress, setIsLoadingAddress] = useState(false);
  const [showQR, setShowQR] = useState(true);

  // Load available networks when dialog opens
  useEffect(() => {
    if (isOpen && tokenSymbol) {
      loadNetworks();
    }
  }, [isOpen, tokenSymbol]);

  const loadNetworks = async () => {
    try {
      setIsLoadingNetworks(true);
      // Include testnets in development environment
      const includeTestnets = process.env.NODE_ENV === 'development';
      const data = await apiClient.getMultiNetworkDepositNetworks(tokenSymbol, includeTestnets);
      
      if (data.success) {
        setNetworks(data.networks);
        // Auto-select first mainnet network
        const mainnetNetwork = data.networks.find((n: NetworkOption) => !n.is_testnet);
        if (mainnetNetwork) {
          setSelectedNetwork(mainnetNetwork);
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

  const loadDepositAddress = async (network: NetworkOption) => {
    try {
      setIsLoadingAddress(true);
      const data = await apiClient.generateMultiNetworkDepositAddress(tokenSymbol, network.network_type);
      
      if (data.success) {
        setDepositAddress(data);
      } else {
        throw new Error(data.error || 'Failed to generate deposit address');
      }
    } catch (error: any) {
      console.error('Failed to load deposit address:', error);
      toast.error(error.message || 'Failed to generate deposit address');
    } finally {
      setIsLoadingAddress(false);
    }
  };

  const handleNetworkSelect = (networkType: string) => {
    const network = networks.find(n => n.network_type === networkType);
    if (network) {
      setSelectedNetwork(network);
      setDepositAddress(null);
      loadDepositAddress(network);
    }
  };

  const getNetworkLogo = (networkType: string) => {
    const networkLogoMap: Record<string, string> = {
      'ethereum': 'ETH',
      'ethereum_sepolia': 'ETH',
      'ethereum_goerli': 'ETH',
      'bsc': 'BNB',
      'bsc_testnet': 'BNB',
      'tron': 'TRX',
      'tron_shasta': 'TRX',
      'polygon': 'MATIC',
      'polygon_mumbai': 'MATIC',
      'bitcoin': 'BTC',
      'bitcoin_testnet': 'BTC',
      'litecoin': 'LTC',
      'litecoin_testnet': 'LTC'
    };
    const symbol = networkLogoMap[networkType] || 'ETH';
    return getCryptoLogo(symbol);
  };

  const getNetworkFallbackLogo = (networkType: string) => {
    const networkLogoMap: Record<string, string> = {
      'ethereum': 'ETH',
      'ethereum_sepolia': 'ETH',
      'ethereum_goerli': 'ETH',
      'bsc': 'BNB',
      'bsc_testnet': 'BNB',
      'tron': 'TRX',
      'tron_shasta': 'TRX',
      'polygon': 'MATIC',
      'polygon_mumbai': 'MATIC',
      'bitcoin': 'BTC',
      'bitcoin_testnet': 'BTC',
      'litecoin': 'LTC',
      'litecoin_testnet': 'LTC'
    };
    const symbol = networkLogoMap[networkType] || 'ETH';
    return createFallbackLogo(symbol);
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard`);
  };

  const handleClose = () => {
    setSelectedNetwork(null);
    setDepositAddress(null);
    setNetworks([]);
    setShowQR(false);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className={`max-w-2xl ${theme === 'dark' ? 'bg-[#1E2329] border-[#2B3139]' : 'bg-white border-gray-200'}`}>
        <DialogHeader>
          <DialogTitle className={`text-xl font-bold ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
            Deposit {tokenName} ({tokenSymbol})
          </DialogTitle>
          <DialogDescription className={theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}>
            Select a network to generate your deposit address
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Network Selection */}
          <div>
            <h3 className={`text-sm font-medium mb-3 ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
              Choose Network
            </h3>
            
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
          </div>

          {/* Deposit Address */}
          {selectedNetwork && (
            <div>
              <h3 className={`text-sm font-medium mb-3 ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                Deposit Address
              </h3>
              
              {isLoadingAddress ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin" />
                  <span className="ml-2">Generating address...</span>
                </div>
              ) : depositAddress ? (
                <Card className={theme === 'dark' ? 'border-[#2B3139]' : 'border-gray-200'}>
                  <CardContent className="p-4 space-y-4">
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

                    {/* QR Code */}
                    <div className="flex justify-center">
                      <Button
                        variant="outline"
                        onClick={() => setShowQR(!showQR)}
                        className="flex items-center space-x-2"
                      >
                        <QrCode className="h-4 w-4" />
                        <span>{showQR ? 'Hide' : 'Show'} QR Code</span>
                      </Button>
                    </div>

                    {showQR && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="flex justify-center"
                      >
                        <div className="p-4 bg-white rounded-lg">
                          <QRCodeSVG value={depositAddress.address} size={200} />
                        </div>
                      </motion.div>
                    )}

                    {/* Network Info */}
                    <div className={`p-3 rounded-lg ${theme === 'dark' ? 'bg-[#2B3139]' : 'bg-gray-50'}`}>
                      <div className="flex items-center space-x-2 mb-2">
                        <AlertCircle className="h-4 w-4 text-yellow-500" />
                        <span className={`text-sm font-medium ${theme === 'dark' ? 'text-white' : 'text-gray-900'}`}>
                          Important Information
                        </span>
                      </div>
                      <ul className={`text-sm space-y-1 ${theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-600'}`}>
                        <li>• Only send {tokenSymbol} to this address on {selectedNetwork.display_name}</li>
                        <li>• Minimum confirmations: {depositAddress.network.confirmation_blocks}</li>
                        <li>• Sending other tokens may result in permanent loss</li>
                        {selectedNetwork.is_testnet && (
                          <li className="text-yellow-500">• This is a testnet address for development only</li>
                        )}
                      </ul>
                    </div>

                    {/* Explorer Link */}
                    {depositAddress.network.explorer_url && (
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
                    )}
                  </CardContent>
                </Card>
              ) : null}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
