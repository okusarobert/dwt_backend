"use client";

import { useEffect, useMemo, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import toast from "react-hot-toast";

interface ReserveStatusItem {
  currency: string;
  accounts: Array<{
    account_type: string;
    balance: number;
    available?: number;
    locked?: number;
    address_count?: number;
  }>;
}

export default function AdminReservesPage() {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<ReserveStatusItem[]>([]);
  const [selectedCurrency, setSelectedCurrency] = useState<string>("");
  const [selectedAccountType, setSelectedAccountType] = useState<string>("");
  const [balanceLoading, setBalanceLoading] = useState(false);
  const [balance, setBalance] = useState<number | null>(null);
  const [topupAmount, setTopupAmount] = useState("");
  const [topupRef, setTopupRef] = useState("");
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [withdrawRef, setWithdrawRef] = useState("");
  const [analytics, setAnalytics] = useState<any | null>(null);
  const [analyticsDays, setAnalyticsDays] = useState(30);
  const [actionLoading, setActionLoading] = useState(false);

  const toNumberish = (val: any): number | string => {
    if (typeof val === "number") return val;
    if (val && typeof val === "object") {
      const i: any = val;
      if (typeof i.total_balance === "number") return i.total_balance;
      if (typeof i.available_balance === "number") return i.available_balance;
      if (typeof i.balance === "number") return i.balance;
    }
    return "-";
  };

  const currencies = useMemo(
    () => Array.from(new Set((status || []).map((s) => s.currency))).sort(),
    [status]
  );

  const accountTypesForCurrency = useMemo(() => {
    const item = status.find((s) => s.currency === selectedCurrency);
    return (item?.accounts || []).map((a) => a.account_type);
  }, [status, selectedCurrency]);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const res = await apiClient.getReserveStatus();
      // Expecting { success: true, reserves: [...] }
      const reserves: ReserveStatusItem[] = res?.reserves || [];
      setStatus(reserves);
      // Auto-select first available account for convenience
      if (reserves.length > 0) {
        const first = reserves[0];
        if (!selectedCurrency) setSelectedCurrency(first.currency);
        const firstType = first.accounts?.[0]?.account_type || "";
        if (!selectedAccountType && firstType)
          setSelectedAccountType(firstType);
      }
    } catch (e: any) {
      console.error(e);
      toast.error("Failed to load reserve status");
    } finally {
      setLoading(false);
    }
  };

  const loadBalance = async () => {
    if (!selectedCurrency || !selectedAccountType) return;
    try {
      setBalanceLoading(true);
      const res = await apiClient.getReserveBalance(
        selectedCurrency,
        selectedAccountType
      );
      setBalance(res?.balance ?? null);
    } catch (e) {
      console.error(e);
      toast.error("Failed to load balance");
    } finally {
      setBalanceLoading(false);
    }
  };

  const runTopup = async () => {
    if (!selectedCurrency || !selectedAccountType || !topupAmount) return;
    try {
      setActionLoading(true);
      const res = await apiClient.topUpReserve(
        selectedCurrency,
        selectedAccountType,
        Number(topupAmount),
        topupRef || undefined
      );
      if (res?.success) {
        toast.success("Reserve topped up");
        setTopupAmount("");
        setTopupRef("");
        await loadStatus();
        await loadBalance();
      } else {
        toast.error(res?.error || "Top up failed");
      }
    } catch (e: any) {
      console.error(e);
      toast.error(e?.message || "Top up failed");
    } finally {
      setActionLoading(false);
    }
  };

  const runWithdraw = async () => {
    if (!selectedCurrency || !selectedAccountType || !withdrawAmount) return;
    try {
      setActionLoading(true);
      const res = await apiClient.withdrawFromReserve(
        selectedCurrency,
        selectedAccountType,
        Number(withdrawAmount),
        withdrawRef || undefined
      );
      if (res?.success) {
        toast.success("Withdrawal executed");
        setWithdrawAmount("");
        setWithdrawRef("");
        await loadStatus();
        await loadBalance();
      } else {
        toast.error(res?.error || "Withdraw failed");
      }
    } catch (e: any) {
      console.error(e);
      toast.error(e?.message || "Withdraw failed");
    } finally {
      setActionLoading(false);
    }
  };

  const loadAnalytics = async () => {
    try {
      const res = await apiClient.getReserveAnalytics(analyticsDays);
      setAnalytics(res?.analytics || null);
    } catch (e) {
      console.error(e);
      toast.error("Failed to load analytics");
    }
  };

  const clearCache = async () => {
    try {
      setActionLoading(true);
      await apiClient.clearReserveCache();
      toast.success("Reserve cache cleared");
    } catch (e) {
      console.error(e);
      toast.error("Failed to clear cache");
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  useEffect(() => {
    setSelectedAccountType("");
    setBalance(null);
  }, [selectedCurrency]);

  useEffect(() => {
    setBalance(null);
    if (selectedAccountType) loadBalance();
  }, [selectedAccountType]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-lg font-semibold text-foreground">Reserves</h1>
        <p className="text-muted-foreground">
          Manage liquidity reserves used for trading and withdrawals.
        </p>
      </div>

      <Card className="p-4">
        {loading ? (
          <div className="flex items-center gap-2">
            <LoadingSpinner /> <span>Loading status...</span>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <label className="text-sm text-muted-foreground">Currency</label>
                <Select
                  value={selectedCurrency}
                  onValueChange={(val) => setSelectedCurrency(val)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select currency" />
                  </SelectTrigger>
                  <SelectContent>
                    {currencies.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Account Type</label>
                <Select
                  value={selectedAccountType}
                  onValueChange={(val) => setSelectedAccountType(val)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select account type" />
                  </SelectTrigger>
                  <SelectContent>
                    {accountTypesForCurrency.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end gap-2">
                <Button
                  onClick={loadBalance}
                  disabled={!selectedAccountType || balanceLoading}
                >
                  {balanceLoading ? "Loading..." : "Refresh Balance"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={loadStatus}
                  disabled={loading}
                >
                  Refresh Status
                </Button>
              </div>
              <div className="flex items-end">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setSelectedCurrency("");
                    setSelectedAccountType("");
                    setBalance(null);
                  }}
                >
                  Clear Selection
                </Button>
              </div>
            </div>

            {balance !== null && (
              <div className="text-foreground">
                <span className="font-medium">Balance:</span>{" "}
                {typeof balance === "number" ? balance : "-"} {selectedCurrency}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="p-4">
                <h3 className="font-medium text-card-foreground mb-3">Top Up</h3>
                <div className="space-y-3">
                  <Input
                    placeholder="Amount"
                    type="number"
                    value={topupAmount}
                    onChange={(e) => setTopupAmount(e.target.value)}
                  />
                  <Input
                    placeholder="Source reference (optional)"
                    value={topupRef}
                    onChange={(e) => setTopupRef(e.target.value)}
                  />
                  <Button
                    onClick={runTopup}
                    disabled={
                      actionLoading || !selectedAccountType || !topupAmount
                    }
                  >
                    {actionLoading ? "Processing..." : "Top Up"}
                  </Button>
                </div>
              </Card>

              <Card className="p-4">
                <h3 className="font-medium text-card-foreground mb-3">Withdraw</h3>
                <div className="space-y-3">
                  <Input
                    placeholder="Amount"
                    type="number"
                    value={withdrawAmount}
                    onChange={(e) => setWithdrawAmount(e.target.value)}
                  />
                  <Input
                    placeholder="Destination reference (optional)"
                    value={withdrawRef}
                    onChange={(e) => setWithdrawRef(e.target.value)}
                  />
                  <Button
                    onClick={runWithdraw}
                    disabled={
                      actionLoading || !selectedAccountType || !withdrawAmount
                    }
                  >
                    {actionLoading ? "Processing..." : "Withdraw"}
                  </Button>
                </div>
              </Card>
            </div>

            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                onClick={clearCache}
                disabled={actionLoading}
              >
                Clear Reserve Cache
              </Button>
            </div>

            {/* Selectable list/table of all reserve accounts */}
            <div className="space-y-2">
              <h3 className="font-medium text-foreground">Accounts</h3>
              {status.length === 0 ? (
                <div className="text-sm text-muted-foreground">
                  No reserves available.
                </div>
              ) : (
                <div className="overflow-auto border rounded-lg">
                  <table className="min-w-full text-sm">
                    <thead className="bg-background text-foreground">
                      <tr>
                        <th className="text-left p-2">Currency</th>
                        <th className="text-left p-2">Type</th>
                        <th className="text-right p-2">Balance</th>
                        <th className="text-right p-2">Available</th>
                        <th className="text-right p-2">Locked</th>
                        <th className="text-right p-2">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {status.flatMap((s) =>
                        s.accounts.map((a) => {
                          const isSelected =
                            s.currency === selectedCurrency &&
                            a.account_type === selectedAccountType;
                          return (
                            <tr
                              key={`${s.currency}-${a.account_type}`}
                              className={`${
                                isSelected ? "bg-accent" : ""
                              } hover:bg-muted/50 cursor-pointer`}
                              onClick={() => {
                                setSelectedCurrency(s.currency);
                                setSelectedAccountType(a.account_type);
                                setBalance(null);
                              }}
                            >
                              <td className="p-2 font-medium text-foreground">
                                {s.currency}
                              </td>
                              <td className="p-2">{a.account_type}</td>
                              <td className="p-2 text-right">
                                {toNumberish(a.balance)}
                              </td>
                              <td className="p-2 text-right">
                                {toNumberish(a.available)}
                              </td>
                              <td className="p-2 text-right">
                                {toNumberish(a.locked)}
                              </td>
                              <td className="p-2 text-right">
                                <Button
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedCurrency(s.currency);
                                    setSelectedAccountType(a.account_type);
                                    loadBalance();
                                  }}
                                >
                                  Select
                                </Button>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}
      </Card>

      <Card className="p-3 space-y-3">
        <div className="flex items-end gap-3">
          <div>
            <label className="text-sm text-muted-foreground">
              Analytics Period (days)
            </label>
            <Input
              type="number"
              min={1}
              max={365}
              value={analyticsDays}
              onChange={(e) => setAnalyticsDays(Number(e.target.value))}
            />
          </div>
          <Button onClick={loadAnalytics}>Load Analytics</Button>
        </div>

        {analytics && (
          <div className="space-y-6">
            {/* Summary cards (USD only) */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-3 rounded border">
                <div className="text-xs text-gray-500">Inflow (USD)</div>
                <div className="text-lg font-semibold">
                  ${Number(analytics?.totals?.inflow_usd || 0).toLocaleString()}
                </div>
              </div>
              <div className="p-3 rounded border">
                <div className="text-xs text-gray-500">Outflow (USD)</div>
                <div className="text-lg font-semibold">
                  $
                  {Number(analytics?.totals?.outflow_usd || 0).toLocaleString()}
                </div>
              </div>
              <div className="p-3 rounded border">
                <div className="text-xs text-gray-500">Net Flow (USD)</div>
                <div
                  className={`text-lg font-semibold ${
                    Number(analytics?.totals?.net_flow_usd || 0) >= 0
                      ? "text-green-600"
                      : "text-red-600"
                  }`}
                >
                  $
                  {Number(
                    analytics?.totals?.net_flow_usd || 0
                  ).toLocaleString()}
                </div>
              </div>
              <div className="p-3 rounded border">
                <div className="text-xs text-gray-500">Total Transactions</div>
                <div className="text-lg font-semibold">
                  {Number(
                    analytics?.totals?.tx_count ||
                      analytics?.total_transactions ||
                      0
                  ).toLocaleString()}
                </div>
              </div>
            </div>

            {/* By operation */}
            <div>
              <div className="font-medium mb-2">By Operation</div>
              <div className="overflow-auto border rounded">
                <table className="min-w-full text-sm">
                  <thead className="bg-muted text-left">
                    <tr>
                      <th className="px-3 py-2">Operation</th>
                      <th className="px-3 py-2">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(analytics?.by_operation || {}).map(
                      ([op, count]) => (
                        <tr key={op} className="border-t">
                          <td className="px-3 py-2">{op}</td>
                          <td className="px-3 py-2">
                            {Number(count as any).toLocaleString()}
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* By currency (USD only) */}
            <div>
              <div className="font-medium text-foreground mb-2">Per-Currency Breakdown</div>
              <div className="overflow-auto border rounded">
                <table className="min-w-full text-sm">
                  <thead className="bg-muted text-left">
                    <tr>
                      <th className="px-3 py-2">Currency</th>
                      <th className="px-3 py-2">Tx Count</th>
                      <th className="px-3 py-2">Inflow (USD)</th>
                      <th className="px-3 py-2">Outflow (USD)</th>
                      <th className="px-3 py-2">Net Flow (USD)</th>
                      <th className="px-3 py-2">Total Volume (USD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(analytics?.by_currency || {}).map(
                      ([cur, stats]: any) => (
                        <tr key={cur} className="border-t border-border">
                          <td className="px-3 py-2">{cur}</td>
                          <td className="px-3 py-2">
                            {Number(
                              stats?.transaction_count || 0
                            ).toLocaleString()}
                          </td>
                          <td className="px-3 py-2">
                            ${Number(stats?.inflow_usd || 0).toLocaleString()}
                          </td>
                          <td className="px-3 py-2">
                            ${Number(stats?.outflow_usd || 0).toLocaleString()}
                          </td>
                          <td className="px-3 py-2">
                            ${Number(stats?.net_flow_usd || 0).toLocaleString()}
                          </td>
                          <td className="px-3 py-2">
                            $
                            {Number(
                              stats?.total_volume_usd || 0
                            ).toLocaleString()}
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Daily breakdown (USD only) */}
            <div>
              <div className="font-medium text-foreground mb-2">Daily Breakdown</div>
              <div className="overflow-auto border rounded">
                <table className="min-w-full text-sm">
                  <thead className="bg-muted text-left">
                    <tr>
                      <th className="px-3 py-2">Date</th>
                      <th className="px-3 py-2">Inflow (USD)</th>
                      <th className="px-3 py-2">Outflow (USD)</th>
                      <th className="px-3 py-2">Total (USD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(analytics?.daily?.total || {})
                      .sort()
                      .map((dateKey) => (
                        <tr key={dateKey} className="border-t border-border">
                          <td className="px-3 py-2 whitespace-nowrap">
                            {dateKey}
                          </td>
                          <td className="px-3 py-2">
                            $
                            {Number(
                              analytics?.daily?.inflow_usd?.[dateKey] || 0
                            ).toLocaleString()}
                          </td>
                          <td className="px-3 py-2">
                            $
                            {Number(
                              analytics?.daily?.outflow_usd?.[dateKey] || 0
                            ).toLocaleString()}
                          </td>
                          <td className="px-3 py-2">
                            $
                            {Number(
                              analytics?.daily?.total_usd?.[dateKey] || 0
                            ).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Removed old cards list in favor of table above */}
    </div>
  );
}
