"""
Unified Amount/Balance Models with Crypto and Fiat Support

This module provides base classes and utilities for handling amounts
consistently across all currency types using smallest units.
"""

from decimal import Decimal
from sqlalchemy import Column, String, Numeric, Integer, BigInteger
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
from typing import Optional
import sys
import os

# Add shared directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
from currency_precision import AmountConverter, CURRENCY_PRECISION

class UnifiedAmountMixin:
    """
    Mixin class for models that need to handle amounts in multiple currencies
    with proper precision for both crypto and fiat.
    """
    
    # Store all amounts as smallest units (NUMERIC(78,0))
    amount_smallest_unit = Column(Numeric(78, 0), nullable=False, default=0)
    currency = Column(String(10), nullable=False)
    
    @hybrid_property
    def amount(self) -> Decimal:
        """Get the display amount (converted from smallest units)"""
        if not self.amount_smallest_unit or not self.currency:
            return Decimal('0')
        return AmountConverter.from_smallest_units(int(self.amount_smallest_unit), self.currency)
    
    @amount.setter
    def amount(self, value: Decimal):
        """Set amount (automatically converts to smallest units for storage)"""
        if not self.currency:
            raise ValueError("Currency must be set before setting amount")
        self.amount_smallest_unit = AmountConverter.to_smallest_units(value, self.currency)
    
    @validates('currency')
    def validate_currency(self, key, currency):
        """Validate that currency is supported"""
        if currency and currency not in CURRENCY_PRECISION:
            raise ValueError(f"Unsupported currency: {currency}")
        return currency
    
    def format_amount(self) -> str:
        """Format amount for display with proper decimal places"""
        if not self.amount_smallest_unit or not self.currency:
            return "0"
        return AmountConverter.format_display_amount(int(self.amount_smallest_unit), self.currency)
    
    def add_amount(self, other_amount: Decimal) -> None:
        """Add amount (in display units) to current amount"""
        if not self.currency:
            raise ValueError("Currency must be set before adding amount")
        
        other_smallest = AmountConverter.to_smallest_units(other_amount, self.currency)
        self.amount_smallest_unit = (self.amount_smallest_unit or 0) + other_smallest
    
    def subtract_amount(self, other_amount: Decimal) -> None:
        """Subtract amount (in display units) from current amount"""
        if not self.currency:
            raise ValueError("Currency must be set before subtracting amount")
        
        other_smallest = AmountConverter.to_smallest_units(other_amount, self.currency)
        self.amount_smallest_unit = (self.amount_smallest_unit or 0) - other_smallest
    
    def is_sufficient_balance(self, required_amount: Decimal) -> bool:
        """Check if current amount is sufficient for required amount"""
        if not self.currency:
            return False
        
        required_smallest = AmountConverter.to_smallest_units(required_amount, self.currency)
        return (self.amount_smallest_unit or 0) >= required_smallest


class UnifiedBalanceMixin:
    """
    Mixin for models that need balance and locked amount fields
    with unified precision handling.
    """
    
    balance_smallest_unit = Column(Numeric(78, 0), nullable=False, default=0)
    locked_amount_smallest_unit = Column(Numeric(78, 0), nullable=False, default=0)
    currency = Column(String(10), nullable=False)
    
    @hybrid_property
    def balance(self) -> Decimal:
        """Get the display balance"""
        if not self.balance_smallest_unit or not self.currency:
            return Decimal('0')
        return AmountConverter.from_smallest_units(int(self.balance_smallest_unit), self.currency)
    
    @balance.setter
    def balance(self, value: Decimal):
        """Set balance (converts to smallest units)"""
        if not self.currency:
            raise ValueError("Currency must be set before setting balance")
        self.balance_smallest_unit = AmountConverter.to_smallest_units(value, self.currency)
    
    @hybrid_property
    def locked_amount(self) -> Decimal:
        """Get the display locked amount"""
        if not self.locked_amount_smallest_unit or not self.currency:
            return Decimal('0')
        return AmountConverter.from_smallest_units(int(self.locked_amount_smallest_unit), self.currency)
    
    @locked_amount.setter
    def locked_amount(self, value: Decimal):
        """Set locked amount (converts to smallest units)"""
        if not self.currency:
            raise ValueError("Currency must be set before setting locked amount")
        self.locked_amount_smallest_unit = AmountConverter.to_smallest_units(value, self.currency)
    
    @hybrid_property
    def available_balance(self) -> Decimal:
        """Get available balance (balance - locked_amount)"""
        return self.balance - self.locked_amount
    
    @property
    def available_balance_smallest_unit(self) -> int:
        """Get available balance in smallest units"""
        return int((self.balance_smallest_unit or 0) - (self.locked_amount_smallest_unit or 0))
    
    def lock_amount(self, amount: Decimal) -> bool:
        """Lock an amount if sufficient balance is available"""
        if not self.currency:
            raise ValueError("Currency must be set")
        
        amount_smallest = AmountConverter.to_smallest_units(amount, self.currency)
        
        if self.available_balance_smallest_unit >= amount_smallest:
            self.locked_amount_smallest_unit = (self.locked_amount_smallest_unit or 0) + amount_smallest
            return True
        return False
    
    def unlock_amount(self, amount: Decimal) -> bool:
        """Unlock a previously locked amount"""
        if not self.currency:
            raise ValueError("Currency must be set")
        
        amount_smallest = AmountConverter.to_smallest_units(amount, self.currency)
        
        if (self.locked_amount_smallest_unit or 0) >= amount_smallest:
            self.locked_amount_smallest_unit = (self.locked_amount_smallest_unit or 0) - amount_smallest
            return True
        return False
    
    def debit_balance(self, amount: Decimal, unlock: bool = False) -> bool:
        """Debit (decrease) balance, optionally unlocking the amount first"""
        if not self.currency:
            raise ValueError("Currency must be set")
        
        amount_smallest = AmountConverter.to_smallest_units(amount, self.currency)
        
        if unlock:
            # Unlock the amount first
            if not self.unlock_amount(amount):
                return False
        
        # Check if sufficient balance
        if (self.balance_smallest_unit or 0) >= amount_smallest:
            self.balance_smallest_unit = (self.balance_smallest_unit or 0) - amount_smallest
            return True
        return False
    
    def credit_balance(self, amount: Decimal) -> None:
        """Credit (increase) balance"""
        if not self.currency:
            raise ValueError("Currency must be set")
        
        amount_smallest = AmountConverter.to_smallest_units(amount, self.currency)
        self.balance_smallest_unit = (self.balance_smallest_unit or 0) + amount_smallest
    
    def format_balance(self) -> str:
        """Format balance for display"""
        if not self.balance_smallest_unit or not self.currency:
            return "0"
        return AmountConverter.format_display_amount(int(self.balance_smallest_unit), self.currency)
    
    def format_locked_amount(self) -> str:
        """Format locked amount for display"""
        if not self.locked_amount_smallest_unit or not self.currency:
            return "0"
        return AmountConverter.format_display_amount(int(self.locked_amount_smallest_unit), self.currency)
    
    @validates('currency')
    def validate_currency(self, key, currency):
        """Validate that currency is supported"""
        if currency and currency not in CURRENCY_PRECISION:
            raise ValueError(f"Unsupported currency: {currency}")
        return currency


# Example usage in existing models
"""
from db.unified_amounts import UnifiedBalanceMixin, UnifiedAmountMixin

class Account(Base, UnifiedBalanceMixin, Timestamped):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    account_type = Column(String(20))
    # currency, balance_smallest_unit, locked_amount_smallest_unit inherited from mixin
    
    # Usage:
    # account.balance = Decimal("123.45")  # Automatically converts to smallest units
    # print(account.format_balance())      # "123.45 USD" or "0.00123456 BTC"
    # account.lock_amount(Decimal("10.00")) # Lock 10 units
    # account.debit_balance(Decimal("5.00"), unlock=True) # Debit and unlock

class Transaction(Base, UnifiedAmountMixin, Timestamped):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_type = Column(String(20))
    # currency, amount_smallest_unit inherited from mixin
    
    # Usage:
    # tx.amount = Decimal("0.001")  # Automatically converts based on currency
    # print(tx.format_amount())     # Proper display format
"""
