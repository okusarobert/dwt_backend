#!/usr/bin/env python3
"""
BNB Smart Chain Client using Alchemy API
Supports address balance queries and real-time block monitoring
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

class BNBClient:
    """BNB Smart Chain client using Alchemy API"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """
        Initialize BNB client
        
        Args:
            api_key: Alchemy API key
            network: Network to connect to (mainnet, testnet)
        """
        self.api_key = api_key or os.getenv('ALCHEMY_BNB_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.error("❌ No Alchemy BNB API key provided")
            raise ValueError("API key is required")
        
        # Set up API URLs
        if network == "mainnet":
            self.http_url = f"https://bnb-mainnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://bnb-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "testnet":
            self.http_url = f"https://bnb-testnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://bnb-testnet.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        # WebSocket properties
        self.sock = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        logger.info(f"🔧 Initialized BNB Smart Chain client for {network}")
        logger.info(f"📡 HTTP API URL: {self.http_url}")
        logger.info(f"🔌 WebSocket URL: {self.ws_url}")
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make an RPC request to BNB API"""
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else [],
            "id": 1
        }
        try:
            response = requests.post(self.http_url, headers=headers, data=json.dumps(payload), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
            return None
    
    def get_latest_block_number(self) -> Optional[int]:
        """Get the latest block number"""
        response = self.make_request("eth_blockNumber")
        if response and 'result' in response:
            return int(response['result'], 16)
        return None
    
    def get_balance(self, address: str) -> Optional[Dict]:
        """Get balance for a specific address"""
        try:
            logger.info(f"💰 Getting balance for {address}")
            
            response = self.make_request("eth_getBalance", [address, "latest"])
            if response and 'result' in response:
                balance_wei = int(response['result'], 16)
                balance_bnb = balance_wei / 1e18  # Convert wei to BNB
                
                result = {
                    "address": address,
                    "balance_wei": balance_wei,
                    "balance_bnb": balance_bnb,
                    "confirmed": True,
                    "network": self.network
                }
                
                logger.info(f"✅ Balance for {address}: {balance_bnb:.18f} BNB ({balance_wei} wei)")
                return result
            else:
                logger.error(f"❌ Failed to get balance for {address}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting balance for {address}: {e}")
            return None
    
    def get_account_info(self, address: str) -> Optional[Dict]:
        """Get account information"""
        try:
            logger.info(f"📋 Getting account info for {address}")
            
            # Get transaction count (nonce)
            nonce_response = self.make_request("eth_getTransactionCount", [address, "latest"])
            nonce = int(nonce_response['result'], 16) if nonce_response and 'result' in nonce_response else 0
            
            # Get balance
            balance_response = self.make_request("eth_getBalance", [address, "latest"])
            balance_wei = int(balance_response['result'], 16) if balance_response and 'result' in balance_response else 0
            
            result = {
                "address": address,
                "balance_wei": balance_wei,
                "balance_bnb": balance_wei / 1e18,
                "nonce": nonce,
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
                if not result_hex or result_hex == "0x" or result_hex == "0x0":
                    logger.warning(f"⚠️ Token contract {token_address} returned empty balance for {wallet_address}")
                    return {
                        "token_address": token_address,
                        "wallet_address": wallet_address,
                        "balance_wei": 0,
                        "balance_token": 0.0,
                        "decimals": 18,
                        "network": self.network,
                        "note": "Contract may not exist on this network or wallet has no tokens"
                    }
                
                try:
                    balance_wei = int(result_hex, 16)
                except ValueError as e:
                    logger.error(f"❌ Invalid hex response for token balance: {result_hex}")
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

class BNBWebSocketClient:
    """WebSocket client for real-time BNB data"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize WebSocket client"""
        self.api_key = api_key or os.getenv('ALCHEMY_BNB_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.error("❌ No Alchemy BNB API key provided")
            raise ValueError("API key is required")
        
        # Set up WebSocket URL
        if network == "mainnet":
            self.ws_url = f"wss://bnb-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "testnet":
            self.ws_url = f"wss://bnb-testnet.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        self.sock = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        logger.info(f"🔧 Initialized BNB WebSocket client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
    
    def _create_websocket_key(self):
        """Create WebSocket key for handshake"""
        return base64.b64encode(os.urandom(16)).decode()
    
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
            logger.info("🔌 Connecting to BNB WebSocket...")
            
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
            logger.info("📡 Subscribed to BNB new blocks")
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
        gas_used = int(block_data.get("gasUsed", "0"), 16)
        gas_limit = int(block_data.get("gasLimit", "0"), 16)
        miner = block_data.get("miner", "N/A")
        
        # Convert timestamp to readable format
        block_time = datetime.fromtimestamp(timestamp)
        
        # Calculate gas usage percentage
        gas_percentage = (gas_used / gas_limit * 100) if gas_limit > 0 else 0
        
        # Display block information
        print("\n" + "="*80)
        print(f"🆕 NEW BNB BLOCK #{block_number}")
        print("="*80)
        print(f"📅 Time: {block_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 Hash: {block_hash}")
        print(f"⛏️  Miner: {miner}")
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
        logger.info(f"🚀 Starting real-time BNB block monitoring...")
        
        if not self.connect():
            logger.error("❌ Failed to connect to WebSocket")
            return
        
        # Subscribe to new blocks
        self.subscribe_to_new_blocks()
        
        self.is_running = True
        self.start_time = time.time()
        
        print("\n" + "="*80)
        print("🔧 REAL-TIME BNB BLOCK MONITOR")
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

def test_bnb_api():
    """Test BNB API functionality"""
    print("🔧 BNB Smart Chain API Test")
    print("📡 Using Alchemy BNB API")
    print("=" * 50)
    
    # Initialize client
    client = BNBClient(
        network="mainnet",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Using the same API key for testing
    )
    
    # Test 1: Get latest block number
    print("\n🔍 Test 1: Getting latest block number")
    latest_block = client.get_latest_block_number()
    if latest_block:
        print(f"✅ Latest block: {latest_block:,}")
    else:
        print("❌ Failed to get latest block")
    
    # Test 2: Get balance for known BNB addresses
    print("\n🔍 Test 2: Getting balances for BNB addresses")
    test_addresses = [
        {
            "name": "Binance Hot Wallet",
            "address": "0x28C6c06298d514Db089934071355E5743bf21d60"
        },
        {
            "name": "Binance Cold Wallet",
            "address": "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549"
        },
        {
            "name": "PancakeSwap Router",
            "address": "0x10ED43C718714eb63d5aA57B78B54704E256024E"
        },
        {
            "name": "Venus Protocol",
            "address": "0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63"
        }
    ]
    
    for test_addr in test_addresses:
        print(f"\n📍 {test_addr['name']}: {test_addr['address']}")
        balance = client.get_balance(test_addr['address'])
        if balance:
            print(f"✅ Balance: {balance['balance_bnb']:.6f} BNB")
        else:
            print("❌ Failed to get balance")
    
    # Test 3: Get account info
    print("\n🔍 Test 3: Getting account info")
    account_info = client.get_account_info(test_addresses[0]['address'])
    if account_info:
        print(f"✅ Nonce: {account_info['nonce']}")
        print(f"✅ Balance: {account_info['balance_bnb']:.6f} BNB")
    else:
        print("❌ Failed to get account info")
    
    # Test 4: Get token balance (USDT on BSC)
    print("\n🔍 Test 4: Getting USDT token balance")
    usdt_address = "0x55d398326f99059fF775485246999027B3197955"  # USDT on BSC
    token_balance = client.get_token_balance(usdt_address, test_addresses[0]['address'])
    if token_balance:
        if token_balance.get('note'):
            print(f"⚠️ {token_balance['note']}")
        print(f"✅ USDT Balance: {token_balance['balance_token']:.2f} USDT")
    else:
        print("❌ Failed to get token balance")
    
    # Test 5: Get recent blocks
    print("\n🔍 Test 5: Getting recent blocks")
    recent_blocks = client.get_recent_blocks(3)
    if recent_blocks:
        print(f"✅ Retrieved {len(recent_blocks)} recent blocks")
        for block in recent_blocks:
            print(f"   Block {block['number']}: {block['transaction_count']} transactions")
    else:
        print("❌ Failed to get recent blocks")

def main():
    """Main function"""
    print("🔧 BNB Smart Chain Client")
    print("📡 Using Alchemy BNB API")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_BNB_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_BNB_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        print()
    
    # Test HTTP API functionality
    test_bnb_api()
    
    print("\n" + "="*80)
    print("🚀 Starting real-time block monitoring...")
    print("="*80)
    
    # Initialize WebSocket client for real-time monitoring
    ws_client = BNBWebSocketClient(
        network="mainnet",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"
    )
    
    # Start real-time monitoring (run for 3 minutes)
    ws_client.start_realtime_monitoring(duration=180)

if __name__ == "__main__":
    main() 