#!/usr/bin/env python3
"""
Test script for Swap and Mobile Money functionality
Tests all endpoints and service methods
"""

import requests
import json
import time
import uuid
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:3000"
TEST_USER_TOKEN = "your_test_token_here"  # Replace with actual test token

class SwapAndMobileMoneyTester:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def test_swap_functionality(self):
        """Test crypto-to-crypto swap functionality"""
        print("🔄 Testing Swap Functionality...")
        
        # Test 1: Calculate swap amounts
        print("\n1. Testing swap calculation...")
        swap_calc_data = {
            "from_currency": "ETH",
            "to_currency": "USDC",
            "from_amount": 1.0,
            "slippage_tolerance": 0.01
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/swap/calculate",
            headers=self.headers,
            json=swap_calc_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Swap calculation successful: {result['calculation']['to_amount']:.6f} USDC for 1 ETH")
            print(f"   Rate: 1 ETH = {result['calculation']['rate']:.6f} USDC")
            print(f"   Fee: {result['calculation']['swap_fee']:.6f} ETH")
        else:
            print(f"❌ Swap calculation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 2: Execute swap
        print("\n2. Testing swap execution...")
        reference_id = f"test_swap_{uuid.uuid4().hex[:16]}"
        swap_exec_data = {
            "from_currency": "ETH",
            "to_currency": "USDC",
            "from_amount": 0.1,  # Small amount for testing
            "reference_id": reference_id,
            "slippage_tolerance": 0.01
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/swap/execute",
            headers=self.headers,
            json=swap_exec_data
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Swap execution successful: {result['swap_id']}")
            print(f"   Status: {result['status']}")
            print(f"   Reference ID: {result['reference_id']}")
        else:
            print(f"❌ Swap execution failed: {response.status_code} - {response.text}")
            return False
        
        # Test 3: Get swap history
        print("\n3. Testing swap history...")
        response = requests.get(
            f"{self.base_url}/wallet/swap/history",
            headers=self.headers,
            params={"limit": 10}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Swap history retrieved: {len(result['swaps'])} swaps")
        else:
            print(f"❌ Swap history failed: {response.status_code} - {response.text}")
            return False
        
        print("✅ Swap functionality tests completed successfully!")
        return True
    
    def test_mobile_money_functionality(self):
        """Test mobile money buy/sell functionality"""
        print("\n📱 Testing Mobile Money Functionality...")
        
        # Test 1: Get supported providers
        print("\n1. Testing provider list...")
        response = requests.get(
            f"{self.base_url}/wallet/mobile-money/providers",
            headers=self.headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Providers retrieved: {len(result['providers'])} providers")
            for provider in result['providers']:
                print(f"   - {provider['name']} ({provider['provider_id']})")
        else:
            print(f"❌ Provider list failed: {response.status_code} - {response.text}")
            return False
        
        # Test 2: Calculate buy amounts
        print("\n2. Testing buy calculation...")
        buy_calc_data = {
            "fiat_amount": 1000,
            "fiat_currency": "UGX",
            "crypto_currency": "USDT",
            "provider": "relworx",
            "slippage_tolerance": 0.02
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/mobile-money/buy/calculate",
            headers=self.headers,
            json=buy_calc_data
        )
        
        if response.status_code == 200:
            result = response.json()
            calculation = result['calculation']
            print(f"✅ Buy calculation successful: {calculation['crypto_amount']:.6f} USDT for {calculation['fiat_amount']} UGX")
            print(f"   Provider fee: {calculation['provider_fee']:.2f} UGX")
            print(f"   Net amount: {calculation['net_fiat_amount']:.2f} UGX")
        else:
            print(f"❌ Buy calculation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 3: Calculate sell amounts
        print("\n3. Testing sell calculation...")
        sell_calc_data = {
            "crypto_amount": 10,
            "crypto_currency": "USDT",
            "fiat_currency": "UGX",
            "provider": "relworx",
            "slippage_tolerance": 0.02
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/mobile-money/sell/calculate",
            headers=self.headers,
            json=sell_calc_data
        )
        
        if response.status_code == 200:
            result = response.json()
            calculation = result['calculation']
            print(f"✅ Sell calculation successful: {calculation['crypto_amount']} USDT = {calculation['net_fiat_amount']:.2f} UGX")
            print(f"   Provider fee: {calculation['provider_fee']:.2f} UGX")
            print(f"   Processing time: {calculation['processing_time']}")
        else:
            print(f"❌ Sell calculation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 4: Initiate buy order
        print("\n4. Testing buy order initiation...")
        reference_id = f"test_buy_{uuid.uuid4().hex[:16]}"
        buy_init_data = {
            "fiat_amount": 5000,
            "fiat_currency": "UGX",
            "crypto_currency": "USDT",
            "provider": "relworx",
            "phone_number": "256700000000",
            "reference_id": reference_id,
            "slippage_tolerance": 0.02
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/mobile-money/buy/initiate",
            headers=self.headers,
            json=buy_init_data
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Buy order initiated: {result['transaction_id']}")
            print(f"   Status: {result['status']}")
            print(f"   Reference ID: {result['reference_id']}")
            print(f"   Next steps: {result['next_steps']}")
            
            # Store reference_id for payment confirmation test
            self.test_reference_id = reference_id
        else:
            print(f"❌ Buy order initiation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 5: Initiate sell order
        print("\n5. Testing sell order initiation...")
        reference_id = f"test_sell_{uuid.uuid4().hex[:16]}"
        sell_init_data = {
            "crypto_amount": 5,
            "crypto_currency": "USDT",
            "fiat_currency": "UGX",
            "provider": "relworx",
            "phone_number": "256700000000",
            "reference_id": reference_id,
            "slippage_tolerance": 0.02
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/mobile-money/sell/initiate",
            headers=self.headers,
            json=sell_init_data
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Sell order initiated: {result['transaction_id']}")
            print(f"   Status: {result['status']}")
            print(f"   Reference ID: {result['reference_id']}")
            print(f"   Next steps: {result['next_steps']}")
        else:
            print(f"❌ Sell order initiation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 6: Get mobile money history
        print("\n6. Testing mobile money history...")
        response = requests.get(
            f"{self.base_url}/wallet/mobile-money/history",
            headers=self.headers,
            params={"limit": 10}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Mobile money history retrieved: {len(result['transactions'])} transactions")
        else:
            print(f"❌ Mobile money history failed: {response.status_code} - {response.text}")
            return False
        
        print("✅ Mobile money functionality tests completed successfully!")
        return True
    
    def test_payment_confirmation(self):
        """Test payment confirmation functionality"""
        print("\n💳 Testing Payment Confirmation...")
        
        if not hasattr(self, 'test_reference_id'):
            print("⚠️  No test reference ID available. Skipping payment confirmation test.")
            return True
        
        # Test 1: Confirm successful payment
        print("\n1. Testing successful payment confirmation...")
        confirm_data = {
            "reference_id": self.test_reference_id,
            "payment_status": "completed",
            "provider_reference": f"relworx_{int(time.time())}",
            "additional_data": {
                "phone_number": "256700000000",
                "transaction_time": time.time()
            }
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/mobile-money/confirm-payment",
            headers=self.headers,
            json=confirm_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Payment confirmation successful: {result['status']}")
            print(f"   Transaction ID: {result['transaction_id']}")
            print(f"   Message: {result['message']}")
        else:
            print(f"❌ Payment confirmation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 2: Test failed payment
        print("\n2. Testing failed payment handling...")
        failed_reference_id = f"test_failed_{uuid.uuid4().hex[:16]}"
        failed_data = {
            "reference_id": failed_reference_id,
            "payment_status": "failed",
            "provider_reference": f"relworx_failed_{int(time.time())}",
            "additional_data": {
                "failure_reason": "Insufficient funds",
                "phone_number": "256700000000"
            }
        }
        
        response = requests.post(
            f"{self.base_url}/wallet/mobile-money/confirm-payment",
            headers=self.headers,
            json=failed_data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Failed payment handling successful: {result['status']}")
            print(f"   Message: {result['message']}")
        else:
            print(f"❌ Failed payment handling failed: {response.status_code} - {response.text}")
            return False
        
        print("✅ Payment confirmation tests completed successfully!")
        return True
    
    def test_idempotency(self):
        """Test idempotency for all operations"""
        print("\n🔄 Testing Idempotency...")
        
        # Test 1: Swap idempotency
        print("\n1. Testing swap idempotency...")
        reference_id = f"idempotent_swap_{uuid.uuid4().hex[:16]}"
        swap_data = {
            "from_currency": "BTC",
            "to_currency": "ETH",
            "from_amount": 0.01,
            "reference_id": reference_id,
            "slippage_tolerance": 0.01
        }
        
        # First request
        response1 = requests.post(
            f"{self.base_url}/wallet/swap/execute",
            headers=self.headers,
            json=swap_data
        )
        
        if response1.status_code == 201:
            result1 = response1.json()
            print(f"✅ First swap request successful: {result1['swap_id']}")
            
            # Second request with same reference_id
            response2 = requests.post(
                f"{self.base_url}/wallet/swap/execute",
                headers=self.headers,
                json=swap_data
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                if result2.get('status') == 'idempotent':
                    print(f"✅ Swap idempotency working: {result2['message']}")
                else:
                    print(f"❌ Swap idempotency not working properly")
                    return False
            else:
                print(f"❌ Second swap request failed: {response2.status_code}")
                return False
        else:
            print(f"❌ First swap request failed: {response1.status_code}")
            return False
        
        # Test 2: Mobile money buy idempotency
        print("\n2. Testing mobile money buy idempotency...")
        reference_id = f"idempotent_buy_{uuid.uuid4().hex[:16]}"
        buy_data = {
            "fiat_amount": 1000,
            "fiat_currency": "UGX",
            "crypto_currency": "USDT",
            "provider": "relworx",
            "phone_number": "256700000000",
            "reference_id": reference_id
        }
        
        # First request
        response1 = requests.post(
            f"{self.base_url}/wallet/mobile-money/buy/initiate",
            headers=self.headers,
            json=buy_data
        )
        
        if response1.status_code == 201:
            result1 = response1.json()
            print(f"✅ First buy request successful: {result1['transaction_id']}")
            
            # Second request with same reference_id
            response2 = requests.post(
                f"{self.base_url}/wallet/mobile-money/buy/initiate",
                headers=self.headers,
                json=buy_data
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                if result2.get('status') == 'idempotent':
                    print(f"✅ Mobile money buy idempotency working: {result2['message']}")
                else:
                    print(f"❌ Mobile money buy idempotency not working properly")
                    return False
            else:
                print(f"❌ Second buy request failed: {response2.status_code}")
                return False
        else:
            print(f"❌ First buy request failed: {response1.status_code}")
            return False
        
        print("✅ Idempotency tests completed successfully!")
        return True
    
    def run_all_tests(self):
        """Run all tests"""
        print("🚀 Starting Swap and Mobile Money Tests...")
        print("=" * 60)
        
        try:
            # Run all test suites
            tests = [
                ("Swap Functionality", self.test_swap_functionality),
                ("Mobile Money Functionality", self.test_mobile_money_functionality),
                ("Payment Confirmation", self.test_payment_confirmation),
                ("Idempotency", self.test_idempotency)
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
            print("\n" + "=" * 60)
            print("📊 TEST SUMMARY")
            print("=" * 60)
            
            passed = 0
            total = len(results)
            
            for test_name, result in results:
                status = "✅ PASSED" if result else "❌ FAILED"
                print(f"{test_name}: {status}")
                if result:
                    passed += 1
            
            print(f"\nOverall Result: {passed}/{total} tests passed")
            
            if passed == total:
                print("🎉 All tests passed! Swap and Mobile Money functionality is working correctly.")
            else:
                print("⚠️  Some tests failed. Please check the implementation.")
            
            return passed == total
            
        except Exception as e:
            print(f"❌ Test suite failed with exception: {e}")
            return False

def main():
    """Main function to run tests"""
    print("Swap and Mobile Money Test Suite")
    print("=" * 40)
    
    # Check if token is provided
    if TEST_USER_TOKEN == "your_test_token_here":
        print("❌ Please set TEST_USER_TOKEN with a valid authentication token")
        print("   You can get this by logging into the wallet system")
        return
    
    # Create tester instance
    tester = SwapAndMobileMoneyTester(BASE_URL, TEST_USER_TOKEN)
    
    # Run all tests
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 Ready for production use!")
    else:
        print("\n🔧 Please fix the failing tests before deploying")

if __name__ == "__main__":
    main()
