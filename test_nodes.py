#!/usr/bin/env python3
"""
Simple SPV (Simplified Payment Verification) Bitcoin Client
Connects to a Bitcoin node and listens to blocks and transactions
"""

import socket
import struct
import hashlib
import time
import json
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    VERSION = b'version'
    VERACK = b'verack'
    PING = b'ping'
    PONG = b'pong'
    GETBLOCKS = b'getblocks'
    INV = b'inv'
    GETDATA = b'getdata'
    BLOCK = b'block'
    TX = b'tx'
    HEADERS = b'headers'
    GETHEADERS = b'getheaders'

@dataclass
class BitcoinMessage:
    """Bitcoin network message structure"""
    magic: bytes = b'\xf9\xbe\xb4\xd9'  # Mainnet magic
    command: bytes = b''
    length: int = 0
    checksum: bytes = b''
    payload: bytes = b''

class SimpleSPVClient:
    """Simple SPV client that connects to Bitcoin nodes"""
    
    def __init__(self, node_host: str = "127.0.0.1", node_port: int = 8333):
        self.node_host = node_host
        self.node_port = node_port
        self.socket = None
        self.connected = False
        self.peer_version = 0
        self.user_agent = b'/SimpleSPV:0.1.0/'
        self.start_height = 0
        self.relay = True
        self.watched_addresses = set()
        self.transaction_cache = {}
        self.block_cache = {}
        
    def connect(self) -> bool:
        """Connect to Bitcoin node"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(30)
            self.socket.connect((self.node_host, self.node_port))
            self.connected = True
            logger.info(f"Connected to Bitcoin node {self.node_host}:{self.node_port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to node: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Bitcoin node"""
        if self.socket:
            self.socket.close()
        self.connected = False
        logger.info("Disconnected from Bitcoin node")
    
    def create_message(self, command: MessageType, payload: bytes = b'') -> BitcoinMessage:
        """Create a Bitcoin network message"""
        message = BitcoinMessage()
        message.command = command.value.ljust(12, b'\x00')
        message.length = len(payload)
        message.payload = payload
        
        # Calculate checksum (double SHA256)
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        message.checksum = checksum
        
        return message
    
    def send_message(self, message: BitcoinMessage):
        """Send message to Bitcoin node"""
        if not self.connected:
            logger.error("Not connected to node")
            return
        
        try:
            # Pack message header
            header = struct.pack('<I12sI4s', 
                               0xf9beb4d9,  # Magic
                               message.command,
                               message.length,
                               message.checksum)
            
            # Send header and payload
            self.socket.send(header + message.payload)
            logger.debug(f"Sent {message.command.strip(b'\x00').decode()} message")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.connected = False
    
    def receive_message(self) -> Optional[BitcoinMessage]:
        """Receive message from Bitcoin node"""
        if not self.connected:
            return None
        
        try:
            # Read message header (24 bytes)
            header = self.socket.recv(24)
            if len(header) < 24:
                return None
            
            # Parse header
            magic, command, length, checksum = struct.unpack('<I12sI4s', header)
            
            # Read payload
            payload = b''
            if length > 0:
                payload = self.socket.recv(length)
                while len(payload) < length:
                    chunk = self.socket.recv(length - len(payload))
                    if not chunk:
                        break
                    payload += chunk
            
            message = BitcoinMessage()
            message.magic = struct.pack('<I', magic)
            message.command = command
            message.length = length
            message.checksum = checksum
            message.payload = payload
            
            return message
        except Exception as e:
            logger.error(f"Failed to receive message: {e}")
            self.connected = False
            return None
    
    def create_version_payload(self) -> bytes:
        """Create version message payload"""
        version = 70015  # Protocol version
        services = 0     # No services
        timestamp = int(time.time())
        addr_recv_services = 0
        addr_recv_ip = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton(self.node_host)
        addr_recv_port = struct.pack('>H', self.node_port)
        addr_trans_services = 0
        addr_trans_ip = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton('127.0.0.1')
        addr_trans_port = struct.pack('>H', 8333)
        nonce = struct.pack('<Q', int(time.time() * 1000000))
        user_agent_bytes = struct.pack('<B', len(self.user_agent)) + self.user_agent
        start_height = struct.pack('<I', self.start_height)
        relay = struct.pack('<?', self.relay)
        
        payload = struct.pack('<IQQ26s26sQQ26s26sQ', 
                            version, services, timestamp,
                            addr_recv_services, addr_recv_ip, addr_recv_port,
                            addr_trans_services, addr_trans_ip, addr_trans_port,
                            int(time.time() * 1000000))
        payload += user_agent_bytes + start_height + relay
        
        return payload
    
    def handshake(self) -> bool:
        """Perform Bitcoin protocol handshake"""
        try:
            # Send version message
            version_payload = self.create_version_payload()
            version_msg = self.create_message(MessageType.VERSION, version_payload)
            self.send_message(version_msg)
            
            # Wait for version response
            version_response = self.receive_message()
            if not version_response:
                return False
            
            # Send verack
            verack_msg = self.create_message(MessageType.VERACK)
            self.send_message(verack_msg)
            
            # Wait for verack response
            verack_response = self.receive_message()
            if not verack_response:
                return False
            
            logger.info("Handshake completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Handshake failed: {e}")
            return False
    
    def add_watch_address(self, address: str):
        """Add Bitcoin address to watch list"""
        self.watched_addresses.add(address)
        logger.info(f"Added address to watch list: {address}")
    
    def remove_watch_address(self, address: str):
        """Remove Bitcoin address from watch list"""
        self.watched_addresses.discard(address)
        logger.info(f"Removed address from watch list: {address}")
    
    def process_transaction(self, tx_data: bytes):
        """Process incoming transaction"""
        try:
            # Parse transaction (simplified)
            tx_hash = hashlib.sha256(hashlib.sha256(tx_data).digest()).digest()
            tx_hash_hex = tx_hash[::-1].hex()  # Reverse for display
            
            logger.info(f"Received transaction: {tx_hash_hex}")
            
            # Check if transaction involves watched addresses
            # This is a simplified check - in real implementation you'd parse the outputs
            if self.watched_addresses:
                logger.info(f"Checking transaction {tx_hash_hex} against {len(self.watched_addresses)} watched addresses")
            
            # Cache transaction
            self.transaction_cache[tx_hash_hex] = {
                'data': tx_data,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to process transaction: {e}")
    
    def process_block(self, block_data: bytes):
        """Process incoming block"""
        try:
            # Parse block header (first 80 bytes)
            if len(block_data) >= 80:
                header = block_data[:80]
                version, prev_block, merkle_root, timestamp, bits, nonce = struct.unpack('<I32s32sIII', header)
                
                # Calculate block hash
                block_hash = hashlib.sha256(hashlib.sha256(header).digest()).digest()
                block_hash_hex = block_hash[::-1].hex()
                
                logger.info(f"Received block: {block_hash_hex} (height: {self.start_height})")
                
                # Cache block
                self.block_cache[block_hash_hex] = {
                    'header': header,
                    'data': block_data,
                    'timestamp': time.time(),
                    'height': self.start_height
                }
                
                self.start_height += 1
                
        except Exception as e:
            logger.error(f"Failed to process block: {e}")
    
    def listen_for_messages(self):
        """Listen for incoming messages from Bitcoin node"""
        logger.info("Starting message listener...")
        
        while self.connected:
            try:
                message = self.receive_message()
                if not message:
                    continue
                
                command = message.command.strip(b'\x00').decode()
                
                if command == 'version':
                    logger.info("Received version message")
                    
                elif command == 'verack':
                    logger.info("Received verack message")
                    
                elif command == 'ping':
                    # Respond with pong
                    pong_msg = self.create_message(MessageType.PONG, message.payload)
                    self.send_message(pong_msg)
                    logger.debug("Responded to ping with pong")
                    
                elif command == 'inv':
                    # Handle inventory message
                    logger.debug("Received inventory message")
                    
                elif command == 'tx':
                    # Handle transaction
                    self.process_transaction(message.payload)
                    
                elif command == 'block':
                    # Handle block
                    self.process_block(message.payload)
                    
                elif command == 'headers':
                    # Handle headers
                    logger.debug("Received headers message")
                    
                else:
                    logger.debug(f"Received unknown message: {command}")
                    
            except Exception as e:
                logger.error(f"Error in message listener: {e}")
                break
        
        logger.info("Message listener stopped")
    
    def start_listening(self):
        """Start listening for messages in a separate thread"""
        listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        listener_thread.start()
        return listener_thread
    
    def get_watched_addresses(self) -> List[str]:
        """Get list of watched addresses"""
        return list(self.watched_addresses)
    
    def get_transaction_cache(self) -> Dict:
        """Get cached transactions"""
        return self.transaction_cache.copy()
    
    def get_block_cache(self) -> Dict:
        """Get cached blocks"""
        return self.block_cache.copy()
    
    def clear_caches(self):
        """Clear transaction and block caches"""
        self.transaction_cache.clear()
        self.block_cache.clear()
        logger.info("Caches cleared")

def main():
    """Example usage of SimpleSPVClient"""
    
    # Create SPV client
    spv = SimpleSPVClient(node_host="127.0.0.1", node_port=8333)
    
    # Connect to node
    if not spv.connect():
        logger.error("Failed to connect to Bitcoin node")
        return
    
    # Perform handshake
    if not spv.handshake():
        logger.error("Handshake failed")
        spv.disconnect()
        return
    
    # Add some addresses to watch
    spv.add_watch_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")  # Genesis block address
    spv.add_watch_address("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")  # Example address
    
    # Start listening for messages
    listener_thread = spv.start_listening()
    
    try:
        logger.info("SPV client running. Press Ctrl+C to stop.")
        
        # Keep main thread alive
        while spv.connected:
            time.sleep(1)
            
            # Print stats every 30 seconds
            if int(time.time()) % 30 == 0:
                logger.info(f"Watched addresses: {len(spv.get_watched_addresses())}")
                logger.info(f"Cached transactions: {len(spv.get_transaction_cache())}")
                logger.info(f"Cached blocks: {len(spv.get_block_cache())}")
                
    except KeyboardInterrupt:
        logger.info("Stopping SPV client...")
    finally:
        spv.disconnect()

if __name__ == "__main__":
    main()
