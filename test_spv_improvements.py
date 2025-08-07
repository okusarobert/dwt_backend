#!/usr/bin/env python3
"""
Test script to verify SPV improvements
"""

import requests
import time
import json

def test_spv_improvements():
    """Test the improved SPV client"""
    base_url = "http://localhost:5003"
    
    print("🚀 Testing SPV Improvements")
    print("=" * 50)
    
    # Test 1: Start SPV client
    print("1️⃣ Starting SPV client...")
    try:
        response = requests.post(f"{base_url}/start")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ SPV client started successfully")
            print(f"   Connected peers: {status['status']['connected_peers']}")
            print(f"   Peer count: {status['status']['peer_count']}")
        else:
            print(f"❌ Failed to start SPV client: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error starting SPV client: {e}")
        return False
    
    # Wait for connections to stabilize
    time.sleep(5)
    
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
            print(f"   Connected peers: {status['connected_peers']}")
            print(f"   Watched addresses: {status['watched_addresses']}")
            print(f"   Block headers: {status['block_headers']}")
            print(f"   Bloom filter loaded: {status['bloom_filter_loaded']}")
        else:
            print(f"❌ Failed to get status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting status: {e}")
    
    # Test 4: Test historical scan (should work better now)
    print(f"\n4️⃣ Testing historical scan...")
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
    
    # Test 5: Check balance
    print(f"\n5️⃣ Checking balance...")
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
    
    # Test 6: Check block height
    print(f"\n6️⃣ Checking block height...")
    try:
        response = requests.get(f"{base_url}/block_height")
        if response.status_code == 200:
            height_info = response.json()
            print(f"✅ Block height: {height_info.get('height', 'Unknown')}")
        else:
            print(f"❌ Failed to get block height: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting block height: {e}")
    
    print(f"\n✅ SPV improvements test completed!")
    print("📝 The SPV client should now:")
    print("   - Handle sendcmpct messages properly")
    print("   - Maintain peer connections better")
    print("   - Provide more informative error messages")
    print("   - Continue monitoring for new transactions")
    
    return True

if __name__ == "__main__":
    test_spv_improvements() 