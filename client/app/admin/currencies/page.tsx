"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "react-hot-toast";
import { Plus, Edit, Trash2, Search, Network, DollarSign } from "lucide-react";
import { getCryptoLogo } from "@/lib/crypto-logos";
import Image from "next/image";
import { apiClient } from "@/lib/api-client";
import CurrencyForm from "./currency-form";

interface Currency {
  id: string;
  symbol: string;
  name: string;
  is_enabled: boolean;
  is_multi_network: boolean;
  contract_address?: string;
  decimals: number;
  networks: NetworkConfig[];
  created_at: string;
  updated_at: string;
}

interface NetworkConfig {
  network_type: string;
  network_name: string;
  is_enabled: boolean;
  contract_address?: string;
  confirmation_blocks: number;
  explorer_url: string;
}

export default function CurrenciesPage() {
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [filteredCurrencies, setFilteredCurrencies] = useState<Currency[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingCurrency, setEditingCurrency] = useState<Currency | null>(null);

  useEffect(() => {
    loadCurrencies();
  }, []);

  useEffect(() => {
    const filtered = currencies.filter(currency =>
      currency.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      currency.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredCurrencies(filtered);
  }, [currencies, searchTerm]);

  const loadCurrencies = async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.getCurrencies();
      if (data.success) {
        setCurrencies(data.currencies);
      } else {
        toast.error("Failed to load currencies");
      }
    } catch (error: any) {
      console.error("Failed to load currencies:", error);
      toast.error("Failed to load currencies");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleCurrencyStatus = async (currencyId: string, isEnabled: boolean) => {
    try {
      const data = await apiClient.updateCurrencyStatus(currencyId, isEnabled);
      if (data.success) {
        setCurrencies(prev => prev.map(c => 
          c.id === currencyId ? { ...c, is_enabled: isEnabled } : c
        ));
        toast.success(`Currency ${isEnabled ? 'enabled' : 'disabled'} successfully`);
      } else {
        toast.error(data.error || "Failed to update currency status");
      }
    } catch (error: any) {
      console.error("Failed to update currency status:", error);
      toast.error("Failed to update currency status");
    }
  };

  const deleteCurrency = async (currencyId: string) => {
    if (!confirm("Are you sure you want to delete this currency? This action cannot be undone.")) {
      return;
    }

    try {
      const data = await apiClient.deleteCurrency(currencyId);
      if (data.success) {
        setCurrencies(prev => prev.filter(c => c.id !== currencyId));
        toast.success("Currency deleted successfully");
      } else {
        toast.error(data.error || "Failed to delete currency");
      }
    } catch (error: any) {
      console.error("Failed to delete currency:", error);
      toast.error("Failed to delete currency");
    }
  };

  const handleCurrencySubmit = async (currencyData: any) => {
    try {
      let data;
      if (editingCurrency) {
        data = await apiClient.updateCurrency(editingCurrency.id, currencyData);
      } else {
        data = await apiClient.createCurrency(currencyData);
      }

      if (data.success) {
        await loadCurrencies();
        setShowAddDialog(false);
        setEditingCurrency(null);
        toast.success(`Currency ${editingCurrency ? 'updated' : 'created'} successfully`);
      } else {
        toast.error(data.error || `Failed to ${editingCurrency ? 'update' : 'create'} currency`);
      }
    } catch (error: any) {
      console.error(`Failed to ${editingCurrency ? 'update' : 'create'} currency:`, error);
      toast.error(`Failed to ${editingCurrency ? 'update' : 'create'} currency`);
    }
  };

  const openEditDialog = (currency: Currency) => {
    setEditingCurrency(currency);
    setShowAddDialog(true);
  };

  const closeDialog = () => {
    setShowAddDialog(false);
    setEditingCurrency(null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Currency Management</h1>
          <p className="text-gray-600">Manage supported cryptocurrencies and their network configurations</p>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button onClick={() => setEditingCurrency(null)}>
              <Plus className="w-4 h-4 mr-2" />
              Add Currency
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingCurrency ? 'Edit Currency' : 'Add New Currency'}
              </DialogTitle>
              <DialogDescription>
                {editingCurrency 
                  ? 'Update the currency configuration and network settings'
                  : 'Configure a new cryptocurrency with its network settings'
                }
              </DialogDescription>
            </DialogHeader>
            <CurrencyForm
              currency={editingCurrency}
              onSubmit={handleCurrencySubmit}
              onCancel={closeDialog}
            />
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <DollarSign className="w-5 h-5" />
            Currencies
          </CardTitle>
          <CardDescription>
            Manage cryptocurrency configurations, network settings, and availability
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search currencies..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Currency</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Networks</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredCurrencies.map((currency) => (
                  <TableRow key={currency.id}>
                    <TableCell>
                      <div className="flex items-center space-x-3">
                        <div className="relative w-8 h-8">
                          <Image
                            src={getCryptoLogo(currency.symbol)}
                            alt={currency.name}
                            width={32}
                            height={32}
                            className="rounded-full"
                          />
                        </div>
                        <div>
                          <div className="font-medium">{currency.symbol}</div>
                          <div className="text-sm text-gray-500">{currency.name}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={currency.is_multi_network ? "default" : "secondary"}>
                        {currency.is_multi_network ? "Multi-Network" : "Single Network"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Network className="w-4 h-4 text-gray-400" />
                        <span className="text-sm">
                          {currency.networks.filter(n => n.is_enabled).length} / {currency.networks.length} active
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Switch
                          checked={currency.is_enabled}
                          onCheckedChange={(checked) => toggleCurrencyStatus(currency.id, checked)}
                        />
                        <span className="text-sm">
                          {currency.is_enabled ? "Enabled" : "Disabled"}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => openEditDialog(currency)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => deleteCurrency(currency.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {filteredCurrencies.length === 0 && !isLoading && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-gray-500">
                      {searchTerm ? "No currencies found matching your search" : "No currencies configured"}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
