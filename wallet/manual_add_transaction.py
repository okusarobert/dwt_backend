#!/usr/bin/env python3
"""
Manually add the missing transaction to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionType, CryptoAddress
from decimal import Decimal
import json

def manual_add_transaction():
    """Manually add the missing transaction to the database"""
    session = get_session()
    
    try:
        # Transaction details
        tx_hash = "0xf7f728234765d60f757cd6084419da7fc28ad3410272a937af2bc5c3c1192aac"
        from_address = "0x54c8f97598ea64c6cc48832aa8ea712d24bb481f"
        to_address = "0x153feee2fd50018f2d9dd643174f7c244aa77c95"
        value_wei = 1000000000000000  # 0.001 ETH
        block_number = 8935058
        
        # Check if transaction already exists
        existing_tx = session.query(Transaction).filter_by(blockchain_txid=tx_hash).first()
        if existing_tx:
            print(f"✅ Transaction {tx_hash} already exists in database")
            print(f"   Reference: {existing_tx.reference_id}")
            print(f"   Type: {existing_tx.type}")
            print(f"   Status: {existing_tx.status}")
            return
        
        # Get the crypto address for the destination
        crypto_address = session.query(CryptoAddress).filter_by(address=to_address).first()
        if not crypto_address:
            print(f"❌ Crypto address {to_address} not found in database")
            return
        
        # Create the transaction record
        transaction = Transaction(
            reference_id=f"manual_{tx_hash[:8]}",
            type=TransactionType.DEPOSIT,
            currency="ETH",
            amount=Decimal("0.001"),
            address=to_address,
            blockchain_txid=tx_hash,
            provider_reference=tx_hash,
            status="confirmed",
            metadata_json={
                "block_number": block_number,
                "from_address": from_address,
                "to_address": to_address,
                "value_wei": value_wei,
                "gas_price": 20000000000,  # 20 gwei
                "gas_used": 21000,
                "manual_add": True
            }
        )
        
        session.add(transaction)
        session.commit()
        
        print(f"✅ Successfully added transaction {tx_hash}")
        print(f"   Reference: {transaction.reference_id}")
        print(f"   Type: {transaction.type}")
        print(f"   Amount: {transaction.amount} ETH")
        print(f"   Address: {transaction.address}")
        print(f"   Block: {block_number}")
        
        # Update account balance
        account = crypto_address.account
        if account:
            # Convert wei to ETH for balance update
            eth_amount = Decimal(value_wei) / Decimal(10**18)
            account.crypto_balance_smallest_unit += value_wei
            session.commit()
            
            print(f"✅ Updated account balance")
            print(f"   Account: {account.id}")
            print(f"   New balance: {account.crypto_balance_smallest_unit} wei")
            print(f"   New balance: {Decimal(account.crypto_balance_smallest_unit) / Decimal(10**18)} ETH")
        
    except Exception as e:
        print(f"❌ Error adding transaction: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Manually Adding Missing Transaction")
    print("=" * 50)
    manual_add_transaction() 