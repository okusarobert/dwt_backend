"""
Currency information utilities
"""
import json
import os
from typing import Dict, Any, Optional

# Load currency data from JSON file
_currencies_data = None

def _load_currencies():
    """Load currency data from currencies.json"""
    global _currencies_data
    if _currencies_data is None:
        current_dir = os.path.dirname(__file__)
        currencies_file = os.path.join(current_dir, 'currencies.json')
        with open(currencies_file, 'r') as f:
            _currencies_data = json.load(f)
    return _currencies_data

def get_currency_info(currency_code: str) -> Dict[str, Any]:
    """
    Get currency information for a given currency code
    
    Args:
        currency_code: The currency code (e.g., 'USD', 'BTC', 'UGX')
        
    Returns:
        Dictionary containing currency information including:
        - name: Currency name
        - symbol: Currency symbol (if available)
        - divisibility: Number of decimal places (default 2)
        - crypto: Whether it's a cryptocurrency (default False)
    """
    currencies = _load_currencies()
    
    # Default currency info
    default_info = {
        'name': currency_code,
        'symbol': currency_code,
        'divisibility': 2,
        'crypto': False
    }
    
    if currency_code not in currencies:
        return default_info
    
    currency_data = currencies[currency_code]
    
    # Handle simple string format (just name)
    if isinstance(currency_data, str):
        return {
            'name': currency_data,
            'symbol': currency_code,
            'divisibility': 2,
            'crypto': False
        }
    
    # Handle dictionary format
    if isinstance(currency_data, dict):
        result = default_info.copy()
        result.update(currency_data)
        
        # Ensure symbol defaults to currency code if not provided
        if 'symbol' not in result:
            result['symbol'] = currency_code
            
        return result
    
    return default_info

def get_currency_divisibility(currency_code: str) -> int:
    """Get the number of decimal places for a currency"""
    info = get_currency_info(currency_code)
    return info.get('divisibility', 2)

def get_currency_symbol(currency_code: str) -> str:
    """Get the symbol for a currency"""
    info = get_currency_info(currency_code)
    return info.get('symbol', currency_code)

def is_cryptocurrency(currency_code: str) -> bool:
    """Check if a currency is a cryptocurrency"""
    info = get_currency_info(currency_code)
    return info.get('crypto', False)

def get_smallest_unit_multiplier(currency_code: str) -> int:
    """Get the multiplier to convert to smallest units (e.g., cents, satoshis, wei)"""
    divisibility = get_currency_divisibility(currency_code)
    return 10 ** divisibility
