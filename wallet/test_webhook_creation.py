#!/usr/bin/env python3
"""
Test script for webhook creation using Alchemy dashboard API
"""

import requests
import json
from decouple import config

def test_create_webhook():
    """Test creating a webhook using the Alchemy dashboard API"""
    
    # Get the Alchemy Auth Key
    auth_key = config('ALCHEMY_AUTH_KEY', default=None)
    if not auth_key:
        print("❌ ALCHEMY_AUTH_KEY not configured")
        return
    
    # Webhook URL for our Solana webhook endpoint
    webhook_url = "http://localhost:3030/api/v1/wallet/sol/callbacks/address-webhook"
    
    payload = {
        "network": "SOL_MAINNET",
        "webhook_type": "ADDRESS_ACTIVITY",
        "webhook_url": webhook_url,
        "addresses": ["9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"]  # Test address
    }
    
    headers = {
        "X-Alchemy-Token": auth_key,
        "Content-Type": "application/json"
    }
    
    url = "https://dashboard.alchemy.com/api/create-webhook"
    
    try:
        print(f"🔧 Testing webhook creation...")
        print(f"   URL: {webhook_url}")
        print(f"   Network: SOL_MAINNET")
        print(f"   Type: ADDRESS_ACTIVITY")
        print(f"   Auth Key: {auth_key[:10]}...")
        
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Webhook created successfully!")
            print(f"   Webhook ID: {result.get('id', 'N/A')}")
            print(f"   Webhook URL: {result.get('url', 'N/A')}")
            print(f"   Signing Key: {result.get('signing_key', 'N/A')}")
            print(f"   Network: {result.get('network', 'N/A')}")
            print(f"   Type: {result.get('webhook_type', 'N/A')}")
            
            # Save the signing key for future use
            if result.get('signing_key'):
                print(f"\n📝 Add this signing key to your environment:")
                print(f"ALCHEMY_WEBHOOK_KEY_3={result.get('signing_key')}")
            
            return result
        else:
            print(f"❌ Failed to create webhook: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating webhook: {e}")
        return None

def test_list_webhooks():
    """Test listing existing webhooks"""
    
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
                print(f"   Signing Key: {webhook.get('signing_key', 'N/A')}")
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
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        test_list_webhooks()
    else:
        test_create_webhook()
