"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "./auth-provider";

interface AuthMiddlewareProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  redirectTo?: string;
}

export function AuthMiddleware({
  children,
  requireAuth = false,
  redirectTo = "/auth/signin",
}: AuthMiddlewareProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [shouldRender, setShouldRender] = useState(false);
  const [hasRedirected, setHasRedirected] = useState(false);

  useEffect(() => {
    // Don't do anything while loading
    if (isLoading) {
      return;
    }

    // Prevent multiple redirects
    if (hasRedirected) {
      return;
    }

    // If authentication is required and user is not authenticated
    if (requireAuth && !isAuthenticated) {
      setHasRedirected(true);
      router.push(redirectTo);
      return;
    }

    // If user is authenticated and trying to access auth pages, redirect to dashboard
    if (
      isAuthenticated &&
      (pathname === "/auth/signin" ||
        pathname === "/auth/signup" ||
        pathname === "/auth/verify-email")
    ) {
      setHasRedirected(true);
      router.push("/dashboard");
      return;
    }

    // All conditions met, render the children
    setShouldRender(true);
  }, [
    isAuthenticated,
    isLoading,
    requireAuth,
    redirectTo,
    router,
    pathname,
    hasRedirected,
  ]);

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render anything if redirecting
  if (!shouldRender) {
    return null;
  }

  return <>{children}</>;
}

// Higher-order component for protected routes
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  redirectTo: string = "/auth/signin"
) {
  return function AuthenticatedComponent(props: P) {
    return (
      <AuthMiddleware requireAuth={true} redirectTo={redirectTo}>
        <Component {...props} />
      </AuthMiddleware>
    );
  };
}

// Higher-order component for public routes (redirects authenticated users)
export function withPublicAuth<P extends object>(
  Component: React.ComponentType<P>,
  redirectTo: string = "/dashboard"
) {
  return function PublicComponent(props: P) {
    return (
      <AuthMiddleware requireAuth={false} redirectTo={redirectTo}>
        <Component {...props} />
      </AuthMiddleware>
    );
  };
}
