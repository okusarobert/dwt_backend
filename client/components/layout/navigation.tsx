"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  User,
  LogOut,
  Settings,
  Shield,
  ChevronDown,
  LayoutDashboard,
  Wallet as WalletIcon,
  ArrowLeftRight,
  LineChart,
  PieChart,
  Menu,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/components/auth/auth-provider";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import NotificationCenter from "@/components/notifications/notification-center";

export function Navigation() {
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const mobilePanelRef = useRef<HTMLDivElement | null>(null);
  const userMenuRef = useRef<HTMLDivElement | null>(null);

  const userInitials = (() => {
    const first = (user?.first_name || "").trim();
    const last = (user?.last_name || "").trim();
    if (first || last) return `${first.charAt(0)}${last.charAt(0)}`.toUpperCase() || "U";
    const email = (user?.email || "").trim();
    return email ? email.charAt(0).toUpperCase() : "U";
  })();

  const handleLogout = () => {
    logout();
    setIsUserMenuOpen(false);
  };

  // Close mobile menu on ESC and click outside
  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsMobileMenuOpen(false);
    };

    const onClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (mobilePanelRef.current && !mobilePanelRef.current.contains(target)) {
        setIsMobileMenuOpen(false);
      }
    };

    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [isMobileMenuOpen]);

  // Close desktop user menu on ESC and click outside
  useEffect(() => {
    if (!isUserMenuOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsUserMenuOpen(false);
    };
    const onClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (userMenuRef.current && !userMenuRef.current.contains(target)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [isUserMenuOpen]);

  return (
    <nav className="bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-lg">D</span>
            </div>
            <span className="text-xl font-bold text-foreground">
              DWT Exchange
            </span>
          </Link>

          {/* Navigation Tabs (desktop) */}
          <div className="hidden md:flex items-center">
            {(() => {
              const items = [
                { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
                { href: "/dashboard/wallet", label: "Wallet", Icon: WalletIcon },
                { href: "/trading", label: "Buy / Sell", Icon: LineChart },
                { href: "/convert", label: "Convert", Icon: ArrowLeftRight },
                { href: "/portfolio", label: "Portfolio", Icon: PieChart },
                ...(user?.role === "ADMIN" ? [{ href: "/admin", label: "Admin", Icon: Shield }] : []),
              ];

              // pick the longest matching href prefix as active value
              const active = items
                .filter((i) => pathname?.startsWith(i.href))
                .sort((a, b) => b.href.length - a.href.length)[0]?.href || "/dashboard";

              return (
                <Tabs
                  value={active}
                  onValueChange={(v) => router.push(v)}
                  className="w-auto"
                >
                  <TabsList className="bg-muted/60">
                    {items.map(({ href, label, Icon }) => (
                      <TabsTrigger
                        key={href}
                        value={href}
                        className="px-3 py-2 gap-2 data-[state=active]:bg-background data-[state=active]:shadow-sm text-muted-foreground data-[state=active]:text-foreground"
                      >
                        <Icon className="w-4 h-4" />
                        <span>{label}</span>
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>
              );
            })()}
          </div>

          {/* Right Side */}
          <div className="flex items-center space-x-2">
            {/* Notifications */}
            {isAuthenticated && <NotificationCenter />}
            {/* Theme toggle */}
            <ThemeToggle />
            {/* Hamburger (mobile) */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setIsMobileMenuOpen((v) => !v)}
              aria-label="Toggle menu"
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
            {/* User Menu */}
            {isAuthenticated ? (
              <div className="relative" ref={userMenuRef}>
                <Button
                  variant="ghost"
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="hidden md:flex items-center space-x-2"
                >
                  <Avatar className="h-6 w-6">
                    <AvatarImage src={(user as any)?.avatar_url || ""} alt={user?.first_name || "User"} />
                    <AvatarFallback className="text-xs">{userInitials}</AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium text-foreground">
                    {user?.first_name}
                  </span>
                  <ChevronDown className="w-4 h-4" />
                </Button>

                <AnimatePresence>
                  {isUserMenuOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      className="absolute right-0 mt-2 w-48 bg-popover text-popover-foreground rounded-lg shadow-lg border border-border py-1 z-50"
                    >
                      <div className="p-1">
                        <Link
                          href="/profile"
                          className="flex items-center px-3 py-1.5 text-sm rounded-md hover:bg-accent"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <User className="w-4 h-4 mr-3" />
                          Profile
                        </Link>
                        <Link
                          href="/settings"
                          className="flex items-center px-3 py-1.5 text-sm rounded-md hover:bg-accent"
                          onClick={() => setIsUserMenuOpen(false)}
                        >
                          <Settings className="w-4 h-4 mr-3" />
                          Settings
                        </Link>
                        {user?.role === "ADMIN" && (
                          <Link
                            href="/admin"
                            className="flex items-center px-3 py-1.5 text-sm rounded-md hover:bg-accent"
                            onClick={() => setIsUserMenuOpen(false)}
                          >
                            <Shield className="w-4 h-4 mr-3" />
                            Admin Panel
                          </Link>
                        )}
                      </div>
                      <div className="border-t border-border mx-1 my-1" />
                      <div className="p-1">
                        <button
                          onClick={handleLogout}
                          className="flex items-center w-full px-3 py-1.5 text-sm rounded-md text-destructive hover:bg-destructive/20 hover:text-destructive font-medium"
                        >
                          <LogOut className="w-4 h-4 mr-3" />
                          Sign Out
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ) : (
              <div className="hidden md:flex items-center space-x-3">
                <Link href="/auth/signin">
                  <Button variant="ghost">Sign In</Button>
                </Link>
                <Link href="/auth/signup">
                  <Button>Get Started</Button>
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Mobile Navigation Panel */}
        <div className="md:hidden pb-2 -mx-4 px-4">
          {(() => {
            const items = [
              { href: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
              { href: "/dashboard/wallet", label: "Wallet", Icon: WalletIcon },
              { href: "/trading", label: "Buy / Sell", Icon: LineChart },
              { href: "/convert", label: "Convert", Icon: ArrowLeftRight },
              { href: "/portfolio", label: "Portfolio", Icon: PieChart },
              ...(user?.role === "ADMIN" ? [{ href: "/admin", label: "Admin", Icon: Shield }] : []),
            ];

            const active = items
              .filter((i) => pathname?.startsWith(i.href))
              .sort((a, b) => b.href.length - a.href.length)[0]?.href || "/dashboard";

            return (
              <AnimatePresence>
                {isMobileMenuOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    ref={mobilePanelRef}
                    className="border border-border rounded-lg bg-background shadow-sm overflow-hidden"
                  >
                    <div className="divide-y divide-gray-100">
                      <div className="flex overflow-x-auto no-scrollbar">
                        <Tabs
                          value={active}
                          onValueChange={(v) => {
                            setIsMobileMenuOpen(false);
                            router.push(v);
                          }}
                          className="w-full"
                        >
                          <TabsList className="w-full flex justify-start gap-1 bg-muted/60">
                            {items.map(({ href, label, Icon }) => (
                              <TabsTrigger
                                key={href}
                                value={href}
                                className="px-3 py-2 gap-2 whitespace-nowrap data-[state=active]:bg-background data-[state=active]:shadow-sm text-muted-foreground data-[state=active]:text-foreground"
                              >
                                <Icon className="w-4 h-4" />
                                <span>{label}</span>
                              </TabsTrigger>
                            ))}
                          </TabsList>
                        </Tabs>
                      </div>
                      {/* Mobile user actions */}
                      <div className="p-2 bg-background">
                        {isAuthenticated ? (
                          <div className="grid grid-cols-2 gap-2">
                            <Link href="/profile" onClick={() => setIsMobileMenuOpen(false)}>
                              <Button
                                variant="ghost"
                                className="w-full justify-start gap-2 text-foreground hover:bg-accent focus-visible:ring-2 focus-visible:ring-primary/40"
                              >
                                <User className="w-4 h-4" /> Profile
                              </Button>
                            </Link>
                            <Link href="/settings" onClick={() => setIsMobileMenuOpen(false)}>
                              <Button
                                variant="ghost"
                                className="w-full justify-start gap-2 text-foreground hover:bg-accent focus-visible:ring-2 focus-visible:ring-primary/40"
                              >
                                <Settings className="w-4 h-4" /> Settings
                              </Button>
                            </Link>
                            {user?.role === "ADMIN" && (
                              <Link href="/admin" onClick={() => setIsMobileMenuOpen(false)}>
                                <Button
                                  variant="ghost"
                                  className="w-full justify-start gap-2 text-foreground hover:bg-accent focus-visible:ring-2 focus-visible:ring-primary/40"
                                >
                                  <Shield className="w-4 h-4" /> Admin Panel
                                </Button>
                              </Link>
                            )}
                            <Button
                              onClick={() => {
                                setIsMobileMenuOpen(false);
                                handleLogout();
                              }}
                              variant="ghost"
                              className="w-full justify-start gap-2 text-destructive-foreground hover:text-destructive-foreground hover:bg-destructive/20 focus-visible:ring-2 focus-visible:ring-destructive/40"
                            >
                              <LogOut className="w-4 h-4" /> Sign Out
                            </Button>
                          </div>
                        ) : (
                          <div className="grid grid-cols-2 gap-2">
                            <Link href="/auth/signin" onClick={() => setIsMobileMenuOpen(false)}>
                              <Button
                                variant="ghost"
                                className="w-full justify-start text-foreground hover:bg-accent focus-visible:ring-2 focus-visible:ring-primary/40"
                              >
                                Sign In
                              </Button>
                            </Link>
                            <Link href="/auth/signup" onClick={() => setIsMobileMenuOpen(false)}>
                              <Button className="w-full justify-start">Get Started</Button>
                            </Link>
                          </div>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            );
          })()}
        </div>
      </div>
    </nav>
  );
}
