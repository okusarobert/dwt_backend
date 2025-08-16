#!/usr/bin/env python3
"""
Simple script to check transaction status on the blockchain
"""

import requests
import json
from decouple import config

def check_transaction_status(tx_hash):
    """Check transaction status using Alchemy API"""
    api_key = config('ALCHEMY_API_KEY', default='')
    if not api_key:
        print("❌ ALCHEMY_API_KEY not found")
        return None
    
    url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
    
    # Get transaction receipt
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionReceipt",
        "params": [tx_hash],
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if 'result' in result and result['result']:
            receipt = result['result']
            block_number = int(receipt['blockNumber'], 16)
            status = int(receipt['status'], 16)
            
            print(f"✅ Transaction {tx_hash}")
            print(f"   Block Number: {block_number}")
            print(f"   Status: {'Success' if status == 1 else 'Failed'}")
            print(f"   Gas Used: {int(receipt['gasUsed'], 16)}")
            return {
                'block_number': block_number,
                'status': status,
                'gas_used': int(receipt['gasUsed'], 16)
            }
        else:
            print(f"❌ Transaction {tx_hash} not found on blockchain")
            return None
            
    except Exception as e:
        print(f"❌ Error checking transaction {tx_hash}: {e}")
        return None

def main():
    print("Checking Transaction Status on Blockchain")
    print("=" * 50)
    
    # Check our withdrawal transactions
    tx_hashes = [
        "0x630bca026fffcbc9b4df330aa0f0ddeee6727080df33bbdfe8e5f5ee539350ed",
        "0x6613fc49877c63c1580437b9959def3b487b7f4a4c47dc5a989954b5e338c484"
    ]
    
    results = []
    for tx_hash in tx_hashes:
        result = check_transaction_status(tx_hash)
        if result:
            results.append((tx_hash, result))
    
    print(f"\n📊 Summary: {len(results)}/{len(tx_hashes)} transactions found on blockchain")
    
    if results:
        print("\nTransactions found:")
        for tx_hash, result in results:
            print(f"  {tx_hash}: Block {result['block_number']}, Status: {'Success' if result['status'] == 1 else 'Failed'}")

if __name__ == "__main__":
    main() 