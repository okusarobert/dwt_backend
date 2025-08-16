#!/usr/bin/env python3
"""
Test script to verify duplicate transaction prevention
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionType, TransactionStatus, Account, CryptoAddress
from decimal import Decimal

def test_duplicate_prevention():
    """Test that duplicate transactions are prevented"""
    session = get_session()
    
    try:
        print("🧪 Testing Duplicate Transaction Prevention")
        print("=" * 50)
        
        # Get a test account
        account = session.query(Account).first()
        if not account:
            print("❌ No accounts found for testing")
            return
        
        # Create a test transaction
        tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        amount = 0.001
        
        print(f"Creating first transaction with hash: {tx_hash}")
        
        # Create first transaction
        tx1 = Transaction(
            account_id=account.id,
            reference_id=tx_hash,
            amount=amount,
            amount_smallest_unit=int(amount * 10**18),
            precision_config={
                "currency": "ETH",
                "decimals": 18,
                "smallest_unit": "wei"
            },
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.AWAITING_CONFIRMATION,
            description=f"Test transaction {tx_hash[:8]}...",
            blockchain_txid=tx_hash,
            address="0x1234567890abcdef1234567890abcdef12345678"
        )
        
        session.add(tx1)
        session.commit()
        
        print("✅ First transaction created successfully!")
        print(f"   ID: {tx1.id}")
        print(f"   Hash: {tx1.blockchain_txid}")
        
        # Try to create a duplicate transaction with the same hash
        print(f"\nAttempting to create duplicate transaction with same hash...")
        
        tx2 = Transaction(
            account_id=account.id,
            reference_id=tx_hash,
            amount=amount,
            amount_smallest_unit=int(amount * 10**18),
            precision_config={
                "currency": "ETH",
                "decimals": 18,
                "smallest_unit": "wei"
            },
            type=TransactionType.WITHDRAWAL,  # Different type
            status=TransactionStatus.AWAITING_CONFIRMATION,
            description=f"Duplicate test transaction {tx_hash[:8]}...",
            blockchain_txid=tx_hash,  # Same hash!
            address="0x876543210fedcba9876543210fedcba98765432"  # Different address
        )
        
        session.add(tx2)
        session.commit()
        
        print("❌ Duplicate transaction was created! This should not happen.")
        print(f"   Duplicate ID: {tx2.id}")
        
        # Check how many transactions exist with this hash
        duplicate_count = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash
        ).count()
        
        print(f"   Total transactions with this hash: {duplicate_count}")
        
        # Clean up
        session.delete(tx1)
        session.delete(tx2)
        session.commit()
        
        print("\n❌ Duplicate prevention test failed!")
        
    except Exception as e:
        print(f"❌ Error in duplicate prevention test: {e}")
        session.rollback()
    finally:
        session.close()

def test_duplicate_detection_logic():
    """Test the duplicate detection logic"""
    session = get_session()
    
    try:
        print("\n🔍 Testing Duplicate Detection Logic")
        print("=" * 40)
        
        # Get a test account
        account = session.query(Account).first()
        if not account:
            print("❌ No accounts found for testing")
            return
        
        tx_hash = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        
        # Check if transaction exists (should be false)
        existing_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash
        ).first()
        
        if existing_tx:
            print(f"❌ Transaction {tx_hash} already exists in database")
            return
        else:
            print(f"✅ Transaction {tx_hash} does not exist (expected)")
        
        # Create a transaction
        tx = Transaction(
            account_id=account.id,
            reference_id=tx_hash,
            amount=0.001,
            amount_smallest_unit=int(0.001 * 10**18),
            precision_config={
                "currency": "ETH",
                "decimals": 18,
                "smallest_unit": "wei"
            },
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.AWAITING_CONFIRMATION,
            description=f"Test transaction {tx_hash[:8]}...",
            blockchain_txid=tx_hash,
            address="0x1234567890abcdef1234567890abcdef12345678"
        )
        
        session.add(tx)
        session.commit()
        
        print(f"✅ Transaction created with ID: {tx.id}")
        
        # Check if transaction exists now (should be true)
        existing_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash
        ).first()
        
        if existing_tx:
            print(f"✅ Transaction {tx_hash} now exists in database (expected)")
        else:
            print(f"❌ Transaction {tx_hash} not found after creation")
        
        # Clean up
        session.delete(tx)
        session.commit()
        
        print("✅ Duplicate detection logic test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in duplicate detection logic test: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_duplicate_detection_logic()
    test_duplicate_prevention() 