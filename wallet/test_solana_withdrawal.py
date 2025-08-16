#!/usr/bin/env python3
"""
Test script for Solana withdrawal functionality
"""

import requests
import json
from decouple import config

def test_solana_withdrawal():
    """Test Solana withdrawal endpoint"""
    
    # Test data
    withdrawal_data = {
        "to_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "amount": 0.001,  # Small amount for testing
        "reference_id": f"sol_test_{int(time.time())}",
        "description": "Test SOL withdrawal",
        "priority_fee": 5000
    }
    
    # Get auth token (you'll need to replace this with a real token)
    auth_token = config('TEST_AUTH_TOKEN', default='your-auth-token-here')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    # Test the API proxy endpoint
    api_url = "http://localhost:3030/api/v1/wallet/withdraw/solana"
    
    try:
        print(f"🔧 Testing Solana withdrawal...")
        print(f"   URL: {api_url}")
        print(f"   Data: {withdrawal_data}")
        
        response = requests.post(api_url, json=withdrawal_data, headers=headers)
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Solana withdrawal successful!")
            print(f"   Reference ID: {result.get('transaction_info', {}).get('reference_id')}")
            print(f"   Transaction Hash: {result.get('transaction_info', {}).get('transaction_hash')}")
            print(f"   Amount: {result.get('transaction_info', {}).get('amount_sol')} SOL")
            print(f"   To Address: {result.get('transaction_info', {}).get('to_address')}")
            
            # Test status endpoint
            reference_id = result.get('transaction_info', {}).get('reference_id')
            if reference_id:
                test_withdrawal_status(reference_id, auth_token)
            
            return result
        else:
            print(f"❌ Solana withdrawal failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing Solana withdrawal: {e}")
        return None

def test_withdrawal_status(reference_id, auth_token):
    """Test Solana withdrawal status endpoint"""
    
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    
    # Test the API proxy endpoint
    api_url = f"http://localhost:3030/api/v1/wallet/withdraw/solana/status/{reference_id}"
    
    try:
        print(f"🔧 Testing Solana withdrawal status...")
        print(f"   URL: {api_url}")
        
        response = requests.get(api_url, headers=headers)
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Solana withdrawal status retrieved!")
            print(f"   Reference ID: {result.get('reference_id')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Transaction Hash: {result.get('transaction_hash')}")
            print(f"   Confirmations: {result.get('confirmations')}/{result.get('required_confirmations')}")
            
            return result
        else:
            print(f"❌ Solana withdrawal status failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing Solana withdrawal status: {e}")
        return None

def test_direct_wallet_endpoint():
    """Test the wallet service endpoint directly"""
    
    # Test data
    withdrawal_data = {
        "to_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "amount": 0.001,
        "reference_id": f"sol_direct_test_{int(time.time())}",
        "description": "Direct test SOL withdrawal",
        "priority_fee": 5000
    }
    
    # Get auth token
    auth_token = config('TEST_AUTH_TOKEN', default='your-auth-token-here')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    }
    
    # Test the wallet service directly
    wallet_url = "http://localhost:3000/wallet/withdraw/solana"
    
    try:
        print(f"🔧 Testing direct wallet endpoint...")
        print(f"   URL: {wallet_url}")
        print(f"   Data: {withdrawal_data}")
        
        response = requests.post(wallet_url, json=withdrawal_data, headers=headers)
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Direct wallet test successful!")
            return result
        else:
            print(f"❌ Direct wallet test failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error testing direct wallet endpoint: {e}")
        return None

if __name__ == "__main__":
    import time
    
    print("🧪 Testing Solana Withdrawal Functionality")
    print("=" * 50)
    
    # Test 1: Direct wallet endpoint
    print("\n1. Testing direct wallet endpoint...")
    test_direct_wallet_endpoint()
    
    # Test 2: API proxy endpoint
    print("\n2. Testing API proxy endpoint...")
    test_solana_withdrawal()
    
    print("\n✅ Testing complete!")
