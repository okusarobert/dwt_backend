#!/usr/bin/env python3
"""
Crypto Price Refresh Service

This service runs in the background to periodically refresh crypto prices
from the Alchemy API and keep the Redis cache updated.
"""

import os
import time
import logging
import threading
from datetime import datetime, timedelta
from decouple import config
from .price_cache_service import get_price_cache_service

logger = logging.getLogger(__name__)

class PriceRefreshService:
    """Background service for refreshing crypto prices."""
    
    def __init__(self, refresh_interval: int = 300):  # 5 minutes default
        """
        Initialize the price refresh service.
        
        Args:
            refresh_interval: Refresh interval in seconds
        """
        self.refresh_interval = refresh_interval
        self.running = False
        self.thread = None
        self.price_cache_service = get_price_cache_service()
        
        # Configure refresh interval from environment
        env_interval = config('CRYPTO_PRICE_REFRESH_INTERVAL', default=None, cast=int)
        if env_interval:
            self.refresh_interval = env_interval
        
        logger.info(f"Price refresh service initialized with {self.refresh_interval}s interval")
    
    def start(self):
        """Start the background refresh service."""
        if self.running:
            logger.warning("Price refresh service is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.thread.start()
        logger.info("Price refresh service started")
    
    def stop(self):
        """Stop the background refresh service."""
        if not self.running:
            logger.warning("Price refresh service is not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Price refresh service stopped")
    
    def _refresh_loop(self):
        """Main refresh loop."""
        logger.info(f"Starting price refresh loop with {self.refresh_interval}s interval")
        
        while self.running:
            try:
                start_time = time.time()
                
                # Check if we're rate limited before making API calls
                if self.price_cache_service.is_rate_limited():
                    logger.warning("Rate limit detected, skipping price refresh this cycle")
                    # Sleep for a longer time when rate limited
                    time.sleep(min(300, self.refresh_interval * 2))  # 5 minutes or 2x interval
                    continue
                
                # Use cache-first approach - only refresh expired prices
                logger.info("Checking for expired crypto prices...")
                prices = self.price_cache_service.refresh_expired_prices()
                
                # Log refresh results
                if prices:
                    successful_refreshes = sum(1 for price in prices.values() if price is not None)
                    total_symbols = len(prices)
                    logger.info(f"Expired price refresh completed: {successful_refreshes}/{total_symbols} symbols updated")
                    
                    # Log individual prices for debugging
                    for symbol, price in prices.items():
                        if price is not None:
                            logger.debug(f"{symbol}: ${price}")
                        else:
                            logger.warning(f"{symbol}: Price not available")
                else:
                    logger.info("No expired prices found, all cache entries are fresh")
                
                # Calculate sleep time to maintain interval
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.refresh_interval - elapsed_time)
                
                if sleep_time > 0:
                    logger.debug(f"Sleeping for {sleep_time:.2f}s until next refresh")
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Refresh took {elapsed_time:.2f}s, longer than interval {self.refresh_interval}s")
                    
            except Exception as e:
                logger.error(f"Error in price refresh loop: {e}")
                # Sleep for a shorter time on error to retry sooner
                time.sleep(min(60, self.refresh_interval // 2))
    
    def refresh_now(self):
        """Trigger an immediate price refresh."""
        try:
            logger.info("Manual price refresh triggered")
            # Use cache-first approach - only refresh expired prices
            prices = self.price_cache_service.refresh_expired_prices()
            
            if prices:
                successful_refreshes = sum(1 for price in prices.values() if price is not None)
                total_symbols = len(prices)
                logger.info(f"Manual refresh completed: {successful_refreshes}/{total_symbols} expired symbols updated")
            else:
                logger.info("Manual refresh completed: No expired prices found")
            
            return prices
            
        except Exception as e:
            logger.error(f"Error in manual price refresh: {e}")
            return {}
    
    def force_refresh_all(self):
        """Force refresh all prices from API (bypasses cache)."""
        try:
            logger.info("Force refresh all prices triggered")
            prices = self.price_cache_service.refresh_prices()
            
            successful_refreshes = sum(1 for price in prices.values() if price is not None)
            total_symbols = len(prices)
            logger.info(f"Force refresh completed: {successful_refreshes}/{total_symbols} symbols updated")
            
            return prices
            
        except Exception as e:
            logger.error(f"Error in force refresh: {e}")
            return {}
    
    def get_status(self):
        """Get service status information."""
        return {
            "running": self.running,
            "refresh_interval": self.refresh_interval,
            "thread_alive": self.thread.is_alive() if self.thread else False,
            "last_refresh": datetime.now().isoformat() if self.running else None
        }


# Global service instance
_price_refresh_service = None

def get_price_refresh_service() -> PriceRefreshService:
    """Get or create the global price refresh service instance."""
    global _price_refresh_service
    if _price_refresh_service is None:
        _price_refresh_service = PriceRefreshService()
    return _price_refresh_service


def start_price_refresh_service():
    """Start the global price refresh service."""
    service = get_price_refresh_service()
    service.start()
    return service


def stop_price_refresh_service():
    """Stop the global price refresh service."""
    service = get_price_refresh_service()
    service.stop()
    return service


# Convenience functions for integration
def refresh_prices_now():
    """Quick function to refresh prices immediately."""
    try:
        service = get_price_refresh_service()
        return service.refresh_now()
    except Exception as e:
        logger.error(f"Failed to refresh prices: {e}")
        return {}

def force_refresh_all_prices():
    """Quick function to force refresh all prices from API."""
    try:
        service = get_price_refresh_service()
        return service.force_refresh_all()
    except Exception as e:
        logger.error(f"Failed to force refresh prices: {e}")
        return {}


def is_price_refresh_service_running():
    """Check if the price refresh service is running."""
    try:
        service = get_price_refresh_service()
        return service.running
    except Exception as e:
        logger.error(f"Failed to check service status: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create and start the service
        service = PriceRefreshService(refresh_interval=30)  # 30s for testing
        
        print("🚀 Starting Price Refresh Service...")
        service.start()
        
        # Let it run for a few cycles
        print("Service running... Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(10)
                status = service.get_status()
                print(f"Status: {status}")
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping service...")
            service.stop()
            print("Service stopped")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
