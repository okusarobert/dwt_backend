"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { apiClient, User } from "@/lib/api-client";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  register: (userData: any) => Promise<any>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already authenticated on mount
    const checkAuth = async () => {
      try {
        // Check authentication status with server
        const isAuth = await apiClient.isAuthenticated();

        if (isAuth) {
          // If authenticated, get fresh user data from server
          try {
            const userConfig = await apiClient.getUserConfig();
            if (userConfig) {
              setUser(userConfig);
            }
          } catch (error: any) {
            console.error("Failed to fetch user data:", error);
            // If 403 (email verification required), user is authenticated but needs verification
            if (error.response?.status === 403) {
              // Try to get user info from verification endpoint
              try {
                const verificationInfo = await apiClient.getVerificationInfo();
                if (verificationInfo) {
                  setUser({
                    id: 0, // Will be updated when verification completes
                    email: verificationInfo.email,
                    first_name: "",
                    last_name: "",
                    role: "user"
                  });
                }
              } catch (verifyError) {
                console.error("Failed to get verification info:", error);
                setUser(null);
              }
            } else {
              // Other errors mean not authenticated
              setUser(null);
            }
          }
        } else {
          // Not authenticated, clear user state
          setUser(null);
        }
      } catch (error) {
        console.error("Auth check failed:", error);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      const response = await apiClient.login({ email, password });

      // The response now contains user data directly
      if (response.user) {
        setUser(response.user);
        return true;
      }
      return false;
    } catch (error) {
      console.error("Login failed:", error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: any): Promise<any> => {
    // Don't set global loading state for registration
    // This prevents form state loss during the request
    // setIsLoading(true);

    const response = await apiClient.register(userData);

    // Backend now returns user data with verification requirements
    // Set user state immediately after successful registration
    if (response.user) {
      setUser(response.user);
    }
    
    // Return the response so the form can handle verification redirects
    return response;
  };

  const logout = async () => {
    try {
      setIsLoading(true);

      // Call the server logout endpoint
      const success = await apiClient.logout();

      if (success) {
        // Clear local user state
        setUser(null);
        console.log("Logout successful - user state cleared");
      } else {
        console.error("Logout failed on server");
        // Even if server logout fails, clear local state for security
        setUser(null);
      }
    } catch (error) {
      console.error("Logout failed:", error);
      // Clear local state even if server call fails
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
