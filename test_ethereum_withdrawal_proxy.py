#!/usr/bin/env python3
"""
Test script for Ethereum withdrawal proxy endpoints
Tests the API gateway proxy functionality for Ethereum withdrawals
"""

import requests
import json
import time
from decimal import Decimal

# Configuration
API_BASE_URL = "http://localhost:3030/api/v1"  # API gateway URL
WALLET_BASE_URL = "http://localhost:3000"  # Direct wallet service URL

# Test user token (you'll need to get a valid token)
TEST_TOKEN = "your_test_token_here"  # Replace with actual token

def test_ethereum_withdrawal_proxy():
    """Test the Ethereum withdrawal proxy endpoint"""
    
    print("🧪 Testing Ethereum Withdrawal Proxy")
    print("=" * 50)
    
    # Test data
    withdrawal_data = {
        "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
        "amount": 0.01,
        "reference_id": f"test_withdrawal_{int(time.time())}",
        "description": "Test withdrawal via API proxy",
        "gas_limit": 21000
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_TOKEN}"
    }
    
    print(f"📤 Sending withdrawal request via API proxy...")
    print(f"   Amount: {withdrawal_data['amount']} ETH")
    print(f"   To: {withdrawal_data['to_address']}")
    print(f"   Reference: {withdrawal_data['reference_id']}")
    
    try:
        # Test via API proxy
        proxy_response = requests.post(
            f"{API_BASE_URL}/wallet/withdraw/ethereum",
            json=withdrawal_data,
            headers=headers,
            timeout=60
        )
        
        print(f"📥 Proxy Response Status: {proxy_response.status_code}")
        print(f"📥 Proxy Response: {json.dumps(proxy_response.json(), indent=2)}")
        
        if proxy_response.status_code == 201:
            print("✅ Proxy withdrawal request successful!")
            
            # Test status check via proxy
            reference_id = withdrawal_data['reference_id']
            print(f"\n🔍 Checking withdrawal status via proxy...")
            print(f"   Reference ID: {reference_id}")
            
            status_response = requests.get(
                f"{API_BASE_URL}/wallet/withdraw/ethereum/status/{reference_id}",
                headers=headers,
                timeout=30
            )
            
            print(f"📥 Status Response Status: {status_response.status_code}")
            print(f"📥 Status Response: {json.dumps(status_response.json(), indent=2)}")
            
            if status_response.status_code == 200:
                print("✅ Proxy status check successful!")
            else:
                print("❌ Proxy status check failed!")
                
        else:
            print("❌ Proxy withdrawal request failed!")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_direct_wallet_comparison():
    """Compare proxy vs direct wallet service calls"""
    
    print("\n🔄 Comparing Proxy vs Direct Wallet Service")
    print("=" * 50)
    
    # Test data
    withdrawal_data = {
        "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
        "amount": 0.005,
        "reference_id": f"comparison_test_{int(time.time())}",
        "description": "Comparison test",
        "gas_limit": 21000
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TEST_TOKEN}"
    }
    
    print("📊 Testing both endpoints...")
    
    try:
        # Test via API proxy
        print("1️⃣ Testing via API proxy...")
        proxy_start = time.time()
        proxy_response = requests.post(
            f"{API_BASE_URL}/wallet/withdraw/ethereum",
            json=withdrawal_data,
            headers=headers,
            timeout=60
        )
        proxy_time = time.time() - proxy_start
        
        print(f"   Proxy Status: {proxy_response.status_code}")
        print(f"   Proxy Time: {proxy_time:.2f}s")
        
        # Test via direct wallet service
        print("2️⃣ Testing via direct wallet service...")
        direct_start = time.time()
        direct_response = requests.post(
            f"{WALLET_BASE_URL}/wallet/withdraw/ethereum",
            json=withdrawal_data,
            headers=headers,
            timeout=60
        )
        direct_time = time.time() - direct_start
        
        print(f"   Direct Status: {direct_response.status_code}")
        print(f"   Direct Time: {direct_time:.2f}s")
        
        # Compare responses
        print("\n📈 Comparison Results:")
        print(f"   Proxy Overhead: {proxy_time - direct_time:.2f}s")
        print(f"   Status Match: {proxy_response.status_code == direct_response.status_code}")
        
        if proxy_response.status_code == direct_response.status_code:
            print("✅ Proxy correctly forwards requests!")
        else:
            print("❌ Proxy response differs from direct service!")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_error_handling():
    """Test error handling scenarios"""
    
    print("\n🚨 Testing Error Handling")
    print("=" * 40)
    
    # Test scenarios
    test_cases = [
        {
            "name": "Invalid token",
            "data": {
                "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
                "amount": 0.01,
                "reference_id": "error_test_1"
            },
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer invalid_token"
            }
        },
        {
            "name": "Missing required fields",
            "data": {
                "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7"
                # Missing amount and reference_id
            },
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TEST_TOKEN}"
            }
        },
        {
            "name": "Invalid address format",
            "data": {
                "to_address": "invalid_address",
                "amount": 0.01,
                "reference_id": "error_test_3"
            },
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {TEST_TOKEN}"
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print(f"   Data: {json.dumps(test_case['data'], indent=6)}")
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/wallet/withdraw/ethereum",
                json=test_case['data'],
                headers=test_case['headers'],
                timeout=30
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {json.dumps(response.json(), indent=6)}")
            
        except requests.exceptions.RequestException as e:
            print(f"   Network Error: {e}")
        except Exception as e:
            print(f"   Error: {e}")


def test_api_health():
    """Test API gateway health"""
    
    print("\n🏥 Testing API Gateway Health")
    print("=" * 40)
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        print(f"API Health Status: {response.status_code}")
        print(f"API Health Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ API gateway is healthy!")
        else:
            print("❌ API gateway health check failed!")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach API gateway: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main test function"""
    
    print("🚀 Ethereum Withdrawal Proxy Test Suite")
    print("=" * 60)
    
    # Check if test token is set
    if TEST_TOKEN == "your_test_token_here":
        print("⚠️  Please set a valid TEST_TOKEN in the script")
        print("   You can get a token by logging in through the API")
        return
    
    # Run tests
    test_api_health()
    test_ethereum_withdrawal_proxy()
    test_direct_wallet_comparison()
    test_error_handling()
    
    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    main() 