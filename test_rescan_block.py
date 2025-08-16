#!/usr/bin/env python3
"""
Test script to manually trigger a re-scan of a specific block
"""

import requests
import json
from decouple import config

def test_rescan_block():
    """Test re-scanning a specific block for transactions"""
    api_key = config('ALCHEMY_API_KEY', default='')
    if not api_key:
        print("❌ ALCHEMY_API_KEY not found")
        return
    
    url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
    
    # Test block 8935058 (where our transaction was mined)
    block_number = 8935058
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getBlockByNumber",
        "params": [hex(block_number), True],  # True to include full transaction objects
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if 'result' in result and result['result']:
            block_data = result['result']
            transactions = block_data.get("transactions", [])
            
            print(f"🔍 Re-scanning block {block_number}")
            print(f"   Found {len(transactions)} transactions")
            
            # Our monitored addresses
            monitored_addresses = [
                "0x54c8F97598Ea64C6cC48832AA8EA712d24bb481f",
                "0x153fEEe2FD50018f2d9DD643174F7C244aA77C95"
            ]
            monitored_addresses_lower = {addr.lower() for addr in monitored_addresses}
            
            found_transactions = 0
            for tx_data in transactions:
                from_address = tx_data.get("from", "").lower() if tx_data.get("from") else ""
                to_address = tx_data.get("to", "").lower() if tx_data.get("to") else ""
                
                if (from_address in monitored_addresses_lower or 
                    to_address in monitored_addresses_lower):
                    
                    tx_hash = tx_data.get("hash")
                    value = int(tx_data.get("value", "0"), 16)
                    value_eth = value / (10**18)
                    
                    print(f"💰 Relevant transaction found:")
                    print(f"   Hash: {tx_hash}")
                    print(f"   From: {from_address}")
                    print(f"   To: {to_address}")
                    print(f"   Value: {value_eth} ETH")
                    print(f"   Is incoming: {to_address in monitored_addresses_lower}")
                    print(f"   Is outgoing: {from_address in monitored_addresses_lower}")
                    print()
                    
                    found_transactions += 1
            
            print(f"✅ Found {found_transactions} relevant transactions in block {block_number}")
            
            if found_transactions == 0:
                print("❌ No relevant transactions found")
                
        else:
            print(f"❌ No block data returned for block {block_number}")
            
    except Exception as e:
        print(f"❌ Error re-scanning block: {e}")

if __name__ == "__main__":
    print("Testing Block Re-scan")
    print("=" * 30)
    test_rescan_block() 