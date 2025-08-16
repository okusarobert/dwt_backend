#!/usr/bin/env python3
"""
Script to credit crypto accounts with crypto amounts
Uses the new smallest unit system for precision
"""

import os
import sys
import argparse
from decimal import Decimal
from typing import Optional

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.logger import setup_logging
from db.connection import session
from db.wallet import Account, AccountType, Transaction, TransactionType, TransactionStatus
from db.crypto_precision import CryptoPrecisionManager

logger = setup_logging()


def get_account_by_id(account_id: int) -> Optional[Account]:
    """Get account by ID"""
    try:
        return session.query(Account).filter_by(id=account_id).first()
    except Exception as e:
        logger.error(f"❌ Error getting account {account_id}: {e}")
        return None


def get_account_by_user_and_currency(user_id: int, currency: str) -> Optional[Account]:
    """Get account by user ID and currency"""
    try:
        return session.query(Account).filter_by(
            user_id=user_id,
            currency=currency.upper(),
            account_type=AccountType.CRYPTO
        ).first()
    except Exception as e:
        logger.error(f"❌ Error getting account for user {user_id}, currency {currency}: {e}")
        return None


def list_crypto_accounts():
    """List all crypto accounts"""
    try:
        accounts = session.query(Account).filter_by(account_type=AccountType.CRYPTO).all()
        
        if not accounts:
            print("📋 No crypto accounts found")
            return
        
        print("📋 Crypto Accounts:")
        print("-" * 80)
        print(f"{'ID':<5} {'User ID':<8} {'Currency':<10} {'Balance':<15} {'Locked':<15} {'Available':<15}")
        print("-" * 80)
        
        for account in accounts:
            balance = account.get_balance()
            locked = account.get_locked_amount()
            available = account.available_balance()
            
            print(f"{account.id:<5} {account.user_id:<8} {account.currency:<10} "
                  f"{balance:<15.8f} {locked:<15.8f} {available:<15.8f}")
        
        print("-" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error listing accounts: {e}")


def credit_account(account_id: int, amount: float, currency: str, description: str = "Manual credit"):
    """Credit a crypto account with the specified amount"""
    try:
        # Get the account
        account = get_account_by_id(account_id)
        if not account:
            print(f"❌ Account {account_id} not found")
            return False
        
        if account.account_type != AccountType.CRYPTO:
            print(f"❌ Account {account_id} is not a crypto account")
            return False
        
        if account.currency != currency.upper():
            print(f"❌ Account currency ({account.currency}) doesn't match requested currency ({currency.upper()})")
            return False
        
        # Convert amount to smallest units
        amount_smallest_unit = CryptoPrecisionManager.to_smallest_unit(amount, currency)
        
        # Get current balance in smallest units
        current_balance = account.crypto_balance_smallest_unit or 0
        new_balance = current_balance + amount_smallest_unit
        
        # Update account balance
        account.crypto_balance_smallest_unit = new_balance
        
        # Create transaction record
        transaction = Transaction(
            account_id=account_id,
            reference_id=f"manual_credit_{int(Decimal(amount) * 10**8)}",  # Simple unique reference
            amount=amount,
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description=description,
            metadata_json={
                "manual_credit": True,
                "amount_smallest_unit": amount_smallest_unit,
                "currency": currency.upper(),
                "previous_balance": current_balance,
                "new_balance": new_balance
            }
        )
        
        session.add(transaction)
        session.commit()
        
        # Convert back to standard units for display
        amount_standard = CryptoPrecisionManager.from_smallest_unit(amount_smallest_unit, currency)
        new_balance_standard = CryptoPrecisionManager.from_smallest_unit(new_balance, currency)
        
        print(f"✅ Successfully credited account {account_id}")
        print(f"   User: {account.user_id}")
        print(f"   Currency: {currency.upper()}")
        print(f"   Amount: {amount_standard} {currency.upper()}")
        print(f"   Previous Balance: {CryptoPrecisionManager.from_smallest_unit(current_balance, currency)} {currency.upper()}")
        print(f"   New Balance: {new_balance_standard} {currency.upper()}")
        print(f"   Transaction ID: {transaction.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error crediting account: {e}")
        session.rollback()
        return False


def debit_account(account_id: int, amount: float, currency: str, description: str = "Manual debit"):
    """Debit a crypto account with the specified amount"""
    try:
        # Get the account
        account = get_account_by_id(account_id)
        if not account:
            print(f"❌ Account {account_id} not found")
            return False
        
        if account.account_type != AccountType.CRYPTO:
            print(f"❌ Account {account_id} is not a crypto account")
            return False
        
        if account.currency != currency.upper():
            print(f"❌ Account currency ({account.currency}) doesn't match requested currency ({currency.upper()})")
            return False
        
        # Convert amount to smallest units
        amount_smallest_unit = CryptoPrecisionManager.to_smallest_unit(amount, currency)
        
        # Get current balance in smallest units
        current_balance = account.crypto_balance_smallest_unit or 0
        current_locked = account.crypto_locked_amount_smallest_unit or 0
        available_balance = current_balance - current_locked
        
        # Check if sufficient balance
        if available_balance < amount_smallest_unit:
            print(f"❌ Insufficient available balance")
            print(f"   Available: {CryptoPrecisionManager.from_smallest_unit(available_balance, currency)} {currency.upper()}")
            print(f"   Requested: {amount} {currency.upper()}")
            return False
        
        new_balance = current_balance - amount_smallest_unit
        
        # Update account balance
        account.crypto_balance_smallest_unit = new_balance
        
        # Create transaction record
        transaction = Transaction(
            account_id=account_id,
            reference_id=f"manual_debit_{int(Decimal(amount) * 10**8)}",  # Simple unique reference
            amount=-amount,  # Negative amount for debit
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            description=description,
            metadata_json={
                "manual_debit": True,
                "amount_smallest_unit": amount_smallest_unit,
                "currency": currency.upper(),
                "previous_balance": current_balance,
                "new_balance": new_balance
            }
        )
        
        session.add(transaction)
        session.commit()
        
        # Convert back to standard units for display
        amount_standard = CryptoPrecisionManager.from_smallest_unit(amount_smallest_unit, currency)
        new_balance_standard = CryptoPrecisionManager.from_smallest_unit(new_balance, currency)
        
        print(f"✅ Successfully debited account {account_id}")
        print(f"   User: {account.user_id}")
        print(f"   Currency: {currency.upper()}")
        print(f"   Amount: {amount_standard} {currency.upper()}")
        print(f"   Previous Balance: {CryptoPrecisionManager.from_smallest_unit(current_balance, currency)} {currency.upper()}")
        print(f"   New Balance: {new_balance_standard} {currency.upper()}")
        print(f"   Transaction ID: {transaction.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error debiting account: {e}")
        session.rollback()
        return False


def show_account_details(account_id: int):
    """Show detailed information about an account"""
    try:
        account = get_account_by_id(account_id)
        if not account:
            print(f"❌ Account {account_id} not found")
            return
        
        print(f"📊 Account Details:")
        print(f"   ID: {account.id}")
        print(f"   User ID: {account.user_id}")
        print(f"   Currency: {account.currency}")
        print(f"   Account Type: {account.account_type.value}")
        print(f"   Account Number: {account.account_number}")
        print(f"   Label: {account.label}")
        
        if account.account_type == AccountType.CRYPTO:
            balance_smallest = account.crypto_balance_smallest_unit or 0
            locked_smallest = account.crypto_locked_amount_smallest_unit or 0
            
            print(f"   Balance (smallest units): {balance_smallest:,}")
            print(f"   Locked (smallest units): {locked_smallest:,}")
            print(f"   Available (smallest units): {balance_smallest - locked_smallest:,}")
            
            if account.currency:
                print(f"   Balance: {account.get_balance()} {account.currency}")
                print(f"   Locked: {account.get_locked_amount()} {account.currency}")
                print(f"   Available: {account.available_balance()} {account.currency}")
        else:
            print(f"   Balance: {account.balance}")
            print(f"   Locked: {account.locked_amount}")
            print(f"   Available: {account.available_balance()}")
        
        print(f"   Created: {account.created_at}")
        print(f"   Updated: {account.updated_at}")
        
    except Exception as e:
        logger.error(f"❌ Error showing account details: {e}")


def main():
    parser = argparse.ArgumentParser(description="Credit/Debit crypto accounts")
    parser.add_argument("--list", action="store_true", help="List all crypto accounts")
    parser.add_argument("--show", type=int, help="Show details for specific account ID")
    parser.add_argument("--credit", type=int, help="Account ID to credit")
    parser.add_argument("--debit", type=int, help="Account ID to debit")
    parser.add_argument("--amount", type=float, required=False, help="Amount to credit/debit")
    parser.add_argument("--currency", type=str, required=False, help="Currency (ETH, BTC, etc.)")
    parser.add_argument("--description", type=str, default="Manual operation", help="Transaction description")
    parser.add_argument("--user", type=int, help="User ID (for finding account by user and currency)")
    
    args = parser.parse_args()
    
    if args.list:
        list_crypto_accounts()
        return
    
    if args.show:
        show_account_details(args.show)
        return
    
    if not args.amount or not args.currency:
        print("❌ Amount and currency are required for credit/debit operations")
        parser.print_help()
        return
    
    # Validate currency
    supported_currencies = ["ETH", "BTC", "SOL", "XRP", "XLM", "TRX", "BNB", "OPTIMISM", "POLYGON", "AVAX", "WORLD"]
    if args.currency.upper() not in supported_currencies:
        print(f"❌ Unsupported currency: {args.currency}")
        print(f"   Supported currencies: {', '.join(supported_currencies)}")
        return
    
    if args.credit:
        if args.user:
            # Find account by user and currency
            account = get_account_by_user_and_currency(args.user, args.currency)
            if account:
                credit_account(account.id, args.amount, args.currency, args.description)
            else:
                print(f"❌ No crypto account found for user {args.user} with currency {args.currency}")
        else:
            credit_account(args.credit, args.amount, args.currency, args.description)
    
    elif args.debit:
        if args.user:
            # Find account by user and currency
            account = get_account_by_user_and_currency(args.user, args.currency)
            if account:
                debit_account(account.id, args.amount, args.currency, args.description)
            else:
                print(f"❌ No crypto account found for user {args.user} with currency {args.currency}")
        else:
            debit_account(args.debit, args.amount, args.currency, args.description)
    
    else:
        print("❌ Please specify --credit or --debit")
        parser.print_help()


if __name__ == "__main__":
    main() 