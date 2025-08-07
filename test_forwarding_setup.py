#!/usr/bin/env python3
"""
Test script for BTC address forwarding setup.
Tests the creation of user addresses and master addresses with forwarding logic.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.btc import BTCWallet
from db.connection import session
from db.wallet import CryptoAddress, Account, AccountType
from shared.logger import setup_logging
from decouple import config

logger = setup_logging()

def test_address_creation_with_forwarding():
    """Test creating addresses with BlockCypher forwarding setup."""
    print("🧪 Testing BTC Address Creation with BlockCypher Forwarding")
    print("=" * 60)
    
    try:
        # Create a test user account
        test_user_id = 999  # Test user ID
        
        # Check if account already exists
        existing_account = session.query(Account).filter(
            Account.user_id == test_user_id,
            Account.currency == "BTC",
            Account.account_type == AccountType.CRYPTO
        ).first()
        
        if existing_account:
            print(f"✅ Test account already exists for user {test_user_id}")
            account_id = existing_account.id
        else:
            # Create test account
            test_account = Account(
                user_id=test_user_id,
                balance=0,
                locked_amount=0,
                currency="BTC",
                account_type=AccountType.CRYPTO,
                account_number="TEST999",
                label="Test BTC Account"
            )
            session.add(test_account)
            session.flush()
            account_id = test_account.id
            print(f"✅ Created test account with ID: {account_id}")
        
        # Create BTC wallet and address
        btc_wallet = BTCWallet(user_id=test_user_id, session=session)
        
        # Create wallet (this will also create an address)
        btc_wallet.create_wallet()
        
        # Check created addresses
        addresses = session.query(CryptoAddress).filter(
            CryptoAddress.account_id == account_id
        ).all()
        
        print(f"\n📋 Created Addresses for Account {account_id}:")
        for addr in addresses:
            print(f"  Address: {addr.address}")
            print(f"  Type: {addr.address_type}")
            print(f"  Label: {addr.label}")
            print(f"  Active: {addr.is_active}")
            print(f"  Webhook IDs: {addr.webhook_ids}")
            print()
        
        # Test address forwarding setup
        user_address = None
        for addr in addresses:
            if addr.address_type == "hd_wallet":
                user_address = addr.address
                break
        
        if user_address:
            print(f"\n🔄 Testing BlockCypher Address Forwarding:")
            print(f"  User Address: {user_address}")
            print(f"  Master Address: {config('BTC_MASTER_ADDRESS', default='Not configured')}")
            print(f"  Forwarding: Automatic via BlockCypher")
            
            # Test listing forwards
            forwards = btc_wallet.list_address_forwards()
            if forwards:
                print(f"  ✅ Found {len(forwards)} active forwards")
            else:
                print(f"  ℹ️  No active forwards found")
        
        session.commit()
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        session.rollback()
        print(f"❌ Test failed: {e}")

def list_all_addresses():
    """List all addresses in the database."""
    print("\n📋 All Addresses in Database:")
    print("=" * 40)
    
    try:
        addresses = session.query(CryptoAddress).all()
        
        if addresses:
            for addr in addresses:
                account = session.query(Account).filter(Account.id == addr.account_id).first()
                user_id = account.user_id if account else "Unknown"
                
                print(f"User {user_id} - {addr.currency_code}")
                print(f"  Address: {addr.address}")
                print(f"  Type: {addr.address_type}")
                print(f"  Label: {addr.label}")
                print(f"  Active: {addr.is_active}")
                print()
        else:
            print("No addresses found in database.")
            
    except Exception as e:
        logger.error(f"Error listing addresses: {e}")

def test_address_forwarding_management():
    """Test address forwarding management."""
    print("\n🔍 Testing Address Forwarding Management:")
    print("=" * 40)
    
    try:
        # Get all accounts
        accounts = session.query(Account).filter(
            Account.currency == "BTC",
            Account.account_type == AccountType.CRYPTO
        ).all()
        
        for account in accounts:
            btc_wallet = BTCWallet(user_id=account.user_id, session=session)
            
            # List forwards for this account
            forwards = btc_wallet.list_address_forwards()
            if forwards:
                print(f"✅ User {account.user_id}: {len(forwards)} active forwards")
            else:
                print(f"ℹ️  User {account.user_id}: No active forwards")
                
    except Exception as e:
        logger.error(f"Error testing address forwarding management: {e}")

def main():
    """Run all tests."""
    print("🚀 BTC Address Forwarding Test Suite")
    print("=" * 60)
    
    # Test 1: Address creation with forwarding
    test_address_creation_with_forwarding()
    
    # Test 2: List all addresses
    list_all_addresses()
    
    # Test 3: Address forwarding management
    test_address_forwarding_management()
    
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    main() 