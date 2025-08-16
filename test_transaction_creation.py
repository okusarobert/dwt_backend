#!/usr/bin/env python3
"""
Test script to verify that transaction creation works with the new smallest unit fields
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionType, TransactionStatus, Account
from decimal import Decimal

def test_transaction_creation():
    """Test creating a transaction with the new smallest unit fields"""
    session = get_session()
    
    try:
        # Get a test account
        account = session.query(Account).first()
        if not account:
            print("❌ No accounts found for testing")
            return
        
        # Test transaction data
        test_amount = 0.001
        test_amount_smallest = int(test_amount * 10**18)  # Convert to wei
        
        # Create test transaction
        test_tx = Transaction(
            account_id=account.id,
            reference_id="test_tx_creation_123",
            amount=test_amount,
            amount_smallest_unit=test_amount_smallest,
            precision_config={
                "currency": "ETH",
                "decimals": 18,
                "smallest_unit": "wei"
            },
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.AWAITING_CONFIRMATION,
            description="Test transaction creation",
            provider_reference="test_hash_123",
            blockchain_txid="test_hash_123"
        )
        
        session.add(test_tx)
        session.commit()
        
        print("✅ Transaction created successfully!")
        print(f"   Reference: {test_tx.reference_id}")
        print(f"   Amount: {test_tx.amount}")
        print(f"   Amount Smallest Unit: {test_tx.amount_smallest_unit}")
        print(f"   Precision Config: {test_tx.precision_config}")
        print(f"   Get Amount Standard: {test_tx.get_amount_standard()}")
        print(f"   Get Amount Smallest Unit: {test_tx.get_amount_smallest_unit()}")
        
        # Clean up - delete the test transaction
        session.delete(test_tx)
        session.commit()
        print("✅ Test transaction cleaned up")
        
    except Exception as e:
        print(f"❌ Error creating transaction: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Testing Transaction Creation with Smallest Unit Fields")
    print("=" * 55)
    test_transaction_creation() 