#!/usr/bin/env python3
"""
Script to create an Alchemy webhook for Solana address activity
"""

import requests
import json
from decouple import config

def create_alchemy_webhook():
    """Create an Alchemy webhook for Solana address activity"""
    
    # Get the Alchemy Auth Key
    auth_key = config('ALCHEMY_AUTH_KEY', default=None)
    if not auth_key:
        print("❌ ALCHEMY_AUTH_KEY not configured")
        return
    
    # Webhook URL for our Solana webhook endpoint
    webhook_url = "http://localhost:3030/api/v1/wallet/sol/callbacks/address-webhook"
    
    # For production, you would use your actual domain
    # webhook_url = "https://your-domain.com/api/v1/wallet/sol/callbacks/address-webhook"
    
    payload = {
        "network": "SOL_MAINNET",  # Solana mainnet
        "webhook_type": "ADDRESS_ACTIVITY",  # Monitor address activity
        "webhook_url": webhook_url,
        "addresses": [],  # Will be populated when addresses are added
        "app_id": "your-app-id"  # Optional: your Alchemy app ID
    }
    
    headers = {
        "X-Alchemy-Token": auth_key,
        "Content-Type": "application/json"
    }
    
    url = "https://dashboard.alchemy.com/api/create-webhook"
    
    try:
        print(f"🔧 Creating Alchemy webhook...")
        print(f"   URL: {webhook_url}")
        print(f"   Network: SOL_MAINNET")
        print(f"   Type: ADDRESS_ACTIVITY")
        
        response = requests.post(url, json=payload, headers=headers)
        
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

def list_webhooks():
    """List existing Alchemy webhooks"""
    
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
        print(f"📋 Listing Alchemy webhooks...")
        
        response = requests.get(url, headers=headers)
        
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
        list_webhooks()
    else:
        create_alchemy_webhook()
