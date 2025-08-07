#!/usr/bin/env python3
"""
Demonstration of Enhanced SPV Logging
"""

import requests
import time
import json

def demo_spv_logging():
    """Demonstrate the enhanced SPV logging"""
    
    base_url = "http://localhost:5003"
    
    print("🔍 SPV Transaction Scanning with Enhanced Logging")
    print("=" * 60)
    
    # 1. Check current status
    print("\n1️⃣ Checking current SPV status...")
    try:
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ SPV client running: {status['is_running']}")
            print(f"   🔗 Connected peers: {status['connected_peers']}")
            print(f"   📊 Peer count: {status['peer_count']}")
            print(f"   👀 Watched addresses: {status['watched_addresses']}")
        else:
            print(f"   ❌ Failed to get status: {response.text}")
            return
    except Exception as e:
        print(f"   ❌ Error connecting to SPV server: {e}")
        return
    
    # 2. Start SPV client if not running
    print("\n2️⃣ Starting SPV client...")
    try:
        response = requests.post(f"{base_url}/start")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ {result['message']}")
            print(f"   🔗 Peers: {result['status']['connected_peers']}")
        else:
            print(f"   ℹ️ SPV client already running")
    except Exception as e:
        print(f"   ❌ Error starting SPV client: {e}")
    
    # Wait for peer connections
    time.sleep(5)
    
    # 3. Add test address
    print("\n3️⃣ Adding test address...")
    address = "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T"
    try:
        response = requests.post(f"{base_url}/add_address", 
                               json={"address": address})
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ {result['message']}")
        else:
            print(f"   ❌ Failed to add address: {response.text}")
    except Exception as e:
        print(f"   ❌ Error adding address: {e}")
    
    # 4. Get initial balance
    print("\n4️⃣ Getting initial balance...")
    try:
        response = requests.get(f"{base_url}/balance/{address}")
        if response.status_code == 200:
            balance = response.json()
            print(f"   💰 Balance: {balance['confirmed_balance_btc']} BTC")
            print(f"   📊 UTXO count: {balance['utxo_count']}")
        else:
            print(f"   ❌ Failed to get balance: {response.text}")
    except Exception as e:
        print(f"   ❌ Error getting balance: {e}")
    
    # 5. Start historical scanning with detailed logging
    print("\n5️⃣ Starting historical scan with enhanced logging...")
    print("   🔍 This will show detailed logs of the scanning process")
    print("   📦 You should see logs like:")
    print("      - 🔍 Starting historical scan for address")
    print("      - 📊 Scanning last X blocks")
    print("      - 🔗 Connected peers")
    print("      - 📡 Requesting headers from peers")
    print("      - 📦 Processing inventory")
    print("      - 💸 Processing transactions")
    print("      - 🎯 Found transaction involving watched addresses")
    
    try:
        response = requests.post(f"{base_url}/scan_history/{address}", 
                               json={"blocks_back": 10})
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ {result['message']}")
            print(f"   📊 Scanning {result['blocks_back']} blocks")
            print(f"   🔄 Status: {result['status']}")
        else:
            print(f"   ❌ Failed to start scan: {response.text}")
    except Exception as e:
        print(f"   ❌ Error starting scan: {e}")
    
    # 6. Wait for scan to complete
    print("\n6️⃣ Waiting for scan to complete...")
    print("   ⏳ Check the server logs for detailed scanning information")
    time.sleep(10)
    
    # 7. Get final results
    print("\n7️⃣ Getting final results...")
    
    # Final balance
    try:
        response = requests.get(f"{base_url}/balance/{address}")
        if response.status_code == 200:
            balance = response.json()
            print(f"   💰 Final balance: {balance['confirmed_balance_btc']} BTC")
            print(f"   📊 Final UTXO count: {balance['utxo_count']}")
    except Exception as e:
        print(f"   ❌ Error getting final balance: {e}")
    
    # Transactions
    try:
        response = requests.get(f"{base_url}/transactions/{address}")
        if response.status_code == 200:
            transactions = response.json()
            print(f"   📋 Found {transactions['count']} transactions")
            if transactions['count'] > 0:
                for tx in transactions['transactions']:
                    print(f"      💸 TX: {tx['txid'][:16]}...")
                    total_value = sum(out['value_btc'] for out in tx['outputs'])
                    print(f"         💰 Total value: {total_value} BTC")
    except Exception as e:
        print(f"   ❌ Error getting transactions: {e}")
    
    # UTXOs
    try:
        response = requests.get(f"{base_url}/utxos/{address}")
        if response.status_code == 200:
            utxos = response.json()
            print(f"   🪙 Found {utxos['count']} UTXOs")
            for utxo in utxos['utxos']:
                print(f"      💰 UTXO: {utxo['value_btc']} BTC")
    except Exception as e:
        print(f"   ❌ Error getting UTXOs: {e}")
    
    print("\n✅ Demonstration completed!")
    print("\n📝 What you should see in the server logs:")
    print("   🔍 Detailed scanning process with emojis")
    print("   📦 Block processing information")
    print("   💸 Transaction parsing details")
    print("   🎯 Address matching results")
    print("   📊 Inventory processing")
    print("   📡 Network communication")
    print("   ⚠️ Peer connection handling")
    print("   🔄 Reconnection attempts")

if __name__ == "__main__":
    demo_spv_logging() 