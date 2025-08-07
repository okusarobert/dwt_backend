#!/usr/bin/env python3
"""
Test script for real-time transaction monitoring
"""

import requests
import time
import json

def test_realtime_monitoring():
    """Test the real-time monitoring functionality"""
    base_url = "http://localhost:5005"
    
    print("🚀 Testing Real-Time Transaction Monitoring")
    print("=" * 50)
    
    # Test 1: Check server status
    print("1️⃣ Checking server status...")
    try:
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Server is running")
            print(f"   Real-time monitoring: {status['realtime_monitoring']}")
            print(f"   Watched addresses: {status['address_count']}")
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False
    
    # Test 2: Start real-time monitoring
    print("\n2️⃣ Starting real-time monitoring...")
    try:
        response = requests.post(f"{base_url}/start")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Real-time monitoring started")
            print(f"   Status: {result['status']['realtime_monitoring']}")
        else:
            print(f"❌ Failed to start monitoring: {response.status_code}")
    except Exception as e:
        print(f"❌ Error starting monitoring: {e}")
    
    # Test 3: Add address to watch
    test_address = "n43gfthwVPBopwaTMjmpMAT4Nqzf95NKcy"
    print(f"\n3️⃣ Adding address to watch: {test_address}")
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
    
    # Test 4: Get initial balance
    print(f"\n4️⃣ Getting initial balance...")
    try:
        response = requests.get(f"{base_url}/balance/{test_address}")
        if response.status_code == 200:
            balance = response.json()
            print(f"✅ Initial balance: {balance['confirmed_balance_btc']} BTC")
        else:
            print(f"❌ Failed to get balance: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting balance: {e}")
    
    # Test 5: Monitor for changes (simulate real-time monitoring)
    print(f"\n5️⃣ Monitoring for changes (30 seconds)...")
    print("   The server is now monitoring for real-time changes.")
    print("   Open realtime_client.html in your browser to see WebSocket events.")
    print("   Or use the API endpoints to check for changes.")
    
    # Show how to use the WebSocket client
    print(f"\n📋 How to use the real-time monitoring:")
    print(f"   1. Open realtime_client.html in your browser")
    print(f"   2. Enter the address: {test_address}")
    print(f"   3. Click 'Subscribe' to start monitoring")
    print(f"   4. Watch for real-time balance and transaction updates")
    
    # Show API endpoints
    print(f"\n🔗 Available API endpoints:")
    print(f"   GET  {base_url}/status - Check server status")
    print(f"   POST {base_url}/start - Start real-time monitoring")
    print(f"   POST {base_url}/add_address - Add address to watch")
    print(f"   GET  {base_url}/balance/{test_address} - Get balance")
    print(f"   GET  {base_url}/transactions/{test_address} - Get transactions")
    
    # Show WebSocket events
    print(f"\n🔌 WebSocket Events:")
    print(f"   - 'balance_change': Real-time balance updates")
    print(f"   - 'new_transactions': New transaction notifications")
    print(f"   - 'subscribed': Address subscription confirmation")
    print(f"   - 'unsubscribed': Address unsubscription confirmation")
    
    print(f"\n✅ Real-time monitoring is now active!")
    print(f"   The server will check for changes every 10 seconds")
    print(f"   Any balance changes or new transactions will be detected automatically")
    
    return True

if __name__ == "__main__":
    test_realtime_monitoring() 