# Cookie-Based Authentication System

This document describes the implementation of HTTP-only cookie-based authentication for enhanced security.

## Overview

We've migrated from localStorage-based JWT token storage to HTTP-only cookies to improve security and protect against XSS attacks.

## Security Benefits

### 🛡️ **XSS Protection**
- **HTTP-only cookies** cannot be accessed by JavaScript, preventing XSS attacks from stealing authentication tokens
- **Secure flag** ensures cookies are only sent over HTTPS (in production)
- **SameSite attribute** provides CSRF protection

### 🔒 **Automatic Token Management**
- Tokens are automatically sent with every request
- No manual token handling required in frontend code
- Automatic token expiration handling

## Implementation Details

### Backend Changes

#### 1. **Flask CORS Configuration**
```python
CORS(app, 
     origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
```

#### 2. **Login Endpoint**
```python
@app.route('/login', methods=['POST'])
def login():
    # ... authentication logic ...
    return create_auth_response(encoded, user_data)
```

#### 3. **Cookie Response Helper**
```python
def create_auth_response(token: str, user_data: dict = None, status_code: int = 200):
    response = make_response(jsonify(response_data), status_code)
    response.set_cookie(
        'auth_token',
        token,
        max_age=30 * 24 * 60 * 60,  # 30 days
        path='/',
        httponly=True,  # HTTP-only cookie
        secure=not is_development,  # HTTPS only in production
        samesite='Lax'  # CSRF protection
    )
    return response
```

#### 4. **Updated Token Middleware**
```python
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First try cookie, then fallback to Authorization header
        token = request.cookies.get('auth_token') or extract_from_header()
        # ... validation logic ...
```

### Frontend Changes

#### 1. **Cookie Authentication Utility**
```typescript
// client/lib/cookie-auth.ts
export class CookieAuth {
  setAuthCookie(token: string, expiresInDays: number = 30): void
  getAuthCookie(): string | null
  removeAuthCookie(): void
  isTokenValid(): boolean
  getDecodedToken(): any
  isAuthenticated(): boolean
}
```

#### 2. **Updated API Client**
```typescript
// client/lib/api-client.ts
const authClient = axios.create({
  baseURL: API_ENDPOINTS.AUTH,
  withCredentials: true, // Important for cookies
});

// Automatic token inclusion in requests
private setupInterceptors(): void {
  const addAuthHeader = (config: any) => {
    const token = cookieAuth.getAuthCookie();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  };
}
```

#### 3. **Updated Auth Provider**
```typescript
// client/components/auth/auth-provider.tsx
const login = async (email: string, password: string): Promise<boolean> => {
  const response = await apiClient.login({ email, password });
  if (response.token) {
    const userData = cookieAuth.getDecodedToken();
    setUser(userData);
    return true;
  }
  return false;
};
```

## Usage

### Login
```typescript
const { login } = useAuth();
const success = await login(email, password);
if (success) {
  // User is now authenticated
  // Token is automatically stored in HTTP-only cookie
}
```

### Logout
```typescript
const { logout } = useAuth();
await logout(); // Clears both server and client cookies
```

### Check Authentication
```typescript
const { isAuthenticated } = useAuth();
if (isAuthenticated) {
  // User is authenticated
}
```

## Environment Configuration

### Development
- `secure=False` for HTTP cookies
- CORS allows localhost origins
- Debug logging enabled

### Production
- `secure=True` for HTTPS-only cookies
- CORS restricted to production domains
- Enhanced security headers

## Migration Notes

### Backward Compatibility
- The system still supports Authorization header tokens for backward compatibility
- Existing API endpoints continue to work
- Gradual migration possible

### Breaking Changes
- Frontend no longer stores tokens in localStorage
- All authentication requests now include credentials
- Logout now calls backend endpoint

## Security Considerations

### ✅ **Implemented**
- HTTP-only cookies prevent XSS token theft
- SameSite=Lax provides CSRF protection
- Secure flag in production
- Automatic token expiration

### 🔄 **Recommended**
- Implement refresh token rotation
- Add rate limiting on auth endpoints
- Monitor for suspicious authentication patterns
- Regular security audits

## Testing

### Manual Testing
1. Login and verify cookie is set
2. Check that token is not accessible via JavaScript
3. Verify logout clears cookies
4. Test token expiration handling

### Automated Testing
```typescript
// Run cookie auth tests
import { testCookieAuth } from './lib/cookie-auth.test';
testCookieAuth();
```

## Troubleshooting

### Common Issues

#### 1. **CORS Errors**
- Ensure `withCredentials: true` is set in axios
- Verify CORS configuration allows credentials
- Check origin whitelist

#### 2. **Cookie Not Set**
- Verify `httponly=True` in backend
- Check domain and path settings
- Ensure secure flag matches environment

#### 3. **Authentication Fails**
- Check token expiration
- Verify JWT secret configuration
- Review server logs for errors

### Debug Commands
```bash
# Check cookies in browser
document.cookie

# Test authentication state
cookieAuth.isAuthenticated()

# Verify token validity
cookieAuth.isTokenValid()
```

## Future Enhancements

1. **Refresh Token Implementation**
2. **Multi-factor Authentication**
3. **Session Management**
4. **Device Tracking**
5. **Audit Logging**
