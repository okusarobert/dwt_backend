#!/usr/bin/env python3
"""
Check for recent transactions to a specific address
"""

import requests
import json
from decouple import config

def check_transactions_to_address(address):
    """Check for recent transactions to a specific address"""
    api_key = config('ALCHEMY_API_KEY', default='')
    if not api_key:
        print("❌ ALCHEMY_API_KEY not found")
        return
    
    url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
    
    # Get recent transactions for the address (broader range)
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getLogs",
        "params": [{
            "fromBlock": "0x880000",  # Broader range
            "toBlock": "latest",
            "address": address,
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
            print(f"✅ Found {len(result['result'])} recent transactions to {address}")
            for i, log in enumerate(result['result'][:10]):  # Show first 10
                block_num = int(log['blockNumber'], 16)
                tx_hash = log['transactionHash']
                print(f"   {i+1}. Block {block_num}: {tx_hash}")
                
                # Get transaction details
                tx_payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionByHash",
                    "params": [tx_hash],
                    "id": 1
                }
                
                tx_response = requests.post(url, json=tx_payload)
                tx_result = tx_response.json()
                
                if 'result' in tx_result and tx_result['result']:
                    tx = tx_result['result']
                    from_addr = tx['from']
                    to_addr = tx['to']
                    value_wei = int(tx['value'], 16)
                    value_eth = value_wei / 10**18
                    
                    print(f"      From: {from_addr}")
                    print(f"      To: {to_addr}")
                    print(f"      Value: {value_eth} ETH")
                    print(f"      Block: {block_num}")
                    print()
        else:
            print(f"❌ No recent transactions found to {address}")
            
    except Exception as e:
        print(f"❌ Error checking transactions: {e}")

def check_specific_transaction(tx_hash):
    """Check a specific transaction by hash"""
    api_key = config('ALCHEMY_API_KEY', default='')
    if not api_key:
        print("❌ ALCHEMY_API_KEY not found")
        return
    
    url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
    
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionByHash",
        "params": [tx_hash],
        "id": 1
    }
    
    try:
        response = requests.post(url, json=payload)
        result = response.json()
        
        if 'result' in result and result['result']:
            tx = result['result']
            from_addr = tx['from']
            to_addr = tx['to']
            value_wei = int(tx['value'], 16)
            value_eth = value_wei / 10**18
            block_num = int(tx['blockNumber'], 16) if tx['blockNumber'] else None
            
            print(f"✅ Transaction {tx_hash} found:")
            print(f"   From: {from_addr}")
            print(f"   To: {to_addr}")
            print(f"   Value: {value_eth} ETH")
            print(f"   Block: {block_num}")
            print(f"   Status: {'Confirmed' if block_num else 'Pending'}")
        else:
            print(f"❌ Transaction {tx_hash} not found")
            
    except Exception as e:
        print(f"❌ Error checking transaction: {e}")

def main():
    print("Checking Recent Transactions")
    print("=" * 50)
    
    # Check transactions to the address you sent to
    address = "0x153fEEe2FD50018f2d9DD643174F7C244aA77C95"
    print(f"Checking transactions to: {address}")
    check_transactions_to_address(address)
    
    print("\n" + "=" * 50)
    print("If you have a transaction hash, enter it below:")
    print("(Press Enter to skip)")
    
    tx_hash = input("Transaction hash: ").strip()
    if tx_hash:
        print(f"\nChecking specific transaction: {tx_hash}")
        check_specific_transaction(tx_hash)
    
    print(f"\n📋 To check if the transaction was detected:")
    print(f"   1. Check eth_monitor logs: docker logs eth-monitor --tail 20")
    print(f"   2. Check database: docker exec -it dwt_backend-wallet-1 python -c \"from db.connection import get_session; from db.wallet import Transaction, TransactionType; session = get_session(); txs = session.query(Transaction).filter(Transaction.type == TransactionType.DEPOSIT).order_by(Transaction.created_at.desc()).limit(5).all(); [print(f'{{tx.reference_id}}: {{tx.amount}} -> {{tx.address}}') for tx in txs]\"")

if __name__ == "__main__":
    main() 