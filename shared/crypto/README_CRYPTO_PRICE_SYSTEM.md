# Crypto Price Caching System

A comprehensive system for caching crypto prices using Redis and the Alchemy Prices API, with automatic background refresh and REST API endpoints.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client Apps   │───▶│   API Gateway    │───▶│  Wallet Service │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │  Price Cache     │    │  Alchemy API    │
                       │  Service         │◀───│  (External)     │
                       └──────────────────┘    └─────────────────┘
                                │
                                │
                                ▼
                       ┌──────────────────┐
                       │      Redis       │
                       │   (Cache DB)     │
                       └──────────────────┘
```

## 🚀 Features

- **Real-time Price Caching**: Cache crypto prices in Redis with configurable TTL
- **Automatic Background Refresh**: Background service keeps prices updated
- **REST API Endpoints**: Full CRUD operations for price management
- **Multi-Symbol Support**: Support for 12+ crypto symbols by default
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Error Handling**: Graceful fallbacks and comprehensive error handling
- **Admin Controls**: Admin-only endpoints for cache management

## 📦 Components

### 1. **Price Utilities** (`price_utils.py`)
- Direct Alchemy API client
- Rate limiting and error handling
- Support for single and batch price fetching

### 2. **Price Cache Service** (`price_cache_service.py`)
- Redis-based caching layer
- Automatic cache invalidation
- Symbol management (add/remove)

### 3. **Price Refresh Service** (`price_refresh_service.py`)
- Background service for automatic price updates
- Configurable refresh intervals
- Manual refresh triggers

### 4. **Wallet Service Integration**
- REST API endpoints for price access
- Authentication and authorization
- Admin-only management endpoints

### 5. **API Gateway Proxies**
- Proxy endpoints for external access
- Authentication forwarding
- Request/response handling

## 🔧 Installation & Setup

### 1. **Install Dependencies**
```bash
cd shared/crypto
pip install -r requirements.txt
```

### 2. **Environment Configuration**

#### **Option 1: Using Redis URL (Simple)**
```bash
# Required
export ALCHEMY_API_KEY="your-alchemy-api-key"
export REDIS_URL="redis://localhost:6379"

# Optional
export CRYPTO_PRICE_REFRESH_INTERVAL="300"  # 5 minutes
```

#### **Option 2: Using Individual Redis Parameters (Advanced)**
```bash
# Required
export ALCHEMY_API_KEY="your-alchemy-api-key"

# Redis Configuration
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"

# Optional Redis Authentication
export REDIS_USERNAME="your-username"  # if using Redis ACLs
export REDIS_PASSWORD="your-password"  # if using Redis auth

# Optional
export CRYPTO_PRICE_REFRESH_INTERVAL="300"  # 5 minutes
```

### 3. **Redis Setup**
```bash
# Install Redis (Ubuntu/Debian)
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test connection
redis-cli ping
```

## 📡 API Endpoints

### **Public Endpoints** (Require Authentication)

#### Get All Prices
```http
GET /api/v1/wallet/prices
Authorization: Bearer <token>

# Query Parameters:
# - symbols: List of specific symbols (optional)
# - refresh: Force refresh (true/false, default: false)

# Response:
{
  "success": true,
  "prices": {
    "BTC": 45000.00,
    "ETH": 3000.00,
    "SOL": 150.00
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Get Single Price
```http
GET /api/v1/wallet/prices/{symbol}
Authorization: Bearer <token>

# Response:
{
  "success": true,
  "symbol": "ETH",
  "price": 3000.00,
  "currency": "USD",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### **Admin Endpoints** (Require Admin Role)

#### Refresh Prices
```http
POST /api/v1/wallet/prices/refresh
Authorization: Bearer <admin-token>

# Query Parameters:
# - symbols: List of specific symbols (optional)

# Response:
{
  "success": true,
  "message": "Refreshed prices for 12 symbols",
  "prices": {...},
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Get Cache Status
```http
GET /api/v1/wallet/prices/status
Authorization: Bearer <admin-token>

# Response:
{
  "success": true,
  "status": {
    "symbols": ["BTC", "ETH", "SOL"],
    "cache_ttl": 300,
    "redis_connected": true,
    "alchemy_configured": true,
    "last_update": "2024-01-15T10:30:00Z",
    "cached_prices_count": 12
  }
}
```

#### Manage Symbols
```http
POST /api/v1/wallet/prices/symbols
Authorization: Bearer <admin-token>

# Body:
{
  "action": "add",  # or "remove"
  "symbols": ["ADA", "DOT"]
}

# Response:
{
  "success": true,
  "action": "add",
  "results": {
    "ADA": true,
    "DOT": true
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🎯 Default Supported Symbols

The system comes pre-configured with these 12 popular crypto symbols:

- **USDT** - Tether
- **TRX** - TRON
- **BTC** - Bitcoin
- **LTC** - Litecoin
- **USDC** - USD Coin
- **ETH** - Ethereum
- **WLD** - Worldcoin
- **POL** - Polygon
- **OP** - Optimism
- **SOL** - Solana
- **BNB** - Binance Coin
- **AVAX** - Avalanche

## ⚙️ Configuration

### **Environment Variables**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ALCHEMY_API_KEY` | Alchemy API key | None | ✅ |
| `REDIS_URL` | Redis connection URL | None | ❌ |
| `REDIS_HOST` | Redis host | `localhost` | ❌ |
| `REDIS_PORT` | Redis port | `6379` | ❌ |
| `REDIS_USERNAME` | Redis username | None | ❌ |
| `REDIS_PASSWORD` | Redis password | None | ❌ |
| `REDIS_DB` | Redis database number | `0` | ❌ |
| `CRYPTO_PRICE_REFRESH_INTERVAL` | Refresh interval (seconds) | `300` (5 min) | ❌ |

### **Cache Configuration**

| Setting | Value | Description |
|---------|-------|-------------|
| Cache TTL | 300 seconds | How long prices stay fresh |
| Max Symbols | 25 per request | Alchemy API limit |
| Rate Limit | 100ms | Delay between API calls |

## 🔄 Background Services

### **Price Refresh Service**

The system automatically starts a background service that:

1. **Runs every 5 minutes** (configurable)
2. **Fetches fresh prices** from Alchemy API
3. **Updates Redis cache** with new prices
4. **Logs refresh status** and any errors
5. **Handles failures gracefully** with retry logic

### **Starting/Stopping the Service**

```python
from shared.crypto.price_refresh_service import (
    start_price_refresh_service,
    stop_price_refresh_service
)

# Start the service
start_price_refresh_service()

# Stop the service
stop_price_refresh_service()
```

## 📊 Monitoring & Debugging

### **Cache Status Endpoint**

Use the status endpoint to monitor the system:

```bash
curl -H "Authorization: Bearer <admin-token>" \
     http://localhost:8000/api/v1/wallet/prices/status
```

### **Logs**

The system provides comprehensive logging:

```python
import logging
logging.getLogger('shared.crypto').setLevel(logging.DEBUG)
```

### **Redis Inspection**

```bash
# Connect to Redis
redis-cli

# View all cached prices
KEYS crypto:price:*

# Get specific price
GET crypto:price:ETH

# View cache metadata
GET crypto:last_update
GET crypto:symbols
```

## 🧪 Testing

### **Test the Price Utilities**

```bash
cd shared/crypto
python test_price_utils.py
```

### **Test the Cache Service**

```bash
cd shared/crypto
python -c "
from price_cache_service import get_price_cache_service
service = get_price_cache_service()
print('Cache status:', service.get_cache_status())
"
```

### **Test the Refresh Service**

```bash
cd shared/crypto
python price_refresh_service.py
```

## 🚨 Error Handling

### **Common Error Scenarios**

1. **Alchemy API Unavailable**
   - System falls back to cached prices
   - Logs error and retries on next cycle

2. **Redis Connection Issues**
   - System logs connection errors
   - Continues operation with in-memory fallback

3. **Invalid API Responses**
   - System validates responses
   - Logs warnings for malformed data

4. **Rate Limit Exceeded**
   - Built-in delays prevent rate limiting
   - Automatic retry with exponential backoff

### **Error Response Format**

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

## 🔒 Security Considerations

### **Authentication**
- All endpoints require valid JWT tokens
- Admin endpoints require admin role

### **Rate Limiting**
- Built-in delays prevent API abuse
- Configurable limits per endpoint

### **Data Validation**
- Input sanitization for all parameters
- Symbol validation and normalization

## 📈 Performance

### **Response Times**
- **Cached prices**: < 10ms
- **Fresh API calls**: 100-500ms
- **Background refresh**: Non-blocking

### **Scalability**
- **Redis caching**: Handles high concurrent access
- **Background refresh**: No impact on API performance
- **Configurable TTL**: Balance between freshness and performance

## 🔮 Future Enhancements

### **Planned Features**
- [ ] Historical price data
- [ ] Price alerts and notifications
- [ ] Multi-currency support (EUR, GBP, etc.)
- [ ] WebSocket real-time updates
- [ ] Advanced caching strategies
- [ ] Price analytics and charts

### **Integration Opportunities**
- [ ] Trading bot integration
- [ ] Portfolio tracking
- [ ] Price comparison tools
- [ ] Market analysis dashboards

## 🆘 Troubleshooting

### **Common Issues**

1. **"Alchemy API key not configured"**
   - Set `ALCHEMY_API_KEY` environment variable
   - Verify API key is valid

2. **"Failed to connect to Redis"**
   - Check Redis server is running
   - Verify Redis configuration (URL or individual parameters)
   - Check firewall/network settings
   - Verify Redis authentication if using ACLs
   - Test Redis connection manually: `redis-cli -h <host> -p <port> -a <password> ping`

3. **"No prices available"**
   - Check Alchemy API status
   - Verify API key permissions
   - Check network connectivity

4. **Slow response times**
   - Check Redis performance
   - Verify cache TTL settings
   - Monitor background refresh service

5. **Redis Authentication Issues**
   - Verify `REDIS_USERNAME` and `REDIS_PASSWORD` are correct
   - Check Redis ACL configuration
   - Test authentication manually with redis-cli

### **Debug Mode**

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Additional Resources

- [Alchemy Prices API Documentation](https://www.alchemy.com/docs/reference/prices-api-quickstart)
- [Redis Documentation](https://redis.io/documentation)
- [Flask Documentation](https://flask.palletsprojects.com/)

## 🤝 Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Submit pull requests

## 📄 License

This project is part of the DWT Backend system.
