#!/usr/bin/env python3
"""
Real-time Ethereum WebSocket Client using Alchemy
Subscribes to new blocks and displays them in real-time
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
from datetime import datetime
from typing import Dict, Optional

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleWebSocketClient:
    """Simple WebSocket client for real-time Ethereum data"""
    
    def __init__(self, api_key: str = None, network: str = "sepolia"):
        """
        Initialize WebSocket client
        
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
        
        self.sock = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        logger.info(f"🔧 Initialized simple WebSocket client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
    
    def _create_websocket_key(self):
        """Create WebSocket key for handshake"""
        return base64.b64encode(os.urandom(16)).decode()
    
    def _create_websocket_accept(self, key):
        """Create WebSocket accept key"""
        magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        accept_key = key + magic
        sha1 = hashlib.sha1(accept_key.encode()).digest()
        return base64.b64encode(sha1).decode()
    
    def _send_websocket_frame(self, data, opcode=1):
        """Send WebSocket frame"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        length = len(data)
        frame = bytearray()
        
        # First byte: FIN + RSV + opcode
        frame.append(0x80 | opcode)
        
        # Second byte: MASK + payload length
        if length < 126:
            frame.append(0x80 | length)
        elif length < 65536:
            frame.append(0x80 | 126)
            frame.extend(struct.pack('>H', length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack('>Q', length))
        
        # Masking key (4 bytes)
        mask = os.urandom(4)
        frame.extend(mask)
        
        # Masked payload
        masked_data = bytearray()
        for i, byte in enumerate(data):
            masked_data.append(byte ^ mask[i % 4])
        frame.extend(masked_data)
        
        self.sock.send(frame)
    
    def _receive_websocket_frame(self):
        """Receive WebSocket frame"""
        # Read first byte
        first_byte = self.sock.recv(1)[0]
        fin = (first_byte & 0x80) != 0
        opcode = first_byte & 0x0F
        
        # Read second byte
        second_byte = self.sock.recv(1)[0]
        masked = (second_byte & 0x80) != 0
        payload_length = second_byte & 0x7F
        
        # Read extended payload length if needed
        if payload_length == 126:
            payload_length = struct.unpack('>H', self.sock.recv(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack('>Q', self.sock.recv(8))[0]
        
        # Read masking key if present
        mask = None
        if masked:
            mask = self.sock.recv(4)
        
        # Read payload
        payload = self.sock.recv(payload_length)
        
        # Unmask payload if needed
        if masked and mask:
            unmasked = bytearray()
            for i, byte in enumerate(payload):
                unmasked.append(byte ^ mask[i % 4])
            payload = bytes(unmasked)
        
        return fin, opcode, payload
    
    def connect(self):
        """Connect to WebSocket"""
        try:
            logger.info("🔌 Connecting to Alchemy WebSocket...")
            
            # Parse WebSocket URL
            if self.ws_url.startswith("wss://"):
                host = self.ws_url[6:].split("/")[0]
                path = "/" + "/".join(self.ws_url[6:].split("/")[1:])
                port = 443
                use_ssl = True
            else:
                host = self.ws_url[5:].split("/")[0]
                path = "/" + "/".join(self.ws_url[5:].split("/")[1:])
                port = 80
                use_ssl = False
            
            logger.info(f"🔍 Connecting to {host}:{port}{path}")
            
            # Create socket connection
            if use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.sock = context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=host)
            else:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            self.sock.connect((host, port))
            logger.info("✅ Socket connection established!")
            
            # Send WebSocket handshake
            ws_key = self._create_websocket_key()
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {ws_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"\r\n"
            )
            
            self.sock.send(handshake.encode())
            response = self.sock.recv(1024).decode()
            
            if "101 Switching Protocols" in response:
                logger.info("✅ WebSocket handshake successful!")
                self.is_connected = True
                return True
            else:
                logger.error(f"❌ WebSocket handshake failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            return False
    
    def subscribe_to_new_blocks(self):
        """Subscribe to new block notifications"""
        subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": ["newHeads"]
        }
        
        if self.is_connected:
            self._send_websocket_frame(json.dumps(subscription))
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
    
    def listen_for_messages(self):
        """Listen for WebSocket messages"""
        try:
            while self.is_running and self.is_connected:
                try:
                    fin, opcode, payload = self._receive_websocket_frame()
                    
                    if opcode == 1:  # Text frame
                        try:
                            data = json.loads(payload.decode('utf-8'))
                            
                            # Handle subscription confirmation
                            if "id" in data and "result" in data:
                                subscription_id = data["result"]
                                logger.info(f"✅ Subscription confirmed: {subscription_id}")
                                continue
                            
                            # Handle new block notifications
                            if "method" in data and data["method"] == "eth_subscription":
                                params = data.get("params", {})
                                result = params.get("result")
                                
                                if result:
                                    self._handle_new_block(result)
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ Failed to parse message: {e}")
                        except Exception as e:
                            logger.error(f"❌ Error handling message: {e}")
                    
                    elif opcode == 8:  # Close frame
                        logger.info("🔌 Received close frame")
                        break
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"❌ Error reading WebSocket: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"❌ WebSocket listening error: {e}")
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self.is_running = False
        if self.sock:
            try:
                # Send close frame
                self._send_websocket_frame(b"", opcode=8)
                self.sock.close()
            except:
                pass
            logger.info("🔌 WebSocket disconnected")
    
    def start_realtime_monitoring(self, duration: int = None):
        """Start real-time monitoring"""
        logger.info(f"🚀 Starting real-time block monitoring...")
        
        if not self.connect():
            logger.error("❌ Failed to connect to WebSocket")
            return
        
        # Subscribe to new blocks
        self.subscribe_to_new_blocks()
        
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
        
        # Set socket timeout
        self.sock.settimeout(1)
        
        try:
            # Start listening in a separate thread
            listen_thread = threading.Thread(target=self.listen_for_messages)
            listen_thread.daemon = True
            listen_thread.start()
            
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
    client = SimpleWebSocketClient(
        network="sepolia",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"
    )
    
    # Start real-time monitoring (run for 5 minutes)
    client.start_realtime_monitoring(duration=300)

if __name__ == "__main__":
    main() 