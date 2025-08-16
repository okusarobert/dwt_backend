import logging
from datetime import datetime
from typing import Dict, List
import time
import random

logger = logging.getLogger('crypto_price_service_simple')

class CryptoPriceServiceSimple:
    def __init__(self, socketio):
        self.socketio = socketio
        self.price_cache: Dict[str, dict] = {}
        self.is_running = False
        
        # Initialize with some sample data
        self.initialize_sample_data()
        
    def initialize_sample_data(self):
        """Initialize with sample crypto data"""
        sample_data = [
            {"symbol": "BTC", "name": "Bitcoin", "base_price": 43250.0},
            {"symbol": "ETH", "name": "Ethereum", "base_price": 2680.5},
            {"symbol": "BNB", "name": "Binance Coin", "base_price": 315.8},
            {"symbol": "ADA", "name": "Cardano", "base_price": 0.485},
            {"symbol": "SOL", "name": "Solana", "base_price": 98.75},
            {"symbol": "DOT", "name": "Polkadot", "base_price": 7.42},
            {"symbol": "USDT", "name": "Tether", "base_price": 1.0},
            {"symbol": "USDC", "name": "USD Coin", "base_price": 1.0},
            {"symbol": "XRP", "name": "Ripple", "base_price": 0.58},
            {"symbol": "MATIC", "name": "Polygon", "base_price": 0.85}
        ]
        
        for crypto in sample_data:
            # Generate realistic price variations
            price = crypto["base_price"]
            change_24h = random.uniform(-15, 15)  # -15% to +15%
            change_24h_abs = (price * change_24h) / 100
            volume_24h = price * random.uniform(1000000, 100000000)
            market_cap = price * random.uniform(10000000, 1000000000)
            
            self.price_cache[crypto["symbol"]] = {
                "symbol": crypto["symbol"],
                "name": crypto["name"],
                "price": price,
                "change24h": change_24h_abs,
                "changePercent24h": change_24h,
                "volume24h": volume_24h,
                "marketCap": market_cap,
                "lastUpdated": datetime.now().isoformat()
            }
    
    def update_prices(self):
        """Update prices with realistic variations"""
        for symbol, crypto in self.price_cache.items():
            # Add small random price movements
            price_change = random.uniform(-0.02, 0.02)  # -2% to +2%
            new_price = crypto["price"] * (1 + price_change)
            
            # Update 24h change
            change_24h = random.uniform(-15, 15)
            change_24h_abs = (new_price * change_24h) / 100
            
            # Update other metrics
            volume_24h = new_price * random.uniform(1000000, 100000000)
            market_cap = new_price * random.uniform(10000000, 1000000000)
            
            self.price_cache[symbol].update({
                "price": new_price,
                "change24h": change_24h_abs,
                "changePercent24h": change_24h,
                "volume24h": volume_24h,
                "marketCap": market_cap,
                "lastUpdated": datetime.now().isoformat()
            })
    
    def broadcast_prices(self, prices: List[dict]):
        """Broadcast price updates to all connected clients"""
        try:
            # Emit to all clients subscribed to crypto-prices
            self.socketio.emit('crypto-prices', prices, namespace='/')
            logger.info(f"Broadcasted prices for {len(prices)} cryptocurrencies")
        except Exception as e:
            logger.error(f"Error broadcasting prices: {e}")
    
    def start_price_streaming_sync(self, interval: int = 10):
        """Synchronous price streaming with sample data"""
        self.is_running = True
        logger.info(f"Starting simple crypto price streaming with {interval}s interval")
        
        while self.is_running:
            try:
                # Update prices
                self.update_prices()
                
                # Get all prices
                prices = list(self.price_cache.values())
                
                # Broadcast to clients
                self.broadcast_prices(prices)
                
                # Wait for next update
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in simple price streaming loop: {e}")
                time.sleep(interval)
    
    def stop_price_streaming(self):
        """Stop the price streaming service"""
        self.is_running = False
        logger.info("Stopped simple crypto price streaming")
    
    def get_cached_prices(self) -> List[dict]:
        """Get cached prices for initial load"""
        return list(self.price_cache.values())
