#!/usr/bin/env python3
"""
Test different LTC testnet servers for rate limiting
"""

import asyncio
import aiohttp
import json
import sys
import time

class LTCServerTester:
    def __init__(self):
        self.auth = aiohttp.BasicAuth("okusa", "uQa4nq5kkDsjILyiDgxJc4bCVrLnt8NQRWsuHCB27jg")
        self.test_address = "n2t1mXrfuCRF4FC94B4746tUSHZm6BSqeQ"
        
        # List of known LTC testnet servers
        self.servers = [
            "testnet.blockstream.info:995",
            "electrum-ltc-testnet.criptolayer.net:51001", 
            "testnet.ltc.bitaps.com:995",
            "electrum-ltc.bysh.me:51001",
            "electrum.ltc.xurious.com:51001"
        ]

    async def test_server_connection(self, server):
        """Test basic connection to a server"""
        print(f"🔍 Testing server: {server}")
        
        try:
            # Test basic connectivity
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                # Try to connect to the server
                url = f"http://{server}"
                async with session.get(url) as response:
                    print(f"   ✅ Server {server} is reachable")
                    return True
        except Exception as e:
            print(f"   ❌ Server {server} failed: {str(e)}")
            return False

    async def test_server_rpc(self, server):
        """Test RPC calls to a server"""
        print(f"🔍 Testing RPC for server: {server}")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getinfo",
            "params": {}
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15), auth=self.auth) as session:
                url = f"http://{server}"
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        if 'result' in data:
                            print(f"   ✅ RPC successful for {server}")
                            print(f"   Network: {data['result'].get('network', 'unknown')}")
                            print(f"   Connected: {data['result'].get('connected', False)}")
                            return True
                        else:
                            print(f"   ❌ RPC failed for {server}: {data}")
                            return False
                    else:
                        print(f"   ❌ HTTP {response.status} for {server}")
                        return False
        except Exception as e:
            print(f"   ❌ RPC error for {server}: {str(e)}")
            return False

    async def test_rate_limiting(self, server):
        """Test rate limiting by making multiple requests"""
        print(f"🔍 Testing rate limiting for server: {server}")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getaddresshistory",
            "params": [self.test_address]
        }
        
        success_count = 0
        error_count = 0
        
        for i in range(3):  # Make 3 requests
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10), auth=self.auth) as session:
                    url = f"http://{server}"
                    async with session.post(url, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            if 'error' in data:
                                error_msg = data['error'].get('message', '')
                                if 'excessive resource usage' in error_msg:
                                    print(f"   ❌ Rate limited on request {i+1}")
                                    error_count += 1
                                else:
                                    print(f"   ✅ Request {i+1} successful")
                                    success_count += 1
                            else:
                                print(f"   ✅ Request {i+1} successful")
                                success_count += 1
                        else:
                            print(f"   ❌ HTTP {response.status} on request {i+1}")
                            error_count += 1
                
                # Small delay between requests
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"   ❌ Error on request {i+1}: {str(e)}")
                error_count += 1
        
        print(f"   📊 Results: {success_count} successful, {error_count} failed")
        return success_count > error_count

    async def test_all_servers(self):
        """Test all servers"""
        print("🚀 Testing LTC Testnet Servers for Rate Limiting")
        print("=" * 60)
        
        results = {}
        
        for server in self.servers:
            print(f"\n📋 Testing: {server}")
            print("-" * 40)
            
            # Test basic connection
            connection_ok = await self.test_server_connection(server)
            
            if connection_ok:
                # Test RPC
                rpc_ok = await self.test_server_rpc(server)
                
                if rpc_ok:
                    # Test rate limiting
                    rate_limit_ok = await self.test_rate_limiting(server)
                    
                    results[server] = {
                        "connection": connection_ok,
                        "rpc": rpc_ok,
                        "rate_limit": rate_limit_ok,
                        "overall": rate_limit_ok
                    }
                else:
                    results[server] = {
                        "connection": connection_ok,
                        "rpc": False,
                        "rate_limit": False,
                        "overall": False
                    }
            else:
                results[server] = {
                    "connection": False,
                    "rpc": False,
                    "rate_limit": False,
                    "overall": False
                }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 SERVER TEST SUMMARY")
        print("=" * 60)
        
        good_servers = []
        for server, result in results.items():
            status = "✅" if result["overall"] else "❌"
            print(f"{status} {server}")
            if result["overall"]:
                good_servers.append(server)
        
        print(f"\n🎯 Recommended servers (no rate limiting):")
        if good_servers:
            for server in good_servers:
                print(f"   ✅ {server}")
        else:
            print("   ❌ No servers found without rate limiting")
        
        return good_servers

async def main():
    """Main function"""
    tester = LTCServerTester()
    
    try:
        good_servers = await tester.test_all_servers()
        if good_servers:
            print(f"\n🎉 Found {len(good_servers)} server(s) without rate limiting!")
            return 0
        else:
            print(f"\n⚠️  All servers have rate limiting issues")
            return 1
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main())) 