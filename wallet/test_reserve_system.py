#!/usr/bin/env python3
"""
Test script for Reserve Management System
Tests reserve operations and integration with swap/mobile money
"""

import requests
import json
import time
import uuid
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:3000"
TEST_USER_TOKEN = "your_test_token_here"  # Replace with actual test token
ADMIN_TOKEN = "your_admin_token_here"     # Replace with actual admin token

class ReserveSystemTester:
    def __init__(self, base_url: str, user_token: str, admin_token: str):
        self.base_url = base_url
        self.user_headers = {
            "Authorization": f"Bearer {user_token}",
            "Content-Type": "application/json"
        }
        self.admin_headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    def test_reserve_management(self):
        """Test reserve management operations"""
        print("🏦 Testing Reserve Management System...")
        
        # Test 1: Get all reserves status
        print("\n1. Testing reserve status retrieval...")
        response = requests.get(
            f"{self.base_url}/wallet/reserves/status",
            headers=self.admin_headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Reserve status retrieved successfully")
            print(f"   Overall status: {result['reserves']['summary']['overall_status']}")
            print(f"   Crypto reserves: {len(result['reserves']['crypto'])}")
            print(f"   Fiat reserves: {len(result['reserves']['fiat'])}")
            
            # Store reserve info for later tests
            self.reserve_info = result['reserves']
        else:
            print(f"❌ Reserve status failed: {response.status_code} - {response.text}")
            return False
        
        # Test 2: Get specific reserve balance
        print("\n2. Testing specific reserve balance...")
        test_currency = "USDT"
        test_type = "crypto"
        
        response = requests.get(
            f"{self.base_url}/wallet/reserves/{test_currency}/{test_type}/balance",
            headers=self.admin_headers
        )
        
        if response.status_code == 200:
            result = response.json()
            balance = result['balance']
            print(f"✅ {test_currency} {test_type} reserve balance retrieved")
            print(f"   Total balance: {balance['total_balance']}")
            print(f"   Available balance: {balance['available_balance']}")
            print(f"   Utilization: {balance['utilization_percentage']}%")
            print(f"   Status: {balance['status']}")
        else:
            print(f"❌ Reserve balance failed: {response.status_code} - {response.text}")
            return False
        
        # Test 3: Top up a reserve
        print("\n3. Testing reserve top-up...")
        topup_data = {
            "amount": 1000.0,
            "source_reference": f"test_topup_{int(time.time())}"
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/reserves/{test_currency}/{test_type}/topup",
            headers=self.admin_headers,
            json=topup_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Reserve top-up successful: {result['topped_up_amount']} {test_currency}")
            print(f"   New total balance: {result['new_total_balance']}")
            print(f"   Transaction ID: {result['transaction_id']}")
            
            # Store topup info for withdrawal test
            self.topup_amount = topup_data["amount"]
            self.topup_transaction_id = result['transaction_id']
        else:
            print(f"❌ Reserve top-up failed: {response.status_code} - {response.text}")
            return False
        
        # Test 4: Withdraw from reserve
        print("\n4. Testing reserve withdrawal...")
        withdrawal_data = {
            "amount": 500.0,
            "destination_reference": f"test_withdrawal_{int(time.time())}"
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/reserves/{test_currency}/{test_type}/withdraw",
            headers=self.admin_headers,
            json=withdrawal_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Reserve withdrawal successful: {result['withdrawn_amount']} {test_currency}")
            print(f"   New total balance: {result['new_total_balance']}")
            print(f"   Transaction ID: {result['transaction_id']}")
        else:
            print(f"❌ Reserve withdrawal failed: {response.status_code} - {response.text}")
            return False
        
        # Test 5: Get reserve analytics
        print("\n5. Testing reserve analytics...")
        response = requests.get(
            f"{self.base_url}/wallet/reserves/analytics?period_days=7",
            headers=self.admin_headers
        )
        
        if response.status_code == 200:
            result = response.json()
            analytics = result['analytics']
            print(f"✅ Reserve analytics retrieved successfully")
            print(f"   Period: {analytics['period_days']} days")
            print(f"   Total transactions: {analytics['total_transactions']}")
            print(f"   Operations: {analytics['by_operation']}")
        else:
            print(f"❌ Reserve analytics failed: {response.status_code} - {response.text}")
            return False
        
        # Test 6: Clear reserve cache
        print("\n6. Testing reserve cache clear...")
        response = requests.post(
            f"{self.base_url}/wallet/reserves/cache/clear",
            headers=self.admin_headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Reserve cache cleared: {result['message']}")
        else:
            print(f"❌ Reserve cache clear failed: {response.status_code} - {response.text}")
            return False
        
        print("✅ Reserve management tests completed successfully!")
        return True
    
    def test_reserve_integration_with_swap(self):
        """Test how reserves integrate with swap operations"""
        print("\n🔄 Testing Reserve Integration with Swap...")
        
        # Test 1: Check reserve sufficiency before swap
        print("\n1. Testing reserve sufficiency check for swap...")
        
        # First, get current reserve status
        response = requests.get(
            f"{self.base_url}/wallet/reserves/status",
            headers=self.admin_headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get reserve status: {response.status_code}")
            return False
        
        reserves = response.json()['reserves']
        
        # Find a crypto currency with sufficient reserve
        crypto_with_reserve = None
        for currency, data in reserves['crypto'].items():
            if data['available_balance'] > 0.1:  # Need at least 0.1 for testing
                crypto_with_reserve = currency
                break
        
        if not crypto_with_reserve:
            print("⚠️  No crypto currency with sufficient reserve found. Skipping swap test.")
            return True
        
        print(f"   Using {crypto_with_reserve} for swap test")
        
        # Test 2: Attempt swap with reserve check
        print("\n2. Testing swap with reserve integration...")
        reference_id = f"test_swap_reserve_{uuid.uuid4().hex[:16]}"
        
        swap_data = {
            "from_currency": crypto_with_reserve,
            "to_currency": "USDT",
            "from_amount": 0.01,  # Small amount
            "reference_id": reference_id,
            "slippage_tolerance": 0.01
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/swap/execute",
            headers=self.user_headers,
            json=swap_data
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Swap with reserve integration successful")
            print(f"   Swap ID: {result['swap_id']}")
            print(f"   Status: {result['status']}")
            if 'reserve_status' in result:
                print(f"   Reserve status included in response")
        elif response.status_code == 400:
            result = response.json()
            if "Insufficient system reserve" in result.get('error', ''):
                print(f"✅ Swap correctly rejected due to insufficient reserve: {result['error']}")
            else:
                print(f"❌ Swap failed for unexpected reason: {result['error']}")
                return False
        else:
            print(f"❌ Swap request failed: {response.status_code} - {response.text}")
            return False
        
        print("✅ Reserve integration with swap tests completed successfully!")
        return True
    
    def test_reserve_integration_with_mobile_money(self):
        """Test how reserves integrate with mobile money operations"""
        print("\n📱 Testing Reserve Integration with Mobile Money...")
        
        # Test 1: Check reserve sufficiency for mobile money buy
        print("\n1. Testing mobile money buy with reserve check...")
        
        # Get current reserve status
        response = requests.get(
            f"{self.base_url}/wallet/reserves/status",
            headers=self.admin_headers
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get reserve status: {response.status_code}")
            return False
        
        reserves = response.json()['reserves']
        
        # Find a crypto currency with sufficient reserve
        crypto_with_reserve = None
        for currency, data in reserves['crypto'].items():
            if data['available_balance'] > 0.1:
                crypto_with_reserve = currency
                break
        
        if not crypto_with_reserve:
            print("⚠️  No crypto currency with sufficient reserve found. Skipping mobile money test.")
            return True
        
        print(f"   Using {crypto_with_reserve} for mobile money test")
        
        # Test 2: Attempt mobile money buy with reserve check
        print("\n2. Testing mobile money buy with reserve integration...")
        reference_id = f"test_mobile_reserve_{uuid.uuid4().hex[:16]}"
        
        buy_data = {
            "fiat_amount": 1000,
            "fiat_currency": "UGX",
            "crypto_currency": crypto_with_reserve,
            "provider": "relworx",
            "phone_number": "256700000000",
            "reference_id": reference_id,
            "slippage_tolerance": 0.02
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/mobile-money/buy/initiate",
            headers=self.user_headers,
            json=buy_data
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Mobile money buy with reserve integration successful")
            print(f"   Transaction ID: {result['transaction_id']}")
            print(f"   Status: {result['status']}")
            if 'reserve_status' in result:
                print(f"   Reserve status included in response")
        elif response.status_code == 400:
            result = response.json()
            if "Insufficient system reserve" in result.get('error', ''):
                print(f"✅ Mobile money buy correctly rejected due to insufficient reserve: {result['error']}")
            else:
                print(f"❌ Mobile money buy failed for unexpected reason: {result['error']}")
                return False
        else:
            print(f"❌ Mobile money buy request failed: {response.status_code} - {response.text}")
            return False
        
        print("✅ Reserve integration with mobile money tests completed successfully!")
        return True
    
    def test_reserve_operations_edge_cases(self):
        """Test edge cases and error handling in reserve operations"""
        print("\n⚠️  Testing Reserve Operations Edge Cases...")
        
        # Test 1: Invalid account type
        print("\n1. Testing invalid account type...")
        response = requests.get(
            f"{self.base_url}/wallet/reserves/USDT/invalid_type/balance",
            headers=self.admin_headers
        )
        
        if response.status_code == 400:
            result = response.json()
            print(f"✅ Correctly rejected invalid account type: {result['error']}")
        else:
            print(f"❌ Should have rejected invalid account type: {response.status_code}")
            return False
        
        # Test 2: Negative amount for top-up
        print("\n2. Testing negative amount for top-up...")
        topup_data = {
            "amount": -100.0,
            "source_reference": "test_negative"
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/reserves/USDT/crypto/topup",
            headers=self.admin_headers,
            json=topup_data
        )
        
        if response.status_code == 400:
            result = response.json()
            print(f"✅ Correctly rejected negative amount: {result['error']}")
        else:
            print(f"❌ Should have rejected negative amount: {response.status_code}")
            return False
        
        # Test 3: Zero amount for withdrawal
        print("\n3. Testing zero amount for withdrawal...")
        withdrawal_data = {
            "amount": 0.0,
            "destination_reference": "test_zero"
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/reserves/USDT/crypto/withdraw",
            headers=self.admin_headers,
            json=withdrawal_data
        )
        
        if response.status_code == 400:
            result = response.json()
            print(f"✅ Correctly rejected zero amount: {result['error']}")
        else:
            print(f"❌ Should have rejected zero amount: {response.status_code}")
            return False
        
        # Test 4: Invalid period for analytics
        print("\n4. Testing invalid period for analytics...")
        response = requests.get(
            f"{self.base_url}/wallet/reserves/analytics?period_days=400",
            headers=self.admin_headers
        )
        
        if response.status_code == 400:
            result = response.json()
            print(f"✅ Correctly rejected invalid period: {result['error']}")
        else:
            print(f"❌ Should have rejected invalid period: {response.status_code}")
            return False
        
        print("✅ Reserve edge case tests completed successfully!")
        return True
    
    def run_all_tests(self):
        """Run all reserve system tests"""
        print("🚀 Starting Reserve Management System Tests...")
        print("=" * 70)
        
        try:
            # Run all test suites
            tests = [
                ("Reserve Management", self.test_reserve_management),
                ("Reserve Integration with Swap", self.test_reserve_integration_with_swap),
                ("Reserve Integration with Mobile Money", self.test_reserve_integration_with_mobile_money),
                ("Reserve Operations Edge Cases", self.test_reserve_operations_edge_cases)
            ]
            
            results = []
            for test_name, test_func in tests:
                try:
                    result = test_func()
                    results.append((test_name, result))
                except Exception as e:
                    print(f"❌ {test_name} test failed with exception: {e}")
                    results.append((test_name, False))
            
            # Print summary
            print("\n" + "=" * 70)
            print("📊 RESERVE SYSTEM TEST SUMMARY")
            print("=" * 70)
            
            passed = 0
            total = len(results)
            
            for test_name, result in results:
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"{test_name}: {status}")
                if result:
                    passed += 1
            
            print(f"\nOverall Result: {passed}/{total} tests passed")
            
            if passed == total:
                print("🎉 All reserve system tests passed! The system is working correctly.")
            else:
                print("⚠️  Some tests failed. Please check the implementation.")
            
            return passed == total
            
        except Exception as e:
            print(f"❌ Test suite failed with exception: {e}")
            return False

def main():
    """Main function to run reserve system tests"""
    print("Reserve Management System Test Suite")
    print("=" * 50)
    
    # Check if tokens are provided
    if TEST_USER_TOKEN == "your_test_token_here":
        print("❌ Please set TEST_USER_TOKEN with a valid user authentication token")
        print("   You can get this by logging into the wallet system")
        return
    
    if ADMIN_TOKEN == "your_admin_token_here":
        print("❌ Please set ADMIN_TOKEN with a valid admin authentication token")
        print("   You can get this by logging into the wallet system as an admin")
        return
    
    # Create tester instance
    tester = ReserveSystemTester(BASE_URL, TEST_USER_TOKEN, ADMIN_TOKEN)
    
    # Run all tests
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 Reserve system ready for production use!")
    else:
        print("\n🔧 Please fix the failing tests before deploying")

if __name__ == "__main__":
    main()
