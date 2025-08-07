#!/usr/bin/env python3
"""
Test script for the new crypto transaction flow with reservations and locked amounts.
This script simulates the complete flow from unconfirmed to confirmed transactions.
"""

import requests
import json
import time
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:3000"
WEBHOOK_URL = f"{API_BASE_URL}/api/v1/wallet/btc/callbacks/address-webhook"

def create_test_signature():
    """Create a test signature for webhook testing."""
    return "keyId=\"test\",algorithm=\"sha256-ecdsa\",signature=\"test_signature\""

def send_webhook_event(event_type, tx_hash, address, amount, confirmations=0):
    """Send a webhook event to the API."""
    payload = {
        "event": event_type,
        "hash": tx_hash,
        "address": address,
        "value": amount,
        "confirmations": confirmations,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-BlockCypher-Signature": create_test_signature()
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=10)
        print(f"✅ {event_type.upper()} Event Response: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
        else:
            print(f"   Error: {response.text}")
        return response
    except Exception as e:
        print(f"❌ Error sending {event_type} event: {e}")
        return None

def test_complete_transaction_flow():
    """Test the complete transaction flow from unconfirmed to confirmed."""
    print("🚀 Testing Complete Crypto Transaction Flow")
    print("=" * 50)
    
    # Test data
    test_tx_hash = f"test_tx_{int(time.time())}"
    test_address = "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"
    test_amount = 0.001  # 0.001 BTC
    
    print(f"📝 Test Transaction Hash: {test_tx_hash}")
    print(f"📝 Test Address: {test_address}")
    print(f"📝 Test Amount: {test_amount} BTC")
    print()
    
    # Step 1: Unconfirmed transaction
    print("1️⃣ Testing Unconfirmed Transaction...")
    send_webhook_event("unconfirmed-tx", test_tx_hash, test_address, test_amount, 0)
    print()
    
    # Step 2: First confirmation
    print("2️⃣ Testing First Confirmation...")
    send_webhook_event("confirmed-tx", test_tx_hash, test_address, test_amount, 1)
    print()
    
    # Step 3: Second confirmation (should credit wallet)
    print("3️⃣ Testing Second Confirmation (Should Credit Wallet)...")
    send_webhook_event("tx-confirmation", test_tx_hash, test_address, test_amount, 2)
    print()
    
    # Step 4: Additional confirmations
    print("4️⃣ Testing Additional Confirmations...")
    send_webhook_event("tx-confirmation", test_tx_hash, test_address, test_amount, 3)
    send_webhook_event("tx-confirmation", test_tx_hash, test_address, test_amount, 4)
    print()
    
    # Step 5: Confidence updates
    print("5️⃣ Testing Confidence Updates...")
    send_webhook_event("tx-confidence", test_tx_hash, test_address, test_amount, 4)
    print()

def test_double_spend_scenario():
    """Test the double spend scenario."""
    print("🚨 Testing Double Spend Scenario")
    print("=" * 50)
    
    # Test data
    test_tx_hash = f"double_spend_tx_{int(time.time())}"
    test_address = "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"
    test_amount = 0.002  # 0.002 BTC
    
    print(f"📝 Double Spend Transaction Hash: {test_tx_hash}")
    print(f"📝 Test Address: {test_address}")
    print(f"📝 Test Amount: {test_amount} BTC")
    print()
    
    # Step 1: Create unconfirmed transaction
    print("1️⃣ Creating Unconfirmed Transaction...")
    send_webhook_event("unconfirmed-tx", test_tx_hash, test_address, test_amount, 0)
    print()
    
    # Step 2: Confirm transaction (should lock amount)
    print("2️⃣ Confirming Transaction (Should Lock Amount)...")
    send_webhook_event("confirmed-tx", test_tx_hash, test_address, test_amount, 1)
    print()
    
    # Step 3: Double spend detected (should fail transaction and remove locked amount)
    print("3️⃣ Detecting Double Spend (Should Fail Transaction)...")
    send_webhook_event("double-spend-tx", test_tx_hash, test_address, test_amount, 1)
    print()

def test_invalid_scenarios():
    """Test invalid scenarios."""
    print("⚠️ Testing Invalid Scenarios")
    print("=" * 50)
    
    # Test 1: Unknown address
    print("1️⃣ Testing Unknown Address...")
    send_webhook_event("unconfirmed-tx", "test_unknown_tx", "unknown_address", 0.001, 0)
    print()
    
    # Test 2: Invalid signature
    print("2️⃣ Testing Invalid Signature...")
    payload = {
        "event": "unconfirmed-tx",
        "hash": "test_invalid_sig_tx",
        "address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
        "value": 0.001,
        "confirmations": 0
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-BlockCypher-Signature": "invalid_signature"
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=10)
        print(f"✅ Invalid Signature Response: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing invalid signature: {e}")
    print()
    
    # Test 3: Missing data
    print("3️⃣ Testing Missing Data...")
    payload = {
        "event": "unconfirmed-tx"
        # Missing required fields
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-BlockCypher-Signature": create_test_signature()
    }
    
    try:
        response = requests.post(WEBHOOK_URL, json=payload, headers=headers, timeout=10)
        print(f"✅ Missing Data Response: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing missing data: {e}")
    print()

def main():
    """Run all tests."""
    print("🧪 Crypto Transaction Flow Test Suite")
    print("=" * 60)
    print()
    
    # Test 1: Complete transaction flow
    test_complete_transaction_flow()
    print()
    
    # Test 2: Double spend scenario
    test_double_spend_scenario()
    print()
    
    # Test 3: Invalid scenarios
    test_invalid_scenarios()
    print()
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    main() 