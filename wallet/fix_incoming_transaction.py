#!/usr/bin/env python3
"""
Manually add the missing incoming transaction record
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionType, TransactionStatus, CryptoAddress
from decimal import Decimal
import json

def fix_incoming_transaction():
    """Manually add the missing incoming transaction record"""
    session = get_session()
    
    try:
        # Transaction details
        tx_hash = "0xf7f728234765d60f757cd6084419da7fc28ad3410272a937af2bc5c3c1192aac"
        from_address = "0x54c8f97598ea64c6cc48832aa8ea712d24bb481f"
        to_address = "0x153fEEe2FD50018f2d9DD643174F7C244aA77C95"  # Fixed case
        value_wei = 1000000000000000  # 0.001 ETH
        block_number = 8935058
        
        # Check if incoming transaction already exists for the destination address
        existing_incoming_tx = session.query(Transaction).filter_by(
            blockchain_txid=tx_hash,
            address=to_address,
            type=TransactionType.DEPOSIT
        ).first()
        
        if existing_incoming_tx:
            print(f"✅ Incoming transaction {tx_hash} already exists for {to_address}")
            print(f"   Reference: {existing_incoming_tx.reference_id}")
            print(f"   Status: {existing_incoming_tx.status}")
            return
        
        # Get the crypto address for the destination
        crypto_address = session.query(CryptoAddress).filter_by(address=to_address).first()
        if not crypto_address:
            print(f"❌ Crypto address {to_address} not found in database")
            return
        
        # Create the incoming transaction record
        incoming_transaction = Transaction(
            account_id=crypto_address.account_id,
            reference_id=f"incoming_{tx_hash[:8]}",
            type=TransactionType.DEPOSIT,
            amount=Decimal("0.001"),
            address=to_address,
            blockchain_txid=tx_hash,
            provider_reference=tx_hash,
            status=TransactionStatus.COMPLETED,
            confirmations=15,
            required_confirmations=15,
            metadata_json={
                "block_number": block_number,
                "from_address": from_address,
                "to_address": to_address,
                "value_wei": value_wei,
                "gas_price": 20000000000,  # 20 gwei
                "gas_used": 21000,
                "manual_add": True,
                "transaction_type": "incoming"
            }
        )
        
        session.add(incoming_transaction)
        session.commit()
        
        print(f"✅ Successfully added incoming transaction {tx_hash}")
        print(f"   Reference: {incoming_transaction.reference_id}")
        print(f"   Type: {incoming_transaction.type}")
        print(f"   Amount: {incoming_transaction.amount} ETH")
        print(f"   Address: {incoming_transaction.address}")
        print(f"   Block: {block_number}")
        
        # Update account balance for the destination address
        account = crypto_address.account
        if account:
            account.crypto_balance_smallest_unit += value_wei
            session.commit()
            
            print(f"✅ Updated account balance")
            print(f"   Account: {account.id}")
            print(f"   New balance: {account.crypto_balance_smallest_unit} wei")
            print(f"   New balance: {Decimal(account.crypto_balance_smallest_unit) / Decimal(10**18)} ETH")
        
    except Exception as e:
        print(f"❌ Error adding incoming transaction: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Fixing Missing Incoming Transaction")
    print("=" * 40)
    fix_incoming_transaction() 