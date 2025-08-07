#!/usr/bin/env python3
"""
Polygon PoS Client using Alchemy API
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

class PolygonClient:
    """Polygon PoS client using Alchemy API"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """
        Initialize Polygon client
        
        Args:
            api_key: Alchemy API key
            network: Network to connect to (mainnet, testnet)
        """
        self.api_key = api_key or os.getenv('ALCHEMY_POLYGON_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.error("❌ No Alchemy Polygon API key provided")
            raise ValueError("API key is required")
        
        # Set up API URLs
        if network == "mainnet":
            self.http_url = f"https://polygon-mainnet.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://polygon-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "testnet":
            self.http_url = f"https://polygon-mumbai.g.alchemy.com/v2/{self.api_key}"
            self.ws_url = f"wss://polygon-mumbai.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        # WebSocket properties
        self.sock = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        logger.info(f"🔧 Initialized Polygon PoS client for {network}")
        logger.info(f"📡 HTTP API URL: {self.http_url}")
        logger.info(f"🔌 WebSocket URL: {self.ws_url}")
    
    def make_request(self, method: str, params: list = None) -> Optional[Dict]:
        """Make an RPC request to Polygon API"""
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
                balance_matic = balance_wei / 1e18  # Convert wei to MATIC
                
                result = {
                    "address": address,
                    "balance_wei": balance_wei,
                    "balance_matic": balance_matic,
                    "confirmed": True,
                    "network": self.network
                }
                
                logger.info(f"✅ Balance for {address}: {balance_matic:.18f} MATIC ({balance_wei} wei)")
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
            nonce = 0
            if nonce_response and 'result' in nonce_response:
                nonce = int(nonce_response['result'], 16)
            
            # Get balance
            balance_response = self.make_request("eth_getBalance", [address, "latest"])
            balance_wei = 0
            balance_matic = 0
            if balance_response and 'result' in balance_response:
                balance_wei = int(balance_response['result'], 16)
                balance_matic = balance_wei / 1e18
            
            result = {
                "address": address,
                "nonce": nonce,
                "balance_wei": balance_wei,
                "balance_matic": balance_matic,
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


class PolygonWebSocketClient:
    """Polygon WebSocket client for real-time monitoring"""
    
    def __init__(self, api_key: str = None, network: str = "mainnet"):
        """Initialize Polygon WebSocket client"""
        self.api_key = api_key or os.getenv('ALCHEMY_POLYGON_API_KEY')
        self.network = network
        
        if not self.api_key:
            logger.error("❌ No Alchemy Polygon API key provided")
            raise ValueError("API key is required")
        
        # Set up WebSocket URL
        if network == "mainnet":
            self.ws_url = f"wss://polygon-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif network == "testnet":
            self.ws_url = f"wss://polygon-mumbai.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {network}")
        
        # WebSocket properties
        self.sock = None
        self.is_connected = False
        self.is_running = False
        self.block_count = 0
        self.start_time = None
        
        logger.info(f"🔧 Initialized Polygon WebSocket client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
    
    def _create_websocket_key(self):
        """Create WebSocket key for handshake"""
        import secrets
        return base64.b64encode(secrets.token_bytes(16)).decode('utf-8')
    
    def _send_websocket_frame(self, data, opcode=1):
        """Send WebSocket frame"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        length = len(data)
        frame = bytearray()
        
        # FIN bit and opcode
        frame.append(0x80 | opcode)
        
        if length < 126:
            frame.append(length)
        elif length < 65536:
            frame.append(126)
            frame.extend(length.to_bytes(2, 'big'))
        else:
            frame.append(127)
            frame.extend(length.to_bytes(8, 'big'))
        
        frame.extend(data)
        self.sock.send(frame)
    
    def _receive_websocket_frame(self):
        """Receive WebSocket frame"""
        try:
            # Read first byte with timeout
            first_byte = self.sock.recv(1)
            if not first_byte:
                return None
            
            fin = (first_byte[0] & 0x80) != 0
            opcode = first_byte[0] & 0x0F
            
            # Read second byte
            second_byte = self.sock.recv(1)
            if not second_byte:
                return None
            
            masked = (second_byte[0] & 0x80) != 0
            payload_length = second_byte[0] & 0x7F
            
            if payload_length == 126:
                length_bytes = self.sock.recv(2)
                if len(length_bytes) < 2:
                    return None
                payload_length = int.from_bytes(length_bytes, 'big')
            elif payload_length == 127:
                length_bytes = self.sock.recv(8)
                if len(length_bytes) < 8:
                    return None
                payload_length = int.from_bytes(length_bytes, 'big')
            
            # Read masking key if masked
            masking_key = None
            if masked:
                masking_key = self.sock.recv(4)
                if len(masking_key) < 4:
                    return None
            
            # Read payload in chunks if large
            payload = b''
            remaining = payload_length
            while remaining > 0:
                chunk = self.sock.recv(min(remaining, 4096))
                if not chunk:
                    break
                payload += chunk
                remaining -= len(chunk)
            
            if len(payload) != payload_length:
                logger.warning(f"⚠️ Incomplete payload: got {len(payload)}, expected {payload_length}")
                return None
            
            # Unmask if necessary
            if masked and masking_key:
                unmasked = bytearray()
                for i, byte in enumerate(payload):
                    unmasked.append(byte ^ masking_key[i % 4])
                payload = bytes(unmasked)
            
            return {
                'fin': fin,
                'opcode': opcode,
                'payload': payload
            }
            
        except socket.timeout:
            # Timeout is expected with non-blocking socket
            return None
        except Exception as e:
            logger.error(f"❌ Error receiving WebSocket frame: {e}")
            return None
    
    def connect(self):
        """Connect to Polygon WebSocket"""
        try:
            logger.info("🔌 Connecting to Polygon WebSocket...")
            
            # Parse WebSocket URL
            if self.ws_url.startswith('wss://'):
                host_port = self.ws_url[6:]
            else:
                host_port = self.ws_url[5:]
            
            if '/' in host_port:
                host, path = host_port.split('/', 1)
                path = '/' + path
            else:
                host = host_port
                path = '/'
            
            if ':' in host:
                host, port = host.split(':')
                port = int(port)
            else:
                port = 443
            
            logger.info(f"🔍 Connecting to {host}:{port}{path}")
            
            # Create SSL context
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Create socket and wrap with SSL
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)  # Set socket timeout to 30 seconds
            sock = context.wrap_socket(sock, server_hostname=host)
            sock.connect((host, port))
            
            # Create WebSocket key
            key = self._create_websocket_key()
            
            # Send WebSocket handshake with additional headers
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"User-Agent: Polygon-Client/1.0\r\n"
                f"Accept: */*\r\n"
                f"\r\n"
            )
            
            sock.send(handshake.encode())
            
            # Read response with timeout
            sock.settimeout(10)
            response = sock.recv(4096).decode()
            
            if "101 Switching Protocols" in response:
                logger.info("✅ WebSocket handshake successful!")
                # Set socket to blocking with timeout for better control
                sock.settimeout(1)  # 1 second timeout
                self.sock = sock
                self.is_connected = True
                return True
            else:
                logger.error(f"❌ WebSocket handshake failed: {response}")
                return False
                
        except socket.timeout:
            logger.error("❌ Connection timeout")
            return False
        except Exception as e:
            logger.error(f"❌ Error connecting to WebSocket: {e}")
            return False
    
    def subscribe_to_new_blocks(self):
        """Subscribe to new block notifications"""
        try:
            subscription_message = {
                "jsonrpc": "2.0",
                "method": "eth_subscribe",
                "params": ["newHeads"],
                "id": 1
            }
            
            self._send_websocket_frame(json.dumps(subscription_message))
            logger.info("📡 Subscribed to Polygon new blocks")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error subscribing to new blocks: {e}")
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
    
    def listen_for_messages(self):
        """Listen for WebSocket messages"""
        while self.is_connected and self.is_running:
            try:
                frame = self._receive_websocket_frame()
                if frame is None:
                    logger.warning("⚠️ Received empty frame, continuing...")
                    continue
                
                if frame['opcode'] == 1:  # Text frame
                    try:
                        data = json.loads(frame['payload'].decode('utf-8'))
                        
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
                        # Don't break, continue listening
                
                elif frame['opcode'] == 8:  # Close frame
                    logger.info("🔌 Received close frame from server")
                    # Try to reconnect instead of breaking
                    if self.is_running:
                        logger.info("🔄 Attempting to reconnect...")
                        time.sleep(2)
                        if self.connect() and self.subscribe_to_new_blocks():
                            logger.info("✅ Reconnected successfully")
                            continue
                        else:
                            logger.error("❌ Failed to reconnect")
                            break
                    else:
                        break
                
                elif frame['opcode'] == 9:  # Ping frame
                    logger.debug("🏓 Received ping, sending pong")
                    try:
                        self._send_websocket_frame(b'', opcode=10)  # Pong
                    except Exception as e:
                        logger.error(f"❌ Error sending pong: {e}")
                
                elif frame['opcode'] == 10:  # Pong frame
                    logger.debug("🏓 Received pong")
                
                else:
                    logger.debug(f"📡 Received frame with opcode: {frame['opcode']}")
                
            except socket.timeout:
                logger.warning("⏰ Socket timeout, continuing...")
                continue
            except Exception as e:
                logger.error(f"❌ Error in message loop: {e}")
                # Don't break immediately, try to continue
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                continue
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        try:
            if self.sock:
                self._send_websocket_frame(b'', opcode=8)  # Close frame
                self.sock.close()
                self.is_connected = False
                logger.info("🔌 WebSocket disconnected")
        except Exception as e:
            logger.error(f"❌ Error disconnecting: {e}")
    
    def start_realtime_monitoring(self, duration: int = None):
        """Start real-time block monitoring"""
        try:
            logger.info("🚀 Starting real-time Polygon block monitoring...")
            
            if not self.connect():
                logger.error("❌ Failed to connect to WebSocket")
                return
            
            if not self.subscribe_to_new_blocks():
                logger.error("❌ Failed to subscribe to new blocks")
                return
            
            # Display monitoring info
            print("=" * 80)
            print("🔧 REAL-TIME POLYGON BLOCK MONITOR")
            print("=" * 80)
            print(f"📡 Network: {self.network}")
            print(f"🔌 WebSocket: {self.ws_url}")
            print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if duration:
                print(f"⏱️  Duration: {duration} seconds")
            print("=" * 80)
            print("⏳ Waiting for new blocks...")
            print("=" * 80)
            print()
            
            self.is_running = True
            self.start_time = time.time()
            
            # Start monitoring
            self.listen_for_messages()
            
            # Calculate statistics
            if self.start_time:
                total_time = time.time() - self.start_time
                blocks_per_minute = (self.block_count / total_time * 60) if total_time > 0 else 0
                
                print("=" * 80)
                print("📊 MONITORING STATISTICS")
                print("=" * 80)
                print(f"📈 Total Blocks Received: {self.block_count}")
                print(f"⏱️  Total Time: {total_time:.1f} seconds")
                print(f"📊 Average Blocks per Minute: {blocks_per_minute:.2f}")
                print("=" * 80)
            
        except KeyboardInterrupt:
            logger.info("⏹️  Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Error in monitoring: {e}")
        finally:
            self.disconnect()


def test_polygon_api():
    """Test Polygon API functionality"""
    print("🔧 Polygon PoS API Test")
    print("📡 Using Alchemy Polygon API")
    print("=" * 50)
    
    # Initialize client
    client = PolygonClient(
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
    
    # Test 2: Get balance for known Polygon addresses
    print("\n🔍 Test 2: Getting balances for Polygon addresses")
    test_addresses = [
        {
            "name": "Polygon Foundation",
            "address": "0x0000000000000000000000000000000000000000"
        },
        {
            "name": "Polygon Treasury",
            "address": "0x0000000000000000000000000000000000000001"
        },
        {
            "name": "Uniswap V3 Router",
            "address": "0xE592427A0AEce92De3Edee1F18E0157C05861564"
        },
        {
            "name": "Aave V3 Pool",
            "address": "0x794a61358D6845594F94dc1DB02A252b5b4814aD"
        }
    ]
    
    for test_addr in test_addresses:
        print(f"\n📍 {test_addr['name']}: {test_addr['address']}")
        balance = client.get_balance(test_addr['address'])
        if balance:
            print(f"✅ Balance: {balance['balance_matic']:.6f} MATIC")
        else:
            print("❌ Failed to get balance")
    
    # Test 3: Get account info
    print("\n🔍 Test 3: Getting account info")
    account_info = client.get_account_info(test_addresses[0]['address'])
    if account_info:
        print(f"✅ Nonce: {account_info['nonce']}")
        print(f"✅ Balance: {account_info['balance_matic']:.6f} MATIC")
    else:
        print("❌ Failed to get account info")
    
    # Test 4: Get token balance (USDC on Polygon)
    print("\n🔍 Test 4: Getting USDC token balance")
    usdc_address = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC on Polygon
    token_balance = client.get_token_balance(usdc_address, test_addresses[0]['address'])
    if token_balance:
        if token_balance.get('note'):
            print(f"⚠️ {token_balance['note']}")
        print(f"✅ USDC Balance: {token_balance['balance_token']:.2f} USDC")
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
    print("🔧 Polygon PoS Client")
    print("📡 Using Alchemy Polygon API")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_POLYGON_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_POLYGON_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using provided API key for testing.")
        print()
    
    # Test HTTP API functionality
    test_polygon_api()
    
    print("\n" + "="*80)
    print("🚀 Starting real-time block monitoring...")
    print("="*80)
    
    # Initialize WebSocket client for real-time monitoring
    ws_client = PolygonWebSocketClient(
        network="mainnet",
        api_key="EbcNdRQag_4Ep75VtLuPLV3-MMfLKMvH"  # Using the same API key for testing
    )
    
    # Start real-time monitoring
    ws_client.start_realtime_monitoring(duration=300)  # Monitor for 5 minutes


if __name__ == "__main__":
    main() 