#!/usr/bin/env python3
"""
Base Client using Alchemy API
Supports address balance queries, token balances, and real-time block monitoring
"""

import os
import json
import time
import threading
import socket
import ssl
import base64
import hashlib
import struct
import requests
from datetime import datetime
from typing import Dict, Optional, List

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BaseClient:
    """Base client using Alchemy API"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """
        Initialize Base client
        
        Args:
            api_key: Alchemy API key (optional, will use env var)
            network: Network to use (mainnet or testnet)
        """
        self.api_key = api_key or os.getenv('ALCHEMY_BASE_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.warning("⚠️  No ALCHEMY_BASE_API_KEY environment variable found.")
            logger.info("📝 Get your free API key at: https://www.alchemy.com/")
            logger.info("💡 Using provided API key for testing.")
            self.api_key = "EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Test key
        
        # Set up API URLs
        if network == "mainnet":
            self.api_url = f"https://base-mainnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://base-mainnet.g.alchemy.com/v2/{self.api_key}"
        else:
            self.api_url = f"https://base-sepolia.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://base-sepolia.g.alchemy.com/v2/{self.api_key}"
        
        logger.info(f"🔧 Initialized Base client for {network}")
        logger.info(f"📡 HTTP API URL: {self.api_url}")
        logger.info(f"🔌 WebSocket URL: {self.ws_url}")
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make JSON-RPC request to Base API"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params or []
            }
            
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ HTTP error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error making request: {e}")
            return None
    
    def get_latest_block_number(self) -> Optional[int]:
        """Get latest block number"""
        try:
            logger.info("🔍 Getting latest block number")
            
            response = self.make_request("eth_blockNumber")
            if response and 'result' in response:
                block_number = int(response['result'], 16)
                logger.info(f"✅ Latest block: {block_number:,}")
                return block_number
            else:
                logger.error("❌ Failed to get latest block number")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting latest block number: {e}")
            return None
    
    def get_balance(self, address: str) -> Optional[Dict]:
        """Get balance for a specific address"""
        try:
            logger.info(f"💰 Getting balance for {address}")
            
            response = self.make_request("eth_getBalance", [address, "latest"])
            if response and 'result' in response:
                balance_wei = int(response['result'], 16)
                balance_eth = balance_wei / (10 ** 18)
                
                result = {
                    "address": address,
                    "balance_wei": balance_wei,
                    "balance_eth": balance_eth,
                    "network": self.network
                }
                
                logger.info(f"✅ Balance for {address}: {balance_eth:.18f} ETH ({balance_wei} wei)")
                return result
            else:
                logger.error(f"❌ Failed to get balance for {address}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting balance for {address}: {e}")
            return None
    
    def get_account_info(self, address: str) -> Optional[Dict]:
        """Get account information (nonce and balance)"""
        try:
            logger.info(f"📋 Getting account info for {address}")
            
            # Get nonce
            nonce_response = self.make_request("eth_getTransactionCount", [address, "latest"])
            nonce = 0
            if nonce_response and 'result' in nonce_response:
                nonce = int(nonce_response['result'], 16)
            
            # Get balance
            balance_response = self.make_request("eth_getBalance", [address, "latest"])
            balance_wei = 0
            if balance_response and 'result' in balance_response:
                balance_wei = int(balance_response['result'], 16)
            
            result = {
                "address": address,
                "nonce": nonce,
                "balance_wei": balance_wei,
                "balance_eth": balance_wei / (10 ** 18),
                "network": self.network
            }
            
            logger.info(f"✅ Account info retrieved for {address}")
            return result
                
        except Exception as e:
            logger.error(f"❌ Error getting account info for {address}: {e}")
            return None
    
    def get_token_balance(self, token_address: str, wallet_address: str) -> Optional[Dict]:
        """Get token balance for a specific address"""
        try:
            logger.info(f"🪙 Getting token balance for {wallet_address}")
            
            # ERC-20 balanceOf function signature
            balance_of_signature = "0x70a08231"  # balanceOf(address)
            data = balance_of_signature + "000000000000000000000000" + wallet_address[2:]  # Remove 0x prefix
            
            response = self.make_request("eth_call", [
                {
                    "to": token_address,
                    "data": data
                },
                "latest"
            ])
            
            if response and 'result' in response:
                result_hex = response['result']
                
                # Handle empty or invalid responses
                if result_hex == "0x" or result_hex == "0x0" or not result_hex:
                    logger.warning(f"⚠️ Empty token balance response for {wallet_address}")
                    return {
                        "token_address": token_address,
                        "wallet_address": wallet_address,
                        "balance_wei": 0,
                        "balance_token": 0.0,
                        "decimals": 18,
                        "network": self.network,
                        "note": "Token contract may not exist or have no balance"
                    }
                
                try:
                    balance_wei = int(result_hex, 16)
                except ValueError as e:
                    logger.error(f"❌ Error parsing token balance: {e}")
                    return None
                
                # Try to get token decimals
                decimals_response = self.make_request("eth_call", [
                    {
                        "to": token_address,
                        "data": "0x313ce567"  # decimals()
                    },
                    "latest"
                ])
                
                decimals = 18  # Default to 18
                if decimals_response and 'result' in decimals_response:
                    try:
                        decimals = int(decimals_response['result'], 16)
                    except ValueError:
                        logger.warning(f"⚠️ Could not parse token decimals, using default 18")
                
                balance_token = balance_wei / (10 ** decimals)
                
                result = {
                    "token_address": token_address,
                    "wallet_address": wallet_address,
                    "balance_wei": balance_wei,
                    "balance_token": balance_token,
                    "decimals": decimals,
                    "network": self.network
                }
                
                logger.info(f"✅ Token balance for {wallet_address}: {balance_token:.{decimals}f}")
                return result
            else:
                logger.error(f"❌ Failed to get token balance for {wallet_address}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting token balance for {wallet_address}: {e}")
            return None
    
    def get_block_by_number(self, block_number: int) -> Optional[Dict]:
        """Get block information by number"""
        try:
            logger.info(f"📦 Getting block {block_number}")
            
            response = self.make_request("eth_getBlockByNumber", [hex(block_number), True])
            if response and 'result' in response:
                block_data = response['result']
                
                if block_data:
                    result = {
                        "number": int(block_data.get('number', '0'), 16),
                        "hash": block_data.get('hash'),
                        "parent_hash": block_data.get('parentHash'),
                        "timestamp": int(block_data.get('timestamp', '0'), 16),
                        "gas_limit": int(block_data.get('gasLimit', '0'), 16),
                        "gas_used": int(block_data.get('gasUsed', '0'), 16),
                        "miner": block_data.get('miner'),
                        "transactions": block_data.get('transactions', []),
                        "transaction_count": len(block_data.get('transactions', [])),
                        "network": self.network
                    }
                    
                    logger.info(f"✅ Retrieved block {block_number}")
                    return result
                else:
                    logger.error(f"❌ Block {block_number} not found")
                    return None
            else:
                logger.error(f"❌ Failed to get block {block_number}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting block {block_number}: {e}")
            return None
    
    def get_recent_blocks(self, limit: int = 10) -> Optional[List[Dict]]:
        """Get recent blocks"""
        try:
            logger.info(f"📦 Getting {limit} recent blocks")
            
            latest_block = self.get_latest_block_number()
            if latest_block is None:
                logger.error("❌ Could not get latest block number")
                return None
            
            blocks = []
            for i in range(limit):
                block_number = latest_block - i
                if block_number >= 0:
                    block_data = self.get_block_by_number(block_number)
                    if block_data:
                        blocks.append(block_data)
            
            logger.info(f"✅ Retrieved {len(blocks)} recent blocks")
            return blocks
                
        except Exception as e:
            logger.error(f"❌ Error getting recent blocks: {e}")
            return None


class BaseWebSocketClient:
    """Base WebSocket client for real-time monitoring"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize Base WebSocket client"""
        self.api_key = api_key or os.getenv('ALCHEMY_BASE_API_KEY')
        self.network = network
        self.websocket = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        # Set up WebSocket URL
        if network == "mainnet":
            self.ws_url = f"wss://base-mainnet.g.alchemy.com/v2/{self.api_key}"
        else:
            self.ws_url = f"wss://base-sepolia.g.alchemy.com/v2/{self.api_key}"
        
        logger.info(f"🔧 Initialized Base WebSocket client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
    
    async def connect_and_subscribe(self):
        """Connect to WebSocket and subscribe to new blocks"""
        try:
            # Import websockets here to avoid import issues
            import websockets
            
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers={
                    "User-Agent": "Base-Client/1.0",
                    "Accept": "*/*"
                }
            )
            
            self.is_connected = True
            logger.info("🔌 WebSocket connection opened")
            
            # Subscribe to new blocks
            subscription_message = {
                "jsonrpc": "2.0",
                "method": "eth_subscribe",
                "params": ["newHeads"],
                "id": 1
            }
            
            await self.websocket.send(json.dumps(subscription_message))
            logger.info("📡 Subscribed to Base new blocks")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error connecting to WebSocket: {e}")
            return False
    
    def _handle_new_block(self, block_data):
        """Handle new block data"""
        try:
            if 'params' in block_data and 'result' in block_data['params']:
                block = block_data['params']['result']
                
                # Extract block information
                block_number = int(block.get('number', '0'), 16)
                block_hash = block.get('hash', '')
                timestamp = int(block.get('timestamp', '0'), 16)
                gas_used = int(block.get('gasUsed', '0'), 16)
                gas_limit = int(block.get('gasLimit', '0'), 16)
                miner = block.get('miner', '')
                
                # Calculate gas usage percentage
                gas_percentage = (gas_used / gas_limit * 100) if gas_limit > 0 else 0
                
                # Calculate blocks per minute
                current_time = time.time()
                if self.start_time:
                    elapsed = current_time - self.start_time
                    blocks_per_minute = (self.block_count / elapsed * 60) if elapsed > 0 else 0
                else:
                    blocks_per_minute = 0
                
                self.block_count += 1
                
                # Display block information
                print("=" * 80)
                print(f"🆕 NEW BASE BLOCK #{block_number}")
                print("=" * 80)
                print(f"📅 Time: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"🔗 Hash: {block_hash}")
                print(f"⛏️  Miner: {miner}")
                print(f"⛽ Gas Used: {gas_used:,} / {gas_limit:,} ({gas_percentage:.1f}%)")
                print(f"📈 Total Blocks Received: {self.block_count}")
                print(f"⏱️  Blocks per minute: {blocks_per_minute:.2f}")
                print("=" * 80)
                print()
                
        except Exception as e:
            logger.error(f"❌ Error handling new block: {e}")
    
    async def listen_for_messages(self):
        """Listen for WebSocket messages"""
        try:
            import websockets
            
            async for message in self.websocket:
                if not self.is_running:
                    break
                
                try:
                    data = json.loads(message)
                    
                    # Handle subscription confirmation
                    if 'result' in data and isinstance(data['result'], str):
                        logger.info(f"✅ Subscription confirmed: {data['result']}")
                    
                    # Handle new block
                    elif 'params' in data:
                        self._handle_new_block(data)
                    
                    # Handle error responses
                    elif 'error' in data:
                        logger.error(f"❌ WebSocket error: {data['error']}")
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Received non-JSON message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("🔌 WebSocket connection closed")
        except Exception as e:
            logger.error(f"❌ Error in message loop: {e}")
        finally:
            self.is_connected = False
    
    async def start_monitoring(self, duration: int = 300):
        """Start real-time block monitoring"""
        try:
            logger.info("🚀 Starting real-time Base block monitoring...")
            
            # Connect and subscribe
            if not await self.connect_and_subscribe():
                logger.error("❌ Failed to connect and subscribe")
                return
            
            self.is_running = True
            self.start_time = time.time()
            self.block_count = 0
            
            # Display monitoring info
            print("=" * 80)
            print("🔧 REAL-TIME BASE BLOCK MONITOR")
            print("=" * 80)
            print(f"📡 Network: {self.network}")
            print(f"🔌 WebSocket: {self.ws_url}")
            print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  Duration: {duration} seconds")
            print("=" * 80)
            print("⏳ Waiting for new blocks...")
            print("=" * 80)
            
            # Start listening for messages
            import asyncio
            await asyncio.wait_for(
                self.listen_for_messages(),
                timeout=duration
            )
            
        except asyncio.TimeoutError:
            logger.info(f"⏰ Monitoring completed after {duration} seconds")
        except Exception as e:
            logger.error(f"❌ Error starting monitoring: {e}")
        finally:
            self.is_running = False
            self.is_connected = False
            
            # Display final statistics
            total_time = time.time() - self.start_time if self.start_time else 0
            blocks_per_minute = (self.block_count / total_time * 60) if total_time > 0 else 0
            
            print("=" * 80)
            print("📊 MONITORING STATISTICS")
            print("=" * 80)
            print(f"📈 Total Blocks Received: {self.block_count}")
            print(f"⏱️  Total Time: {total_time:.1f} seconds")
            print(f"📊 Average Blocks per Minute: {blocks_per_minute:.2f}")
            print("=" * 80)
    
    async def stop_monitoring(self):
        """Stop real-time monitoring"""
        logger.info("⏹️  Stopping monitoring...")
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
        logger.info("🔌 WebSocket disconnected")


def test_base_api():
    """Test Base API functionality"""
    print("🔧 Base API Test")
    print("📡 Using Alchemy Base API")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_BASE_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_BASE_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        api_key = "EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Test key
    
    # Create client
    client = BaseClient(api_key=api_key, network="mainnet")
    
    # Test 1: Get latest block number
    print("\n🔍 Test 1: Getting latest block number")
    latest_block = client.get_latest_block_number()
    if latest_block:
        print(f"✅ Latest block: {latest_block:,}")
    else:
        print("❌ Failed to get latest block number")
    
    # Test 2: Get balances for Base addresses
    print("\n🔍 Test 2: Getting balances for Base addresses")
    test_addresses = [
        {"name": "Base Foundation", "address": "0x0000000000000000000000000000000000000000"},
        {"name": "Base Treasury", "address": "0x0000000000000000000000000000000000000001"},
        {"name": "Uniswap V3 Router", "address": "0xE592427A0AEce92De3Edee1F18E0157C05861564"},
        {"name": "Aave V3 Pool", "address": "0x794a61358D6845594F94dc1DB02A252b5b4814aD"}
    ]
    
    for addr_info in test_addresses:
        print(f"\n📍 {addr_info['name']}: {addr_info['address']}")
        balance = client.get_balance(addr_info['address'])
        if balance:
            print(f"✅ Balance: {balance['balance_eth']:.6f} ETH")
        else:
            print("❌ Balance error: Failed to get balance")
    
    # Test 3: Get account info
    print("\n🔍 Test 3: Getting account info")
    account_info = client.get_account_info(test_addresses[0]['address'])
    if account_info:
        print(f"✅ Nonce: {account_info['nonce']}")
        print(f"✅ Balance: {account_info['balance_eth']:.6f} ETH")
    else:
        print("❌ Account info error: Failed to get account info")
    
    # Test 4: Get USDC token balance
    print("\n🔍 Test 4: Getting USDC token balance")
    usdc_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC on Base
    token_balance = client.get_token_balance(usdc_address, test_addresses[0]['address'])
    if token_balance:
        if token_balance.get('note'):
            print(f"⚠️ {token_balance['note']}")
        print(f"✅ USDC Balance: {token_balance['balance_token']:.2f} USDC")
    else:
        print("❌ Failed to get token balance")
    
    # Test 5: Get recent blocks
    print("\n🔍 Test 5: Getting recent blocks")
    recent_blocks = client.get_recent_blocks(limit=3)
    if recent_blocks:
        print(f"✅ Retrieved {len(recent_blocks)} recent blocks")
        for block in recent_blocks:
            print(f"   Block {block['number']}: {block['transaction_count']} transactions")
    else:
        print("❌ Failed to get recent blocks")
    
    print("\n" + "=" * 80)
    print("🚀 Starting real-time block monitoring...")
    print("=" * 80)


async def main():
    """Main function"""
    print("🔧 Base Client")
    print("📡 Using Alchemy Base API")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_BASE_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_BASE_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        api_key = "EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Test key
    
    # Test HTTP API first
    test_base_api()
    
    # Create WebSocket client
    client = BaseWebSocketClient(api_key=api_key, network="mainnet")
    
    try:
        # Start monitoring for 5 minutes
        await client.start_monitoring(duration=300)
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        await client.stop_monitoring()
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")
        await client.stop_monitoring()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 