#!/usr/bin/env python3
"""
Test script for the Simple SPV implementation using bitcoinlib
"""

import requests
import time
import json

def test_simple_spv():
    """Test the simple SPV client using bitcoinlib"""
    base_url = "http://localhost:5004"
    
    print("🚀 Testing Simple SPV Implementation (bitcoinlib)")
    print("=" * 60)
    
    # Test 1: Start SPV client
    print("1️⃣ Starting Simple SPV client...")
    try:
        response = requests.post(f"{base_url}/start")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Simple SPV client started successfully")
            print(f"   Status: {status['status']}")
        else:
            print(f"❌ Failed to start SPV client: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error starting SPV client: {e}")
        return False
    
    # Wait a moment
    time.sleep(2)
    
    # Test 2: Add test address
    test_address = "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T"
    print(f"\n2️⃣ Adding test address: {test_address}")
    try:
        response = requests.post(f"{base_url}/add_address", 
                               json={"address": test_address})
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Address added: {result['message']}")
        else:
            print(f"❌ Failed to add address: {response.status_code}")
    except Exception as e:
        print(f"❌ Error adding address: {e}")
    
    # Test 3: Check status
    print(f"\n3️⃣ Checking SPV status...")
    try:
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Status retrieved:")
            print(f"   Running: {status['is_running']}")
            print(f"   Watched addresses: {status['watched_addresses']}")
            print(f"   Address count: {status['address_count']}")
            print(f"   Total UTXOs: {status['total_utxos']}")
            print(f"   Transactions: {status['transactions']}")
            print(f"   Testnet: {status['testnet']}")
        else:
            print(f"❌ Failed to get status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting status: {e}")
    
    # Test 4: Get balance
    print(f"\n4️⃣ Getting balance for {test_address}...")
    try:
        response = requests.get(f"{base_url}/balance/{test_address}")
        if response.status_code == 200:
            balance = response.json()
            print(f"✅ Balance retrieved:")
            print(f"   Address: {balance['address']}")
            print(f"   Confirmed: {balance['confirmed_balance_btc']} BTC")
            print(f"   Unconfirmed: {balance['unconfirmed_balance_btc']} BTC")
            print(f"   UTXO count: {balance['utxo_count']}")
        else:
            print(f"❌ Failed to get balance: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting balance: {e}")
    
    # Test 5: Get UTXOs
    print(f"\n5️⃣ Getting UTXOs for {test_address}...")
    try:
        response = requests.get(f"{base_url}/utxos/{test_address}")
        if response.status_code == 200:
            utxos_data = response.json()
            print(f"✅ UTXOs retrieved:")
            print(f"   Address: {utxos_data['address']}")
            print(f"   Count: {utxos_data['count']}")
            for i, utxo in enumerate(utxos_data['utxos'][:3]):  # Show first 3
                print(f"   UTXO {i+1}: {utxo['value_btc']} BTC (confirmed: {utxo['confirmed']})")
        else:
            print(f"❌ Failed to get UTXOs: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting UTXOs: {e}")
    
    # Test 6: Get transactions
    print(f"\n6️⃣ Getting transactions for {test_address}...")
    try:
        response = requests.get(f"{base_url}/transactions/{test_address}")
        if response.status_code == 200:
            txs_data = response.json()
            print(f"✅ Transactions retrieved:")
            print(f"   Address: {txs_data['address']}")
            print(f"   Count: {txs_data['count']}")
        else:
            print(f"❌ Failed to get transactions: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting transactions: {e}")
    
    # Test 7: Test historical scan
    print(f"\n7️⃣ Testing historical scan...")
    try:
        response = requests.post(f"{base_url}/scan_history/{test_address}", 
                               json={"blocks_back": 20})
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Historical scan initiated: {result['message']}")
            print(f"   Blocks back: {result['blocks_back']}")
        else:
            print(f"❌ Failed to start historical scan: {response.status_code}")
    except Exception as e:
        print(f"❌ Error starting historical scan: {e}")
    
    # Test 8: Get block height
    print(f"\n8️⃣ Getting block height...")
    try:
        response = requests.get(f"{base_url}/block_height")
        if response.status_code == 200:
            height_info = response.json()
            print(f"✅ Block height: {height_info.get('height', 'Unknown')}")
            print(f"   Network: {height_info.get('network', 'Unknown')}")
        else:
            print(f"❌ Failed to get block height: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting block height: {e}")
    
    print(f"\n✅ Simple SPV test completed!")
    print("📝 Advantages of this approach:")
    print("   - Uses mature, well-tested bitcoinlib library")
    print("   - Handles all Bitcoin protocol details automatically")
    print("   - Much simpler and more reliable code")
    print("   - Better error handling and edge cases")
    print("   - No need to manage peer connections manually")
    print("   - Automatic handling of network issues")
    
    return True

if __name__ == "__main__":
    test_simple_spv() 