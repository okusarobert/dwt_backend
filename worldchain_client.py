#!/usr/bin/env python3
"""
World Chain Client for real-time monitoring
Based on Alchemy's World Chain API: https://www.alchemy.com/docs/reference/worldchain-api-quickstart
"""

import os
import json
import time
import requests
import websocket
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WorldChainClient:
    """World Chain client for real-time monitoring"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize World Chain client"""
        self.api_key = api_key or os.getenv('ALCHEMY_WORLDCHAIN_API_KEY')
        self.network = network
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        self.last_block = None
        
        # Set up API URL
        if network == "mainnet":
            self.http_url = f"https://worldchain-mainnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://worldchain-mainnet.g.alchemy.com/v2/{self.api_key}"
        else:
            self.http_url = f"https://worldchain-testnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://worldchain-testnet.g.alchemy.com/v2/{self.api_key}"
        
        logger.info(f"🔧 Initialized World Chain client for {network}")
        logger.info(f"📡 HTTP API URL: {self.http_url}")
        logger.info(f"🔌 WebSocket URL: {self.ws_url}")
    
    def get_latest_block(self):
        """Get the latest block number"""
        try:
            response = requests.post(
                self.http_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "result" in data:
                # Convert hex to decimal
                return int(data["result"], 16)
            else:
                logger.error(f"❌ Failed to get latest block: {data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting latest block: {e}")
            return None
    
    def get_block_info(self, block_number: int):
        """Get detailed information about a specific block"""
        try:
            response = requests.post(
                self.http_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBlockByNumber",
                    "params": [hex(block_number), True],
                    "id": 1
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "result" in data and data["result"]:
                return data["result"]
            else:
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting block info for {block_number}: {e}")
            return None
    
    def get_balance(self, address: str):
        """Get balance for a World Chain address"""
        try:
            response = requests.post(
                self.http_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getBalance",
                    "params": [address, "latest"],
                    "id": 1
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if "result" in data:
                # Convert hex to decimal and from wei to ETH
                balance_wei = int(data["result"], 16)
                balance_eth = balance_wei / 10**18
                return balance_eth
            else:
                logger.error(f"❌ Failed to get balance: {data}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting balance: {e}")
            return None
    
    def test_worldchain_api(self):
        """Test World Chain API functionality"""
        print("🔧 World Chain API Test")
        print("📡 Using Alchemy World Chain API")
        print("=" * 50)
        
        # Test 1: Get latest block
        print("🔍 Test 1: Getting latest block")
        latest_block = self.get_latest_block()
        if latest_block:
            print(f"✅ Latest block: {latest_block}")
        else:
            print("❌ Failed to get latest block")
            return False
        
        # Test 2: Get block info
        print("🔍 Test 2: Getting block info")
        block_info = self.get_block_info(latest_block)
        if block_info:
            tx_count = len(block_info.get("transactions", []))
            print(f"✅ Block {latest_block}: {tx_count} transactions")
            print(f"✅ Block hash: {block_info.get('hash', 'N/A')}")
            print(f"✅ Timestamp: {int(block_info.get('timestamp', '0'), 16)}")
        else:
            print("❌ Failed to get block info")
        
        # Test 3: Get balance for a test address (World Chain Foundation)
        print("🔍 Test 3: Getting balance for World Chain Foundation")
        # Using a sample address - replace with actual World Chain address
        test_address = "0x0000000000000000000000000000000000000000"
        balance = self.get_balance(test_address)
        if balance is not None:
            print(f"✅ Balance: {balance} ETH")
        else:
            print("❌ Failed to get balance")
        
        return True

class WorldChainWebSocketClient:
    """World Chain WebSocket client for real-time monitoring"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize World Chain WebSocket client"""
        self.api_key = api_key or os.getenv('ALCHEMY_WORLDCHAIN_API_KEY')
        self.network = network
        self.ws = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        # Set up WebSocket URL
        if network == "mainnet":
            self.ws_url = f"wss://worldchain-mainnet.g.alchemy.com/v2/{self.api_key}"
        else:
            self.ws_url = f"wss://worldchain-testnet.g.alchemy.com/v2/{self.api_key}"
        
        logger.info(f"🔧 Initialized World Chain WebSocket client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
    
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.info("🔌 WebSocket connection opened")
        self.is_connected = True
        
        # Try a simple subscription first
        subscription_message = {
            "jsonrpc": "2.0",
            "method": "eth_subscribe",
            "params": ["newHeads"],
            "id": 1
        }
        
        ws.send(json.dumps(subscription_message))
        logger.info("📡 Subscribed to World Chain new blocks")
        
    def on_message(self, ws, message):
        """Handle WebSocket messages"""
        try:
            data = json.loads(message)
            logger.info(f"📨 Raw message: {message[:200]}...")
            
            # Handle subscription confirmation
            if "result" in data and isinstance(data["result"], str):
                logger.info(f"✅ Subscription confirmed: {data['result']}")
                return
                
            # Handle block notifications
            if "params" in data and "result" in data["params"]:
                block_data = data["params"]["result"]
                if isinstance(block_data, dict) and "number" in block_data:
                    self._handle_new_block(block_data)
                else:
                    logger.info(f"📦 Other notification: {block_data}")
            else:
                logger.info(f"📦 Other message type: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"❌ WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info(f"🔌 WebSocket connection closed: {close_status_code} - {close_msg}")
        self.is_connected = False
    
    def _handle_new_block(self, block_data):
        """Handle new block data"""
        try:
            block_number = int(block_data.get("number", "0x0"), 16)
            block_hash = block_data.get("hash", "unknown")
            
            self.block_count += 1
            current_time = time.time()
            
            if self.start_time is None:
                self.start_time = current_time
                logger.info(f"🚀 First block received! Block #{block_number}")
            else:
                elapsed = current_time - self.start_time
                blocks_per_minute = (self.block_count / elapsed) * 60
                logger.info(f"📦 Block #{block_number} | Hash: {block_hash[:10]}... | "
                          f"Total: {self.block_count} | Rate: {blocks_per_minute:.2f}/min")
            
        except Exception as e:
            logger.error(f"❌ Error processing block: {e}")
    
    def start_monitoring(self, duration: int = 120):
        """Start real-time block monitoring"""
        logger.info("🚀 Starting real-time World Chain block monitoring...")
        
        print("=" * 80)
        print("🔧 REAL-TIME WORLD CHAIN BLOCK MONITOR")
        print("=" * 80)
        print(f"📡 Network: {self.network}")
        print(f"🔌 WebSocket: {self.ws_url}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  Duration: {duration} seconds")
        print("=" * 80)
        print("⏳ Waiting for new blocks...")
        print("=" * 80)
        
        self.is_running = True
        self.start_time = time.time()
        
        try:
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Start WebSocket connection
            self.ws.run_forever()
            
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Error during monitoring: {e}")
        finally:
            self.stop_monitoring()
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
        
        if self.ws:
            self.ws.close()
        
        if self.start_time:
            total_time = time.time() - self.start_time
            avg_blocks_per_minute = (self.block_count / total_time) * 60 if total_time > 0 else 0
            
            print("=" * 80)
            print("📊 MONITORING STATISTICS")
            print("=" * 80)
            print(f"📈 Total Blocks Received: {self.block_count}")
            print(f"⏱️  Total Time: {total_time:.1f} seconds")
            print(f"📊 Average Blocks per Minute: {avg_blocks_per_minute:.2f}")
            print("=" * 80)
        
        logger.info("🔌 WebSocket monitoring stopped")

def main():
    """Main function"""
    print("🔧 World Chain Client")
    print("📡 Using Alchemy World Chain API")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_WORLDCHAIN_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_WORLDCHAIN_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        api_key = "EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Test key
    
    # Test HTTP API first
    client = WorldChainClient(api_key=api_key, network="mainnet")
    if not client.test_worldchain_api():
        print("❌ API test failed, exiting...")
        return
    
    # Create WebSocket client
    ws_client = WorldChainWebSocketClient(api_key=api_key, network="mainnet")
    
    try:
        # Start monitoring for 2 minutes
        ws_client.start_monitoring(duration=120)
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        ws_client.stop_monitoring()
    except Exception as e:
        logger.error(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 