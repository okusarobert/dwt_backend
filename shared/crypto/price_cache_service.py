"""
Crypto Price Cache Service

This service fetches crypto prices from Alchemy API and caches them in Redis
to reduce API calls and improve response times.
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import redis
from decouple import config
from .price_utils import AlchemyPriceAPI

logger = logging.getLogger(__name__)

class PriceCacheService:
    """Service for caching crypto prices in Redis."""
    
    # Default symbols to cache
    DEFAULT_SYMBOLS = ["USDT", "TRX", "BTC", "LTC", "USDC", "ETH", "WLD", "POL", "OP", "SOL", "BNB", "AVAX"]
    
    # Cache configuration
    CACHE_TTL = 300  # 5 minutes in seconds
    CACHE_KEY_PREFIX = "crypto:price:"
    CACHE_LAST_UPDATE_KEY = "crypto:last_update"
    CACHE_SYMBOLS_KEY = "crypto:symbols"
    
    def __init__(self, redis_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the price cache service.
        
        Args:
            redis_url: Redis connection URL. If not provided, will try to get from environment.
            api_key: Alchemy API key. If not provided, will try to get from environment.
        """
        # Initialize Redis connection
        self.redis_url = redis_url or config('REDIS_URL', default=None)
        self.redis_client = self._init_redis()
        
        # Initialize Alchemy API client
        self.api_key = api_key or config('ALCHEMY_API_KEY', default=None)
        self.alchemy_api = AlchemyPriceAPI(self.api_key) if self.api_key else None
        
        # Initialize symbols to cache
        self.symbols = self._load_cached_symbols()
        if not self.symbols:
            self.symbols = self.DEFAULT_SYMBOLS
            self._save_symbols_to_cache()
    
    def _init_redis(self) -> redis.Redis:
        """Initialize Redis connection."""
        try:
            # Parse Redis URL or use individual environment variables
            if self.redis_url and self.redis_url != 'redis://localhost:6379':
                # Use URL-based connection
                redis_client = redis.from_url(self.redis_url, decode_responses=True)
            else:
                # Use individual environment variables for more control
                redis_host = os.environ.get('REDIS_HOST', 'localhost')
                redis_port = int(os.environ.get('REDIS_PORT', 6379))
                redis_username = os.environ.get('REDIS_USERNAME', None)
                redis_password = os.environ.get('REDIS_PASSWORD', None)
                redis_db = int(os.environ.get('REDIS_DB', 0))

                redis_kwargs = {
                    "host": redis_host,
                    "port": redis_port,
                    "db": redis_db,
                    "decode_responses": True
                }
                if redis_username:
                    redis_kwargs["username"] = redis_username
                if redis_password:
                    redis_kwargs["password"] = redis_password

                redis_client = redis.Redis(**redis_kwargs)
            
            # Test connection
            redis_client.ping()
            logger.info(f"Successfully connected to Redis at {redis_client.connection_pool.connection_kwargs}")
            return redis_client
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _load_cached_symbols(self) -> List[str]:
        """Load cached symbols from Redis."""
        try:
            symbols_json = self.redis_client.get(self.CACHE_SYMBOLS_KEY)
            if symbols_json:
                return json.loads(symbols_json)
        except Exception as e:
            logger.warning(f"Failed to load cached symbols: {e}")
        return []
    
    def _save_symbols_to_cache(self):
        """Save symbols to Redis cache."""
        try:
            self.redis_client.setex(
                self.CACHE_SYMBOLS_KEY,
                self.CACHE_TTL * 2,  # Longer TTL for symbols
                json.dumps(self.symbols)
            )
        except Exception as e:
            logger.error(f"Failed to save symbols to cache: {e}")
    
    def _get_cache_key(self, symbol: str) -> str:
        """Get Redis cache key for a symbol."""
        return f"{self.CACHE_KEY_PREFIX}{symbol.upper()}"
    
    def _is_cache_fresh(self, symbol: str) -> bool:
        """Check if cached price is still fresh."""
        try:
            last_update = self.redis_client.get(self.CACHE_LAST_UPDATE_KEY)
            if not last_update:
                return False
            
            last_update_time = datetime.fromisoformat(last_update)
            return datetime.now() - last_update_time < timedelta(seconds=self.CACHE_TTL)
        except Exception as e:
            logger.warning(f"Failed to check cache freshness: {e}")
            return False
    
    def _is_symbol_cache_expired(self, symbol: str) -> bool:
        """Check if a specific symbol's cache is expired."""
        try:
            cache_key = self._get_cache_key(symbol)
            # Check if the key exists and has TTL
            ttl = self.redis_client.ttl(cache_key)
            return ttl <= 0  # TTL <= 0 means expired or doesn't exist
        except Exception as e:
            logger.warning(f"Failed to check cache expiry for {symbol}: {e}")
            return True  # Assume expired if we can't check
    
    def _update_cache_timestamp(self):
        """Update the last cache update timestamp."""
        try:
            self.redis_client.setex(
                self.CACHE_LAST_UPDATE_KEY,
                self.CACHE_TTL * 2,
                datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to update cache timestamp: {e}")
    
    def get_cached_price(self, symbol: str) -> Optional[float]:
        """
        Get cached price for a symbol.
        
        Args:
            symbol: Token symbol (e.g., "ETH")
            
        Returns:
            Cached price as float or None if not available
        """
        try:
            cache_key = self._get_cache_key(symbol.upper())
            cached_price = self.redis_client.get(cache_key)
            
            if cached_price:
                return float(cached_price)
            
        except Exception as e:
            logger.warning(f"Failed to get cached price for {symbol}: {e}")
        
        return None
    
    def get_cached_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, Optional[float]]:
        """
        Get cached prices for multiple symbols.
        
        Args:
            symbols: List of token symbols. If None, uses default symbols.
            
        Returns:
            Dictionary mapping symbols to cached prices
        """
        if symbols is None:
            symbols = self.symbols
        
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_cached_price(symbol)
        
        return prices
    
    def refresh_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, Optional[float]]:
        """
        Refresh prices from Alchemy API and update cache.
        
        Args:
            symbols: List of token symbols. If None, uses default symbols.
            
        Returns:
            Dictionary mapping symbols to updated prices
        """
        if not self.alchemy_api:
            logger.error("Alchemy API not configured")
            return {}
        
        if symbols is None:
            symbols = self.symbols
        
        logger.info(f"Refreshing prices for {len(symbols)} symbols")
        
        try:
            # Fetch prices from Alchemy
            response = self.alchemy_api.get_prices_by_symbols(symbols)
            prices = {}
            
            # Process response and update cache
            for item in response.get("data", []):
                symbol = item.get("symbol")
                if not symbol:
                    continue
                
                if item.get("error"):
                    error_msg = item['error']
                    logger.warning(f"Error fetching price for {symbol}: {error_msg}")
                    
                    # Handle rate limit errors specifically
                    if "429" in error_msg or "Too Many Requests" in error_msg:
                        logger.warning(f"Rate limit hit for {symbol}, will retry later")
                        # Don't cache rate limit errors, just return None
                        prices[symbol] = None
                        continue
                    
                    prices[symbol] = None
                    continue
                
                # Extract USD price
                usd_price = None
                for price in item.get("prices", []):
                    if price.get("currency", "").upper() == "USD":
                        try:
                            usd_price = float(price["value"])
                            break
                        except (ValueError, KeyError):
                            continue
                
                prices[symbol] = usd_price
                
                # Cache the price
                if usd_price is not None:
                    self._cache_price(symbol, usd_price)
            
            # Update cache timestamp
            self._update_cache_timestamp()
            
            successful_refreshes = sum(1 for price in prices.values() if price is not None)
            logger.info(f"Successfully refreshed prices for {successful_refreshes}/{len(symbols)} symbols")
            return prices
            
        except Exception as e:
            logger.error(f"Failed to refresh prices: {e}")
            # Return empty dict on error, but don't crash the service
            return {}
    
    def _cache_price(self, symbol: str, price: float):
        """Cache a price in Redis."""
        try:
            cache_key = self._get_cache_key(symbol)
            self.redis_client.setex(cache_key, self.CACHE_TTL, str(price))
        except Exception as e:
            logger.error(f"Failed to cache price for {symbol}: {e}")
    
    def get_all_prices(self, force_refresh: bool = False) -> Dict[str, Optional[float]]:
        """
        Get all prices, refreshing cache if necessary.
        
        Args:
            force_refresh: Force refresh from API regardless of cache freshness
            
        Returns:
            Dictionary mapping symbols to prices
        """
        # Always try to get from cache first
        cached_prices = self.get_cached_prices()
        logger.debug(f"Retrieved {len([p for p in cached_prices.values() if p is not None])} prices from cache")
        
        # If force refresh is requested, fetch from API
        if force_refresh:
            logger.info("Force refresh requested, fetching new prices from API")
            api_prices = self.refresh_prices()
            # Merge API prices with cached prices (API prices take precedence)
            for symbol, price in api_prices.items():
                if price is not None:
                    cached_prices[symbol] = price
            return cached_prices
        
        # Check if we need to refresh any missing prices
        missing_symbols = [symbol for symbol, price in cached_prices.items() if price is None]
        
        if missing_symbols:
            logger.info(f"Found {len(missing_symbols)} missing prices, fetching from API")
            api_prices = self.refresh_prices(missing_symbols)
            # Update cache with new prices
            for symbol, price in api_prices.items():
                if price is not None:
                    cached_prices[symbol] = price
        
        return cached_prices
    
    def get_price_with_fallback(self, symbol: str, force_refresh: bool = False) -> Optional[float]:
        """
        Get price for a symbol with fallback to cache.
        
        Args:
            symbol: Token symbol
            force_refresh: Force refresh from API
            
        Returns:
            Price as float or None if not available
        """
        # Always try to get from cache first
        cached_price = self.get_cached_price(symbol)
        if cached_price is not None and not force_refresh:
            logger.debug(f"Using cached price for {symbol}: {cached_price}")
            return cached_price
        
        # If force refresh or no cached price, fetch from API
        if force_refresh or cached_price is None:
            logger.info(f"Fetching price for {symbol} from API")
            api_prices = self.refresh_prices([symbol])
            if symbol in api_prices and api_prices[symbol] is not None:
                return api_prices[symbol]
        
        return None
    
    def add_symbol(self, symbol: str) -> bool:
        """
        Add a new symbol to the cache service.
        
        Args:
            symbol: Token symbol to add
            
        Returns:
            True if added successfully, False otherwise
        """
        symbol = symbol.upper().strip()
        if symbol not in self.symbols:
            self.symbols.append(symbol)
            self._save_symbols_to_cache()
            
            # Fetch initial price for the new symbol
            try:
                self.refresh_prices([symbol])
                logger.info(f"Added symbol {symbol} to cache service")
                return True
            except Exception as e:
                logger.error(f"Failed to fetch initial price for {symbol}: {e}")
                return False
        
        return True
    
    def remove_symbol(self, symbol: str) -> bool:
        """
        Remove a symbol from the cache service.
        
        Args:
            symbol: Token symbol to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        symbol = symbol.upper().strip()
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            self._save_symbols_to_cache()
            
            # Remove from cache
            try:
                cache_key = self._get_cache_key(symbol)
                self.redis_client.delete(cache_key)
                logger.info(f"Removed symbol {symbol} from cache service")
                return True
            except Exception as e:
                logger.error(f"Failed to remove {symbol} from cache: {e}")
                return False
        
        return False
    
    def refresh_expired_prices(self) -> Dict[str, Optional[float]]:
        """
        Refresh only expired prices from the API.
        
        Returns:
            Dictionary mapping symbols to updated prices
        """
        expired_symbols = []
        for symbol in self.symbols:
            if self._is_symbol_cache_expired(symbol):
                expired_symbols.append(symbol)
        
        if not expired_symbols:
            logger.info("No expired prices found, all cache entries are fresh")
            return {}
        
        logger.info(f"Refreshing {len(expired_symbols)} expired prices: {expired_symbols}")
        return self.refresh_prices(expired_symbols)
    
    def is_rate_limited(self) -> bool:
        """
        Check if we're currently rate limited by checking recent error logs.
        
        Returns:
            True if rate limited, False otherwise
        """
        try:
            # Check if we have any recent rate limit errors in the cache
            # This is a simple heuristic - in production you might want more sophisticated tracking
            recent_errors = 0
            for symbol in self.symbols:
                cache_key = self._get_cache_key(symbol)
                if self.redis_client.exists(cache_key):
                    # Check if the cached value indicates a recent error
                    cached_value = self.redis_client.get(cache_key)
                    if cached_value and "error" in cached_value.lower():
                        recent_errors += 1
            
            # If more than half of symbols have errors, assume we're rate limited
            return recent_errors > len(self.symbols) // 2
            
        except Exception as e:
            logger.warning(f"Failed to check rate limit status: {e}")
            return False
    
    def get_cache_status(self) -> Dict:
        """Get cache service status information."""
        try:
            status = {
                "symbols": self.symbols,
                "cache_ttl": self.CACHE_TTL,
                "redis_connected": False,
                "alchemy_configured": self.alchemy_api is not None,
                "last_update": None,
                "cached_prices_count": 0,
                "expired_prices_count": 0,
                "symbol_expiry_info": {}
            }
            
            # Check Redis connection
            try:
                self.redis_client.ping()
                status["redis_connected"] = True
                
                # Get last update time
                last_update = self.redis_client.get(self.CACHE_LAST_UPDATE_KEY)
                if last_update:
                    status["last_update"] = last_update.decode() if isinstance(last_update, bytes) else last_update
                
                # Count cached prices and get expiry info
                cached_count = 0
                expired_count = 0
                for symbol in self.symbols:
                    cache_key = self._get_cache_key(symbol)
                    if self.redis_client.exists(cache_key):
                        cached_count += 1
                        # Get TTL for this symbol
                        ttl = self.redis_client.ttl(cache_key)
                        status["symbol_expiry_info"][symbol] = {
                            "cached": True,
                            "ttl_seconds": ttl,
                            "expires_in": f"{ttl}s" if ttl > 0 else "expired"
                        }
                    else:
                        expired_count += 1
                        status["symbol_expiry_info"][symbol] = {
                            "cached": False,
                            "ttl_seconds": 0,
                            "expires_in": "not cached"
                        }
                
                status["cached_prices_count"] = cached_count
                status["expired_prices_count"] = expired_count
                
            except Exception as e:
                logger.warning(f"Failed to get cache status: {e}")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get cache status: {e}")
            return {"error": str(e)}


# Global instance for easy access
_price_cache_service = None

def get_price_cache_service() -> PriceCacheService:
    """Get or create the global price cache service instance."""
    global _price_cache_service
    if _price_cache_service is None:
        _price_cache_service = PriceCacheService()
    return _price_cache_service


# Convenience functions
def get_cached_price(symbol: str) -> Optional[float]:
    """Quick function to get cached price for a symbol."""
    try:
        service = get_price_cache_service()
        return service.get_cached_price(symbol)
    except Exception as e:
        logger.error(f"Failed to get cached price for {symbol}: {e}")
        return None


def get_cached_prices(symbols: Optional[List[str]] = None) -> Dict[str, Optional[float]]:
    """Quick function to get cached prices for multiple symbols."""
    try:
        service = get_price_cache_service()
        return service.get_cached_prices(symbols)
    except Exception as e:
        logger.error(f"Failed to get cached prices: {e}")
        return {}


def refresh_cached_prices(symbols: Optional[List[str]] = None) -> Dict[str, Optional[float]]:
    """Quick function to refresh cached prices."""
    try:
        service = get_price_cache_service()
        return service.refresh_prices(symbols)
    except Exception as e:
        logger.error(f"Failed to refresh cached prices: {e}")
        return {}

def refresh_expired_prices() -> Dict[str, Optional[float]]:
    """Quick function to refresh only expired prices."""
    try:
        service = get_price_cache_service()
        return service.refresh_expired_prices()
    except Exception as e:
        logger.error(f"Failed to refresh expired prices: {e}")
        return {}
