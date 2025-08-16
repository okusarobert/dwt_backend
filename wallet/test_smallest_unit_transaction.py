#!/usr/bin/env python3
"""
Test script to verify the new smallest unit transaction system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionType, TransactionStatus, CryptoAddress
from decimal import Decimal
import json

def test_smallest_unit_transaction():
    """Test creating a transaction with smallest unit precision"""
    session = get_session()
    
    try:
        # Get a crypto address for testing
        crypto_address = session.query(CryptoAddress).filter_by(currency_code='ETH').first()
        if not crypto_address:
            print("❌ No ETH crypto address found for testing")
            return
        
        # Test transaction details
        test_tx_hash = "0xTEST123456789abcdef"
        test_amount_eth = Decimal("0.0025")  # 0.0025 ETH
        test_amount_wei = int(test_amount_eth * Decimal(10**18))  # 2,500,000,000,000,000 wei
        
        # Check if test transaction already exists
        existing_tx = session.query(Transaction).filter_by(blockchain_txid=test_tx_hash).first()
        if existing_tx:
            print(f"✅ Test transaction already exists")
            print(f"   Amount: {existing_tx.amount}")
            print(f"   Amount Smallest Unit: {existing_tx.amount_smallest_unit}")
            print(f"   Get Amount Standard: {existing_tx.get_amount_standard()}")
            print(f"   Get Amount Smallest Unit: {existing_tx.get_amount_smallest_unit()}")
            return
        
        # Create test transaction with smallest unit precision
        test_transaction = Transaction(
            account_id=crypto_address.account_id,
            reference_id=f"test_{test_tx_hash[:8]}",
            amount=float(test_amount_eth),  # Backward compatibility
            amount_smallest_unit=test_amount_wei,  # New precision field
            precision_config={
                "currency": "ETH",
                "decimals": 18,
                "smallest_unit": "wei"
            },
            type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            description="Test transaction with smallest unit precision",
            blockchain_txid=test_tx_hash,
            provider_reference=test_tx_hash,
            confirmations=15,
            required_confirmations=15,
            address=crypto_address.address,
            metadata_json={
                "from_address": "0x1234567890123456789012345678901234567890",
                "to_address": crypto_address.address,
                "block_number": 8935200,
                "gas_price": 20000000000,
                "gas_used": 21000,
                "timestamp": 1733692800,
                "value_wei": str(test_amount_wei),
                "amount_eth": str(test_amount_eth),
                "test_transaction": True
            }
        )
        
        session.add(test_transaction)
        session.commit()
        
        print(f"✅ Test transaction created successfully")
        print(f"   Amount: {test_transaction.amount}")
        print(f"   Amount Smallest Unit: {test_transaction.amount_smallest_unit}")
        print(f"   Precision Config: {test_transaction.precision_config}")
        print(f"   Get Amount Standard: {test_transaction.get_amount_standard()}")
        print(f"   Get Amount Smallest Unit: {test_transaction.get_amount_smallest_unit()}")
        print(f"   Expected Amount: {test_amount_eth}")
        print(f"   Expected Wei: {test_amount_wei}")
        
        # Verify the conversion methods work correctly
        if test_transaction.get_amount_standard() == float(test_amount_eth):
            print("✅ Amount conversion working correctly")
        else:
            print("❌ Amount conversion failed")
            
        if test_transaction.get_amount_smallest_unit() == test_amount_wei:
            print("✅ Smallest unit conversion working correctly")
        else:
            print("❌ Smallest unit conversion failed")
        
    except Exception as e:
        print(f"❌ Error creating test transaction: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Testing Smallest Unit Transaction System")
    print("=" * 45)
    test_smallest_unit_transaction() 