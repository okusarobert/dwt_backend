#!/usr/bin/env python3
"""
Test script to manually check a specific block for transactions
"""

import requests
import json
from decouple import config

def test_manual_block_check():
    """Manually test the eth_monitor's block checking functionality"""
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
            
            print(f"✅ Block {block_number} fetched successfully")
            print(f"   Transactions in block: {len(transactions)}")
            
            # Look for our specific transaction
            target_tx = "0xf7f728234765d60f757cd6084419da7fc28ad3410272a937af2bc5c3c1192aac"
            found = False
            
            for tx in transactions:
                if tx.get("hash") == target_tx:
                    found = True
                    print(f"✅ Found our transaction in block!")
                    print(f"   From: {tx.get('from', 'N/A')}")
                    print(f"   To: {tx.get('to', 'N/A')}")
                    print(f"   Value: {int(tx.get('value', '0'), 16)} wei")
                    break
            
            if not found:
                print(f"❌ Transaction {target_tx} not found in block {block_number}")
                print("   This explains why eth_monitor didn't detect it")
                
            # Test the eth_monitor's logic
            print(f"\n🧪 Testing eth_monitor logic:")
            monitored_addresses = [
                "0x54c8F97598Ea64C6cC48832AA8EA712d24bb481f",
                "0x153fEEe2FD50018f2d9DD643174F7C244aA77C95"
            ]
            monitored_addresses_lower = [addr.lower() for addr in monitored_addresses]
            
            relevant_transactions = []
            for tx in transactions:
                from_address = tx.get("from", "").lower() if tx.get("from") else ""
                to_address = tx.get("to", "").lower() if tx.get("to") else ""
                
                if (from_address in monitored_addresses_lower or 
                    to_address in monitored_addresses_lower):
                    relevant_transactions.append(tx)
                    print(f"   Found relevant transaction: {tx.get('hash')}")
                    print(f"     From: {tx.get('from', 'N/A')}")
                    print(f"     To: {tx.get('to', 'N/A')}")
                    print(f"     Value: {int(tx.get('value', '0'), 16)} wei")
            
            print(f"\n📊 Summary:")
            print(f"   Total transactions in block: {len(transactions)}")
            print(f"   Relevant transactions found: {len(relevant_transactions)}")
            print(f"   Our transaction should be in relevant transactions: {target_tx in [tx.get('hash') for tx in relevant_transactions]}")
                
        else:
            print(f"❌ Failed to fetch block {block_number}")
            print(f"   Response: {result}")
            
    except Exception as e:
        print(f"❌ Error fetching block: {e}")

if __name__ == "__main__":
    print("Testing Manual Block Check")
    print("=" * 50)
    test_manual_block_check() 