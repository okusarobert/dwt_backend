#!/usr/bin/env python3
"""
Test script for Ethereum withdrawal functionality
"""

import requests
import json
import time
from decimal import Decimal

# Configuration
BASE_URL = "http://localhost:3000"  # Wallet service URL
AUTH_TOKEN = "your-auth-token-here"  # Replace with actual token

def test_eth_withdrawal():
    """Test the Ethereum withdrawal endpoint"""
    
    # Test data
    withdrawal_data = {
        "to_address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        "amount": 0.001,  # Small amount for testing
        "reference_id": f"eth_test_{int(time.time())}",
        "description": "Test ETH withdrawal",
        "gas_limit": 21000
    }
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("🚀 Testing Ethereum Withdrawal")
    print(f"📤 Request: {json.dumps(withdrawal_data, indent=2)}")
    
    try:
        # Make withdrawal request
        response = requests.post(
            f"{BASE_URL}/wallet/withdraw/ethereum",
            json=withdrawal_data,
            headers=headers
        )
        
        print(f"📥 Response Status: {response.status_code}")
        print(f"📥 Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            result = response.json()
            reference_id = result.get("transaction_info", {}).get("reference_id")
            
            if reference_id:
                print(f"✅ Withdrawal prepared successfully!")
                print(f"📋 Reference ID: {reference_id}")
                
                # Test status check
                test_status_check(reference_id, headers)
            else:
                print("❌ No reference ID in response")
        else:
            print("❌ Withdrawal request failed")
            
    except Exception as e:
        print(f"❌ Error testing withdrawal: {e}")

def test_status_check(reference_id, headers):
    """Test the transaction status check endpoint"""
    
    print(f"\n🔍 Checking transaction status for: {reference_id}")
    
    try:
        response = requests.get(
            f"{BASE_URL}/wallet/withdraw/ethereum/status/{reference_id}",
            headers=headers
        )
        
        print(f"📥 Status Response: {response.status_code}")
        print(f"📥 Status Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            status_data = response.json()
            status = status_data.get("status")
            
            if status == "prepared":
                print("📋 Transaction is prepared but not yet sent to blockchain")
            elif status == "pending":
                print("⏳ Transaction is pending on blockchain")
            elif status == "success":
                print("✅ Transaction confirmed successfully!")
            elif status == "failed":
                print("❌ Transaction failed on blockchain")
            else:
                print(f"❓ Unknown status: {status}")
        else:
            print("❌ Status check failed")
            
    except Exception as e:
        print(f"❌ Error checking status: {e}")

def test_validation_errors():
    """Test various validation error scenarios"""
    
    print("\n🧪 Testing Validation Errors")
    
    test_cases = [
        {
            "name": "Missing to_address",
            "data": {
                "amount": 0.001,
                "reference_id": "test_1"
            }
        },
        {
            "name": "Invalid Ethereum address",
            "data": {
                "to_address": "invalid_address",
                "amount": 0.001,
                "reference_id": "test_2"
            }
        },
        {
            "name": "Negative amount",
            "data": {
                "to_address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                "amount": -0.001,
                "reference_id": "test_3"
            }
        },
        {
            "name": "Missing amount",
            "data": {
                "to_address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                "reference_id": "test_4"
            }
        }
    ]
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case['name']}")
        print(f"📤 Data: {json.dumps(test_case['data'], indent=2)}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/wallet/withdraw/ethereum",
                json=test_case['data'],
                headers=headers
            )
            
            print(f"📥 Status: {response.status_code}")
            print(f"📥 Response: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 400:
                print("✅ Validation error caught correctly")
            else:
                print("❌ Expected validation error but got different response")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def test_balance_check():
    """Test balance validation"""
    
    print("\n💰 Testing Balance Validation")
    
    # Try to withdraw a very large amount
    large_withdrawal = {
        "to_address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        "amount": 1000.0,  # Very large amount
        "reference_id": f"large_test_{int(time.time())}",
        "description": "Large withdrawal test"
    }
    
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/wallet/withdraw/ethereum",
            json=large_withdrawal,
            headers=headers
        )
        
        print(f"📥 Status: {response.status_code}")
        print(f"📥 Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✅ Insufficient balance error caught correctly")
        else:
            print("❌ Expected balance error but got different response")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main test function"""
    print("🧪 Ethereum Withdrawal Test Suite")
    print("=" * 50)
    
    # Test successful withdrawal
    test_eth_withdrawal()
    
    # Test validation errors
    test_validation_errors()
    
    # Test balance validation
    test_balance_check()
    
    print("\n✅ Test suite completed!")

if __name__ == "__main__":
    main() 