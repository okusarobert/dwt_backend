# Crypto Price Utilities

This module provides utilities for fetching current crypto prices using the [Alchemy Prices API](https://www.alchemy.com/docs/reference/prices-api-quickstart).

## Features

- ✅ Fetch prices for single or multiple crypto symbols
- ✅ Automatic rate limiting (100ms between requests)
- ✅ Comprehensive error handling
- ✅ USD price extraction
- ✅ Support for up to 25 symbols per request
- ✅ Environment variable configuration
- ✅ Convenience functions for quick access

## Installation

1. **Install required dependencies:**
   ```bash
   pip install requests python-decouple
   ```

2. **Set your Alchemy API key:**
   ```bash
   export ALCHEMY_API_KEY="your-api-key-here"
   ```
   
   Or add it to your `.env` file:
   ```
   ALCHEMY_API_KEY=your-api-key-here
   ```

## Quick Start

### Basic Usage

```python
from shared.crypto.price_utils import get_crypto_price, get_crypto_prices

# Get single price
eth_price = get_crypto_price("ETH")
print(f"ETH: ${eth_price}")

# Get multiple prices
prices = get_crypto_prices(["BTC", "ETH", "SOL"])
for symbol, price in prices.items():
    print(f"{symbol}: ${price}")
```

### Advanced Usage

```python
from shared.crypto.price_utils import AlchemyPriceAPI

# Initialize API client
api = AlchemyPriceAPI("your-api-key")

# Get detailed price data
eth_data = api.get_price_by_symbol("ETH")
print(f"ETH Data: {eth_data}")

# Get prices for multiple symbols
symbols = ["BTC", "ETH", "USDT", "SOL"]
prices = api.get_prices_by_symbols(symbols)
print(f"Prices: {prices}")

# Extract USD prices only
usd_prices = api.get_multiple_usd_prices(symbols)
print(f"USD Prices: {usd_prices}")
```

## API Reference

### AlchemyPriceAPI Class

#### Constructor
```python
AlchemyPriceAPI(api_key: Optional[str] = None)
```
- `api_key`: Your Alchemy API key. If not provided, will try to get from `ALCHEMY_API_KEY` environment variable.

#### Methods

##### `get_prices_by_symbols(symbols: List[str]) -> Dict`
Fetch current prices for multiple tokens by symbol.

**Parameters:**
- `symbols`: List of token symbols (e.g., ["ETH", "BTC", "USDT"])

**Returns:**
- Dictionary containing price data for each symbol

**Example Response:**
```json
{
  "data": [
    {
      "symbol": "ETH",
      "prices": [
        {
          "currency": "USD",
          "value": "3000.00",
          "lastUpdatedAt": "2024-04-27T12:34:56Z"
        }
      ],
      "error": null
    }
  ]
}
```

##### `get_price_by_symbol(symbol: str) -> Optional[Dict]`
Fetch current price for a single token by symbol.

**Parameters:**
- `symbol`: Token symbol (e.g., "ETH")

**Returns:**
- Price data dictionary or None if failed

##### `get_usd_price(symbol: str) -> Optional[float]`
Get USD price for a token symbol.

**Parameters:**
- `symbol`: Token symbol (e.g., "ETH")

**Returns:**
- USD price as float or None if not available

##### `get_multiple_usd_prices(symbols: List[str]) -> Dict[str, Optional[float]]`
Get USD prices for multiple token symbols.

**Parameters:**
- `symbols`: List of token symbols

**Returns:**
- Dictionary mapping symbols to USD prices

### Convenience Functions

#### `get_crypto_price(symbol: str, api_key: Optional[str] = None) -> Optional[float]`
Quick function to get USD price for a single crypto symbol.

#### `get_crypto_prices(symbols: List[str], api_key: Optional[str] = None) -> Dict[str, Optional[float]]`
Quick function to get USD prices for multiple crypto symbols.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALCHEMY_API_KEY` | Your Alchemy API key | None (required) |

### Rate Limiting

The API client implements basic rate limiting with a 100ms delay between requests to respect API limits.

### Request Limits

- Maximum 25 symbols per request
- 30-second timeout for requests
- Automatic symbol validation and cleaning

## Error Handling

The utilities handle various error scenarios gracefully:

- **Network errors**: Logged and re-raised
- **Invalid API responses**: Logged and handled
- **Missing API keys**: Warning logged and error returned
- **Invalid symbols**: Filtered out automatically
- **Rate limiting**: Built-in delays between requests

## Examples

### Portfolio Price Checker

```python
from shared.crypto.price_utils import get_crypto_prices

def check_portfolio_prices(portfolio):
    """Check current prices for a portfolio of crypto assets."""
    symbols = list(portfolio.keys())
    prices = get_crypto_prices(symbols)
    
    total_value = 0
    for symbol, quantity in portfolio.items():
        price = prices.get(symbol)
        if price:
            value = quantity * price
            total_value += value
            print(f"{symbol}: {quantity} × ${price} = ${value:.2f}")
        else:
            print(f"{symbol}: Price not available")
    
    print(f"Total Portfolio Value: ${total_value:.2f}")
    return total_value

# Example usage
portfolio = {
    "BTC": 0.5,
    "ETH": 2.0,
    "SOL": 10.0
}
check_portfolio_prices(portfolio)
```

### Price Monitoring

```python
import time
from shared.crypto.price_utils import get_crypto_price

def monitor_price(symbol, target_price, check_interval=60):
    """Monitor a crypto price and alert when target is reached."""
    print(f"Monitoring {symbol} price (target: ${target_price})")
    
    while True:
        current_price = get_crypto_price(symbol)
        if current_price:
            print(f"{symbol}: ${current_price}")
            
            if current_price >= target_price:
                print(f"🎯 Target price reached! {symbol} is now ${current_price}")
                break
        else:
            print(f"Failed to get {symbol} price")
        
        time.sleep(check_interval)

# Example usage
# monitor_price("ETH", 3500)  # Alert when ETH reaches $3500
```

## Testing

Run the test script to verify functionality:

```bash
cd shared/crypto
python test_price_utils.py
```

## API Endpoints

This utility uses the following Alchemy Prices API endpoints:

- **Token Prices By Symbol**: `GET /prices/v1/{apiKey}/tokens/by-symbol`
  - Fetches current prices for multiple tokens using their symbols
  - Supports up to 25 symbols per request
  - Returns prices in multiple currencies (USD, EUR, etc.)

## Rate Limits

- **Free Tier**: 100 requests per day
- **Growth Tier**: 1,000 requests per day
- **Scale Tier**: 10,000 requests per day

The utility automatically implements rate limiting to stay within these limits.

## Support

For API-related issues, refer to the [Alchemy Prices API documentation](https://www.alchemy.com/docs/reference/prices-api-quickstart).

For utility-specific issues, check the logs and ensure your API key is properly configured.
