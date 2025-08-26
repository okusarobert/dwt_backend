"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Plus, Trash2, Network, Save, X } from "lucide-react";
import { getCryptoLogo } from "@/lib/crypto-logos";
import Image from "next/image";

interface NetworkConfig {
  network_type: string;
  network_name: string;
  display_name: string;
  is_enabled: boolean;
  contract_address?: string;
  confirmation_blocks: number;
  explorer_url: string;
  is_testnet: boolean;
}

interface Currency {
  id: string;
  symbol: string;
  name: string;
  is_enabled: boolean;
  is_multi_network: boolean;
  contract_address?: string;
  decimals: number;
  networks: NetworkConfig[];
}

interface CurrencyFormProps {
  currency?: Currency | null;
  onSubmit: (data: any) => void;
  onCancel: () => void;
}

const AVAILABLE_NETWORKS = [
  { type: "ethereum", name: "Ethereum", display: "Ethereum Mainnet", testnet: false },
  { type: "ethereum_sepolia", name: "Ethereum Sepolia", display: "Ethereum Sepolia", testnet: true },
  { type: "bsc", name: "BSC", display: "BNB Smart Chain", testnet: false },
  { type: "bsc_testnet", name: "BSC Testnet", display: "BNB Smart Chain Testnet", testnet: true },
  { type: "polygon", name: "Polygon", display: "Polygon Mainnet", testnet: false },
  { type: "polygon_mumbai", name: "Polygon Mumbai", display: "Polygon Mumbai", testnet: true },
  { type: "arbitrum", name: "Arbitrum", display: "Arbitrum One", testnet: false },
  { type: "arbitrum_sepolia", name: "Arbitrum Sepolia", display: "Arbitrum Sepolia", testnet: true },
  { type: "optimism", name: "Optimism", display: "Optimism Mainnet", testnet: false },
  { type: "optimism_sepolia", name: "Optimism Sepolia", display: "Optimism Sepolia", testnet: true },
  { type: "base", name: "Base", display: "Base Mainnet", testnet: false },
  { type: "base_sepolia", name: "Base Sepolia", display: "Base Sepolia", testnet: true },
  { type: "bitcoin", name: "Bitcoin", display: "Bitcoin Mainnet", testnet: false },
  { type: "bitcoin_testnet", name: "Bitcoin Testnet", display: "Bitcoin Testnet", testnet: true },
  { type: "litecoin", name: "Litecoin", display: "Litecoin Mainnet", testnet: false },
  { type: "litecoin_testnet", name: "Litecoin Testnet", display: "Litecoin Testnet", testnet: true },
  { type: "tron", name: "Tron", display: "Tron Mainnet", testnet: false },
  { type: "tron_shasta", name: "Tron Shasta", display: "Tron Shasta", testnet: true },
  { type: "xrp", name: "XRP Ledger", display: "XRP Mainnet", testnet: false },
  { type: "xrp_testnet", name: "XRP Testnet", display: "XRP Testnet", testnet: true },
  { type: "solana", name: "Solana", display: "Solana Mainnet", testnet: false },
  { type: "solana_devnet", name: "Solana Devnet", display: "Solana Devnet", testnet: true },
  { type: "solana_testnet", name: "Solana Testnet", display: "Solana Testnet", testnet: true },
];

export default function CurrencyForm({ currency, onSubmit, onCancel }: CurrencyFormProps) {
  const [formData, setFormData] = useState({
    symbol: "",
    name: "",
    is_enabled: true,
    is_multi_network: false,
    contract_address: "",
    decimals: 18,
  });

  const [networks, setNetworks] = useState<NetworkConfig[]>([]);

  useEffect(() => {
    if (currency) {
      setFormData({
        symbol: currency.symbol,
        name: currency.name,
        is_enabled: currency.is_enabled,
        is_multi_network: currency.is_multi_network,
        contract_address: currency.contract_address || "",
        decimals: currency.decimals,
      });
      setNetworks(currency.networks || []);
    } else {
      // Reset form for new currency
      setFormData({
        symbol: "",
        name: "",
        is_enabled: true,
        is_multi_network: false,
        contract_address: "",
        decimals: 18,
      });
      setNetworks([]);
    }
  }, [currency]);

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const addNetwork = () => {
    const newNetwork: NetworkConfig = {
      network_type: "",
      network_name: "",
      display_name: "",
      is_enabled: true,
      contract_address: "",
      confirmation_blocks: 12,
      explorer_url: "",
      is_testnet: false,
    };
    setNetworks(prev => [...prev, newNetwork]);
  };

  const updateNetwork = (index: number, field: string, value: any) => {
    setNetworks(prev => prev.map((network, i) => {
      if (i === index) {
        const updated = { ...network, [field]: value };
        
        // Auto-populate fields when network type changes
        if (field === "network_type") {
          const availableNetwork = AVAILABLE_NETWORKS.find(n => n.type === value);
          if (availableNetwork) {
            updated.network_name = availableNetwork.name;
            updated.display_name = availableNetwork.display;
            updated.is_testnet = availableNetwork.testnet;
            
            // Set default explorer URLs
            switch (value) {
              case "ethereum":
                updated.explorer_url = "https://etherscan.io";
                break;
              case "ethereum_sepolia":
                updated.explorer_url = "https://sepolia.etherscan.io";
                break;
              case "bsc":
                updated.explorer_url = "https://bscscan.com";
                break;
              case "bsc_testnet":
                updated.explorer_url = "https://testnet.bscscan.com";
                break;
              case "polygon":
                updated.explorer_url = "https://polygonscan.com";
                break;
              case "polygon_mumbai":
                updated.explorer_url = "https://mumbai.polygonscan.com";
                break;
              case "arbitrum":
                updated.explorer_url = "https://arbiscan.io";
                break;
              case "arbitrum_sepolia":
                updated.explorer_url = "https://sepolia.arbiscan.io";
                break;
              case "optimism":
                updated.explorer_url = "https://optimistic.etherscan.io";
                break;
              case "optimism_sepolia":
                updated.explorer_url = "https://sepolia-optimism.etherscan.io";
                break;
              case "base":
                updated.explorer_url = "https://basescan.org";
                break;
              case "base_sepolia":
                updated.explorer_url = "https://sepolia.basescan.org";
                break;
              case "bitcoin":
                updated.explorer_url = "https://blockstream.info";
                updated.confirmation_blocks = 6;
                break;
              case "bitcoin_testnet":
                updated.explorer_url = "https://blockstream.info/testnet";
                updated.confirmation_blocks = 6;
                break;
              case "litecoin":
                updated.explorer_url = "https://blockchair.com/litecoin";
                updated.confirmation_blocks = 6;
                break;
              case "litecoin_testnet":
                updated.explorer_url = "https://blockchair.com/litecoin/testnet";
                updated.confirmation_blocks = 6;
                break;
              case "tron":
                updated.explorer_url = "https://tronscan.org";
                updated.confirmation_blocks = 19;
                break;
              case "tron_shasta":
                updated.explorer_url = "https://shasta.tronscan.org";
                updated.confirmation_blocks = 19;
                break;
              case "xrp":
                updated.explorer_url = "https://xrpscan.com";
                updated.confirmation_blocks = 1;
                break;
              case "xrp_testnet":
                updated.explorer_url = "https://testnet.xrpl.org";
                updated.confirmation_blocks = 1;
                break;
              case "solana":
                updated.explorer_url = "https://explorer.solana.com";
                updated.confirmation_blocks = 1;
                break;
              case "solana_devnet":
                updated.explorer_url = "https://explorer.solana.com/?cluster=devnet";
                updated.confirmation_blocks = 1;
                break;
              case "solana_testnet":
                updated.explorer_url = "https://explorer.solana.com/?cluster=testnet";
                updated.confirmation_blocks = 1;
                break;
            }
          }
        }
        
        return updated;
      }
      return network;
    }));
  };

  const removeNetwork = (index: number) => {
    setNetworks(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.symbol.trim()) {
      alert("Symbol is required");
      return;
    }
    if (!formData.name.trim()) {
      alert("Name is required");
      return;
    }
    if (formData.is_multi_network && networks.length === 0) {
      alert("Multi-network currencies must have at least one network configured");
      return;
    }

    const submitData = {
      ...formData,
      networks: formData.is_multi_network ? networks : [],
    };

    onSubmit(submitData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {formData.symbol && (
              <div className="relative w-6 h-6">
                <Image
                  src={getCryptoLogo(formData.symbol)}
                  alt={formData.symbol}
                  width={24}
                  height={24}
                  className="rounded-full"
                />
              </div>
            )}
            Basic Information
          </CardTitle>
          <CardDescription>
            Configure the basic currency properties
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="symbol">Symbol *</Label>
              <Input
                id="symbol"
                value={formData.symbol}
                onChange={(e) => handleInputChange("symbol", e.target.value.toUpperCase())}
                placeholder="BTC, ETH, etc."
                required
              />
            </div>
            <div>
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => handleInputChange("name", e.target.value)}
                placeholder="Bitcoin, Ethereum, etc."
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="decimals">Decimals</Label>
              <Input
                id="decimals"
                type="number"
                value={formData.decimals}
                onChange={(e) => handleInputChange("decimals", parseInt(e.target.value) || 18)}
                min="0"
                max="18"
              />
            </div>
            <div>
              <Label htmlFor="contract_address">Contract Address (if token)</Label>
              <Input
                id="contract_address"
                value={formData.contract_address}
                onChange={(e) => handleInputChange("contract_address", e.target.value)}
                placeholder="0x..."
              />
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="is_enabled"
                checked={formData.is_enabled}
                onCheckedChange={(checked) => handleInputChange("is_enabled", checked)}
              />
              <Label htmlFor="is_enabled">Enabled</Label>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="is_multi_network"
                checked={formData.is_multi_network}
                onCheckedChange={(checked) => handleInputChange("is_multi_network", checked)}
              />
              <Label htmlFor="is_multi_network">Multi-Network</Label>
            </div>
          </div>
        </CardContent>
      </Card>

      {formData.is_multi_network && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Network className="w-5 h-5" />
                  Network Configuration
                </CardTitle>
                <CardDescription>
                  Configure supported networks for this currency
                </CardDescription>
              </div>
              <Button type="button" variant="outline" onClick={addNetwork}>
                <Plus className="w-4 h-4 mr-2" />
                Add Network
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {networks.map((network, index) => (
                <Card key={index} className="border-dashed">
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between mb-4">
                      <Badge variant={network.is_testnet ? "secondary" : "default"}>
                        Network {index + 1}
                      </Badge>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeNetwork(index)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <Label>Network Type *</Label>
                        <select
                          className="w-full p-2 border rounded-md"
                          value={network.network_type}
                          onChange={(e) => updateNetwork(index, "network_type", e.target.value)}
                          required
                        >
                          <option value="">Select Network</option>
                          {AVAILABLE_NETWORKS.map((net) => (
                            <option key={net.type} value={net.type}>
                              {net.display}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <Label>Display Name</Label>
                        <Input
                          value={network.display_name}
                          onChange={(e) => updateNetwork(index, "display_name", e.target.value)}
                          placeholder="Network display name"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div>
                        <Label>Contract Address</Label>
                        <Input
                          value={network.contract_address || ""}
                          onChange={(e) => updateNetwork(index, "contract_address", e.target.value)}
                          placeholder="0x... (leave empty for native token)"
                        />
                      </div>
                      <div>
                        <Label>Confirmation Blocks</Label>
                        <Input
                          type="number"
                          value={network.confirmation_blocks}
                          onChange={(e) => updateNetwork(index, "confirmation_blocks", parseInt(e.target.value) || 12)}
                          min="1"
                        />
                      </div>
                    </div>

                    <div className="mb-4">
                      <Label>Explorer URL</Label>
                      <Input
                        value={network.explorer_url}
                        onChange={(e) => updateNetwork(index, "explorer_url", e.target.value)}
                        placeholder="https://etherscan.io"
                      />
                    </div>

                    <div className="flex items-center space-x-2">
                      <Switch
                        checked={network.is_enabled}
                        onCheckedChange={(checked) => updateNetwork(index, "is_enabled", checked)}
                      />
                      <Label>Network Enabled</Label>
                    </div>
                  </CardContent>
                </Card>
              ))}

              {networks.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  No networks configured. Click "Add Network" to get started.
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <Separator />

      <div className="flex items-center justify-end space-x-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          <X className="w-4 h-4 mr-2" />
          Cancel
        </Button>
        <Button type="submit">
          <Save className="w-4 h-4 mr-2" />
          {currency ? "Update Currency" : "Create Currency"}
        </Button>
      </div>
    </form>
  );
}
