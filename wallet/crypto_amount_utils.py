"""
Crypto Amount Utilities for Wallet Service

This module provides utilities for handling crypto amounts with proper precision
in the wallet service. All crypto amounts are stored in smallest units (wei, satoshis, etc.)
to avoid precision issues.
"""

from decimal import Decimal, ROUND_DOWN
from typing import Union, Optional
from db.crypto_precision import CryptoPrecisionManager, CryptoAmountConverter
from db.wallet import Account, AccountType
import logging

logger = logging.getLogger(__name__)

class CryptoAmountHandler:
    """Handles crypto amounts with proper precision using smallest units"""
    
    @staticmethod
    def format_smallest_unit_amount(amount: int, currency_code: str) -> str:
        """Format smallest unit amount for display"""
        return CryptoPrecisionManager.format_for_display(amount, currency_code)
    
    @staticmethod
    def validate_smallest_unit_amount(amount: int, currency_code: str) -> bool:
        """Validate smallest unit amount"""
        return CryptoPrecisionManager.validate_smallest_unit_amount(amount, currency_code)
    
    @staticmethod
    def get_account_balance_smallest_unit(account: Account, currency_code: str = None) -> int:
        """Get account balance in smallest units (wei, satoshis, etc.)"""
        try:
            return account.get_balance_smallest_unit(currency_code)
        except Exception as e:
            logger.error(f"Error getting account balance in smallest units: {e}")
            return 0
    
    @staticmethod
    def get_account_locked_amount_smallest_unit(account: Account, currency_code: str = None) -> int:
        """Get account locked amount in smallest units (wei, satoshis, etc.)"""
        try:
            return account.get_locked_amount_smallest_unit(currency_code)
        except Exception as e:
            logger.error(f"Error getting account locked amount in smallest units: {e}")
            return 0
    
    @staticmethod
    def get_available_balance_smallest_unit(account: Account, currency_code: str = None) -> int:
        """Get available balance in smallest units (total - locked)"""
        try:
            total_balance = CryptoAmountHandler.get_account_balance_smallest_unit(account, currency_code)
            locked_amount = CryptoAmountHandler.get_account_locked_amount_smallest_unit(account, currency_code)
            return total_balance - locked_amount
        except Exception as e:
            logger.error(f"Error getting available balance in smallest units: {e}")
            return 0
    
    @staticmethod
    def get_account_balance(account: Account, currency_code: str = None) -> Decimal:
        """Get account balance in standard units"""
        try:
            smallest_unit_balance = CryptoAmountHandler.get_account_balance_smallest_unit(account, currency_code)
            if account.is_crypto_account() and account.currency:
                return CryptoPrecisionManager.from_smallest_unit(smallest_unit_balance, account.currency)
            else:
                return Decimal(str(account.balance))
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return Decimal('0')
    
    @staticmethod
    def get_account_locked_amount(account: Account, currency_code: str = None) -> Decimal:
        """Get account locked amount in standard units"""
        try:
            smallest_unit_locked = CryptoAmountHandler.get_account_locked_amount_smallest_unit(account, currency_code)
            if account.is_crypto_account() and account.currency:
                return CryptoPrecisionManager.from_smallest_unit(smallest_unit_locked, account.currency)
            else:
                return Decimal(str(account.locked_amount))
        except Exception as e:
            logger.error(f"Error getting account locked amount: {e}")
            return Decimal('0')
    
    @staticmethod
    def get_available_balance(account: Account, currency_code: str = None) -> Decimal:
        """Get available balance in standard units (total - locked)"""
        try:
            total_balance = CryptoAmountHandler.get_account_balance(account, currency_code)
            locked_amount = CryptoAmountHandler.get_account_locked_amount(account, currency_code)
            return total_balance - locked_amount
        except Exception as e:
            logger.error(f"Error getting available balance: {e}")
            return Decimal('0')
    
    @staticmethod
    def update_account_balance(account: Account, amount: Union[float, Decimal, str], 
                             operation: str = "add", currency_code: str = None) -> bool:
        """
        Update account balance with proper precision
        
        Args:
            account: Account to update
            amount: Amount to add/subtract
            operation: "add" or "subtract"
            currency_code: Currency code for validation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if isinstance(amount, str):
                amount = Decimal(amount)
            elif isinstance(amount, float):
                amount = Decimal(str(amount))
            else:
                amount = Decimal(amount)
            
            # Convert standard amount to smallest unit for validation
            if currency_code:
                smallest_unit_amount = CryptoPrecisionManager.to_smallest_unit(amount, currency_code)
                if not CryptoPrecisionManager.validate_smallest_unit_amount(smallest_unit_amount, currency_code):
                    logger.error(f"Invalid amount {amount} for currency {currency_code}")
                    return False
            
            if account.is_crypto_account():
                current_balance_smallest_unit = account.crypto_balance_smallest_unit or 0
                
                # Convert amount to smallest unit
                amount_smallest_unit = CryptoPrecisionManager.to_smallest_unit(amount, account.currency or "ETH")
                
                if operation == "add":
                    new_balance_smallest_unit = current_balance_smallest_unit + amount_smallest_unit
                elif operation == "subtract":
                    if current_balance_smallest_unit < amount_smallest_unit:
                        logger.error(f"Insufficient balance: {current_balance_smallest_unit} < {amount_smallest_unit}")
                        return False
                    new_balance_smallest_unit = current_balance_smallest_unit - amount_smallest_unit
                else:
                    logger.error(f"Invalid operation: {operation}")
                    return False
                
                account.crypto_balance_smallest_unit = new_balance_smallest_unit
                
            else:
                current_balance = Decimal(str(account.balance))
                
                if operation == "add":
                    new_balance = current_balance + amount
                elif operation == "subtract":
                    if current_balance < amount:
                        logger.error(f"Insufficient balance: {current_balance} < {amount}")
                        return False
                    new_balance = current_balance - amount
                else:
                    logger.error(f"Invalid operation: {operation}")
                    return False
                
                account.balance = new_balance
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating account balance: {e}")
            return False
    
    @staticmethod
    def update_locked_amount(account: Account, amount: Union[float, Decimal, str], 
                           operation: str = "add", currency_code: str = None) -> bool:
        """
        Update account locked amount with proper precision
        
        Args:
            account: Account to update
            amount: Amount to add/subtract
            operation: "add" or "subtract"
            currency_code: Currency code for validation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if isinstance(amount, str):
                amount = Decimal(amount)
            elif isinstance(amount, float):
                amount = Decimal(str(amount))
            else:
                amount = Decimal(amount)
            
            # Convert standard amount to smallest unit for validation
            if currency_code:
                smallest_unit_amount = CryptoPrecisionManager.to_smallest_unit(amount, currency_code)
                if not CryptoPrecisionManager.validate_smallest_unit_amount(smallest_unit_amount, currency_code):
                    logger.error(f"Invalid amount {amount} for currency {currency_code}")
                    return False
            
            if account.is_crypto_account():
                current_locked_smallest_unit = account.crypto_locked_amount_smallest_unit or 0
                
                # Convert amount to smallest unit
                amount_smallest_unit = CryptoPrecisionManager.to_smallest_unit(amount, account.currency or "ETH")
                
                if operation == "add":
                    new_locked_smallest_unit = current_locked_smallest_unit + amount_smallest_unit
                elif operation == "subtract":
                    if current_locked_smallest_unit < amount_smallest_unit:
                        logger.error(f"Insufficient locked amount: {current_locked_smallest_unit} < {amount_smallest_unit}")
                        return False
                    new_locked_smallest_unit = current_locked_smallest_unit - amount_smallest_unit
                else:
                    logger.error(f"Invalid operation: {operation}")
                    return False
                
                account.crypto_locked_amount_smallest_unit = new_locked_smallest_unit
                
            else:
                current_locked = Decimal(str(account.locked_amount))
                
                if operation == "add":
                    new_locked = current_locked + amount
                elif operation == "subtract":
                    if current_locked < amount:
                        logger.error(f"Insufficient locked amount: {current_locked} < {amount}")
                        return False
                    new_locked = current_locked - amount
                else:
                    logger.error(f"Invalid operation: {operation}")
                    return False
                
                account.locked_amount = new_locked
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating locked amount: {e}")
            return False
    
    @staticmethod
    def check_sufficient_balance(account: Account, amount: Union[float, Decimal, str], 
                               currency_code: str = None) -> bool:
        """Check if account has sufficient available balance"""
        try:
            available_balance = CryptoAmountHandler.get_available_balance(account, currency_code)
            
            if isinstance(amount, str):
                amount = Decimal(amount)
            elif isinstance(amount, float):
                amount = Decimal(str(amount))
            else:
                amount = Decimal(amount)
            
            return available_balance >= amount
            
        except Exception as e:
            logger.error(f"Error checking sufficient balance: {e}")
            return False
    
    @staticmethod
    def format_for_display(amount: Union[float, Decimal, str], currency_code: str) -> str:
        """Format amount for display with appropriate decimal places"""
        return CryptoPrecisionManager.format_amount(amount, currency_code, display_format=True)
    
    @staticmethod
    def format_for_storage(amount: Union[float, Decimal, str], currency_code: str) -> str:
        """Format amount for storage with full precision"""
        return CryptoPrecisionManager.format_amount(amount, currency_code, display_format=False)

# Utility functions for easy access
def format_smallest_unit_amount(amount: int, currency_code: str) -> str:
    """Format smallest unit amount for display"""
    return CryptoAmountHandler.format_smallest_unit_amount(amount, currency_code)

def validate_smallest_unit_amount(amount: int, currency_code: str) -> bool:
    """Validate smallest unit amount"""
    return CryptoAmountHandler.validate_smallest_unit_amount(amount, currency_code)

def get_account_balance(account: Account, currency_code: str = None) -> Decimal:
    """Get account balance with proper precision"""
    return CryptoAmountHandler.get_account_balance(account, currency_code)

def get_available_balance(account: Account, currency_code: str = None) -> Decimal:
    """Get available balance with proper precision"""
    return CryptoAmountHandler.get_available_balance(account, currency_code)

def update_account_balance(account: Account, amount: Union[float, Decimal, str], 
                         operation: str = "add", currency_code: str = None) -> bool:
    """Update account balance with proper precision"""
    return CryptoAmountHandler.update_account_balance(account, amount, operation, currency_code)

def check_sufficient_balance(account: Account, amount: Union[float, Decimal, str], 
                           currency_code: str = None) -> bool:
    """Check if account has sufficient available balance"""
    return CryptoAmountHandler.check_sufficient_balance(account, amount, currency_code) 