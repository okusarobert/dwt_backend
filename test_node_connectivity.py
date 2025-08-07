#!/usr/bin/env python3
"""
Test script to verify connectivity to cryptocurrency daemon nodes
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, List, Optional
import time

# Node configurations
NODES = {
    "LTC": {
        "host": "ltc",
        "port": 5001,
        "endpoint": "/ws",
        "description": "Litecoin Testnet Daemon"
    },
    "BTC": {
        "host": "btc", 
        "port": 5000,
        "endpoint": "/ws",
        "description": "Bitcoin Testnet Daemon"
    },
    "ETH": {
        "host": "eth",
        "port": 5008,
        "endpoint": "/ws", 
        "description": "Ethereum Testnet Daemon"
    },
    "TRX": {
        "host": "trx",
        "port": 5009,
        "endpoint": "/ws",
        "description": "Tron Testnet Daemon"
    },
    "XMR": {
        "host": "xmr",
        "port": 5008,
        "endpoint": "/ws",
        "description": "Monero Testnet Daemon"
    },
    "BNB": {
        "host": "bnb",
        "port": 5008,
        "endpoint": "/ws",
        "description": "Binance Smart Chain Testnet Daemon"
    },
    "BCH": {
        "host": "bch",
        "port": 5008,
        "endpoint": "/ws",
        "description": "Bitcoin Cash Testnet Daemon"
    },
    "POL": {
        "host": "pol",
        "port": 5008,
        "endpoint": "/ws",
        "description": "Polygon Testnet Daemon"
    }
}

class NodeConnectivityTester:
    def __init__(self):
        self.results = {}
        
    async def test_http_connectivity(self, node_name: str, config: Dict) -> Dict:
        """Test HTTP connectivity to a node"""
        url = f"http://{config['host']}:{config['port']}{config['endpoint']}"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return {
                            "status": "SUCCESS",
                            "url": url,
                            "response_code": response.status,
                            "message": f"Successfully connected to {node_name}"
                        }
                    else:
                        return {
                            "status": "HTTP_ERROR",
                            "url": url,
                            "response_code": response.status,
                            "message": f"HTTP error {response.status} for {node_name}"
                        }
        except aiohttp.ClientConnectorError as e:
            return {
                "status": "CONNECTION_ERROR",
                "url": url,
                "error": str(e),
                "message": f"Cannot connect to {node_name}: {str(e)}"
            }
        except asyncio.TimeoutError:
            return {
                "status": "TIMEOUT",
                "url": url,
                "message": f"Connection timeout for {node_name}"
            }
        except Exception as e:
            return {
                "status": "UNKNOWN_ERROR",
                "url": url,
                "error": str(e),
                "message": f"Unknown error for {node_name}: {str(e)}"
            }

    async def test_rpc_call(self, node_name: str, config: Dict) -> Dict:
        """Test RPC call to a node"""
        url = f"http://{config['host']}:{config['port']}"
        
        # Simple RPC call to get info
        rpc_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getinfo",
            "params": {}
        }
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.post(url, json=rpc_payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "status": "SUCCESS",
                            "url": url,
                            "response_code": response.status,
                            "rpc_response": data,
                            "message": f"RPC call successful for {node_name}"
                        }
                    else:
                        return {
                            "status": "HTTP_ERROR",
                            "url": url,
                            "response_code": response.status,
                            "message": f"RPC HTTP error {response.status} for {node_name}"
                        }
        except aiohttp.ClientConnectorError as e:
            return {
                "status": "CONNECTION_ERROR",
                "url": url,
                "error": str(e),
                "message": f"RPC connection failed for {node_name}: {str(e)}"
            }
        except asyncio.TimeoutError:
            return {
                "status": "TIMEOUT",
                "url": url,
                "message": f"RPC timeout for {node_name}"
            }
        except Exception as e:
            return {
                "status": "UNKNOWN_ERROR",
                "url": url,
                "error": str(e),
                "message": f"RPC unknown error for {node_name}: {str(e)}"
            }

    async def test_node(self, node_name: str, config: Dict) -> Dict:
        """Test both HTTP connectivity and RPC functionality for a node"""
        print(f"Testing {node_name} ({config['description']})...")
        
        # Test HTTP connectivity
        http_result = await self.test_http_connectivity(node_name, config)
        
        # Test RPC call
        rpc_result = await self.test_rpc_call(node_name, config)
        
        return {
            "node_name": node_name,
            "description": config["description"],
            "http_test": http_result,
            "rpc_test": rpc_result,
            "overall_status": "SUCCESS" if http_result["status"] == "SUCCESS" and rpc_result["status"] == "SUCCESS" else "FAILED"
        }

    async def test_all_nodes(self) -> Dict:
        """Test all configured nodes"""
        print("🔍 Starting node connectivity tests...")
        print("=" * 60)
        
        results = {}
        
        for node_name, config in NODES.items():
            result = await self.test_node(node_name, config)
            results[node_name] = result
            
            # Print immediate result
            status_emoji = "✅" if result["overall_status"] == "SUCCESS" else "❌"
            print(f"{status_emoji} {node_name}: {result['overall_status']}")
            
            # Add delay between tests to avoid overwhelming the system
            await asyncio.sleep(1)
        
        return results

    def print_summary(self, results: Dict):
        """Print a detailed summary of test results"""
        print("\n" + "=" * 60)
        print("📊 NODE CONNECTIVITY TEST SUMMARY")
        print("=" * 60)
        
        successful_nodes = []
        failed_nodes = []
        
        for node_name, result in results.items():
            if result["overall_status"] == "SUCCESS":
                successful_nodes.append(node_name)
            else:
                failed_nodes.append(node_name)
        
        print(f"✅ Successful connections: {len(successful_nodes)}")
        if successful_nodes:
            print(f"   - {', '.join(successful_nodes)}")
        
        print(f"❌ Failed connections: {len(failed_nodes)}")
        if failed_nodes:
            print(f"   - {', '.join(failed_nodes)}")
        
        print("\n" + "=" * 60)
        print("📋 DETAILED RESULTS")
        print("=" * 60)
        
        for node_name, result in results.items():
            print(f"\n🔸 {node_name} ({result['description']})")
            print(f"   Overall Status: {result['overall_status']}")
            
            print(f"   HTTP Test:")
            print(f"     Status: {result['http_test']['status']}")
            print(f"     Message: {result['http_test']['message']}")
            
            print(f"   RPC Test:")
            print(f"     Status: {result['rpc_test']['status']}")
            print(f"     Message: {result['rpc_test']['message']}")
            
            if result['rpc_test']['status'] == 'SUCCESS' and 'rpc_response' in result['rpc_test']:
                print(f"     RPC Response: {json.dumps(result['rpc_test']['rpc_response'], indent=6)}")

async def main():
    """Main function to run the connectivity tests"""
    tester = NodeConnectivityTester()
    
    try:
        results = await tester.test_all_nodes()
        tester.print_summary(results)
        
        # Return appropriate exit code
        failed_count = sum(1 for result in results.values() if result["overall_status"] == "FAILED")
        if failed_count > 0:
            print(f"\n⚠️  {failed_count} node(s) failed connectivity tests")
            sys.exit(1)
        else:
            print(f"\n🎉 All nodes are accessible!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 