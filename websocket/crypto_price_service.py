import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import sys
import os

# Add shared directory to Python path
from shared.currency_utils import get_cached_enabled_currencies

logger = logging.getLogger('crypto_price_service')

class CryptoPriceService:
    def __init__(self, socketio):
        self.socketio = socketio
        self.base_url = "https://api.coingecko.com/api/v3"
        self.supported_coins = []  # Will be loaded dynamically
        self.price_cache: Dict[str, dict] = {}
        self.is_running = False
        
        # Load enabled currencies on initialization
        self.load_enabled_currencies()
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def fetch_crypto_prices(self) -> List[dict]:
        """Fetch current crypto prices from CoinGecko API with retry logic"""
        try:
            # Use the simple price endpoint for better performance
            coin_ids = ",".join(self.supported_coins)
            url = f"{self.base_url}/simple/price"
            params = {
                "ids": coin_ids,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
                "include_market_cap": "true"
            }
            
            # Add rate limiting - CoinGecko allows 50 calls/minute for free tier
            await asyncio.sleep(1.2)  # Ensure we don't exceed rate limits
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Successfully fetched prices for {len(data)} cryptocurrencies")
                        return self.format_price_data(data)
                    elif response.status == 429:
                        logger.warning("Rate limit exceeded, waiting before retry...")
                        await asyncio.sleep(60)  # Wait 1 minute on rate limit
                        raise Exception("Rate limit exceeded")
                    else:
                        logger.error(f"Failed to fetch prices: HTTP {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching crypto prices: {e}")
            raise  # Re-raise for retry logic
    
    def format_price_data(self, raw_data: dict) -> List[dict]:
        """Format raw API data into our standard format"""
        formatted_prices = []
        
        for coin_id, coin_data in raw_data.items():
            symbol = self.get_symbol_from_id(coin_id)
            name = self.get_name_from_id(coin_id)
            
            # Calculate 24h change
            price = coin_data.get("usd", 0)
            change_24h = coin_data.get("usd_24h_change", 0)
            volume_24h = coin_data.get("usd_24h_vol", 0)
            market_cap = coin_data.get("usd_market_cap", 0)
            
            # Calculate absolute change
            change_24h_abs = (price * change_24h) / 100 if change_24h else 0
            
            formatted_price = {
                "symbol": symbol,
                "name": name,
                "price": price,
                "change24h": change_24h_abs,
                "changePercent24h": change_24h,
                "volume24h": volume_24h,
                "marketCap": market_cap,
                "lastUpdated": datetime.now().isoformat()
            }
            
            formatted_prices.append(formatted_price)
            self.price_cache[symbol] = formatted_price
            
        return formatted_prices
    
    def get_symbol_from_id(self, coin_id: str) -> str:
        """Map CoinGecko IDs to symbols"""
        symbol_map = {
            "bitcoin": "BTC",
            "ethereum": "ETH", 
            "binancecoin": "BNB",
            "cardano": "ADA",
            "solana": "SOL",
            "polkadot": "DOT",
            "tether": "USDT",
            "usd-coin": "USDC",
            "ripple": "XRP",
            "matic-network": "MATIC",
            "tron": "TRX",
            "litecoin": "LTC"
        }
        return symbol_map.get(coin_id, coin_id.upper())
    
    def get_name_from_id(self, coin_id: str) -> str:
        """Map CoinGecko IDs to display names"""
        name_map = {
            "bitcoin": "Bitcoin",
            "ethereum": "Ethereum",
            "binancecoin": "Binance Coin", 
            "cardano": "Cardano",
            "solana": "Solana",
            "polkadot": "Polkadot",
            "tether": "Tether",
            "usd-coin": "USD Coin",
            "ripple": "Ripple",
            "matic-network": "Polygon",
            "tron": "TRON",
            "litecoin": "Litecoin"
        }
        return name_map.get(coin_id, coin_id.title())
    
    def load_enabled_currencies(self):
        """Load enabled currencies from database using currency utils"""
        try:
            logger.info("Loading enabled currencies from database...")
            enabled_symbols = get_cached_enabled_currencies()
            logger.info(f"Retrieved enabled symbols from database: {enabled_symbols}")
            
            self.supported_coins = [self.get_coingecko_id(symbol) for symbol in enabled_symbols]
            self.supported_coins = [coin for coin in self.supported_coins if coin]  # Filter out None values
            logger.info(f"Loaded {len(self.supported_coins)} enabled currencies from database: {self.supported_coins}")
            
            if not self.supported_coins:
                logger.warning("No enabled currencies found in database, using fallback")
                self.use_fallback_currencies()
        except Exception as e:
            logger.error(f"Error loading currencies from database: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.use_fallback_currencies()
    
    def use_fallback_currencies(self):
        """Use fallback currencies if database is unavailable (excluding BTC since it's disabled)"""
        self.supported_coins = [
            "ethereum", "solana", "tron", "ripple", "cardano", 
            "litecoin", "binancecoin", "matic-network"
        ]
        logger.warning(f"Using fallback currencies (BTC excluded): {self.supported_coins}")
    
    def get_coingecko_id(self, symbol: str) -> Optional[str]:
        """Map currency symbols to CoinGecko IDs"""
        symbol_to_id_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum", 
            "BNB": "binancecoin",
            "ADA": "cardano",
            "SOL": "solana",
            "DOT": "polkadot",
            "USDT": "tether",
            "USDC": "usd-coin",
            "XRP": "ripple",
            "MATIC": "matic-network",
            "TRX": "tron",
            "LTC": "litecoin"
        }
        return symbol_to_id_map.get(symbol.upper())
    
    async def broadcast_prices(self, prices: List[dict]):
        """Broadcast price updates to all connected clients"""
        try:
            # Emit to all clients subscribed to crypto-prices
            self.socketio.emit('crypto-prices', prices, namespace='/')
            logger.info(f"Broadcasted prices for {len(prices)} cryptocurrencies")
        except Exception as e:
            logger.error(f"Error broadcasting prices: {e}")
    
    async def start_price_streaming(self, interval: int = 10):
        """Start streaming crypto prices at specified interval"""
        self.is_running = True
        logger.info(f"Starting crypto price streaming with {interval}s interval")
        
        consecutive_failures = 0
        max_failures = 5
        currency_reload_counter = 0
        
        while self.is_running:
            # Reload currencies every 6 iterations (1 minute if interval=10s)
            if currency_reload_counter >= 6:
                logger.info("Reloading enabled currencies from database")
                self.load_enabled_currencies()
                currency_reload_counter = 0
            currency_reload_counter += 1
            try:
                prices = await self.fetch_crypto_prices()
                if prices:
                    await self.broadcast_prices(prices)
                    consecutive_failures = 0  # Reset failure counter on success
                    logger.debug(f"Successfully streamed {len(prices)} price updates")
                else:
                    logger.warning("No prices fetched, using cached data")
                    cached_prices = list(self.price_cache.values())
                    if cached_prices:
                        await self.broadcast_prices(cached_prices)
                
                # Wait for next update
                await asyncio.sleep(interval)
                
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Error in price streaming loop (attempt {consecutive_failures}/{max_failures}): {e}")
                
                if consecutive_failures >= max_failures:
                    logger.error("Too many consecutive failures, stopping price streaming")
                    self.is_running = False
                    break
                
                # Use cached data on failure
                try:
                    cached_prices = list(self.price_cache.values())
                    if cached_prices:
                        await self.broadcast_prices(cached_prices)
                        logger.info("Broadcasted cached prices due to API failure")
                except Exception as cache_error:
                    logger.error(f"Failed to broadcast cached prices: {cache_error}")
                
                # Wait before retry, with exponential backoff
                wait_time = min(interval * (2 ** consecutive_failures), 300)  # Max 5 minutes
                logger.info(f"Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
    
    def stop_price_streaming(self):
        """Stop the price streaming service"""
        self.is_running = False
        logger.info("Stopped crypto price streaming")
    
    def start_price_streaming_sync(self, interval: int = 10):
        """Synchronous wrapper for start_price_streaming"""
        import asyncio
        try:
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_price_streaming(interval))
        except Exception as e:
            logger.error(f"Error in sync price streaming: {e}")
        finally:
            loop.close()
    
    def get_cached_prices(self) -> List[dict]:
        """Get cached prices for initial load"""
        return list(self.price_cache.values())
