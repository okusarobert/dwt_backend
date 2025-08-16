# Cookie-Based Authentication System

## Overview

This document describes the implementation of a secure HTTP-only cookie-based authentication system that replaces the previous localStorage token approach.

## Security Benefits

- **XSS Protection**: HTTP-only cookies cannot be accessed by JavaScript, preventing token theft via XSS attacks
- **CSRF Protection**: SameSite=Lax provides protection against cross-site request forgery
- **Automatic Token Management**: Browser handles cookie inclusion in requests automatically
- **Secure Transmission**: Cookies can be configured to only transmit over HTTPS in production

## Architecture

### Backend Components

1. **Auth Service** (`auth/app.py`): Handles authentication logic and sets HTTP-only cookies
2. **API Service** (`api/app.py`): Proxies requests to auth service and forwards cookies
3. **Token Middleware** (`db/utils.py`): Reads tokens from cookies for protected routes

### Frontend Components

1. **CookieAuth Utility** (`client/lib/cookie-auth.ts`): Client-side cookie management
2. **API Client** (`client/lib/api-client.ts`): HTTP client with cookie support
3. **AuthProvider** (`client/components/auth/auth-provider.tsx`): React context for auth state

## Environment Configuration

### Environment Variables

The system is now environment-aware and supports the following configuration:

#### CORS Origins
```bash
# Development (auto-detected)
FLASK_ENV=development
FLASK_DEBUG=1

# Custom CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,https://yourdomain.com

# Production origin (fallback)
PRODUCTION_ORIGIN=https://yourdomain.com
```

#### Cookie Domain
```bash
# Cookie domain for production
COOKIE_DOMAIN=.yourdomain.com
```

### Environment Detection

The system automatically detects the environment:

- **Development**: Uses localhost origins, `secure=False`, `domain=None`
- **Production**: Uses environment origins, `secure=True`, `domain=COOKIE_DOMAIN`
- **Docker**: Detects container hosts and sets appropriate flags

## Implementation Details

### Backend Changes

#### Auth Service (`auth/app.py`)

```python
def get_cors_origins():
    """Environment-aware CORS origins"""
    cors_origins = os.getenv('CORS_ORIGINS')
    if cors_origins:
        return [origin.strip() for origin in cors_origins.split(',')]
    
    is_development = os.getenv('FLASK_ENV') == 'development'
    if is_development:
        return ["http://localhost:3000", "http://localhost:3001", ...]
    else:
        return [os.getenv('PRODUCTION_ORIGIN', 'https://yourdomain.com')]

def create_auth_response(token: str, user_data: dict = None):
    """Creates response with HTTP-only cookie"""
    is_development = os.getenv('FLASK_ENV') == 'development'
    is_docker = request.host.startswith('auth:') or request.host.startswith('api:')
    
    cookie_domain = None
    if not is_development and not is_docker:
        cookie_domain = os.getenv('COOKIE_DOMAIN')
    
    response.set_cookie(
        'auth-token',
        token,
        max_age=30 * 24 * 60 * 60,  # 30 days
        path='/',
        domain=cookie_domain,
        httponly=True,
        secure=not (is_development or is_docker),
        samesite='Lax'
    )
```

#### API Service (`api/app.py`)

```python
@api.route('/login', methods=['POST'])
def login():
    # Forward request to auth service
    res = requests.post(f"{AUTH_SERVICE_URL}/login", json=data, headers=headers)
    
    # Forward cookies from auth service response
    response = jsonify(res.json())
    if 'Set-Cookie' in res.headers:
        response.headers['Set-Cookie'] = res.headers['Set-Cookie']
    
    return response, res.status_code
```

#### Token Middleware (`db/utils.py`)

```python
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First try to get token from HTTP-only cookie
        if request.cookies.get('auth-token'):
            token = request.cookies.get('auth-token')
        else:
            # Fallback to Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header:
                token = auth_header.split(" ")[1]
        
        # Validate token and attach user to request
        decoded = decode_token(token)
        user = session.query(User).filter(User.id == decoded["user_id"]).first()
        g.user = user
        return f(*args, **kwargs)
    return decorated_function
```

### Frontend Changes

#### CookieAuth Utility (`client/lib/cookie-auth.ts`)

```typescript
export class CookieAuth {
  getAuthCookie(): string | null {
    const cookies = document.cookie.split(";");
    const authCookie = cookies.find((cookie) =>
      cookie.trim().startsWith("auth-token=")
    );
    return authCookie ? authCookie.split("=")[1] : null;
  }

  isAuthenticated(): boolean {
    const token = this.getAuthCookie();
    return token ? this.isTokenValid() : false;
  }
}
```

#### API Client (`client/lib/api-client.ts`)

```typescript
class ApiClient {
  private authClient = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL,
    withCredentials: true,  // Include cookies in requests
  });

  async login(credentials: LoginRequest): Promise<AuthResponse> {
    const response = await this.authClient.post("/login", credentials);
    // Server sets HTTP-only cookie automatically
    return response.data;
  }

  async logout(): Promise<void> {
    await this.authClient.post("/logout");  // Clear server-side cookie
    cookieAuth.removeAuthCookie();  // Clear client-side reference
  }
}
```

#### AuthProvider (`client/components/auth/auth-provider.tsx`)

```typescript
const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);

  const login = async (email: string, password: string): Promise<boolean> => {
    const response = await apiClient.login({ email, password });
    if (response.user) {
      setUser(response.user);  // Direct user data from response
      return true;
    }
    return false;
  };

  const checkAuth = async () => {
    if (cookieAuth.isAuthenticated()) {
      try {
        const userConfig = await apiClient.getUserConfig();
        setUser(userConfig.user);
      } catch (error) {
        const userData = cookieAuth.getDecodedToken();
        setUser(userData);
      }
    }
  };
};
```

## Usage

### Development Setup

1. **Environment Variables**:
   ```bash
   FLASK_ENV=development
   FLASK_DEBUG=1
   ```

2. **CORS Origins**: Automatically configured for localhost development

3. **Cookie Settings**: 
   - `secure=False` (HTTP development)
   - `domain=None` (localhost)
   - `httponly=True`
   - `samesite=Lax`

### Production Setup

1. **Environment Variables**:
   ```bash
   CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
   COOKIE_DOMAIN=.yourdomain.com
   PRODUCTION_ORIGIN=https://yourdomain.com
   ```

2. **Cookie Settings**:
   - `secure=True` (HTTPS only)
   - `domain=.yourdomain.com` (subdomain support)
   - `httponly=True`
   - `samesite=Lax`

### Testing

```bash
# Test authentication
curl -X POST http://localhost:3030/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  -v

# Verify cookie is set
curl -X GET http://localhost:3030/api/v1/user-config \
  -H "Cookie: auth-token=your-token-here" \
  -v
```

## Migration Notes

### From localStorage to Cookies

1. **Token Storage**: No longer stored in localStorage
2. **Automatic Inclusion**: Cookies automatically included in requests
3. **Security**: HTTP-only cookies prevent XSS attacks
4. **Client Code**: Simplified - no manual token management

### Backward Compatibility

- Authorization header fallback still supported
- Existing token validation logic unchanged
- User data structure remains the same

## Security Considerations

1. **HTTPS Required**: In production, always use HTTPS
2. **Domain Configuration**: Set appropriate cookie domain for your domain
3. **CORS Origins**: Restrict to specific domains in production
4. **Token Expiration**: 30-day expiration with automatic renewal
5. **CSRF Protection**: SameSite=Lax provides basic CSRF protection

## Troubleshooting

### Common Issues

1. **Cookie Not Set**: Check CORS configuration and secure flag
2. **CORS Errors**: Verify origins match your frontend domain
3. **Authentication Fails**: Check token middleware and cookie name
4. **Domain Issues**: Ensure cookie domain matches your domain structure

### Debug Logging

The system includes comprehensive logging:
- Cookie setting process
- Environment detection
- CORS origin configuration
- Token validation

Check service logs for debugging information:
```bash
docker compose logs auth
docker compose logs api
```
