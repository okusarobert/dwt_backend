#!/usr/bin/env python3
"""
Real-time Ethereum WebSocket Client using Alchemy
Subscribes to new blocks and displays them in real-time
"""

import os
import json
import time
import threading
import websocket
import requests
from datetime import datetime
from typing import Dict, Optional

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlchemyRealtimeClient:
    """Real-time Ethereum client using Alchemy WebSocket API"""
    
    def __init__(self, api_key: str = None, network: str = "sepolia"):
        """
        Initialize real-time client
        
        Args:
            api_key: Alchemy API key
            network: Network to connect to (mainnet, sepolia, holesky)
        """
        self.api_key = api_key or os.getenv('ALCHEMY_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.error("❌ No Alchemy API key provided")
            raise ValueError("API key is required")
        
        # Set up WebSocket URL
        if network == "mainnet":
            self.ws_url = f"wss://eth-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "sepolia":
            self.ws_url = f"wss://eth-sepolia.g.alchemy.com/v2/{self.api_key}"
        elif network == "holesky":
            self.ws_url = f"wss://eth-holesky.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        self.ws = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        logger.info(f"🔧 Initialized real-time client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Handle subscription confirmation
            if "id" in data and "result" in data:
                subscription_id = data["result"]
                logger.info(f"✅ Subscription confirmed: {subscription_id}")
                return
            
            # Handle new block notifications
            if "method" in data and data["method"] == "eth_subscription":
                params = data.get("params", {})
                subscription = params.get("subscription")
                result = params.get("result")
                
                if result:
                    self._handle_new_block(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling WebSocket message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"❌ WebSocket error: {error}")
        self.is_connected = False
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info(f"🔌 WebSocket connection closed: {close_status_code} - {close_msg}")
        self.is_connected = False
    
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.info("🔌 WebSocket connection established!")
        self.is_connected = True
        
        # Subscribe to new blocks
        self._subscribe_to_new_blocks()
    
    def _subscribe_to_new_blocks(self):
        """Subscribe to new block notifications"""
        subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": ["newHeads"]
        }
        
        if self.ws and self.is_connected:
            self.ws.send(json.dumps(subscription))
            logger.info("📡 Subscribed to new blocks")
        else:
            logger.error("❌ WebSocket not connected")
    
    def _handle_new_block(self, block_data):
        """Handle new block notifications"""
        if not block_data:
            return
        
        self.block_count += 1
        
        # Extract block information
        block_number = int(block_data.get("number", "0"), 16)
        block_hash = block_data.get("hash", "N/A")
        timestamp = int(block_data.get("timestamp", "0"), 16)
        transaction_count = len(block_data.get("transactions", []))
        gas_used = int(block_data.get("gasUsed", "0"), 16)
        gas_limit = int(block_data.get("gasLimit", "0"), 16)
        miner = block_data.get("miner", "N/A")
        
        # Convert timestamp to readable format
        block_time = datetime.fromtimestamp(timestamp)
        
        # Calculate gas usage percentage
        gas_percentage = (gas_used / gas_limit * 100) if gas_limit > 0 else 0
        
        # Display block information
        print("\n" + "="*80)
        print(f"🆕 NEW BLOCK #{block_number}")
        print("="*80)
        print(f"📅 Time: {block_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 Hash: {block_hash}")
        print(f"⛏️  Miner: {miner}")
        print(f"📊 Transactions: {transaction_count}")
        print(f"⛽ Gas Used: {gas_used:,} / {gas_limit:,} ({gas_percentage:.1f}%)")
        print(f"📈 Total Blocks Received: {self.block_count}")
        
        if self.start_time:
            elapsed = time.time() - self.start_time
            blocks_per_minute = (self.block_count / elapsed) * 60
            print(f"⏱️  Blocks per minute: {blocks_per_minute:.2f}")
        
        print("="*80)
    
    def connect(self):
        """Connect to WebSocket"""
        try:
            logger.info("🔌 Connecting to Alchemy WebSocket...")
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            # Start WebSocket connection in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection to establish
            timeout = 10
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.is_connected:
                logger.info("✅ WebSocket connected successfully!")
                return True
            else:
                logger.error("❌ WebSocket connection timeout")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to connect to WebSocket: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self.is_running = False
        if self.ws:
            self.ws.close()
            logger.info("🔌 WebSocket disconnected")
    
    def start_realtime_monitoring(self, duration: int = None):
        """Start real-time monitoring"""
        logger.info(f"🚀 Starting real-time block monitoring...")
        
        if not self.connect():
            logger.error("❌ Failed to connect to WebSocket")
            return
        
        self.is_running = True
        self.start_time = time.time()
        
        print("\n" + "="*80)
        print("🔧 REAL-TIME ETHEREUM BLOCK MONITOR")
        print("="*80)
        print(f"📡 Network: {self.network}")
        print(f"🔌 WebSocket: {self.ws_url}")
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if duration:
            print(f"⏱️  Duration: {duration} seconds")
        print("="*80)
        print("⏳ Waiting for new blocks...")
        print("="*80)
        
        try:
            # Monitor for the specified duration or indefinitely
            if duration:
                start_time = time.time()
                while self.is_running and (time.time() - start_time) < duration:
                    time.sleep(1)
            else:
                # Run indefinitely until interrupted
                while self.is_running:
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("⏹️  Monitoring stopped by user")
        
        # Display final statistics
        if self.start_time:
            elapsed = time.time() - self.start_time
            blocks_per_minute = (self.block_count / elapsed) * 60 if elapsed > 0 else 0
            
            print("\n" + "="*80)
            print("📊 MONITORING STATISTICS")
            print("="*80)
            print(f"📈 Total Blocks Received: {self.block_count}")
            print(f"⏱️  Total Time: {elapsed:.1f} seconds")
            print(f"📊 Average Blocks per Minute: {blocks_per_minute:.2f}")
            print("="*80)
        
        self.disconnect()

def main():
    """Main function"""
    print("🔧 Real-time Ethereum Block Monitor")
    print("📡 Using Alchemy WebSocket API")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        print()
    
    # Initialize real-time client
    client = AlchemyRealtimeClient(
        network="sepolia",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"
    )
    
    # Start real-time monitoring (run for 5 minutes)
    client.start_realtime_monitoring(duration=300)

if __name__ == "__main__":
    main() 