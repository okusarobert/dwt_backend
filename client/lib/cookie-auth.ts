import { jwtDecode } from "jwt-decode";

export interface DecodedToken {
  user_id: number;
  exp: number;
  iat: number;
}

class CookieAuth {
  /**
   * Check if user is authenticated by making a server request
   * This is the only reliable way to check HTTP-only cookies
   */
  async isAuthenticated(): Promise<boolean> {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/user-config`,
        {
          method: "GET",
          credentials: "include", // Include cookies
          headers: {
            Accept: "application/json",
          },
        }
      );

      // Consider 403 (email verification required) as authenticated
      // The user has a valid token but needs email verification
      return response.ok || response.status === 403;
    } catch (error) {
      console.error("Auth check failed:", error);
      return false;
    }
  }

  /**
   * Get decoded token from server response
   * This should only be called after confirming authentication
   */
  async getDecodedToken(): Promise<DecodedToken | null> {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/user-config`,
        {
          method: "GET",
          credentials: "include",
          headers: {
            Accept: "application/json",
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        // The server should return user data, not a token
        // But we can extract user_id from the response
        if (data.user && data.user.id) {
          return {
            user_id: data.user.id,
            exp: Date.now() + 30 * 24 * 60 * 60 * 1000, // 30 days from now
            iat: Date.now(),
          };
        }
      }
      return null;
    } catch (error) {
      console.error("Failed to get decoded token:", error);
      return null;
    }
  }

  /**
   * Remove auth cookie by calling logout endpoint
   */
  async removeAuthCookie(): Promise<void> {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (error) {
      console.error("Failed to remove auth cookie:", error);
    }
  }

  /**
   * Set auth cookie - this should only be called by the server
   * Client-side cookie setting is not needed for HTTP-only cookies
   */
  setAuthCookie(token: string): void {
    // This method is kept for compatibility but should not be used
    // HTTP-only cookies are set by the server
    console.warn(
      "setAuthCookie called on client - this should be handled by the server"
    );
  }

  /**
   * Get auth cookie - this is not possible with HTTP-only cookies
   */
  getAuthCookie(): string | null {
    // This method is kept for compatibility but always returns null
    // HTTP-only cookies are not accessible via JavaScript
    console.warn(
      "getAuthCookie called - HTTP-only cookies are not accessible via JavaScript"
    );
    return null;
  }
}

export const cookieAuth = new CookieAuth();
