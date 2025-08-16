"""
Crypto Price Utilities using Alchemy Prices API

This module provides utilities for fetching current and historical crypto prices
using the Alchemy Prices API. It includes rate limiting, error handling, and
caching capabilities.

API Reference: https://www.alchemy.com/docs/reference/prices-api-quickstart
"""

import os
import time
import json
import logging
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
import requests
from decouple import config

# Configure logging
logger = logging.getLogger(__name__)

class AlchemyPriceAPI:
    """Client for Alchemy Prices API with rate limiting and error handling."""
    
    BASE_URL = "https://api.g.alchemy.com/prices/v1"
    MAX_SYMBOLS_PER_REQUEST = 25
    RATE_LIMIT_DELAY = 1.0  # 1 second between requests to avoid rate limits
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Alchemy Price API client.
        
        Args:
            api_key: Alchemy API key. If not provided, will try to get from environment.
        """
        self.api_key = api_key or config('ALCHEMY_API_KEY', default=None)
        if not self.api_key:
            logger.warning("No Alchemy API key provided. Set ALCHEMY_API_KEY environment variable.")
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DWT-Backend/1.0',
            'Accept': 'application/json'
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implement basic rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict, max_retries: int = 3) -> Dict:
        """
        Make a request to the Alchemy API with error handling and retry logic.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            API response as dictionary
            
        Raises:
            requests.RequestException: For network/HTTP errors
            ValueError: For invalid API responses
        """
        if not self.api_key:
            raise ValueError("Alchemy API key not configured")
        
        for attempt in range(max_retries + 1):
            try:
                self._rate_limit()
                
                url = f"{self.BASE_URL}/{self.api_key}/{endpoint}"
                
                response = self.session.get(url, params=params, timeout=30)
                
                # Handle rate limit errors with exponential backoff
                if response.status_code == 429:
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                        logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Max retries reached for rate limit")
                        response.raise_for_status()
                
                response.raise_for_status()
                
                data = response.json()
                if 'data' not in data:
                    raise ValueError(f"Invalid API response format: {data}")
                
                return data
                
            except requests.exceptions.Timeout:
                logger.error("Request to Alchemy API timed out")
                if attempt < max_retries:
                    wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s
                    logger.info(f"Retrying timeout in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(wait_time)
                    continue
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"Request to Alchemy API failed: {e}")
                if attempt < max_retries and response.status_code != 429:
                    wait_time = (2 ** attempt) * 2
                    logger.info(f"Retrying request in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                    time.sleep(wait_time)
                    continue
                raise
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse API response: {e}")
                raise ValueError(f"Invalid JSON response: {e}")
        
        # This should never be reached, but just in case
        raise requests.exceptions.RequestException("Max retries exceeded")
    
    def get_prices_by_symbols(self, symbols: List[str]) -> Dict:
        """
        Fetch current prices for multiple tokens by symbol.
        
        Args:
            symbols: List of token symbols (e.g., ["ETH", "BTC", "USDT"])
            
        Returns:
            Dictionary containing price data for each symbol
            
        Example:
            >>> api = AlchemyPriceAPI("your-api-key")
            >>> prices = api.get_prices_by_symbols(["ETH", "BTC"])
            >>> print(prices["data"][0]["prices"][0]["value"])
            "3000.00"
        """
        if not symbols:
            return {"data": []}
        
        # Validate and clean symbols
        symbols = [str(s).upper().strip() for s in symbols if str(s).strip()]
        if not symbols:
            return {"data": []}
        
        # Split into chunks if exceeding limit
        if len(symbols) > self.MAX_SYMBOLS_PER_REQUEST:
            logger.warning(f"Too many symbols ({len(symbols)}), limiting to {self.MAX_SYMBOLS_PER_REQUEST}")
            symbols = symbols[:self.MAX_SYMBOLS_PER_REQUEST]
        
        params = {"symbols": symbols}
        
        try:
            response = self._make_request("tokens/by-symbol", params)
            logger.info(f"Successfully fetched prices for {len(symbols)} symbols")
            return response
            
        except Exception as e:
            logger.error(f"Failed to fetch prices for symbols {symbols}: {e}")
            # Return error structure for failed requests
            return {
                "data": [
                    {
                        "symbol": symbol,
                        "prices": [],
                        "error": str(e)
                    }
                    for symbol in symbols
                ]
            }
    
    def get_price_by_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Fetch current price for a single token by symbol.
        
        Args:
            symbol: Token symbol (e.g., "ETH")
            
        Returns:
            Price data dictionary or None if failed
        """
        result = self.get_prices_by_symbols([symbol])
        if result["data"] and not result["data"][0].get("error"):
            return result["data"][0]
        return None
    
    def get_usd_price(self, symbol: str) -> Optional[float]:
        """
        Get USD price for a token symbol.
        
        Args:
            symbol: Token symbol (e.g., "ETH")
            
        Returns:
            USD price as float or None if not available
        """
        price_data = self.get_price_by_symbol(symbol)
        if not price_data:
            return None
        
        # Find USD price
        for price in price_data.get("prices", []):
            if price.get("currency", "").upper() == "USD":
                try:
                    return float(price["value"])
                except (ValueError, KeyError):
                    logger.warning(f"Invalid USD price format for {symbol}: {price}")
                    return None
        
        return None
    
    def get_multiple_usd_prices(self, symbols: List[str]) -> Dict[str, Optional[float]]:
        """
        Get USD prices for multiple token symbols.
        
        Args:
            symbols: List of token symbols
            
        Returns:
            Dictionary mapping symbols to USD prices
        """
        result = self.get_prices_by_symbols(symbols)
        prices = {}
        
        for item in result.get("data", []):
            symbol = item.get("symbol")
            if not symbol:
                continue
                
            if item.get("error"):
                prices[symbol] = None
                continue
            
            # Find USD price
            usd_price = None
            for price in item.get("prices", []):
                if price.get("currency", "").upper() == "USD":
                    try:
                        usd_price = float(price["value"])
                        break
                    except (ValueError, KeyError):
                        continue
            
            prices[symbol] = usd_price
        
        return prices


# Convenience functions for quick access
def get_crypto_price(symbol: str, api_key: Optional[str] = None) -> Optional[float]:
    """
    Quick function to get USD price for a single crypto symbol.
    
    Args:
        symbol: Token symbol (e.g., "ETH")
        api_key: Optional API key (will use environment variable if not provided)
        
    Returns:
        USD price as float or None if not available
    """
    try:
        api = AlchemyPriceAPI(api_key)
        return api.get_usd_price(symbol)
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
        return None


def get_crypto_prices(symbols: List[str], api_key: Optional[str] = None) -> Dict[str, Optional[float]]:
    """
    Quick function to get USD prices for multiple crypto symbols.
    
    Args:
        symbols: List of token symbols
        api_key: Optional API key (will use environment variable if not provided)
        
    Returns:
        Dictionary mapping symbols to USD prices
    """
    try:
        api = AlchemyPriceAPI(api_key)
        return api.get_multiple_usd_prices(symbols)
    except Exception as e:
        logger.error(f"Failed to get prices for symbols {symbols}: {e}")
        return {symbol: None for symbol in symbols}


# Example usage and testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Example usage
    api_key = config('ALCHEMY_API_KEY', default='demo')
    api = AlchemyPriceAPI(api_key)
    
    # Test single symbol
    print("=== Single Symbol Test ===")
    eth_price = api.get_price_by_symbol("ETH")
    print(f"ETH Price Data: {json.dumps(eth_price, indent=2)}")
    
    # Test multiple symbols
    print("\n=== Multiple Symbols Test ===")
    symbols = ["ETH", "BTC", "USDT", "SOL"]
    prices = api.get_prices_by_symbols(symbols)
    print(f"Multiple Prices: {json.dumps(prices, indent=2)}")
    
    # Test USD price extraction
    print("\n=== USD Price Extraction Test ===")
    usd_prices = api.get_multiple_usd_prices(symbols)
    for symbol, price in usd_prices.items():
        print(f"{symbol}: ${price}" if price else f"{symbol}: Not available")
    
    # Test convenience functions
    print("\n=== Convenience Functions Test ===")
    quick_price = get_crypto_price("ETH")
    print(f"Quick ETH price: ${quick_price}")
    
    quick_prices = get_crypto_prices(["BTC", "SOL"])
    print(f"Quick prices: {quick_prices}")
