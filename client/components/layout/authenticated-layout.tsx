"use client";

import { ReactNode } from "react";
import { Navigation } from "./navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

interface AuthenticatedLayoutProps {
  children: ReactNode;
  title?: string;
  description?: string;
}

export function AuthenticatedLayout({
  children,
  title = "Dashboard",
  description,
}: AuthenticatedLayoutProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/auth/signin");
    }
  }, [isAuthenticated, isLoading, router]);

  // Check if user needs email verification
  useEffect(() => {
    const checkVerificationCookie = () => {
      const cookies = document.cookie.split(';');
      const verificationRequired = cookies.find(cookie => 
        cookie.trim().startsWith('email-verification-required=')
      );
      
      if (verificationRequired && verificationRequired.includes('true')) {
        router.push('/auth/verify-email');
      }
    };

    if (!isLoading && isAuthenticated) {
      checkVerificationCookie();
    }
  }, [isAuthenticated, isLoading, router]);

  // Show loading while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render anything if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main className="pt-1">{children}</main>
    </div>
  );
}
