#!/usr/bin/env python3
"""
Test script to check if eth_monitor would detect our transaction
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import CryptoAddress, Transaction, Account, TransactionType, TransactionStatus
from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from decimal import Decimal

def test_transaction_detection():
    """Test if our transaction would be detected by eth_monitor"""
    
    # Our transaction details
    tx_hash = "0x37cc5af0fa25e1fc834992ac2cf04f57780faf41e2fe3cf58826f447182b38ed"
    from_address = "0x54c8F97598Ea64C6cC48832AA8EA712d24bb481f"
    to_address = "0x153fEEe2FD50018f2d9DD643174F7C244aA77C95"
    value_wei = 1000000000000000  # 0.001 ETH
    
    print("🔍 Testing ETH Monitor Transaction Detection")
    print("=" * 50)
    
    # Check if addresses are monitored
    session = get_session()
    
    monitored_addresses = session.query(CryptoAddress).filter_by(
        currency_code="ETH",
        is_active=True
    ).all()
    
    print(f"📋 Monitored addresses: {len(monitored_addresses)}")
    for addr in monitored_addresses:
        print(f"   - {addr.address}")
    
    # Check if our addresses are in the monitored list
    from_addr_in_db = session.query(CryptoAddress).filter_by(
        address=from_address,
        currency_code="ETH",
        is_active=True
    ).first()
    
    to_addr_in_db = session.query(CryptoAddress).filter_by(
        address=to_address,
        currency_code="ETH",
        is_active=True
    ).first()
    
    print(f"\n✅ From address in DB: {from_addr_in_db is not None}")
    print(f"✅ To address in DB: {to_addr_in_db is not None}")
    
    # Simulate the transaction event that eth_monitor would process
    from dataclasses import dataclass
    from decimal import Decimal
    
    @dataclass
    class TransactionEvent:
        """Represents a new transaction event"""
        tx_hash: str
        from_address: str
        to_address: str
        value: Decimal
        block_number: int
        gas_price: int
        gas_used: int
        timestamp: int
        confirmations: int = 0
        status: str = "pending"
    
    event = TransactionEvent(
        tx_hash=tx_hash,
        from_address=from_address.lower(),
        to_address=to_address.lower(),
        value=Decimal(value_wei) / Decimal(10**18),
        block_number=8932957,  # From our transaction
        gas_price=7645694,
        gas_used=21000,
        timestamp=0
    )
    
    print(f"\n💰 Transaction Event:")
    print(f"   Hash: {event.tx_hash}")
    print(f"   From: {event.from_address}")
    print(f"   To: {event.to_address}")
    print(f"   Value: {event.value} ETH")
    print(f"   Block: {event.block_number}")
    
    # Check if this would be detected by eth_monitor
    monitored_addresses_lower = {addr.address.lower() for addr in monitored_addresses}
    
    if (event.from_address in monitored_addresses_lower or 
        event.to_address in monitored_addresses_lower):
        print(f"\n✅ Transaction WOULD be detected by eth_monitor!")
        print(f"   From address monitored: {event.from_address in monitored_addresses_lower}")
        print(f"   To address monitored: {event.to_address in monitored_addresses_lower}")
    else:
        print(f"\n❌ Transaction would NOT be detected by eth_monitor!")
        print(f"   Neither address is in monitored list")
    
    # Check if transaction is already in our database
    existing_tx = session.query(Transaction).filter_by(
        provider_reference=tx_hash
    ).first()
    
    print(f"\n📊 Database Status:")
    print(f"   Transaction in DB: {existing_tx is not None}")
    if existing_tx:
        print(f"   Status: {existing_tx.status}")
        print(f"   Type: {existing_tx.type}")
        print(f"   Amount: {existing_tx.amount}")
    
    session.close()

if __name__ == "__main__":
    test_transaction_detection() 