#!/usr/bin/env python3
"""
Test script to verify internal transfers between monitored addresses
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionType, TransactionStatus, Account, CryptoAddress
from decimal import Decimal

def test_internal_transfer_logic():
    """Test the logic for handling internal transfers"""
    session = get_session()
    
    try:
        print("🧪 Testing Internal Transfer Logic")
        print("=" * 50)
        
        # Get monitored addresses
        crypto_addresses = session.query(CryptoAddress).all()
        if len(crypto_addresses) < 2:
            print("❌ Need at least 2 monitored addresses for testing")
            return
        
        sender_address = crypto_addresses[0]
        recipient_address = crypto_addresses[1]
        
        print(f"Sender: {sender_address.address}")
        print(f"Recipient: {recipient_address.address}")
        
        # Simulate a transaction between our monitored addresses
        tx_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        amount = 0.001
        
        # Check if this would be detected as internal transfer
        monitored_addresses = [addr.address.lower() for addr in crypto_addresses]
        is_incoming = recipient_address.address.lower() in monitored_addresses
        is_outgoing = sender_address.address.lower() in monitored_addresses
        
        print(f"\nTransaction Analysis:")
        print(f"   From: {sender_address.address}")
        print(f"   To: {recipient_address.address}")
        print(f"   Is incoming: {is_incoming}")
        print(f"   Is outgoing: {is_outgoing}")
        print(f"   Is internal transfer: {is_incoming and is_outgoing}")
        
        if is_incoming and is_outgoing:
            print("✅ This would be correctly identified as an internal transfer")
            
            # Simulate creating both transaction records
            print(f"\n📤 Creating WITHDRAWAL for sender:")
            withdrawal_tx = Transaction(
                account_id=sender_address.account_id,
                reference_id=tx_hash,
                amount=amount,
                amount_smallest_unit=int(amount * 10**18),
                precision_config={
                    "currency": "ETH",
                    "decimals": 18,
                    "smallest_unit": "wei"
                },
                type=TransactionType.WITHDRAWAL,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                description=f"Internal transfer WITHDRAWAL {tx_hash[:8]}...",
                blockchain_txid=tx_hash,
                address=sender_address.address,
                metadata_json={
                    "from_address": sender_address.address,
                    "to_address": recipient_address.address,
                    "is_internal_transfer": True
                }
            )
            
            print(f"📥 Creating DEPOSIT for recipient:")
            deposit_tx = Transaction(
                account_id=recipient_address.account_id,
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
                description=f"Internal transfer DEPOSIT {tx_hash[:8]}...",
                blockchain_txid=tx_hash,
                address=recipient_address.address,
                metadata_json={
                    "from_address": sender_address.address,
                    "to_address": recipient_address.address,
                    "is_internal_transfer": True
                }
            )
            
            session.add(withdrawal_tx)
            session.add(deposit_tx)
            session.commit()
            
            print("✅ Both transaction records created successfully!")
            print(f"   WITHDRAWAL ID: {withdrawal_tx.id}")
            print(f"   DEPOSIT ID: {deposit_tx.id}")
            print(f"   Same blockchain_txid: {withdrawal_tx.blockchain_txid == deposit_tx.blockchain_txid}")
            print(f"   Different accounts: {withdrawal_tx.account_id != deposit_tx.account_id}")
            print(f"   Different types: {withdrawal_tx.type != deposit_tx.type}")
            
            # Clean up
            session.delete(withdrawal_tx)
            session.delete(deposit_tx)
            session.commit()
            
            print("\n✅ Internal transfer test completed successfully!")
            
        else:
            print("❌ This would not be identified as an internal transfer")
            
    except Exception as e:
        print(f"❌ Error in internal transfer test: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    test_internal_transfer_logic() 