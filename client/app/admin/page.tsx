"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function AdminHomePage() {
  return (
    <div className="space-y-6 p-6 bg-background text-foreground min-h-screen">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Admin Panel
        </h1>
        <p className="text-muted-foreground">
          Manage users, reserves and platform settings.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-card border rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <h2 className="text-lg font-medium text-card-foreground mb-2">
            Reserves
          </h2>
          <p className="text-sm text-muted-foreground mb-4">
            View status, top up, withdraw, and analytics for trading reserves.
          </p>
          <Link href="/admin/reserves">
            <Button>Open Reserves</Button>
          </Link>
        </div>

        <div className="bg-card border rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
          <h2 className="text-lg font-medium text-card-foreground mb-2">
            Users
          </h2>
          <p className="text-sm text-muted-foreground mb-4">
            List, filter and update users (role, blocked, deleted, default
            currency).
          </p>
          <Link href="/admin/users">
            <Button>Open Users</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
