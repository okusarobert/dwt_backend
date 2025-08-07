#!/usr/bin/env python3
"""
Test script to demonstrate enhanced SPV logging
"""

import requests
import time
import json

def test_spv_logging():
    """Test the SPV client with detailed logging"""
    
    base_url = "http://localhost:5003"
    
    print("🚀 Starting SPV Transaction Scanning Test")
    print("=" * 50)
    
    # 1. Start SPV client
    print("\n1️⃣ Starting SPV client...")
    response = requests.post(f"{base_url}/start")
    if response.status_code == 200:
        status = response.json()
        print(f"   ✅ SPV client started")
        print(f"   🔗 Connected peers: {status['status']['connected_peers']}")
        print(f"   📊 Peer count: {status['status']['peer_count']}")
    else:
        print(f"   ❌ Failed to start SPV client: {response.text}")
        return
    
    # Wait for peer connections
    time.sleep(3)
    
    # 2. Add address to watch
    print("\n2️⃣ Adding address to watch list...")
    address = "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T"
    response = requests.post(f"{base_url}/add_address", 
                           json={"address": address})
    if response.status_code == 200:
        print(f"   ✅ Added address: {address}")
    else:
        print(f"   ❌ Failed to add address: {response.text}")
        return
    
    # 3. Get initial balance
    print("\n3️⃣ Getting initial balance...")
    response = requests.get(f"{base_url}/balance/{address}")
    if response.status_code == 200:
        balance = response.json()
        print(f"   💰 Balance: {balance['confirmed_balance_btc']} BTC")
        print(f"   📊 UTXO count: {balance['utxo_count']}")
    else:
        print(f"   ❌ Failed to get balance: {response.text}")
    
    # 4. Scan historical blocks
    print("\n4️⃣ Scanning historical blocks...")
    print("   🔍 This will show detailed logging of the scanning process")
    print("   📦 Looking for transactions in recent blocks")
    
    response = requests.post(f"{base_url}/scan_history/{address}", 
                           json={"blocks_back": 20})
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Scan started: {result['message']}")
        print(f"   📊 Scanning {result['blocks_back']} blocks")
    else:
        print(f"   ❌ Failed to start scan: {response.text}")
    
    # 5. Wait and check results
    print("\n5️⃣ Waiting for scan results...")
    time.sleep(5)
    
    # 6. Get final balance and transactions
    print("\n6️⃣ Getting final results...")
    
    # Balance
    response = requests.get(f"{base_url}/balance/{address}")
    if response.status_code == 200:
        balance = response.json()
        print(f"   💰 Final balance: {balance['confirmed_balance_btc']} BTC")
        print(f"   📊 Final UTXO count: {balance['utxo_count']}")
    
    # Transactions
    response = requests.get(f"{base_url}/transactions/{address}")
    if response.status_code == 200:
        transactions = response.json()
        print(f"   📋 Found {transactions['count']} transactions")
        if transactions['count'] > 0:
            for tx in transactions['transactions']:
                print(f"      💸 TX: {tx['txid'][:16]}...")
                print(f"         💰 Value: {sum(out['value_btc'] for out in tx['outputs'])} BTC")
    
    # UTXOs
    response = requests.get(f"{base_url}/utxos/{address}")
    if response.status_code == 200:
        utxos = response.json()
        print(f"   🪙 Found {utxos['count']} UTXOs")
        for utxo in utxos['utxos']:
            print(f"      💰 UTXO: {utxo['value_btc']} BTC")
    
    print("\n✅ Test completed!")
    print("\n📝 What you should see in the server logs:")
    print("   🔍 Detailed scanning process")
    print("   📦 Block processing information")
    print("   💸 Transaction parsing details")
    print("   🎯 Address matching results")
    print("   📊 Inventory processing")
    print("   📡 Network communication")

if __name__ == "__main__":
    test_spv_logging() 