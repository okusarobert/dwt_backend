"use client";

import { ReactNode } from "react";
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout";
import { useAuth } from "@/components/auth/auth-provider";

export default function TradingLayout({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();

  return (
    <AuthenticatedLayout title="Trading" description="Trade cryptocurrencies">
      {isAuthenticated ? (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">{children}</div>
      ) : null}
    </AuthenticatedLayout>
  );
}
