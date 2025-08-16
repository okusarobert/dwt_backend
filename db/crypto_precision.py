"""
Crypto Precision Management System

This module handles the precision requirements for different cryptocurrencies.
The primary approach is to store amounts in the smallest unit (wei, satoshis, etc.)
to avoid precision issues.
"""

from decimal import Decimal, ROUND_DOWN, ROUND_UP
from typing import Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)

# Crypto precision configuration
# Format: {currency_code: (smallest_unit_name, decimal_places, display_decimals)}
CRYPTO_PRECISION_CONFIG = {
    # Bitcoin and Bitcoin-like
    "BTC": ("satoshis", 8, 8),      # 8 decimal places (satoshis)
    "LTC": ("litoshis", 8, 8),      # 8 decimal places
    "BCH": ("satoshis", 8, 8),      # 8 decimal places
    "GRS": ("satoshis", 8, 8),      # 8 decimal places
    
    # Ethereum and ERC-20 tokens
    "ETH": ("wei", 18, 18),         # 18 decimal places (wei)
    "BNB": ("wei", 18, 18),         # 18 decimal places
    "OPTIMISM": ("wei", 18, 18),    # 18 decimal places
    "POLYGON": ("wei", 18, 18),     # 18 decimal places
    "AVAX": ("nAVAX", 18, 18),     # 18 decimal places
    "WORLD": ("wei", 18, 18),       # 18 decimal places
    
    # Other cryptocurrencies
    "XRP": ("drops", 6, 6),         # 6 decimal places (drops)
    "XLM": ("stroops", 7, 7),       # 7 decimal places
    "TRX": ("sun", 6, 6),           # 6 decimal places
    "SOL": ("lamports", 9, 9),      # 9 decimal places (lamports)
    
    # Fiat currencies (for reference)
    "USD": ("cents", 2, 2),         # 2 decimal places
    "UGX": ("cents", 2, 2),         # 2 decimal places
    "EUR": ("cents", 2, 2),         # 2 decimal places
}

# Default precision for unknown currencies
DEFAULT_PRECISION = ("smallest_unit", 8, 8)

class CryptoPrecisionManager:
    """Manages precision for different cryptocurrencies"""
    
    @staticmethod
    def get_precision_config(currency_code: str) -> tuple:
        """Get precision configuration for a currency"""
        currency_code = currency_code.upper()
        return CRYPTO_PRECISION_CONFIG.get(currency_code, DEFAULT_PRECISION)
    
    @staticmethod
    def get_smallest_unit_name(currency_code: str) -> str:
        """Get the name of the smallest unit for a currency"""
        smallest_unit, _, _ = CryptoPrecisionManager.get_precision_config(currency_code)
        return smallest_unit
    
    @staticmethod
    def get_decimal_places(currency_code: str) -> int:
        """Get decimal places for a currency"""
        _, decimal_places, _ = CryptoPrecisionManager.get_precision_config(currency_code)
        return decimal_places
    
    @staticmethod
    def get_display_decimals(currency_code: str) -> int:
        """Get display decimal places for a currency"""
        _, _, display_decimals = CryptoPrecisionManager.get_precision_config(currency_code)
        return display_decimals
    
    @staticmethod
    def to_smallest_unit(amount: Union[float, Decimal, str], currency_code: str) -> int:
        """
        Convert amount to smallest unit (e.g., wei for ETH, satoshis for BTC)
        
        Args:
            amount: Amount in standard units
            currency_code: Currency code
            
        Returns:
            Amount in smallest unit as integer
        """
        try:
            if isinstance(amount, str):
                amount = Decimal(amount)
            elif isinstance(amount, float):
                amount = Decimal(str(amount))
            else:
                amount = Decimal(amount)
            
            currency_code = currency_code.upper()
            _, decimal_places, _ = CryptoPrecisionManager.get_precision_config(currency_code)
            
            # Convert to smallest unit
            multiplier = Decimal(10) ** decimal_places
            smallest_unit = amount * multiplier
            
            return int(smallest_unit)
            
        except Exception as e:
            logger.error(f"Error converting {amount} {currency_code} to smallest unit: {e}")
            raise
    
    @staticmethod
    def from_smallest_unit(amount: int, currency_code: str) -> Decimal:
        """
        Convert from smallest unit to standard units
        
        Args:
            amount: Amount in smallest unit
            currency_code: Currency code
            
        Returns:
            Amount in standard units
        """
        try:
            currency_code = currency_code.upper()
            _, decimal_places, _ = CryptoPrecisionManager.get_precision_config(currency_code)
            
            # Convert from smallest unit
            divisor = Decimal(10) ** decimal_places
            standard_amount = Decimal(amount) / divisor
            
            return standard_amount
            
        except Exception as e:
            logger.error(f"Error converting {amount} from smallest unit for {currency_code}: {e}")
            raise
    
    @staticmethod
    def validate_smallest_unit_amount(amount: int, currency_code: str) -> bool:
        """
        Validate if smallest unit amount is within acceptable range
        
        Args:
            amount: Amount in smallest unit
            currency_code: Currency code
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if amount < 0:
                return False
            
            # Check if amount exceeds maximum for the currency
            currency_code = currency_code.upper()
            _, decimal_places, _ = CryptoPrecisionManager.get_precision_config(currency_code)
            
            # Maximum value for smallest unit (e.g., 2^256 - 1 for ETH)
            max_smallest_unit = {
                "ETH": 2**256 - 1,
                "BTC": 2**256 - 1,
                "LTC": 2**256 - 1,
                "BCH": 2**256 - 1,
                "XRP": 2**64 - 1,
                "SOL": 2**64 - 1,
                "TRX": 2**64 - 1,
            }
            
            max_value = max_smallest_unit.get(currency_code, 2**64 - 1)
            return amount <= max_value
            
        except Exception as e:
            logger.error(f"Error validating smallest unit amount {amount} for {currency_code}: {e}")
            return False
    
    @staticmethod
    def format_for_display(amount: int, currency_code: str) -> str:
        """
        Format smallest unit amount for display
        
        Args:
            amount: Amount in smallest unit
            currency_code: Currency code
            
        Returns:
            Formatted string for display
        """
        try:
            standard_amount = CryptoPrecisionManager.from_smallest_unit(amount, currency_code)
            currency_code = currency_code.upper()
            _, _, display_decimals = CryptoPrecisionManager.get_precision_config(currency_code)
            
            # Format with appropriate decimal places
            formatted = f"{standard_amount:.{display_decimals}f}"
            
            # Remove trailing zeros after decimal
            if '.' in formatted:
                formatted = formatted.rstrip('0').rstrip('.')
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting amount {amount} for {currency_code}: {e}")
            return str(amount)
    
    @staticmethod
    def get_unit_names(currency_code: str) -> tuple:
        """Get unit names for a currency (standard, smallest)"""
        unit_names = {
            "BTC": ("BTC", "satoshis"),
            "ETH": ("ETH", "wei"),
            "LTC": ("LTC", "litoshis"),
            "BCH": ("BCH", "satoshis"),
            "XRP": ("XRP", "drops"),
            "XLM": ("XLM", "stroops"),
            "SOL": ("SOL", "lamports"),
            "TRX": ("TRX", "sun"),
            "BNB": ("BNB", "wei"),
            "AVAX": ("AVAX", "nAVAX"),
            "WORLD": ("WORLD", "wei"),
            "OPTIMISM": ("ETH", "wei"),
            "POLYGON": ("MATIC", "wei"),
        }
        
        currency_code = currency_code.upper()
        return unit_names.get(currency_code, (currency_code, "smallest unit"))

class CryptoAmountConverter:
    """Converts between different units for cryptocurrencies"""
    
    @staticmethod
    def standard_to_smallest(amount: Union[float, Decimal, str], currency_code: str) -> int:
        """Convert standard units to smallest unit"""
        return CryptoPrecisionManager.to_smallest_unit(amount, currency_code)
    
    @staticmethod
    def smallest_to_standard(amount: int, currency_code: str) -> Decimal:
        """Convert smallest unit to standard units"""
        return CryptoPrecisionManager.from_smallest_unit(amount, currency_code)
    
    @staticmethod
    def format_amount(amount: int, currency_code: str) -> str:
        """Format smallest unit amount for display"""
        return CryptoPrecisionManager.format_for_display(amount, currency_code)
    
    @staticmethod
    def validate_amount(amount: int, currency_code: str) -> bool:
        """Validate smallest unit amount"""
        return CryptoPrecisionManager.validate_smallest_unit_amount(amount, currency_code)

# Utility functions for easy access
def get_smallest_unit_name(currency_code: str) -> str:
    """Get the name of the smallest unit for a currency"""
    return CryptoPrecisionManager.get_smallest_unit_name(currency_code)

def to_smallest_unit(amount: Union[float, Decimal, str], currency_code: str) -> int:
    """Convert to smallest unit (e.g., satoshis, wei)"""
    return CryptoPrecisionManager.to_smallest_unit(amount, currency_code)

def from_smallest_unit(amount: int, currency_code: str) -> Decimal:
    """Convert from smallest unit to standard units"""
    return CryptoPrecisionManager.from_smallest_unit(amount, currency_code)

def format_smallest_unit_amount(amount: int, currency_code: str) -> str:
    """Format smallest unit amount for display"""
    return CryptoPrecisionManager.format_for_display(amount, currency_code)

def validate_smallest_unit_amount(amount: int, currency_code: str) -> bool:
    """Validate smallest unit amount"""
    return CryptoPrecisionManager.validate_smallest_unit_amount(amount, currency_code) 