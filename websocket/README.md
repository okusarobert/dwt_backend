# DWT Exchange WebSocket Service

Real-time crypto price streaming service for the DWT Exchange platform.

## 🚀 Features

- **Real-time crypto prices** from CoinGecko API
- **WebSocket streaming** with automatic reconnection
- **Price caching** for offline resilience
- **10 major cryptocurrencies** supported
- **10-second update intervals** for live data

## 🛠️ Setup

### Prerequisites

- Python 3.8+
- Required packages (see requirements.txt)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export APP_SECRET="your-secret-key-here"
   # Or create a .env file
   ```

3. **Test the crypto service:**
   ```bash
   python test_crypto_service.py
   ```

## 🚀 Running the Service

### Development Mode

```bash
python start_service.py
```

### Production Mode

```bash
gunicorn -k eventlet -w 1 --bind 0.0.0.0:5000 app:app
```

## 📡 WebSocket Events

### Client → Server

- `subscribe` - Subscribe to crypto price updates
  ```json
  {
    "channel": "crypto-prices"
  }
  ```

### Server → Client

- `crypto-prices` - Array of crypto price data
  ```json
  [
    {
      "symbol": "BTC",
      "name": "Bitcoin",
      "price": 43250.0,
      "change24h": 1056.25,
      "changePercent24h": 2.45,
      "volume24h": 28450000000,
      "marketCap": 847500000000,
      "lastUpdated": "2024-01-15T10:30:00Z"
    }
  ]
  ```

## 🔌 Supported Cryptocurrencies

| Symbol | Name | CoinGecko ID |
|--------|------|--------------|
| BTC    | Bitcoin | bitcoin |
| ETH    | Ethereum | ethereum |
| BNB    | Binance Coin | binancecoin |
| ADA    | Cardano | cardano |
| SOL    | Solana | solana |
| DOT    | Polkadot | polkadot |
| USDT   | Tether | tether |
| USDC   | USD Coin | usd-coin |
| XRP    | Ripple | ripple |
| MATIC  | Polygon | matic-network |

## 🧪 Testing

### Test Crypto Service

```bash
python test_crypto_service.py
```

### Test WebSocket Connection

1. Start the service
2. Visit `/test-websocket` in your browser
3. Check connection status and price data

## 🔧 Configuration

### Environment Variables

- `APP_SECRET` - Flask secret key (required)
- `REDIS_HOST` - Redis host (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `REDIS_USERNAME` - Redis username (optional)
- `REDIS_PASSWORD` - Redis password (optional)

### Update Intervals

- **Crypto prices**: 10 seconds
- **Connection heartbeat**: 10 seconds
- **Reconnection attempts**: 5 max

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Check what's using port 5000
   lsof -i :5000
   # Kill the process or change port
   ```

2. **Import errors:**
   ```bash
   # Make sure you're in the websocket directory
   cd websocket
   # Install dependencies
   pip install -r ../requirements.txt
   ```

3. **WebSocket connection failed:**
   - Check if service is running
   - Verify port configuration
   - Check firewall settings

### Logs

- **Service logs**: `websocket.log`
- **Console output**: Real-time logging
- **Log level**: INFO (configurable)

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:5000/health
```

### Connection Status

- Green indicator: Connected
- Red indicator: Disconnected
- Yellow indicator: Reconnecting

## 🔄 API Updates

The service automatically fetches prices from CoinGecko API every 10 seconds. If the API is unavailable, cached prices are used.

**Rate Limiting**: CoinGecko free tier allows 50 calls/minute. The service includes built-in rate limiting and retry logic.

## 📝 License

Part of the DWT Exchange platform.
