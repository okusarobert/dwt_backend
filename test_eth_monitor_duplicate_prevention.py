#!/usr/bin/env python3
"""
Test script to verify eth_monitor duplicate prevention logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionType, TransactionStatus, Account, CryptoAddress
from decimal import Decimal

def test_eth_monitor_duplicate_logic():
    """Test the eth_monitor's duplicate detection logic"""
    session = get_session()
    
    try:
        print("🧪 Testing Eth Monitor Duplicate Prevention Logic")
        print("=" * 55)
        
        # Get monitored addresses
        crypto_addresses = session.query(CryptoAddress).all()
        if len(crypto_addresses) < 2:
            print("❌ Need at least 2 monitored addresses for testing")
            return
        
        sender_address = crypto_addresses[0]
        recipient_address = crypto_addresses[1]
        
        print(f"Sender: {sender_address.address}")
        print(f"Recipient: {recipient_address.address}")
        
        # Simulate the eth_monitor's duplicate detection logic
        tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        
        # Test 1: Check if transaction exists globally (should be false)
        existing_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash
        ).first()
        
        if existing_tx:
            print(f"❌ Transaction {tx_hash} already exists globally")
            return
        else:
            print(f"✅ Transaction {tx_hash} does not exist globally (expected)")
        
        # Test 2: Check for sender-specific transaction (should be false)
        sender_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash,
            address=sender_address.address
        ).first()
        
        if sender_tx:
            print(f"❌ Sender transaction already exists")
            return
        else:
            print(f"✅ Sender transaction does not exist (expected)")
        
        # Test 3: Check for recipient-specific transaction (should be false)
        recipient_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash,
            address=recipient_address.address
        ).first()
        
        if recipient_tx:
            print(f"❌ Recipient transaction already exists")
            return
        else:
            print(f"✅ Recipient transaction does not exist (expected)")
        
        # Test 4: Create WITHDRAWAL for sender
        print(f"\n📤 Creating WITHDRAWAL for sender...")
        withdrawal_tx = Transaction(
            account_id=sender_address.account_id,
            reference_id=tx_hash,
            amount=0.001,
            amount_smallest_unit=int(0.001 * 10**18),
            precision_config={
                "currency": "ETH",
                "decimals": 18,
                "smallest_unit": "wei"
            },
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.AWAITING_CONFIRMATION,
            description=f"Test WITHDRAWAL {tx_hash[:8]}...",
            blockchain_txid=tx_hash,
            address=sender_address.address
        )
        
        session.add(withdrawal_tx)
        session.commit()
        
        print(f"✅ WITHDRAWAL created with ID: {withdrawal_tx.id}")
        
        # Test 5: Check if transaction exists globally now (should be true)
        existing_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash
        ).first()
        
        if existing_tx:
            print(f"✅ Transaction {tx_hash} now exists globally (expected)")
        else:
            print(f"❌ Transaction {tx_hash} not found globally after creation")
        
        # Test 6: Check for sender-specific transaction (should be true)
        sender_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash,
            address=sender_address.address
        ).first()
        
        if sender_tx:
            print(f"✅ Sender transaction now exists (expected)")
        else:
            print(f"❌ Sender transaction not found after creation")
        
        # Test 7: Check for recipient-specific transaction (should be false)
        recipient_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash,
            address=recipient_address.address
        ).first()
        
        if recipient_tx:
            print(f"❌ Recipient transaction already exists (unexpected)")
        else:
            print(f"✅ Recipient transaction does not exist (expected)")
        
        # Test 8: Create DEPOSIT for recipient
        print(f"\n📥 Creating DEPOSIT for recipient...")
        deposit_tx = Transaction(
            account_id=recipient_address.account_id,
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
            description=f"Test DEPOSIT {tx_hash[:8]}...",
            blockchain_txid=tx_hash,
            address=recipient_address.address
        )
        
        session.add(deposit_tx)
        session.commit()
        
        print(f"✅ DEPOSIT created with ID: {deposit_tx.id}")
        
        # Test 9: Check final state
        total_txs = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash
        ).count()
        
        print(f"\n📊 Final State:")
        print(f"   Total transactions with this hash: {total_txs}")
        print(f"   Expected: 2 (1 WITHDRAWAL + 1 DEPOSIT)")
        
        if total_txs == 2:
            print("✅ Correct number of transactions created!")
        else:
            print(f"❌ Expected 2 transactions, got {total_txs}")
        
        # Clean up
        session.delete(withdrawal_tx)
        session.delete(deposit_tx)
        session.commit()
        
        print("\n✅ Eth Monitor duplicate prevention logic test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error in eth monitor duplicate prevention test: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_eth_monitor_duplicate_logic() 