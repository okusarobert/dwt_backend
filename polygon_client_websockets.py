#!/usr/bin/env python3
"""
Polygon WebSocket Client using websockets library
Real-time block monitoring for Polygon network
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional
import websockets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PolygonWebSocketClient:
    """Polygon WebSocket client using websockets library"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize WebSocket client"""
        self.api_key = api_key or os.getenv('ALCHEMY_POLYGON_API_KEY')
        self.network = network
        self.websocket = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        # Set up WebSocket URL
        if network == "mainnet":
            self.ws_url = f"wss://polygon-mainnet.g.alchemy.com/v2/{self.api_key}"
        else:
            self.ws_url = f"wss://polygon-mumbai.g.alchemy.com/v2/{self.api_key}"
        
        logger.info(f"🔧 Initialized Polygon WebSocket client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
    
    async def connect_and_subscribe(self):
        """Connect to WebSocket and subscribe to new blocks"""
        try:
            # Connect to WebSocket
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers={
                    "User-Agent": "Polygon-Client/1.0",
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
            logger.info("📡 Subscribed to Polygon new blocks")
            
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
                print(f"🆕 NEW POLYGON BLOCK #{block_number}")
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
            logger.info("🚀 Starting real-time Polygon block monitoring...")
            
            # Connect and subscribe
            if not await self.connect_and_subscribe():
                logger.error("❌ Failed to connect and subscribe")
                return
            
            self.is_running = True
            self.start_time = time.time()
            self.block_count = 0
            
            # Display monitoring info
            print("=" * 80)
            print("🔧 REAL-TIME POLYGON BLOCK MONITOR")
            print("=" * 80)
            print(f"📡 Network: {self.network}")
            print(f"🔌 WebSocket: {self.ws_url}")
            print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏱️  Duration: {duration} seconds")
            print("=" * 80)
            print("⏳ Waiting for new blocks...")
            print("=" * 80)
            
            # Start listening for messages
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

async def main():
    """Main function"""
    print("🔧 Polygon WebSocket Client")
    print("📡 Using websockets library")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_POLYGON_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_POLYGON_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        api_key = "EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Test key
    
    # Create client
    client = PolygonWebSocketClient(api_key=api_key, network="mainnet")
    
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
    asyncio.run(main()) 