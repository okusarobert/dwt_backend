"""
Currency Precision Configuration Module

Defines precision rules for all supported currencies to enable
unified amount/balance handling across crypto and fiat.
"""

from decimal import Decimal
from typing import Dict, NamedTuple
from enum import Enum

class CurrencyType(Enum):
    CRYPTO = "crypto"
    FIAT = "fiat"

class PrecisionConfig(NamedTuple):
    """Currency precision configuration"""
    currency_code: str
    currency_type: CurrencyType
    smallest_unit_name: str
    decimal_places: int
    display_decimals: int
    smallest_unit_per_base: int  # How many smallest units = 1 base unit

# Comprehensive currency precision configuration
CURRENCY_PRECISION = {
    # Cryptocurrencies
    'BTC': PrecisionConfig('BTC', CurrencyType.CRYPTO, 'satoshis', 8, 8, 100_000_000),
    'ETH': PrecisionConfig('ETH', CurrencyType.CRYPTO, 'wei', 18, 18, 10**18),
    'SOL': PrecisionConfig('SOL', CurrencyType.CRYPTO, 'lamports', 9, 9, 10**9),
    'TRX': PrecisionConfig('TRX', CurrencyType.CRYPTO, 'sun', 6, 6, 10**6),
    'BNB': PrecisionConfig('BNB', CurrencyType.CRYPTO, 'wei', 18, 18, 10**18),
    'AVAX': PrecisionConfig('AVAX', CurrencyType.CRYPTO, 'nAVAX', 18, 18, 10**18),
    'MATIC': PrecisionConfig('MATIC', CurrencyType.CRYPTO, 'wei', 18, 18, 10**18),
    'OP': PrecisionConfig('OP', CurrencyType.CRYPTO, 'wei', 18, 18, 10**18),
    'WORLD': PrecisionConfig('WORLD', CurrencyType.CRYPTO, 'wei', 18, 18, 10**18),
    'LTC': PrecisionConfig('LTC', CurrencyType.CRYPTO, 'litoshis', 8, 8, 100_000_000),
    'BCH': PrecisionConfig('BCH', CurrencyType.CRYPTO, 'satoshis', 8, 8, 100_000_000),
    
    # Fiat currencies
    'USD': PrecisionConfig('USD', CurrencyType.FIAT, 'cents', 2, 2, 100),
    'UGX': PrecisionConfig('UGX', CurrencyType.FIAT, 'cents', 2, 0, 100),  # UGX typically no decimals in display
    'EUR': PrecisionConfig('EUR', CurrencyType.FIAT, 'cents', 2, 2, 100),
    'GBP': PrecisionConfig('GBP', CurrencyType.FIAT, 'pence', 2, 2, 100),
    'JPY': PrecisionConfig('JPY', CurrencyType.FIAT, 'sen', 0, 0, 1),  # JPY has no fractional units
}

class AmountConverter:
    """Utility class for converting between display amounts and smallest units"""
    
    @staticmethod
    def to_smallest_units(amount: Decimal, currency: str) -> int:
        """Convert display amount to smallest units (for storage)"""
        if currency not in CURRENCY_PRECISION:
            raise ValueError(f"Unsupported currency: {currency}")
        
        config = CURRENCY_PRECISION[currency]
        smallest_units = int(amount * config.smallest_unit_per_base)
        return smallest_units
    
    @staticmethod
    def from_smallest_units(smallest_units: int, currency: str) -> Decimal:
        """Convert smallest units to display amount"""
        if currency not in CURRENCY_PRECISION:
            raise ValueError(f"Unsupported currency: {currency}")
        
        config = CURRENCY_PRECISION[currency]
        amount = Decimal(smallest_units) / Decimal(config.smallest_unit_per_base)
        # Use decimal_places for precision, not display_decimals
        return amount.quantize(Decimal('0.' + '0' * config.decimal_places))
    
    @staticmethod
    def format_display_amount(smallest_units: int, currency: str) -> str:
        """Format amount for display with proper decimal places"""
        amount = AmountConverter.from_smallest_units(smallest_units, currency)
        config = CURRENCY_PRECISION[currency]
        
        # Use decimal_places for precision, but display_decimals for formatting
        # If display_decimals is 0 but we have fractional parts, show them
        if config.display_decimals == 0 and amount % 1 != 0:
            # Show actual precision when there are fractional parts
            return f"{amount:.{config.decimal_places}f} {currency}".rstrip('0').rstrip('.')
        elif config.display_decimals == 0:
            return f"{amount:.0f} {currency}"
        else:
            return f"{amount:.{config.display_decimals}f} {currency}"
    
    @staticmethod
    def get_currency_config(currency: str) -> PrecisionConfig:
        """Get precision configuration for a currency"""
        if currency not in CURRENCY_PRECISION:
            raise ValueError(f"Unsupported currency: {currency}")
        return CURRENCY_PRECISION[currency]
    
    @staticmethod
    def validate_amount(amount: Decimal, currency: str) -> bool:
        """Validate that amount doesn't exceed precision limits"""
        try:
            smallest_units = AmountConverter.to_smallest_units(amount, currency)
            # Check if conversion back matches (no precision loss)
            converted_back = AmountConverter.from_smallest_units(smallest_units, currency)
            return abs(amount - converted_back) < Decimal('1e-' + str(CURRENCY_PRECISION[currency].decimal_places + 2))
        except (ValueError, OverflowError):
            return False

# Example usage and tests
if __name__ == "__main__":
    # Test crypto conversion
    btc_amount = Decimal("0.00123456")
    btc_smallest = AmountConverter.to_smallest_units(btc_amount, "BTC")
    print(f"BTC: {btc_amount} = {btc_smallest} satoshis")
    print(f"Back: {AmountConverter.from_smallest_units(btc_smallest, 'BTC')} BTC")
    print(f"Display: {AmountConverter.format_display_amount(btc_smallest, 'BTC')}")
    
    # Test fiat conversion
    usd_amount = Decimal("123.45")
    usd_smallest = AmountConverter.to_smallest_units(usd_amount, "USD")
    print(f"USD: {usd_amount} = {usd_smallest} cents")
    print(f"Back: {AmountConverter.from_smallest_units(usd_smallest, 'USD')} USD")
    print(f"Display: {AmountConverter.format_display_amount(usd_smallest, 'USD')}")
    
    # Test UGX (no decimal display)
    ugx_amount = Decimal("5000.00")
    ugx_smallest = AmountConverter.to_smallest_units(ugx_amount, "UGX")
    print(f"UGX: {ugx_amount} = {ugx_smallest} cents")
    print(f"Display: {AmountConverter.format_display_amount(ugx_smallest, 'UGX')}")
