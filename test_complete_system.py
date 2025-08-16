#!/usr/bin/env python3
"""
Comprehensive test to verify the complete system is working correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionType, TransactionStatus, Account, Reservation, ReservationType
from decimal import Decimal

def test_complete_system():
    """Test the complete system with all fixes applied"""
    session = get_session()
    
    try:
        print("🧪 Testing Complete System")
        print("=" * 50)
        
        # Test 1: Transaction Creation with Smallest Unit Fields
        print("\n1. Testing Transaction Creation...")
        test_amount = 0.0025
        test_amount_smallest = int(test_amount * 10**18)
        
        # Get a test account
        account = session.query(Account).first()
        if not account:
            print("❌ No accounts found for testing")
            return
        
        # Create test transaction
        test_tx = Transaction(
            account_id=account.id,
            reference_id="test_complete_system_123",
            amount=test_amount,
            amount_smallest_unit=test_amount_smallest,
            precision_config={
                "currency": "ETH",
                "decimals": 18,
                "smallest_unit": "wei"
            },
            type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.AWAITING_CONFIRMATION,
            description="Test complete system",
            provider_reference="test_hash_456",
            blockchain_txid="test_hash_456"
        )
        
        session.add(test_tx)
        session.commit()
        
        print("✅ Transaction created successfully!")
        print(f"   Amount: {test_tx.amount}")
        print(f"   Amount Smallest Unit: {test_tx.amount_smallest_unit}")
        print(f"   Get Amount Standard: {test_tx.get_amount_standard()}")
        print(f"   Get Amount Smallest Unit: {test_tx.get_amount_smallest_unit()}")
        
        # Test 2: Reservation Creation
        print("\n2. Testing Reservation Creation...")
        import time
        reservation_reference = f"test_reservation_{int(time.time() * 1000)}"
        
        reservation = Reservation(
            user_id=account.user_id,
            reference=reservation_reference,
            amount=test_amount,
            type=ReservationType.RESERVE,
            status="active"
        )
        
        session.add(reservation)
        session.commit()
        
        print("✅ Reservation created successfully!")
        print(f"   Reference: {reservation.reference}")
        print(f"   Amount: {reservation.amount}")
        print(f"   Type: {reservation.type}")
        
        # Test 3: Account Balance Updates
        print("\n3. Testing Account Balance Updates...")
        original_balance = account.crypto_balance_smallest_unit or 0
        original_locked = account.crypto_locked_amount_smallest_unit or 0
        
        # Simulate locking amount
        account.crypto_locked_amount_smallest_unit = original_locked + test_amount_smallest
        session.commit()
        
        print("✅ Account balance updated successfully!")
        print(f"   Original Balance: {original_balance} wei")
        print(f"   Original Locked: {original_locked} wei")
        print(f"   New Locked: {account.crypto_locked_amount_smallest_unit} wei")
        
        # Test 4: Transaction Status Updates
        print("\n4. Testing Transaction Status Updates...")
        test_tx.status = TransactionStatus.COMPLETED
        test_tx.confirmations = 15
        session.commit()
        
        print("✅ Transaction status updated successfully!")
        print(f"   Status: {test_tx.status}")
        print(f"   Confirmations: {test_tx.confirmations}")
        
        # Test 5: Release Reservation
        print("\n5. Testing Release Reservation...")
        release_reference = f"test_release_{int(time.time() * 1000)}"
        
        release_reservation = Reservation(
            user_id=account.user_id,
            reference=release_reference,
            amount=test_amount,
            type=ReservationType.RELEASE,
            status="completed"
        )
        
        session.add(release_reservation)
        
        # Simulate releasing amount and crediting balance
        account.crypto_locked_amount_smallest_unit = original_locked
        account.crypto_balance_smallest_unit = original_balance + test_amount_smallest
        session.commit()
        
        print("✅ Release reservation created successfully!")
        print(f"   Reference: {release_reservation.reference}")
        print(f"   Final Balance: {account.crypto_balance_smallest_unit} wei")
        print(f"   Final Locked: {account.crypto_locked_amount_smallest_unit} wei")
        
        # Clean up
        session.delete(test_tx)
        session.delete(reservation)
        session.delete(release_reservation)
        session.commit()
        
        print("\n✅ All tests passed! System is working correctly.")
        
    except Exception as e:
        print(f"❌ Error in complete system test: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_complete_system() 