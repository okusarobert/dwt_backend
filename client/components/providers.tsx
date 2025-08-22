"use client";

import { AuthProvider } from "./auth/auth-provider";
import { ThemeProvider } from "./theme/theme-provider";
import { QueryProvider } from "./providers/query-provider";

interface ProvidersProps {
  children: React.ReactNode;
}

export function Providers({ children }: ProvidersProps) {
  return (
    <QueryProvider>
      <ThemeProvider>
        <AuthProvider>
          {children}
        </AuthProvider>
      </ThemeProvider>
    </QueryProvider>
  );
}
