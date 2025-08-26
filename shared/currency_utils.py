"""
Currency Utilities Module

Provides functions to fetch and manage currency data from the admin database
instead of using hardcoded lists throughout the backend services.
"""

from typing import List, Dict, Optional
import logging
from db.connection import get_session
from db.currency import Currency, CurrencyNetwork

logger = logging.getLogger(__name__)

def get_enabled_currencies(currency_type: Optional[str] = None) -> List[str]:
    """
    Get list of enabled currency symbols from admin database.
    
    Args:
        currency_type: Optional filter - 'crypto' for cryptocurrencies only, 
                      'fiat' for fiat currencies only, None for all
    
    Returns:
        List of enabled currency symbols
    """
    session = get_session()
    try:
        query = session.query(Currency).filter(Currency.is_enabled == True)
        currencies = query.all()
        
        symbols = []
        for currency in currencies:
            # For now, assume all currencies in admin panel are crypto
            # This can be enhanced later with a currency_type field
            if currency_type is None or currency_type == 'crypto':
                symbols.append(currency.symbol)
        
        return symbols
    except Exception as e:
        logger.error(f"Error fetching enabled currencies: {e}")
        # Fallback to basic list if database query fails
        return ['BTC', 'ETH', 'SOL', 'BNB', 'USDT']
    finally:
        session.close()

def get_enabled_crypto_currencies() -> List[str]:
    """Get list of enabled cryptocurrency symbols."""
    return get_enabled_currencies('crypto')

def is_currency_enabled(symbol: str) -> bool:
    """
    Check if a specific currency is enabled in admin panel.
    
    Args:
        symbol: Currency symbol to check
        
    Returns:
        True if currency is enabled, False otherwise
    """
    session = get_session()
    try:
        currency = session.query(Currency).filter(
            Currency.symbol == symbol.upper(),
            Currency.is_enabled == True
        ).first()
        
        return currency is not None
    except Exception as e:
        logger.error(f"Error checking currency status for {symbol}: {e}")
        # Fallback - assume enabled for basic currencies
        return symbol.upper() in ['BTC', 'ETH', 'SOL', 'BNB', 'USDT']
    finally:
        session.close()

def get_currency_networks(symbol: str) -> List[Dict]:
    """
    Get enabled networks for a specific currency.
    
    Args:
        symbol: Currency symbol
        
    Returns:
        List of network configurations
    """
    session = get_session()
    try:
        currency = session.query(Currency).filter(
            Currency.symbol == symbol.upper(),
            Currency.is_enabled == True
        ).first()
        
        if not currency:
            return []
        
        networks = session.query(CurrencyNetwork).filter(
            CurrencyNetwork.currency_id == currency.id,
            CurrencyNetwork.is_enabled == True
        ).all()
        
        return [
            {
                'network_type': network.network_type,
                'network_name': network.network_name,
                'display_name': network.display_name,
                'explorer_url': network.explorer_url,
                'confirmation_blocks': network.confirmation_blocks,
                'is_testnet': network.is_testnet,
                'contract_address': network.contract_address
            }
            for network in networks
        ]
    except Exception as e:
        logger.error(f"Error fetching networks for {symbol}: {e}")
        return []
    finally:
        session.close()

# Cache for performance - refresh every 30 seconds for real-time updates
_currency_cache = {}
_cache_timestamp = 0
CACHE_DURATION = 30  # 30 seconds for real-time updates

def get_cached_enabled_currencies() -> List[str]:
    """Get enabled currencies with caching for better performance."""
    import time
    global _currency_cache, _cache_timestamp
    
    current_time = time.time()
    if current_time - _cache_timestamp > CACHE_DURATION:
        old_cache = _currency_cache.copy() if _currency_cache else []
        _currency_cache = get_enabled_currencies()
        _cache_timestamp = current_time
        
        # Log changes for debugging
        if old_cache != _currency_cache:
            logger.info(f"Currency cache updated: {old_cache} -> {_currency_cache}")
        
    return _currency_cache

def clear_currency_cache():
    """Clear the currency cache to force refresh."""
    global _cache_timestamp, _currency_cache
    _cache_timestamp = 0
    _currency_cache = {}
    logger.info("Currency cache cleared - will refresh on next access")

def force_refresh_currencies() -> List[str]:
    """Force immediate refresh of currency cache and return updated list."""
    clear_currency_cache()
    return get_cached_enabled_currencies()
