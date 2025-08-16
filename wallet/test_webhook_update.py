#!/usr/bin/env python3
"""
Test script for webhook address updates using Alchemy dashboard API
"""

import requests
import json
from decouple import config

def test_add_address_to_webhook():
    """Test adding an address to an existing webhook"""
    
    # Get the Alchemy Auth Key
    auth_key = config('ALCHEMY_AUTH_KEY', default=None)
    if not auth_key:
        print("❌ ALCHEMY_AUTH_KEY not configured")
        return
    
    # Test webhook ID (you'll need to replace this with a real webhook ID)
    webhook_id = "test_webhook_id"  # Replace with actual webhook ID
    test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    
    payload = {
        "webhook_id": webhook_id,
        "addresses_to_add": [test_address],
        "addresses_to_remove": []
    }
    
    headers = {
        "X-Alchemy-Token": auth_key,
        "Content-Type": "application/json"
    }
    
    url = "https://dashboard.alchemy.com/api/update-webhook-addresses"
    
    try:
        print(f"🔧 Testing webhook address addition...")
        print(f"   Webhook ID: {webhook_id}")
        print(f"   Address to add: {test_address}")
        print(f"   Auth Key: {auth_key[:10]}...")
        
        response = requests.patch(url, json=payload, headers=headers)
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Address added successfully!")
            print(f"   Result: {result}")
            return result
        else:
            print(f"❌ Failed to add address: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error adding address: {e}")
        return None

def test_remove_address_from_webhook():
    """Test removing an address from an existing webhook"""
    
    # Get the Alchemy Auth Key
    auth_key = config('ALCHEMY_AUTH_KEY', default=None)
    if not auth_key:
        print("❌ ALCHEMY_AUTH_KEY not configured")
        return
    
    # Test webhook ID (you'll need to replace this with a real webhook ID)
    webhook_id = "test_webhook_id"  # Replace with actual webhook ID
    test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    
    payload = {
        "webhook_id": webhook_id,
        "addresses_to_add": [],
        "addresses_to_remove": [test_address]
    }
    
    headers = {
        "X-Alchemy-Token": auth_key,
        "Content-Type": "application/json"
    }
    
    url = "https://dashboard.alchemy.com/api/update-webhook-addresses"
    
    try:
        print(f"🔧 Testing webhook address removal...")
        print(f"   Webhook ID: {webhook_id}")
        print(f"   Address to remove: {test_address}")
        print(f"   Auth Key: {auth_key[:10]}...")
        
        response = requests.patch(url, json=payload, headers=headers)
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Address removed successfully!")
            print(f"   Result: {result}")
            return result
        else:
            print(f"❌ Failed to remove address: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error removing address: {e}")
        return None

def test_list_webhooks():
    """Test listing existing webhooks to get webhook IDs"""
    
    auth_key = config('ALCHEMY_AUTH_KEY', default=None)
    if not auth_key:
        print("❌ ALCHEMY_AUTH_KEY not configured")
        return
    
    headers = {
        "X-Alchemy-Token": auth_key,
        "Content-Type": "application/json"
    }
    
    url = "https://dashboard.alchemy.com/api/webhooks"
    
    try:
        print(f"📋 Testing webhook listing...")
        
        response = requests.get(url, headers=headers)
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            webhooks = response.json()
            print(f"✅ Found {len(webhooks)} webhooks:")
            
            for webhook in webhooks:
                print(f"   ID: {webhook.get('id', 'N/A')}")
                print(f"   URL: {webhook.get('url', 'N/A')}")
                print(f"   Network: {webhook.get('network', 'N/A')}")
                print(f"   Type: {webhook.get('webhook_type', 'N/A')}")
                print(f"   Addresses: {webhook.get('addresses', [])}")
                print(f"   ---")
            
            return webhooks
        else:
            print(f"❌ Failed to list webhooks: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error listing webhooks: {e}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            test_list_webhooks()
        elif sys.argv[1] == "remove":
            test_remove_address_from_webhook()
        else:
            test_add_address_to_webhook()
    else:
        test_add_address_to_webhook()
