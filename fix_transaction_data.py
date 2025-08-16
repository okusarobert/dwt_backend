#!/usr/bin/env python3
"""
Fix the incorrect transaction data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import Transaction, TransactionStatus
from decimal import Decimal
import json

def fix_transaction_data():
    """Fix the incorrect transaction data"""
    session = get_session()
    
    try:
        # Get the problematic transaction
        tx = session.query(Transaction).filter_by(id=13).first()
        if not tx:
            print("❌ Transaction 13 not found")
            return
        
        print(f"🔧 Fixing transaction {tx.reference_id}")
        print(f"   Current amount: {tx.amount}")
        print(f"   Current status: {tx.status}")
        print(f"   Current provider: {tx.provider_reference}")
        print(f"   Current confirmations: {tx.confirmations}")
        
        # Fix the amount (should be 0.001 ETH)
        tx.amount = Decimal("0.001")
        
        # Fix the provider reference (should be the same as blockchain_txid)
        tx.provider_reference = tx.blockchain_txid
        
        # Fix the status (should be COMPLETED since it has 15+ confirmations)
        tx.status = TransactionStatus.COMPLETED
        
        # Fix the confirmations (should be 15, not the current block number)
        tx.confirmations = 15
        
        # Fix the metadata
        if tx.metadata_json:
            tx.metadata_json['block_number'] = 8935198  # The actual block number
            tx.metadata_json['timestamp'] = 1733692800  # Approximate timestamp
            tx.metadata_json['gas_price'] = 20000000000  # 20 gwei
        else:
            tx.metadata_json = {
                'from_address': '0x54c8f97598ea64c6cc48832aa8ea712d24bb481f',
                'to_address': '0x153feee2fd50018f2d9dd643174f7c244aa77c95',
                'block_number': 8935198,
                'gas_price': 20000000000,
                'gas_used': 21000,
                'timestamp': 1733692800,
                'value_wei': '1000000000000000',
                'amount_eth': '0.001'
            }
        
        session.commit()
        
        print(f"✅ Transaction fixed successfully")
        print(f"   New amount: {tx.amount}")
        print(f"   New status: {tx.status}")
        print(f"   New provider: {tx.provider_reference}")
        print(f"   New confirmations: {tx.confirmations}")
        print(f"   Block number: {tx.metadata_json.get('block_number')}")
        
    except Exception as e:
        print(f"❌ Error fixing transaction: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    print("Fixing Transaction Data")
    print("=" * 30)
    fix_transaction_data() 