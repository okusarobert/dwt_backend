"""
Forex Service for Real-time Currency Exchange Rates
Uses fawazahmed0/exchange-api with 15-minute caching
"""

import requests
import logging
import time
import threading
from typing import Dict, Optional
from datetime import datetime, timedelta
import os
import json

logger = logging.getLogger(__name__)

class ForexService:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 900  # 15 minutes cache (900 seconds)
        self.last_update = {}
        self.lock = threading.Lock()
        
        # Primary and fallback URLs for fawazahmed0/exchange-api
        self.primary_base_url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies"
        self.fallback_base_url = "https://latest.currency-api.pages.dev/v1/currencies"
        
        # Fallback rates in case all APIs fail
        self.fallback_rates = {
            'USD_UGX': 3750.0,
            'UGX_USD': 1/3750.0,
            'USD_EUR': 0.85,
            'EUR_USD': 1.18,
            'USD_GBP': 0.73,
            'GBP_USD': 1.37,
        }
        
    def get_exchange_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Get exchange rate with 15-minute caching
        Returns: exchange rate (1 from_currency = X to_currency)
        """
        from_currency = from_currency.lower()
        to_currency = to_currency.lower()
        
        # Same currency check
        if from_currency == to_currency:
            return 1.0
        
        with self.lock:
            # Check if we have fresh cached data for the base currency
            if self._is_cache_valid(from_currency):
                rates_data = self.cache[from_currency]['rates']
                if to_currency in rates_data:
                    rate = float(rates_data[to_currency])
                    logger.debug(f"Using cached rate {from_currency}/{to_currency}: {rate}")
                    return rate
            
            # Fetch fresh data
            rates_data = self._fetch_rates(from_currency)
            if rates_data and to_currency in rates_data:
                rate = float(rates_data[to_currency])
                logger.info(f"Fetched fresh rate {from_currency}/{to_currency}: {rate}")
                return rate
            
            # Try fallback rate
            fallback_key = f"{from_currency.upper()}_{to_currency.upper()}"
            if fallback_key in self.fallback_rates:
                rate = self.fallback_rates[fallback_key]
                logger.warning(f"Using fallback rate for {from_currency}/{to_currency}: {rate}")
                return rate
            
            # Try inverse rate
            inverse_key = f"{to_currency.upper()}_{from_currency.upper()}"
            if inverse_key in self.fallback_rates:
                rate = 1.0 / self.fallback_rates[inverse_key]
                logger.warning(f"Using inverse fallback rate for {from_currency}/{to_currency}: {rate}")
                return rate
                
        raise ValueError(f"Unable to get exchange rate for {from_currency}/{to_currency}")
    
    def _is_cache_valid(self, currency: str) -> bool:
        """Check if cached data for currency is still valid (within 15 minutes)"""
        if currency not in self.cache:
            return False
        
        cache_time = self.cache[currency]['timestamp']
        return (time.time() - cache_time) < self.cache_ttl
    
    def _fetch_rates(self, base_currency: str) -> Optional[Dict]:
        """Fetch exchange rates for base currency from fawazahmed0/exchange-api"""
        urls = [
            f"{self.primary_base_url}/{base_currency}.min.json",
            f"{self.fallback_base_url}/{base_currency}.min.json"
        ]
        
        for url in urls:
            try:
                logger.debug(f"Fetching rates from: {url}")
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract rates data
                if base_currency in data and isinstance(data[base_currency], dict):
                    rates_data = data[base_currency]
                    
                    # Cache the data
                    self.cache[base_currency] = {
                        'rates': rates_data,
                        'timestamp': time.time()
                    }
                    
                    logger.info(f"Successfully fetched {len(rates_data)} rates for {base_currency}")
                    return rates_data
                else:
                    logger.warning(f"Unexpected data format from {url}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for {url}: {e}")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error for {url}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error fetching from {url}: {e}")
        
        return None
    
    def get_multiple_rates(self, base_currency: str, target_currencies: list) -> Dict[str, float]:
        """Get multiple exchange rates at once with caching"""
        base_currency = base_currency.lower()
        rates = {}
        
        with self.lock:
            # Check if we have fresh cached data
            if self._is_cache_valid(base_currency):
                rates_data = self.cache[base_currency]['rates']
            else:
                rates_data = self._fetch_rates(base_currency)
                if not rates_data:
                    rates_data = {}
            
            for target in target_currencies:
                target_lower = target.lower()
                try:
                    if target_lower in rates_data:
                        rates[target.upper()] = float(rates_data[target_lower])
                    else:
                        # Try individual rate fetch as fallback
                        rate = self.get_exchange_rate(base_currency, target_lower)
                        rates[target.upper()] = rate
                except Exception as e:
                    logger.error(f"Failed to get rate for {base_currency}/{target}: {e}")
                    rates[target.upper()] = 0.0
        
        return rates
    
    def clear_cache(self):
        """Clear the exchange rate cache"""
        with self.lock:
            self.cache.clear()
            logger.info("Forex cache cleared")
    
    def get_cache_info(self) -> Dict:
        """Get information about cached data"""
        with self.lock:
            info = {}
            for currency, data in self.cache.items():
                cache_age = time.time() - data['timestamp']
                info[currency] = {
                    'cached_at': datetime.fromtimestamp(data['timestamp']).isoformat(),
                    'age_seconds': int(cache_age),
                    'is_valid': cache_age < self.cache_ttl,
                    'rates_count': len(data['rates'])
                }
            return info
    
    def refresh_cache(self, currencies: list = None):
        """Manually refresh cache for specified currencies or all cached currencies"""
        if currencies is None:
            currencies = list(self.cache.keys())
        
        with self.lock:
            for currency in currencies:
                try:
                    logger.info(f"Refreshing cache for {currency}")
                    self._fetch_rates(currency.lower())
                except Exception as e:
                    logger.error(f"Failed to refresh cache for {currency}: {e}")
    
    def start_background_refresh(self):
        """Start background thread to refresh cache every 15 minutes"""
        def refresh_worker():
            while True:
                try:
                    time.sleep(self.cache_ttl)  # Wait 15 minutes
                    if self.cache:
                        logger.info("Background refresh: updating cached exchange rates")
                        self.refresh_cache()
                except Exception as e:
                    logger.error(f"Background refresh error: {e}")
        
        refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
        refresh_thread.start()
        logger.info("Started background cache refresh thread (15-minute intervals)")

# Global instance
forex_service = ForexService()

# Start background refresh on import
forex_service.start_background_refresh()
