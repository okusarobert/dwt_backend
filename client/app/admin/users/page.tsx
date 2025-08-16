"use client";

import { useEffect, useMemo, useState } from "react";
import { apiClient, User } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Card } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import toast from "react-hot-toast";

export default function AdminUsersPage() {
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<User[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [role, setRole] = useState<string | undefined>(undefined);
  const [blocked, setBlocked] = useState<string | undefined>(undefined);
  const [deleted, setDeleted] = useState<string | undefined>(undefined);
  const [savingId, setSavingId] = useState<number | null>(null);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / pageSize)), [total, pageSize]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const res = await apiClient.adminListUsers({
        q: q || undefined,
        role: role || undefined,
        blocked: blocked ? blocked === "true" : undefined,
        deleted: deleted ? deleted === "true" : undefined,
        page,
        page_size: pageSize,
      });
      if (res?.success) {
        setUsers(res.data || []);
        setTotal(res.pagination?.total || 0);
      } else {
        toast.error("Failed to load users");
      }
    } catch (e: any) {
      console.error(e);
      toast.error(e?.message || "Failed to load users");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize]);

  const onSearch = async () => {
    setPage(1);
    await loadUsers();
  };

  const resetFilters = async () => {
    setQ("");
    setRole(undefined);
    setBlocked(undefined);
    setDeleted(undefined);
    setPage(1);
    await loadUsers();
  };

  const updateUser = async (id: number, patch: Parameters<typeof apiClient.adminUpdateUser>[1]) => {
    try {
      setSavingId(id);
      const res = await apiClient.adminUpdateUser(id, patch);
      if (res?.success) {
        toast.success("User updated");
        await loadUsers();
      } else {
        toast.error("Update failed");
      }
    } catch (e: any) {
      console.error(e);
      toast.error(e?.message || "Update failed");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="min-h-screen p-4 space-y-4 bg-background text-foreground">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Admin • Users</h1>
      </div>

      <Card className="p-3 space-y-3 bg-card">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          <div className="col-span-2">
            <Input className="text-foreground placeholder:text-muted-foreground" placeholder="Search (name, email, phone)" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div>
            <Select value={role} onValueChange={(v) => setRole(v)}>
              <SelectTrigger className="text-foreground">
                <SelectValue placeholder="Role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="user">User</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Select value={blocked} onValueChange={(v) => setBlocked(v)}>
              <SelectTrigger className="text-foreground">
                <SelectValue placeholder="Blocked?" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="true">Blocked</SelectItem>
                <SelectItem value="false">Not Blocked</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <Select value={deleted} onValueChange={(v) => setDeleted(v)}>
              <SelectTrigger className="text-foreground">
                <SelectValue placeholder="Deleted?" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="true">Deleted</SelectItem>
                <SelectItem value="false">Active</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={onSearch}>Search</Button>
          <Button variant="secondary" onClick={resetFilters}>Reset</Button>
        </div>
      </Card>

      <Card className="p-0 border border-neutral-200 rounded-md">
        <div className="overflow-x-auto rounded-md border">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">ID</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Name</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Email</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Phone</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Role</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Blocked</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Deleted</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading ? (
                <tr>
                  <td className="px-3 py-6" colSpan={8}>
                    <div className="flex items-center gap-2"><LoadingSpinner /> Loading users...</div>
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td className="px-3 py-6 text-muted-foreground" colSpan={8}>No users</td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="hover:bg-muted/50">
                    <td className="px-3 py-2">{u.id}</td>
                    <td className="px-3 py-2">{u.first_name} {u.last_name}</td>
                    <td className="px-3 py-2">{u.email}</td>
                    <td className="px-3 py-2">{u.phone_number || "-"}</td>
                    <td className="px-3 py-2">
                      <Select value={String(u.role || '').toLowerCase()} onValueChange={(v) => updateUser(u.id, { role: v })}>
                        <SelectTrigger className="w-[140px] text-foreground"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="admin">admin</SelectItem>
                          <SelectItem value="user">user</SelectItem>
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-3 py-2">
                      <Button size="sm" variant={u.blocked ? "destructive" : "secondary"} disabled={savingId === u.id}
                        onClick={() => updateUser(u.id, { blocked: !Boolean((u as any).blocked) })}>
                        {savingId === u.id ? "Saving..." : (u as any).blocked ? "Unblock" : "Block"}
                      </Button>
                    </td>
                    <td className="px-3 py-2">
                      <Button size="sm" variant={(u as any).deleted ? "destructive" : "secondary"} disabled={savingId === u.id}
                        onClick={() => updateUser(u.id, { deleted: !Boolean((u as any).deleted) })}>
                        {savingId === u.id ? "Saving..." : (u as any).deleted ? "Restore" : "Delete"}
                      </Button>
                    </td>
                    <td className="px-3 py-2 flex gap-2">
                      <Button
                        size="sm"
                        variant={String((u as any).currency || '').toUpperCase() === 'UGX' ? 'default' : 'outline'}
                        disabled={savingId === u.id}
                        onClick={() => updateUser(u.id, { default_currency: 'UGX' })}
                      >
                        Set UGX
                      </Button>
                      <Button
                        size="sm"
                        variant={String((u as any).currency || '').toUpperCase() === 'USD' ? 'default' : 'outline'}
                        disabled={savingId === u.id}
                        onClick={() => updateUser(u.id, { default_currency: 'USD' })}
                      >
                        Set USD
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between p-3 border-t">
          <div className="text-sm text-muted-foreground">Total: {total.toLocaleString()}</div>
          <div className="flex items-center gap-2">
            <Button disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>Prev</Button>
            <div className="text-sm">Page {page} / {totalPages}</div>
            <Button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
            <Select value={String(pageSize)} onValueChange={(v) => { setPageSize(parseInt(v)); setPage(1); }}>
              <SelectTrigger className="w-[100px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="25">25</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>
    </div>
  );
}
