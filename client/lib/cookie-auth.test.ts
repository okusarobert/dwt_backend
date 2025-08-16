import { cookieAuth } from "./cookie-auth";

// Test cookie authentication functionality
export function testCookieAuth() {
  console.log("Testing Cookie Authentication:");

  // Test 1: Check if no token exists initially
  const initialAuth = cookieAuth.isAuthenticated();
  console.log(
    `1. Initial authentication state: ${
      initialAuth ? "✅ Authenticated" : "❌ Not authenticated"
    }`
  );

  // Test 2: Test setting a cookie
  const testToken =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjk5OTk5OTk5OTl9.test";
  cookieAuth.setAuthCookie(testToken);
  console.log("2. Set test auth cookie");

  // Test 3: Check if token is now valid
  const afterSetAuth = cookieAuth.isAuthenticated();
  console.log(
    `3. Authentication after setting cookie: ${
      afterSetAuth ? "✅ Authenticated" : "❌ Not authenticated"
    }`
  );

  // Test 4: Test getting decoded token
  const decodedToken = cookieAuth.getDecodedToken();
  console.log(`4. Decoded token:`, decodedToken);

  // Test 5: Test removing cookie
  cookieAuth.removeAuthCookie();
  console.log("5. Removed auth cookie");

  // Test 6: Check if token is invalid after removal
  const afterRemoveAuth = cookieAuth.isAuthenticated();
  console.log(
    `6. Authentication after removing cookie: ${
      afterRemoveAuth ? "✅ Authenticated" : "❌ Not authenticated"
    }`
  );

  console.log("\nCookie authentication test completed!");
}

// Run test if this file is executed directly
if (typeof window !== "undefined") {
  testCookieAuth();
}
