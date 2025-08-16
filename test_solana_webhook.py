#!/usr/bin/env python3
"""
Test script for Solana webhook implementation
"""

import requests
import json
import hmac
import hashlib
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:3001"  # API service URL
WALLET_BASE_URL = "http://localhost:3000"  # Wallet service URL
ALCHEMY_WEBHOOK_KEY = "test_webhook_key"  # Test webhook key

def create_test_signature(payload: str, webhook_key: str) -> str:
    """Create a test signature for webhook verification"""
    return hmac.new(
        webhook_key.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()



def test_solana_address_activity_webhook():
    """Test the Solana address activity webhook with sample data"""
    print("\n🔍 Testing Solana address activity webhook...")
    
    # Sample webhook payload based on Alchemy's format
    webhook_data = {
        "webhook_id": "test_webhook_123",
        "id": 1,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "type": "ADDRESS_ACTIVITY",
        "event": {
            "activity": [
                {
                    "fromAddress": "11111111111111111111111111111112",  # System Program
                    "toAddress": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",  # Test address
                    "blockNum": "123456789",
                    "hash": "test_tx_hash_123456",
                    "category": "external",
                    "value": 0.001,
                    "asset": "SOL",
                    "erc721TokenId": None,
                    "erc1155Metadata": None,
                    "tokenId": None,
                    "rawContract": {
                        "value": "1000000",
                        "address": "",
                        "decimal": "9"
                    }
                }
            ]
        }
    }
    
    # Create signature
    payload = json.dumps(webhook_data)
    signature = create_test_signature(payload, ALCHEMY_WEBHOOK_KEY)
    
    # Headers
    headers = {
        'Content-Type': 'application/json',
        'X-Alchemy-Signature': signature
    }
    
    try:
        # Test direct wallet service endpoint
        print("📡 Testing direct wallet service endpoint...")
        response = requests.post(
            f"{WALLET_BASE_URL}/sol/callbacks/address-webhook",
            json=webhook_data,
            headers=headers,
            timeout=10
        )
        
        print(f"✅ Direct wallet response: {response.status_code}")
        print(f"📄 Response: {response.json()}")
        
        # Test API proxy endpoint
        print("\n📡 Testing API proxy endpoint...")
        response = requests.post(
            f"{API_BASE_URL}/api/v1/wallet/sol/callbacks/address-webhook",
            json=webhook_data,
            headers=headers,
            timeout=10
        )
        
        print(f"✅ API proxy response: {response.status_code}")
        print(f"📄 Response: {response.json()}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure the services are running")
        return False
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return False

def test_solana_webhook_without_signature():
    """Test webhook without signature (should fail)"""
    print("\n🔍 Testing webhook without signature...")
    
    webhook_data = {
        "webhook_id": "test_webhook_no_sig",
        "type": "ADDRESS_ACTIVITY",
        "event": {"activity": []}
    }
    
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.post(
            f"{WALLET_BASE_URL}/sol/callbacks/address-webhook",
            json=webhook_data,
            headers=headers,
            timeout=10
        )
        
        print(f"📄 Response: {response.status_code} - {response.json()}")
        
        if response.status_code == 400:
            print("✅ Correctly rejected webhook without signature")
            return True
        else:
            print("❌ Should have rejected webhook without signature")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_solana_webhook_invalid_signature():
    """Test webhook with invalid signature (should fail)"""
    print("\n🔍 Testing webhook with invalid signature...")
    
    webhook_data = {
        "webhook_id": "test_webhook_invalid_sig",
        "type": "ADDRESS_ACTIVITY",
        "event": {"activity": []}
    }
    
    # Invalid signature
    headers = {
        'Content-Type': 'application/json',
        'X-Alchemy-Signature': 'invalid_signature_123'
    }
    
    try:
        response = requests.post(
            f"{WALLET_BASE_URL}/sol/callbacks/address-webhook",
            json=webhook_data,
            headers=headers,
            timeout=10
        )
        
        print(f"📄 Response: {response.status_code} - {response.json()}")
        
        if response.status_code == 401:
            print("✅ Correctly rejected webhook with invalid signature")
            return True
        else:
            print("❌ Should have rejected webhook with invalid signature")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Run all Solana webhook tests"""
    print("🚀 Starting Solana webhook tests...")
    print("=" * 50)
    
    tests = [
        ("Address Activity Webhook", test_solana_address_activity_webhook),
        ("No Signature Test", test_solana_webhook_without_signature),
        ("Invalid Signature Test", test_solana_webhook_invalid_signature)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Solana webhook implementation is working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()
