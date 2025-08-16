#!/usr/bin/env python3
"""
Test script to verify block fetching from Alchemy API
"""

import requests
import json
from decouple import config

def test_get_block_with_transactions():
    """Test fetching a block with transactions from Alchemy API"""
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
                print("   This might explain why eth_monitor didn't detect it")
                
        else:
            print(f"❌ Failed to fetch block {block_number}")
            print(f"   Response: {result}")
            
    except Exception as e:
        print(f"❌ Error fetching block: {e}")

if __name__ == "__main__":
    print("Testing Block Fetching from Alchemy API")
    print("=" * 50)
    test_get_block_with_transactions() 