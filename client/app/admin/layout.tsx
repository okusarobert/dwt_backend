"use client";

import { ReactNode, useEffect, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AuthenticatedLayout } from "@/components/layout/authenticated-layout";
import { useAuth } from "@/components/auth/auth-provider";

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  const isAdmin = (user?.role || "").toUpperCase() === "ADMIN";

  useEffect(() => {
    if (!isLoading && isAuthenticated && !isAdmin) {
      router.replace("/dashboard");
    }
  }, [isAdmin, isAuthenticated, isLoading, router]);

  const pathname = usePathname();
  const nav = useMemo(() => ([
    { href: "/admin", label: "Overview" },
    { href: "/admin/users", label: "Users" },
    { href: "/admin/reserves", label: "Reserves" },
  ]), []);

  const isActive = (href: string) => {
    if (href === "/admin") return pathname === "/admin";
    return pathname?.startsWith(href);
  };

  return (
    <AuthenticatedLayout title="Admin" description="Admin Panel">
      {/* Block render for non-admins to avoid flash */}
      {isAuthenticated && isAdmin ? (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <nav className="mb-4 border-b border-neutral-200">
            <ul className="flex gap-2">
              {nav.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={[
                      "inline-block px-3 py-2 text-sm rounded-t-md",
                      isActive(item.href)
                        ? "bg-white border-x border-t border-neutral-200 text-neutral-900"
                        : "text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100",
                    ].join(" ")}
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          {children}
        </div>
      ) : null}
    </AuthenticatedLayout>
  );
}
