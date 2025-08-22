"use client";

import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api-client";
import { formatUGX } from "@/lib/currency-formatter";
import { Loader2 } from "lucide-react";

interface PnLDisplayProps {
  theme: string;
}

interface PnLData {
  total_pnl_ugx: number;
  total_pnl_percentage: number;
  realized_pnl: {
    total_ugx: number;
    trades: any[];
  };
  unrealized_pnl: {
    total_ugx: number;
    positions: any[];
  };
  cost_basis_ugx: number;
}

export default function PnLDisplay({ theme }: PnLDisplayProps) {
  const [pnlData, setPnlData] = useState<PnLData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPnL = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch ledger-based PnL data
        const data = await apiClient.getUserPnL(undefined, 1); // 1 day period
        setPnlData(data);
      } catch (err) {
        console.error('Error fetching PnL data:', err);
        setError('Failed to load PnL data');
        // Fallback to show zero values
        setPnlData({
          total_pnl_ugx: 0,
          total_pnl_percentage: 0,
          realized_pnl: { total_ugx: 0, trades: [] },
          unrealized_pnl: { total_ugx: 0, positions: [] },
          cost_basis_ugx: 0
        });
      } finally {
        setLoading(false);
      }
    };

    fetchPnL();
  }, []);

  if (loading) {
    return (
      <div className={`text-sm transition-all duration-300 ${
        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-700'
      }`}>
        <div className="flex items-center gap-2">
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>Loading PnL...</span>
        </div>
      </div>
    );
  }

  if (error || !pnlData) {
    return (
      <div className={`text-sm transition-all duration-300 ${
        theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-700'
      }`}>
        Today's PnL: 
        <span className="text-gray-500 tabular-nums ml-1">--</span>
      </div>
    );
  }

  const isPositive = pnlData.total_pnl_ugx >= 0;
  const pnlColor = isPositive ? 'text-green-500' : 'text-red-500';
  const pnlSign = isPositive ? '+' : '';

  return (
    <div className={`text-sm transition-all duration-300 ${
      theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-700'
    }`}>
      Today's PnL: 
      <span className={`${pnlColor} tabular-nums ml-1`}>
        {pnlSign}{pnlData.total_pnl_percentage.toFixed(2)}%
      </span> 
      <span className={`tabular-nums ml-1 ${theme === 'dark' ? 'text-[#B7BDC6]' : 'text-gray-700'}`}>
        {pnlSign}{formatUGX(Math.abs(pnlData.total_pnl_ugx))}
      </span>
    </div>
  );
}
