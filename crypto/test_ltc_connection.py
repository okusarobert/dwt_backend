#!/usr/bin/env python3
"""
Focused test script for LTC daemon connectivity
"""

import asyncio
import aiohttp
import json
import sys
import time

class LTCConnectionTester:
    def __init__(self):
        self.ltc_host = "ltc"
        self.ltc_port = 5001
        self.base_url = "http://{}:{}".format(self.ltc_host, self.ltc_port)
        
    async def test_websocket_endpoint(self):
        """Test the websocket endpoint"""
        url = "{}/ws".format(self.base_url)
        print("🔍 Testing WebSocket endpoint: {}".format(url))
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    print("   Status Code: {}".format(response.status))
                    print("   Headers: {}".format(dict(response.headers)))
                    
                    if response.status == 200:
                        print("   ✅ WebSocket endpoint is accessible")
                        return True
                    else:
                        print("   ❌ WebSocket endpoint returned status {}".format(response.status))
                        return False
        except Exception as e:
            print("   ❌ WebSocket endpoint error: {}".format(str(e)))
            return False

    async def test_rpc_getinfo(self):
        """Test RPC getinfo call"""
        url = self.base_url
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getinfo",
            "params": {}
        }
        
        print("🔍 Testing RPC getinfo: {}".format(url))
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.post(url, json=payload) as response:
                    print("   Status Code: {}".format(response.status))
                    
                    if response.status == 200:
                        data = await response.json()
                        print("   ✅ RPC getinfo successful")
                        print("   Response: {}".format(json.dumps(data, indent=2)))
                        return True
                    else:
                        print("   ❌ RPC getinfo failed with status {}".format(response.status))
                        return False
        except Exception as e:
            print("   ❌ RPC getinfo error: {}".format(str(e)))
            return False

    async def test_rpc_getaddressbalance(self):
        """Test RPC getaddressbalance call with a testnet address"""
        url = self.base_url
        test_address = "n2t1mXrfuCRF4FC94B4746tUSHZm6BSqeQ"  # LTC testnet address
        
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "getaddressbalance",
            "params": [test_address]
        }
        
        print("🔍 Testing RPC getaddressbalance for {}".format(test_address))
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.post(url, json=payload) as response:
                    print("   Status Code: {}".format(response.status))
                    
                    if response.status == 200:
                        data = await response.json()
                        print("   ✅ RPC getaddressbalance successful")
                        print("   Response: {}".format(json.dumps(data, indent=2)))
                        return True
                    else:
                        print("   ❌ RPC getaddressbalance failed with status {}".format(response.status))
                        return False
        except Exception as e:
            print("   ❌ RPC getaddressbalance error: {}".format(str(e)))
            return False

    async def test_network_connection(self):
        """Test if LTC daemon can connect to Electrum servers"""
        url = self.base_url
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "getinfo",
            "params": {}
        }
        
        print("🔍 Testing network connection status")
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check if there's network info in the response
                        if 'result' in data:
                            result = data['result']
                            print("   ✅ Network connection test successful")
                            print("   Network info: {}".format(json.dumps(result, indent=2)))
                            return True
                        else:
                            print("   ⚠️  No network info in response")
                            return False
                    else:
                        print("   ❌ Network test failed with status {}".format(response.status))
                        return False
        except Exception as e:
            print("   ❌ Network test error: {}".format(str(e)))
            return False

    async def run_all_tests(self):
        """Run all LTC connection tests"""
        print("🚀 Starting LTC Daemon Connection Tests")
        print("=" * 60)
        
        tests = [
            ("WebSocket Endpoint", self.test_websocket_endpoint),
            ("RPC getinfo", self.test_rpc_getinfo),
            ("RPC getaddressbalance", self.test_rpc_getaddressbalance),
            ("Network Connection", self.test_network_connection)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            print("-" * 40)
            
            start_time = time.time()
            success = await test_func()
            end_time = time.time()
            
            results[test_name] = {
                "success": success,
                "duration": end_time - start_time
            }
            
            status = "✅ PASSED" if success else "❌ FAILED"
            print("   {} ({:.2f}s)".format(status, end_time - start_time))
            
            # Add delay between tests
            await asyncio.sleep(1)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 LTC CONNECTION TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in results.values() if result["success"])
        total = len(results)
        
        print("✅ Passed: {}/{}".format(passed, total))
        print("❌ Failed: {}/{}".format(total - passed, total))
        
        for test_name, result in results.items():
            status = "✅" if result["success"] else "❌"
            print("{} {} ({:.2f}s)".format(status, test_name, result['duration']))
        
        if passed == total:
            print("\n🎉 All LTC tests passed!")
            return True
        else:
            print("\n⚠️  {} test(s) failed".format(total - passed))
            return False

async def main():
    """Main function"""
    tester = LTCConnectionTester()
    
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 