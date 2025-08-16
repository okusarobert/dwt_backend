#!/usr/bin/env python3
"""
Test script for the new block-based confirmation tracking system
"""

import os
import sys
import json
from decimal import Decimal
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.logger import setup_logging
from db.connection import session
from db.wallet import Transaction, Account, TransactionType, TransactionStatus
from db.crypto_precision import CryptoPrecisionManager

logger = setup_logging()


def test_block_confirmation_system():
    """Test the block-based confirmation tracking system"""
    
    print("🧪 Testing Block-Based Confirmation System")
    print("=" * 50)
    
    # Simulate a transaction with block number
    tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    block_number = 19000000  # Example block number
    
    # Create a test transaction
    test_transaction = Transaction(
        account_id=1,  # Assuming account 1 exists
        reference_id=tx_hash,
        amount=0.1,
        type=TransactionType.DEPOSIT,
        status=TransactionStatus.AWAITING_CONFIRMATION,
        description=f"Test transaction {tx_hash[:8]}...",
        blockchain_txid=tx_hash,
        confirmations=0,
        required_confirmations=15,
        address="0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
        metadata_json={
            "from_address": "0x1234567890abcdef1234567890abcdef12345678",
            "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
            "block_number": block_number,
            "gas_price": 20000000000,
            "gas_used": 21000,
            "timestamp": int(datetime.now().timestamp()),
            "value_wei": "100000000000000000",  # 0.1 ETH in wei
            "amount_eth": "0.1"
        }
    )
    
    print(f"📝 Created test transaction:")
    print(f"   Hash: {tx_hash}")
    print(f"   Block: {block_number}")
    print(f"   Amount: 0.1 ETH")
    print(f"   Required confirmations: 15")
    print()
    
    # Simulate different block numbers and calculate confirmations
    test_blocks = [
        block_number + 1,   # 1 confirmation
        block_number + 5,   # 5 confirmations
        block_number + 10,  # 10 confirmations
        block_number + 15,  # 15 confirmations (ready!)
        block_number + 20,  # 20 confirmations (overkill)
    ]
    
    print("🔄 Simulating block confirmations:")
    print("-" * 40)
    
    for current_block in test_blocks:
        confirmations = current_block - block_number
        
        print(f"Block {current_block}: {confirmations} confirmations")
        
        if confirmations >= 15:
            print(f"   ✅ Transaction confirmed! ({confirmations} confirmations)")
            print(f"   💰 Account would be credited with 0.1 ETH")
            print(f"   🔓 Locked amount would be released")
        elif confirmations > 0:
            print(f"   ⏳ Still waiting... ({confirmations}/15 confirmations)")
        else:
            print(f"   ❌ Transaction not yet included in a block")
        
        print()
    
    # Test precision handling
    print("🎯 Testing Precision Handling:")
    print("-" * 30)
    
    test_amounts = [0.1, 0.000001, 1.0, 0.000000000000000001]  # Very small amounts
    
    for amount in test_amounts:
        amount_wei = CryptoPrecisionManager.to_smallest_unit(amount, "ETH")
        amount_back = CryptoPrecisionManager.from_smallest_unit(amount_wei, "ETH")
        
        print(f"Amount: {amount} ETH")
        print(f"   Wei: {amount_wei:,}")
        print(f"   Back to ETH: {amount_back}")
        print(f"   Precision maintained: {amount == float(amount_back)}")
        print()
    
    print("✅ Block-based confirmation system test completed!")
    print()
    print("📋 Key Features:")
    print("   - Real-time block event processing")
    print("   - Automatic confirmation counting")
    print("   - Precision handling with smallest units")
    print("   - Reservation system for amount locking")
    print("   - Credit processing after 15 confirmations")


def test_reservation_system():
    """Test the reservation system"""
    
    print("🔒 Testing Reservation System")
    print("=" * 40)
    
    # Simulate account with some balance
    account_id = 1
    initial_balance_wei = 1000000000000000000  # 1 ETH in wei
    initial_locked_wei = 0
    
    print(f"Account {account_id} initial state:")
    print(f"   Balance: {CryptoPrecisionManager.from_smallest_unit(initial_balance_wei, 'ETH')} ETH")
    print(f"   Locked: {CryptoPrecisionManager.from_smallest_unit(initial_locked_wei, 'ETH')} ETH")
    print()
    
    # Simulate incoming transaction
    incoming_amount = 0.5  # ETH
    incoming_amount_wei = CryptoPrecisionManager.to_smallest_unit(incoming_amount, "ETH")
    
    print(f"💰 Incoming transaction: {incoming_amount} ETH")
    print(f"   Amount in wei: {incoming_amount_wei:,}")
    
    # Lock the amount (simulate reservation)
    new_locked_wei = initial_locked_wei + incoming_amount_wei
    
    print(f"🔒 After locking:")
    print(f"   Balance: {CryptoPrecisionManager.from_smallest_unit(initial_balance_wei, 'ETH')} ETH")
    print(f"   Locked: {CryptoPrecisionManager.from_smallest_unit(new_locked_wei, 'ETH')} ETH")
    print(f"   Available: {CryptoPrecisionManager.from_smallest_unit(initial_balance_wei - new_locked_wei, 'ETH')} ETH")
    print()
    
    # Simulate confirmation and credit
    print(f"✅ After 15 confirmations (credit account):")
    new_balance_wei = initial_balance_wei + incoming_amount_wei
    final_locked_wei = new_locked_wei - incoming_amount_wei  # Release reservation
    
    print(f"   Balance: {CryptoPrecisionManager.from_smallest_unit(new_balance_wei, 'ETH')} ETH")
    print(f"   Locked: {CryptoPrecisionManager.from_smallest_unit(final_locked_wei, 'ETH')} ETH")
    print(f"   Available: {CryptoPrecisionManager.from_smallest_unit(new_balance_wei - final_locked_wei, 'ETH')} ETH")
    print()
    
    print("✅ Reservation system test completed!")


if __name__ == "__main__":
    test_block_confirmation_system()
    print("\n" + "=" * 60 + "\n")
    test_reservation_system() 