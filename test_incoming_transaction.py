#!/usr/bin/env python3
"""
Test script to verify incoming transaction detection
"""

import requests
import json
from decouple import config

def send_test_transaction():
    """Send a small test transaction to our wallet address"""
    api_key = config('ALCHEMY_API_KEY', default='')
    if not api_key:
        print("❌ ALCHEMY_API_KEY not found")
        return None
    
    # Our wallet address to receive the test transaction
    to_address = "0x54c8F97598Ea64C6cC48832AA8EA712d24bb481f"
    
    # Use a faucet or test account to send a small amount
    print(f"🎯 Testing incoming transaction detection")
    print(f"   Sending to: {to_address}")
    print(f"   Amount: 0.001 ETH")
    print(f"")
    print(f"📝 To test incoming transaction detection:")
    print(f"   1. Send 0.001 ETH to {to_address}")
    print(f"   2. Check eth_monitor logs: docker logs eth-monitor --tail 20")
    print(f"   3. Check database for new DEPOSIT transaction")
    print(f"")
    print(f"🔍 You can use a faucet or send from another wallet")
    print(f"   Sepolia Faucet: https://sepoliafaucet.com/")
    print(f"   Alchemy Faucet: https://sepoliafaucet.com/")
    
    return to_address

def check_recent_transactions():
    """Check for recent transactions to our address"""
    api_key = config('ALCHEMY_API_KEY', default='')
    if not api_key:
        print("❌ ALCHEMY_API_KEY not found")
        return
    
    url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
    
    # Get recent transactions for our address
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{
            "fromBlock": "0x885000",  # Recent blocks
            "toBlock": "latest",
            "address": "0x54c8F97598Ea64C6cC48832AA8EA712d24bb481f",
            "topics": [
                "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # Transfer event
            ]
        }],
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if 'result' in result and result['result']:
            print(f"✅ Found {len(result['result'])} recent transactions to our address")
            for i, log in enumerate(result['result'][:3]):  # Show first 3
                print(f"   {i+1}. Block {int(log['blockNumber'], 16)}: {log['transactionHash']}")
        else:
            print("❌ No recent incoming transactions found")
            
    except Exception as e:
        print(f"❌ Error checking recent transactions: {e}")

def main():
    print("Testing Incoming Transaction Detection")
    print("=" * 50)
    
    # Show our wallet address for testing
    to_address = send_test_transaction()
    
    print("\n" + "=" * 50)
    print("Checking for recent incoming transactions...")
    check_recent_transactions()
    
    print(f"\n📋 Next steps:")
    print(f"   1. Send a test transaction to {to_address}")
    print(f"   2. Monitor eth_monitor logs: docker logs eth-monitor -f")
    print(f"   3. Check database: docker exec -it dwt_backend-wallet-1 python -c \"from db.connection import get_session; from db.wallet import Transaction, TransactionType; session = get_session(); txs = session.query(Transaction).filter(Transaction.type == TransactionType.DEPOSIT).order_by(Transaction.created_at.desc()).limit(5).all(); [print(f'{{tx.reference_id}}: {{tx.amount}} -> {{tx.address}}') for tx in txs]\"")

if __name__ == "__main__":
    main() 