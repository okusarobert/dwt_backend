#!/usr/bin/env python3
"""
Check a specific transaction on the blockchain
"""

import requests
import json
from decouple import config

def check_specific_transaction(tx_hash):
    """Check a specific transaction using Alchemy API"""
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
    print("Checking Specific Transaction")
    print("=" * 50)
    
    # Check the transaction you sent
    tx_hash = "0xf7f728234765d60f757cd6084419da7fc28ad3410272a937af2bc5c3c1192aac"
    
    result = check_specific_transaction(tx_hash)
    
    if result:
        print(f"\n📊 Transaction Details:")
        print(f"   Block: {result['block_number']}")
        print(f"   Status: {'Success' if result['status'] == 1 else 'Failed'}")
        print(f"   Gas Used: {result['gas_used']}")

if __name__ == "__main__":
    main() 