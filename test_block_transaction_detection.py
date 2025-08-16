#!/usr/bin/env python3
"""
Test script to check if our transaction would be detected in block data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db.connection import get_session
from db.wallet import CryptoAddress
from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from decimal import Decimal
import requests
import json

def test_block_transaction_detection():
    """Test if our transaction would be detected in block data"""
    
    # Our transaction details
    tx_hash = "0x37cc5af0fa25e1fc834992ac2cf04f57780faf41e2fe3cf58826f447182b38ed"
    from_address = "0x54c8F97598Ea64C6cC48832AA8EA712d24bb481f"
    to_address = "0x153fEEe2FD50018f2d9DD643174F7C244aA77C95"
    block_number = 8932957
    
    print("🔍 Testing Block Transaction Detection")
    print("=" * 50)
    
    # Get block data from Alchemy
    api_key = "EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Using actual API key
    url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBlockByNumber",
        "params": [hex(block_number), True],  # True to include full transaction objects
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and data['result']:
                block_data = data['result']
                transactions = block_data.get('transactions', [])
                
                print(f"📦 Block {block_number} contains {len(transactions)} transactions")
                
                # Check if our transaction is in this block
                our_tx_found = False
                for tx in transactions:
                    if tx.get('hash') == tx_hash:
                        our_tx_found = True
                        print(f"✅ Our transaction found in block!")
                        print(f"   Hash: {tx.get('hash')}")
                        print(f"   From: {tx.get('from')}")
                        print(f"   To: {tx.get('to')}")
                        print(f"   Value: {int(tx.get('value', '0'), 16)} wei")
                        break
                
                if not our_tx_found:
                    print(f"❌ Our transaction NOT found in block {block_number}")
                
                # Simulate eth_monitor's block checking logic
                monitored_addresses = [
                    "0x54c8F97598Ea64C6cC48832AA8EA712d24bb481f",
                    "0x153fEEe2FD50018f2d9DD643174F7C244aA77C95"
                ]
                monitored_addresses_lower = {addr.lower() for addr in monitored_addresses}
                
                detected_transactions = []
                for tx in transactions:
                    from_addr = tx.get('from', '').lower()
                    to_addr = tx.get('to', '').lower()
                    
                    if (from_addr in monitored_addresses_lower or 
                        to_addr in monitored_addresses_lower):
                        detected_transactions.append(tx)
                
                print(f"\n💰 Transactions detected by eth_monitor: {len(detected_transactions)}")
                for tx in detected_transactions:
                    print(f"   - {tx.get('hash')} (From: {tx.get('from')}, To: {tx.get('to')})")
                
            else:
                print(f"❌ No block data returned for block {block_number}")
        else:
            print(f"❌ Error getting block data: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_block_transaction_detection() 