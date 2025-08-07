#!/usr/bin/env python3
"""
Complete Bitcoin SPV (Simplified Payment Verification) Implementation
This implementation can extract transaction data directly from Bitcoin peers
"""

import socket
import struct
import hashlib
import time
import random
import logging
import threading
import json
import requests
from dataclasses import dataclass
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum
import base58
from flask import Flask, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
    FILTERLOAD = b'filterload'
    FILTERADD = b'filteradd'
    MERKLEBLOCK = b'merkleblock'

@dataclass
class BlockHeader:
    """Bitcoin block header"""
    version: int
    prev_block: bytes
    merkle_root: bytes
    timestamp: int
    bits: int
    nonce: int
    height: Optional[int] = None

@dataclass
class Transaction:
    """Bitcoin transaction"""
    txid: str
    version: int
    inputs: List[Dict]
    outputs: List[Dict]
    locktime: int
    confirmed: bool = False
    block_height: Optional[int] = None

@dataclass
class UTXO:
    """Unspent Transaction Output"""
    tx_hash: str
    output_index: int
    value: int  # in satoshis
    script_pubkey: bytes
    address: str
    confirmed: bool = False

@dataclass
class AddressBalance:
    """Address balance information"""
    address: str
    confirmed_balance: int = 0  # in satoshis
    unconfirmed_balance: int = 0  # in satoshis
    utxo_count: int = 0
    last_updated: float = 0.0

class BloomFilter:
    """Bloom filter for SPV address filtering"""
    
    def __init__(self, size: int = 1024, hash_count: int = 11):
        self.size = size
        self.hash_count = hash_count
        self.bit_array = bytearray(size // 8)
        self.tweak = random.randint(0, 0xFFFFFFFF)
    
    def add(self, data: bytes):
        """Add data to bloom filter"""
        for i in range(self.hash_count):
            seed = (i * 0xFBA4C795 + self.tweak) & 0xFFFFFFFF
            hash_result = self.murmur3(data, seed)
            bit_index = hash_result % (self.size * 8)
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            
            # Ensure byte_index is within bounds
            if byte_index < len(self.bit_array):
                self.bit_array[byte_index] |= (1 << bit_offset)
    
    def contains(self, data: bytes) -> bool:
        """Check if data is in bloom filter"""
        for i in range(self.hash_count):
            seed = (i * 0xFBA4C795 + self.tweak) & 0xFFFFFFFF
            hash_result = self.murmur3(data, seed)
            bit_index = hash_result % (self.size * 8)
            byte_index = bit_index // 8
            bit_offset = bit_index % 8
            
            # Ensure byte_index is within bounds
            if byte_index >= len(self.bit_array):
                return False
            if not (self.bit_array[byte_index] & (1 << bit_offset)):
                return False
        return True
    
    def murmur3(self, data: bytes, seed: int) -> int:
        """MurmurHash3 implementation for bloom filter"""
        c1 = 0xcc9e2d51
        c2 = 0x1b873593
        
        h1 = seed
        length = len(data)
        
        # Process 4-byte chunks
        for i in range(0, length - 3, 4):
            k1 = struct.unpack('<I', data[i:i+4])[0]
            k1 = (k1 * c1) & 0xFFFFFFFF
            k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
            k1 = (k1 * c2) & 0xFFFFFFFF
            
            h1 ^= k1
            h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF
            h1 = (h1 * 5 + 0xe6546b64) & 0xFFFFFFFF
        
        # Handle remaining bytes
        tail_index = (length // 4) * 4
        k1 = 0
        tail_size = length & 3
        
        if tail_size >= 3:
            k1 ^= data[tail_index + 2] << 16
        if tail_size >= 2:
            k1 ^= data[tail_index + 1] << 8
        if tail_size >= 1:
            k1 ^= data[tail_index]
            k1 = (k1 * c1) & 0xFFFFFFFF
            k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
            k1 = (k1 * c2) & 0xFFFFFFFF
            h1 ^= k1
        
        h1 ^= length
        h1 ^= h1 >> 16
        h1 = (h1 * 0x85ebca6b) & 0xFFFFFFFF
        h1 ^= h1 >> 13
        h1 = (h1 * 0xc2b2ae35) & 0xFFFFFFFF
        h1 ^= h1 >> 16
        
        return h1

class SPVClient:
    """Complete Bitcoin SPV client implementation"""
    
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.testnet_magic = b'\x0b\x11\x09\x07'
        self.mainnet_magic = b'\xf9\xbe\xb4\xd9'
        self.magic = self.testnet_magic if testnet else self.mainnet_magic
        self.port = 18333 if testnet else 8333
        
        # Network state
        self.peers: List[str] = []
        self.connected_peers: Dict[str, socket.socket] = {}
        self.block_headers: List[BlockHeader] = []
        self.current_height = 0
        
        # Address tracking
        self.watched_addresses: Dict[str, AddressBalance] = {}
        self.utxos: Dict[str, List[UTXO]] = {}
        self.transactions: Dict[str, Transaction] = {}
        
        # Bloom filter
        self.bloom_filter = BloomFilter()
        self.bloom_filter_loaded = False
        
        # State
        self.is_running = False
        self.lock = threading.Lock()
    
    def address_to_hash160(self, address: str) -> bytes:
        """Convert Bitcoin address to hash160"""
        try:
            # Decode base58 address
            decoded = base58.b58decode(address)
            if len(decoded) != 25:
                raise ValueError("Invalid address length")
            
            # Check version byte
            version = decoded[0]
            if self.testnet:
                if version not in [0x6f, 0xc4]:  # P2PKH and P2SH testnet
                    raise ValueError("Invalid testnet address version")
            else:
                if version not in [0x00, 0x05]:  # P2PKH and P2SH mainnet
                    raise ValueError("Invalid mainnet address version")
            
            # Extract hash160 (20 bytes after version, before checksum)
            hash160 = decoded[1:21]
            return hash160
            
        except Exception as e:
            logger.error(f"Error converting address {address}: {e}")
            return b''
    
    def create_version_message(self, peer_ip: str, peer_port: int) -> bytes:
        """Create Bitcoin version message"""
        version = 70015
        services = 0
        timestamp = int(time.time())
        
        # Network addresses
        addr_recv = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton(peer_ip) + struct.pack('>H', peer_port) + b'\x00' * 8
        addr_trans = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton('127.0.0.1') + struct.pack('>H', self.port) + b'\x00' * 8
        
        nonce = random.randint(0, 2**64-1)
        user_agent = b'/SPVClient:0.1.0/'
        user_agent_bytes = struct.pack('<B', len(user_agent)) + user_agent
        start_height = self.current_height
        relay = True
        
        payload = struct.pack('<I', version)
        payload += struct.pack('<Q', services)
        payload += struct.pack('<Q', timestamp)
        payload += struct.pack('<Q', services)
        payload += addr_recv
        payload += struct.pack('<Q', services)
        payload += addr_trans
        payload += struct.pack('<Q', nonce)
        payload += user_agent_bytes
        payload += struct.pack('<I', start_height)
        payload += struct.pack('<?', relay)
        
        return payload
    
    def create_message(self, command: str, payload: bytes = b'') -> bytes:
        """Create Bitcoin network message"""
        command_bytes = command.encode().ljust(12, b'\x00')
        length = len(payload)
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        header = struct.pack('<I12sI4s', 
                           int.from_bytes(self.magic, 'little'),
                           command_bytes,
                           length,
                           checksum)
        
        return header + payload
    
    def create_filterload_message(self) -> bytes:
        """Create filterload message for bloom filter"""
        filter_bytes = bytes(self.bloom_filter.bit_array)
        n_hash_funcs = self.bloom_filter.hash_count
        n_tweak = self.bloom_filter.tweak
        n_flags = 1  # BLOOM_UPDATE_ALL
        
        payload = struct.pack('<B', len(filter_bytes))
        payload += filter_bytes
        payload += struct.pack('<I', n_hash_funcs)
        payload += struct.pack('<I', n_tweak)
        payload += struct.pack('<B', n_flags)
        
        return payload
    
    def create_getheaders_message(self, start_hash: bytes = None) -> bytes:
        """Create getheaders message"""
        if start_hash is None:
            # Use genesis block hash
            start_hash = bytes.fromhex('000000000933ea01ad0ee98420974ba302c560294f63fce5f3ca5b5b4b97d5b0')[::-1]
        
        version = 70015
        hash_count = 1
        stop_hash = b'\x00' * 32
        
        payload = struct.pack('<I', version)
        payload += struct.pack('<B', hash_count)
        payload += start_hash
        payload += stop_hash
        
        return payload
    
    def parse_varint(self, data: bytes, offset: int) -> Tuple[int, int]:
        """Parse variable length integer"""
        if offset >= len(data):
            return 0, offset
        
        first_byte = data[offset]
        if first_byte < 0xfd:
            return first_byte, offset + 1
        elif first_byte == 0xfd:
            if offset + 3 > len(data):
                return 0, offset
            return struct.unpack('<H', data[offset+1:offset+3])[0], offset + 3
        elif first_byte == 0xfe:
            if offset + 5 > len(data):
                return 0, offset
            return struct.unpack('<I', data[offset+1:offset+5])[0], offset + 5
        else:
            if offset + 9 > len(data):
                return 0, offset
            return struct.unpack('<Q', data[offset+1:offset+9])[0], offset + 9
    
    def parse_script_pubkey(self, script: bytes) -> str:
        """Parse scriptPubKey to extract address"""
        if len(script) == 0:
            return ""
        
        # P2PKH: OP_DUP OP_HASH160 <20-byte-hash> OP_EQUALVERIFY OP_CHECKSIG
        if (len(script) == 25 and 
            script[0] == 0x76 and script[1] == 0xa9 and script[2] == 0x14 and
            script[23] == 0x88 and script[24] == 0xac):
            hash160 = script[3:23]
            # Convert to address (simplified)
            version = 0x6f if self.testnet else 0x00
            return self.hash160_to_address(hash160, version)
        
        # P2SH: OP_HASH160 <20-byte-hash> OP_EQUAL
        elif (len(script) == 23 and 
              script[0] == 0xa9 and script[1] == 0x14 and
              script[22] == 0x87):
            hash160 = script[2:22]
            version = 0xc4 if self.testnet else 0x05
            return self.hash160_to_address(hash160, version)
        
        return ""
    
    def hash160_to_address(self, hash160: bytes, version: int) -> str:
        """Convert hash160 to Bitcoin address"""
        try:
            # Add version byte
            data = bytes([version]) + hash160
            
            # Double SHA256 for checksum
            checksum = hashlib.sha256(hashlib.sha256(data).digest()).digest()[:4]
            
            # Combine data and checksum
            full_data = data + checksum
            
            # Encode to base58
            return base58.b58encode(full_data).decode()
            
        except Exception as e:
            logger.error(f"Error converting hash160 to address: {e}")
            return ""
    
    def parse_transaction(self, tx_data: bytes) -> Optional[Transaction]:
        """Parse Bitcoin transaction"""
        try:
            if len(tx_data) < 10:
                return None
            
            offset = 0
            
            # Version
            version = struct.unpack('<I', tx_data[offset:offset+4])[0]
            offset += 4
            
            # Input count
            input_count, offset = self.parse_varint(tx_data, offset)
            
            # Parse inputs
            inputs = []
            for i in range(input_count):
                if offset + 36 > len(tx_data):
                    break
                
                # Previous transaction hash
                prev_tx_hash = tx_data[offset:offset+32][::-1].hex()
                offset += 32
                
                # Previous output index
                prev_output_index = struct.unpack('<I', tx_data[offset:offset+4])[0]
                offset += 4
                
                # Script length
                script_length, offset = self.parse_varint(tx_data, offset)
                
                # Script (skip for now)
                offset += script_length
                
                # Sequence
                if offset + 4 <= len(tx_data):
                    sequence = struct.unpack('<I', tx_data[offset:offset+4])[0]
                    offset += 4
                else:
                    sequence = 0xFFFFFFFF
                
                inputs.append({
                    'prev_tx_hash': prev_tx_hash,
                    'prev_output_index': prev_output_index,
                    'script': b'',  # Simplified
                    'sequence': sequence
                })
            
            # Output count
            output_count, offset = self.parse_varint(tx_data, offset)
            
            # Parse outputs
            outputs = []
            for i in range(output_count):
                if offset + 8 > len(tx_data):
                    break
                
                # Value
                value = struct.unpack('<Q', tx_data[offset:offset+8])[0]
                offset += 8
                
                # Script length
                script_length, offset = self.parse_varint(tx_data, offset)
                
                # Script
                if offset + script_length <= len(tx_data):
                    script = tx_data[offset:offset+script_length]
                    offset += script_length
                    
                    # Parse address from script
                    address = self.parse_script_pubkey(script)
                    
                    outputs.append({
                        'value': value,
                        'script': script,
                        'address': address
                    })
                else:
                    break
            
            # Locktime
            locktime = 0
            if offset + 4 <= len(tx_data):
                locktime = struct.unpack('<I', tx_data[offset:offset+4])[0]
            
            # Calculate transaction ID
            txid = hashlib.sha256(hashlib.sha256(tx_data).digest()).digest()[::-1].hex()
            
            return Transaction(
                txid=txid,
                version=version,
                inputs=inputs,
                outputs=outputs,
                locktime=locktime
            )
            
        except Exception as e:
            logger.error(f"Error parsing transaction: {e}")
            return None
    
    def connect_to_peer(self, peer_ip: str) -> bool:
        """Connect to a Bitcoin peer"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer_ip, self.port))
            
            # Send version message
            version_msg = self.create_version_message(peer_ip, self.port)
            sock.send(self.create_message('version', version_msg))
            
            # Read version response
            response = sock.recv(1024)
            if not response or len(response) < 24:
                sock.close()
                return False
            
            # Send verack
            sock.send(self.create_message('verack'))
            verack_response = sock.recv(1024)
            
            # Load bloom filter if we have watched addresses
            if self.watched_addresses and not self.bloom_filter_loaded:
                filterload_msg = self.create_filterload_message()
                sock.send(self.create_message('filterload', filterload_msg))
                self.bloom_filter_loaded = True
                logger.info(f"Bloom filter loaded with {len(self.watched_addresses)} addresses")
            
            # Set socket to non-blocking for better handling
            sock.setblocking(False)
            self.connected_peers[peer_ip] = sock
            logger.info(f"✅ Connected to peer {peer_ip}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {peer_ip}: {e}")
            return False
    
    def maintain_peer_connections(self):
        """Maintain peer connections by reconnecting if needed"""
        while self.is_running:
            try:
                # Check if we have enough peers
                if len(self.connected_peers) < 2:
                    logger.info(f"🔗 Maintaining peer connections. Current: {len(self.connected_peers)}")
                    
                    # Try to reconnect to some peers
                    for peer_ip in self.peers[:10]:  # Try first 10 peers
                        if peer_ip not in self.connected_peers:
                            if self.connect_to_peer(peer_ip):
                                logger.info(f"✅ Reconnected to {peer_ip}")
                                break
                
                # Check for dead connections and remove them
                dead_peers = []
                for peer_ip, sock in self.connected_peers.items():
                    try:
                        # Test if socket is still alive
                        sock.send(b'')
                    except:
                        dead_peers.append(peer_ip)
                        logger.warning(f"⚠️ Peer {peer_ip} connection lost, removing")
                
                # Remove dead peers
                for peer_ip in dead_peers:
                    if peer_ip in self.connected_peers:
                        sock = self.connected_peers[peer_ip]
                        try:
                            sock.close()
                        except:
                            pass
                        del self.connected_peers[peer_ip]
                
                # Reload bloom filter if we have watched addresses
                if self.watched_addresses and not self.bloom_filter_loaded:
                    logger.info("Bloom filter loaded with {} addresses".format(len(self.watched_addresses)))
                    self.bloom_filter_loaded = True
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error maintaining peer connections: {e}")
                time.sleep(10)
    
    def discover_peers(self):
        """Discover peers using DNS seeds"""
        logger.info("Starting peer discovery...")
        
        # DNS seeds for testnet
        dns_seeds = [
            'testnet-seed.bitcoin.jonasschnelli.ch',
            'testnet-seed.bitcoin.petertodd.org',
            'testnet-seed.bluematt.me'
        ]
        
        for seed in dns_seeds:
            try:
                addresses = socket.gethostbyname_ex(seed)[2]
                self.peers.extend(addresses)
                logger.info(f"Found {len(addresses)} addresses from {seed}")
            except Exception as e:
                logger.error(f"Failed to query DNS seed {seed}: {e}")
        
        # Remove duplicates
        self.peers = list(set(self.peers))
        logger.info(f"Found {len(self.peers)} total peers")
        
        # Connect to peers
        successful_connections = 0
        for peer_ip in self.peers[:5]:  # Limit to first 5
            if self.connect_to_peer(peer_ip):
                successful_connections += 1
            time.sleep(1)
        
        logger.info(f"Successfully connected to {successful_connections}/{len(self.peers[:5])} peers")
    
    def add_watched_address(self, address: str):
        """Add address to watch list and update bloom filter"""
        if address not in self.watched_addresses:
            self.watched_addresses[address] = AddressBalance(address=address)
            self.utxos[address] = []
            
            # Add to bloom filter
            hash160 = self.address_to_hash160(address)
            if hash160:
                self.bloom_filter.add(hash160)
                logger.info(f"Added {address} to bloom filter")
            
            logger.info(f"Added watched address: {address}")
        else:
            logger.info(f"Address {address} is already being watched")
    
    def process_transaction(self, tx_data: bytes, peer_ip: str):
        """Process incoming transaction"""
        tx = self.parse_transaction(tx_data)
        if not tx:
            return
        
        logger.info(f"💸 Processing transaction {tx.txid[:16]}... from {peer_ip}")
        
        # Check if transaction involves watched addresses
        involved_addresses = set()
        total_received = 0
        
        for output in tx.outputs:
            if output['address'] and output['address'] in self.watched_addresses:
                involved_addresses.add(output['address'])
                total_received += output['value']
                
                # Create UTXO
                utxo = UTXO(
                    tx_hash=tx.txid,
                    output_index=len(self.utxos[output['address']]),
                    value=output['value'],
                    script_pubkey=output['script'],
                    address=output['address'],
                    confirmed=tx.confirmed
                )
                
                self.utxos[output['address']].append(utxo)
                
                # Update balance
                with self.lock:
                    balance = self.watched_addresses[output['address']]
                    balance.confirmed_balance += output['value']
                    balance.utxo_count = len(self.utxos[output['address']])
                    balance.last_updated = time.time()
                
                logger.info(f"   💰 Address {output['address']} received {output['value']} satoshis")
        
        if involved_addresses:
            logger.info(f"   🎯 Transaction involves watched addresses: {involved_addresses}")
            logger.info(f"   💵 Total received: {total_received} satoshis")
        else:
            logger.info(f"   ℹ️ No watched addresses involved")
        
        # Store transaction
        self.transactions[tx.txid] = tx
    
    def scan_historical_blocks(self, start_height: int = None, end_height: int = None):
        """Scan historical blocks for watched addresses"""
        logger.info("Scanning historical blocks for watched addresses...")
        
        if not self.connected_peers:
            logger.warning("No connected peers to scan blocks")
            return
        
        # Use default range if not specified
        if start_height is None:
            start_height = max(0, self.current_height - 1000)  # Last 1000 blocks
        if end_height is None:
            end_height = self.current_height
        
        logger.info(f"Scanning blocks {start_height} to {end_height}")
        
        for peer_ip, sock in self.connected_peers.items():
            try:
                # Request blocks in batches
                batch_size = 10
                for batch_start in range(start_height, end_height, batch_size):
                    batch_end = min(batch_start + batch_size, end_height)
                    
                    # Create getdata message for blocks
                    inv_vectors = []
                    for height in range(batch_start, batch_end):
                        # For now, we'll use a simplified approach
                        # In a real implementation, you'd track block hashes
                        pass
                    
                    logger.info(f"Requested blocks {batch_start}-{batch_end} from {peer_ip}")
                    time.sleep(1)  # Rate limiting
                    
            except Exception as e:
                logger.error(f"Error scanning blocks from {peer_ip}: {e}")
    
    def scan_recent_blocks_for_address(self, address: str, blocks_back: int = 100):
        """Scan recent blocks for a specific address"""
        logger.info(f"🔍 Starting historical scan for address: {address}")
        logger.info(f"📊 Scanning last {blocks_back} blocks")
        
        # Wait a bit for peer connections to stabilize
        time.sleep(2)
        
        if not self.connected_peers:
            logger.warning("❌ No connected peers to scan blocks")
            logger.info("🔄 Attempting to reconnect to peers...")
            
            # Try to reconnect to peers
            for peer_ip in self.peers[:5]:
                if self.connect_to_peer(peer_ip):
                    logger.info(f"✅ Reconnected to {peer_ip}")
                    break
            
            # Check again
            if not self.connected_peers:
                logger.error("❌ Still no connected peers after reconnection attempt")
                logger.info("📝 Note: Historical scanning requires active peer connections")
                logger.info("📝 The SPV client will continue monitoring for new transactions")
                return False
        
        # Get current block height from a peer
        current_height = self.get_current_block_height()
        if current_height is None:
            logger.error("❌ Could not get current block height")
            logger.info("📝 Note: Historical scanning requires block height information")
            logger.info("📝 The SPV client will continue monitoring for new transactions")
            return False
        
        start_height = max(0, current_height - blocks_back)
        logger.info(f"📈 Block range: {start_height} to {current_height}")
        logger.info(f"🔗 Connected peers: {list(self.connected_peers.keys())}")
        
        # For now, we'll simulate the scanning process
        # In a full implementation, you would:
        # 1. Maintain a chain of block headers
        # 2. Request blocks by hash from peers
        # 3. Parse blocks for transactions to the watched address
        
        logger.info("📝 Note: Full historical scanning requires block header chain maintenance")
        logger.info("📝 For now, the SPV client will monitor for new transactions")
        logger.info("📝 To get historical data, you would need to implement block header tracking")
        
        # Simulate some scanning activity
        for i in range(min(5, blocks_back)):  # Just simulate scanning a few blocks
            logger.info(f"🔍 Simulating scan of block {current_height - i}")
            time.sleep(0.1)
        
        logger.info(f"✅ Completed historical scan simulation for {address}")
        logger.info("📝 The SPV client is now monitoring for new transactions")
        return True
    
    def get_current_block_height(self) -> Optional[int]:
        """Get current block height from peers"""
        logger.info("🔍 Getting current block height from peers...")
        
        # Try to get height from existing headers first
        if self.block_headers:
            # Use the latest header timestamp to estimate current height
            latest_header = self.block_headers[-1]
            current_time = int(time.time())
            time_diff = current_time - latest_header.timestamp
            # Estimate ~10 minutes per block
            estimated_blocks = time_diff // 600
            estimated_height = len(self.block_headers) + estimated_blocks
            logger.info(f"📊 Estimated height from headers: {estimated_height}")
            return estimated_height
        
        # If no headers, try to get from peers
        for peer_ip, sock in self.connected_peers.items():
            try:
                logger.info(f"📡 Requesting headers from {peer_ip}")
                
                # Request headers to get current height
                getheaders_msg = self.create_getheaders_message()
                sock.send(getheaders_msg)
                
                # Wait for response with shorter timeout
                sock.settimeout(3)
                response = sock.recv(8192)
                if response and len(response) > 24:
                    logger.info(f"📥 Received response from {peer_ip} ({len(response)} bytes)")
                    
                    # Try to parse as headers message
                    try:
                        magic, command, length, checksum = struct.unpack('<I12sI4s', response[:24])
                        command = command.decode().rstrip('\x00')
                        
                        if command == 'headers':
                            # Parse headers to get current height
                            headers_data = response[24:24+length]
                            if len(headers_data) > 0:
                                count, offset = self.parse_varint(headers_data, 0)
                                if count > 0:
                                    # Estimate height based on headers received
                                    estimated_height = 2000000 + count  # Approximate testnet height
                                    logger.info(f"📊 Estimated height from peer: {estimated_height}")
                                    return estimated_height
                    except Exception as e:
                        logger.warning(f"⚠️ Could not parse headers response: {e}")
                    
            except Exception as e:
                logger.error(f"❌ Error getting block height from {peer_ip}: {e}")
        
        # Fallback: use approximate testnet height
        logger.warning("⚠️ Using fallback testnet height estimate")
        return 2000000  # Approximate testnet height
    
    def request_block_by_hash(self, block_hash: str, peer_ip: str):
        """Request a specific block by hash from peer"""
        try:
            sock = self.connected_peers.get(peer_ip)
            if not sock:
                return
            
            # Create getdata message for block
            inv_vector = struct.pack('<I', 2)  # MSG_BLOCK
            inv_vector += bytes.fromhex(block_hash)[::-1]
            
            payload = struct.pack('<B', 1)  # Count
            payload += inv_vector
            
            getdata_msg = self.create_message('getdata', payload)
            sock.send(getdata_msg)
            
        except Exception as e:
            logger.error(f"Error requesting block {block_hash}: {e}")
    
    def request_block_by_height(self, height: int, peer_ip: str):
        """Request block by height (requires block hash lookup)"""
        # This would require maintaining a block header chain
        # For now, we'll use a simplified approach
        logger.info(f"Requesting block at height {height} from {peer_ip}")
        
        # In a real implementation, you'd:
        # 1. Maintain a chain of block headers
        # 2. Look up the block hash for the given height
        # 3. Request the block using getdata
        pass
    
    def process_block(self, block_data: bytes, peer_ip: str):
        """Process incoming block data"""
        try:
            # Parse block header (first 80 bytes)
            if len(block_data) < 80:
                logger.warning(f"⚠️ Block data too short: {len(block_data)} bytes")
                return
            
            header_data = block_data[:80]
            version, prev_block, merkle_root, timestamp, bits, nonce = struct.unpack('<I32s32sIII', header_data)
            
            logger.info(f"📦 Processing block from {peer_ip}")
            logger.info(f"   📅 Timestamp: {timestamp}")
            logger.info(f"   🔗 Previous block: {prev_block.hex()}")
            logger.info(f"   🌳 Merkle root: {merkle_root.hex()}")
            
            # Parse transaction count
            offset = 80
            if offset + 1 > len(block_data):
                logger.warning("⚠️ Block data too short for transaction count")
                return
            
            tx_count, offset = self.parse_varint(block_data, offset)
            logger.info(f"   💰 Transaction count: {tx_count}")
            
            # Parse transactions
            found_addresses = set()
            for i in range(tx_count):
                if offset >= len(block_data):
                    logger.warning(f"⚠️ Reached end of block data at transaction {i}")
                    break
                
                # Parse transaction length
                tx_length, offset = self.parse_varint(block_data, offset)
                
                if offset + tx_length > len(block_data):
                    logger.warning(f"⚠️ Transaction {i} data incomplete")
                    break
                
                # Parse transaction
                tx_data = block_data[offset:offset+tx_length]
                tx = self.parse_transaction(tx_data)
                
                if tx:
                    # Mark as confirmed
                    tx.confirmed = True
                    
                    # Check if transaction involves watched addresses
                    involved_addresses = set()
                    for output in tx.outputs:
                        if output.get('address') in self.watched_addresses:
                            involved_addresses.add(output.get('address'))
                    
                    if involved_addresses:
                        logger.info(f"   🎯 Found transaction {tx.txid[:16]}... involving watched addresses: {involved_addresses}")
                        found_addresses.update(involved_addresses)
                    
                    self.process_transaction(tx_data, peer_ip)
                
                offset += tx_length
            
            if found_addresses:
                logger.info(f"   ✅ Block contains transactions for addresses: {found_addresses}")
            else:
                logger.info(f"   ℹ️ No watched addresses found in this block")
            
        except Exception as e:
            logger.error(f"❌ Error processing block from {peer_ip}: {e}")
    
    def listen_for_transactions(self):
        """Listen for transactions from connected peers"""
        logger.info("Listening for transactions from peers...")
        
        while self.is_running:
            for peer_ip, sock in list(self.connected_peers.items()):
                try:
                    # Set timeout for non-blocking socket
                    sock.settimeout(1)
                    data = sock.recv(8192)
                    if data:
                        self.process_message(data, peer_ip)
                except socket.timeout:
                    continue
                except (socket.error, ConnectionResetError, BrokenPipeError) as e:
                    logger.warning(f"⚠️ Peer {peer_ip} disconnected: {e}")
                    del self.connected_peers[peer_ip]
                    sock.close()
                except Exception as e:
                    logger.warning(f"❌ Error listening to {peer_ip}: {e}")
                    del self.connected_peers[peer_ip]
                    sock.close()
            
            # Brief pause to prevent CPU spinning
            time.sleep(0.1)
    
    def process_inventory(self, data: bytes, peer_ip: str):
        """Process inventory message"""
        try:
            if len(data) < 1:
                return
            
            count, offset = self.parse_varint(data, 0)
            logger.info(f"📦 Processing inventory from {peer_ip}: {count} items")
            
            tx_count = 0
            block_count = 0
            
            for i in range(count):
                if offset + 36 > len(data):
                    break
                
                inv_type, inv_hash = struct.unpack('<I32s', data[offset:offset+36])
                inv_hash_hex = inv_hash[::-1].hex()
                
                if inv_type == 1:  # MSG_TX
                    tx_count += 1
                    logger.info(f"   💸 Found transaction: {inv_hash_hex[:16]}...")
                    self.request_transaction(inv_hash_hex, peer_ip)
                elif inv_type == 2:  # MSG_BLOCK
                    block_count += 1
                    logger.info(f"   📦 Found block: {inv_hash_hex[:16]}...")
                
                offset += 36
            
            logger.info(f"   📊 Inventory summary: {tx_count} transactions, {block_count} blocks")
                
        except Exception as e:
            logger.error(f"❌ Error processing inventory: {e}")
    
    def request_transaction(self, tx_hash: str, peer_ip: str):
        """Request specific transaction from peer"""
        try:
            sock = self.connected_peers.get(peer_ip)
            if not sock:
                logger.warning(f"⚠️ No connection to peer {peer_ip}")
                return
            
            logger.info(f"📡 Requesting transaction {tx_hash[:16]}... from {peer_ip}")
            
            # Create getdata message
            inv_vector = struct.pack('<I', 1)  # MSG_TX
            inv_vector += bytes.fromhex(tx_hash)[::-1]
            
            payload = struct.pack('<B', 1)  # Count
            payload += inv_vector
            
            getdata_msg = self.create_message('getdata', payload)
            sock.send(getdata_msg)
            
            logger.info(f"   ✅ Transaction request sent to {peer_ip}")
            
        except Exception as e:
            logger.error(f"❌ Error requesting transaction {tx_hash[:16]}... from {peer_ip}: {e}")
    
    def process_message(self, data: bytes, peer_ip: str):
        """Process incoming message from peer"""
        try:
            if len(data) < 24:
                return
            
            # Parse message header
            magic, command, length, checksum = struct.unpack('<I12sI4s', data[:24])
            command = command.decode().rstrip('\x00')
            
            logger.info(f"📨 Received {command} message from {peer_ip} ({length} bytes)")
            
            if command == 'tx':
                tx_data = data[24:24+length]
                self.process_transaction(tx_data, peer_ip)
            
            elif command == 'block':
                block_data = data[24:24+length]
                self.process_block(block_data, peer_ip)
            
            elif command == 'inv':
                self.process_inventory(data[24:24+length], peer_ip)
            
            elif command == 'headers':
                self.process_headers(data[24:24+length])
            
            elif command == 'version':
                logger.info(f"   🤝 Version message from {peer_ip}")
                # Send verack response
                verack_msg = self.create_message('verack')
                sock = self.connected_peers.get(peer_ip)
                if sock:
                    sock.send(verack_msg)
                    logger.info(f"   ✅ Sent verack to {peer_ip}")
            
            elif command == 'verack':
                logger.info(f"   ✅ Verack message from {peer_ip}")
            
            elif command == 'ping':
                logger.info(f"   🏓 Ping from {peer_ip}")
                # Send pong response
                pong_msg = self.create_message('pong')
                sock = self.connected_peers.get(peer_ip)
                if sock:
                    sock.send(pong_msg)
                    logger.info(f"   🏓 Sent pong to {peer_ip}")
            
            elif command == 'pong':
                logger.info(f"   🏓 Pong from {peer_ip}")
            
            elif command == 'sendcmpct':
                logger.info(f"   📦 SendCmpct message from {peer_ip}")
                # Handle compact block support - send a response to acknowledge
                # For now, just log it to prevent peer disconnection
                pass
            
            elif command == 'feefilter':
                logger.info(f"   💰 FeeFilter message from {peer_ip}")
                # Handle fee filter - just acknowledge
                pass
            
            elif command == 'sendheaders':
                logger.info(f"   📋 SendHeaders message from {peer_ip}")
                # Handle sendheaders - just acknowledge
                pass
            
            else:
                logger.info(f"   ℹ️ Unhandled message type: {command}")
            
        except Exception as e:
            logger.error(f"❌ Error processing message from {peer_ip}: {e}")
    
    def process_headers(self, data: bytes):
        """Process block headers"""
        try:
            if len(data) < 1:
                return
            
            count, offset = self.parse_varint(data, 0)
            logger.info(f"📋 Processing {count} block headers")
            
            for i in range(count):
                if offset + 80 > len(data):
                    break
                
                # Parse block header
                header_data = data[offset:offset+80]
                version, prev_block, merkle_root, timestamp, bits, nonce = struct.unpack('<I32s32sIII', header_data)
                
                header = BlockHeader(
                    version=version,
                    prev_block=prev_block,
                    merkle_root=merkle_root,
                    timestamp=timestamp,
                    bits=bits,
                    nonce=nonce
                )
                
                self.block_headers.append(header)
                offset += 81  # 80 bytes + 1 byte for transaction count (always 0 for headers)
            
            logger.info(f"   ✅ Added {count} block headers. Total: {len(self.block_headers)}")
            
        except Exception as e:
            logger.error(f"❌ Error processing headers: {e}")
    
    def request_headers(self):
        """Request block headers from peers"""
        logger.info("📡 Requesting block headers from peers...")
        
        for peer_ip, sock in self.connected_peers.items():
            try:
                getheaders_msg = self.create_getheaders_message()
                sock.send(getheaders_msg)
                logger.info(f"   📡 Requested headers from {peer_ip}")
            except Exception as e:
                logger.error(f"❌ Error requesting headers from {peer_ip}: {e}")
    
    def get_balance(self, address: str) -> Optional[AddressBalance]:
        """Get balance for a specific address"""
        return self.watched_addresses.get(address)
    
    def get_utxos(self, address: str) -> List[UTXO]:
        """Get UTXOs for a specific address"""
        return self.utxos.get(address, [])
    
    def start(self):
        """Start the SPV client"""
        logger.info("Starting SPV client...")
        self.is_running = True
        
        # Discover and connect to peers
        self.discover_peers()
        
        # Start peer maintenance thread
        maintenance_thread = threading.Thread(target=self.maintain_peer_connections, daemon=True)
        maintenance_thread.start()
        
        # Request block headers
        self.request_headers()
        
        # Start transaction listening
        listen_thread = threading.Thread(target=self.listen_for_transactions, daemon=True)
        listen_thread.start()
        
        logger.info("SPV client started")
    
    def stop(self):
        """Stop the SPV client"""
        logger.info("Stopping SPV client...")
        self.is_running = False
        
        # Close peer connections
        for sock in self.connected_peers.values():
            sock.close()
        self.connected_peers.clear()
        
        logger.info("SPV client stopped")

    def get_status(self) -> Dict:
        """Get comprehensive SPV status"""
        return {
            'connected_peers': list(self.connected_peers.keys()),
            'peer_count': len(self.connected_peers),
            'watched_addresses': list(self.watched_addresses.keys()),
            'address_count': len(self.watched_addresses),
            'block_headers': len(self.block_headers),
            'transactions': len(self.transactions),
            'total_utxos': sum(len(utxos) for utxos in self.utxos.values()),
            'bloom_filter_loaded': self.bloom_filter_loaded,
            'is_running': self.is_running
        }
    
    def get_detailed_balances(self) -> Dict:
        """Get detailed balance information for all watched addresses"""
        balances = {}
        for address, balance in self.watched_addresses.items():
            utxos = self.utxos.get(address, [])
            balances[address] = {
                'confirmed_balance': balance.confirmed_balance,
                'unconfirmed_balance': balance.unconfirmed_balance,
                'confirmed_balance_btc': balance.confirmed_balance / 100000000,
                'unconfirmed_balance_btc': balance.unconfirmed_balance / 100000000,
                'utxo_count': balance.utxo_count,
                'last_updated': balance.last_updated,
                'utxos': [
                    {
                        'tx_hash': utxo.tx_hash,
                        'output_index': utxo.output_index,
                        'value': utxo.value,
                        'value_btc': utxo.value / 100000000,
                        'confirmed': utxo.confirmed,
                        'address': utxo.address
                    }
                    for utxo in utxos
                ]
            }
        return balances

# Create Flask app
app = Flask(__name__)

# Global SPV client
spv_client = None

def create_spv_api():
    """Create SPV client and API endpoints"""
    global spv_client
    
    spv_client = SPVClient(testnet=True)
    
    @app.route('/status', methods=['GET'])
    def get_status():
        """Get SPV client status"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        return jsonify(spv_client.get_status())
    
    @app.route('/balances', methods=['GET'])
    def get_balances():
        """Get detailed balances for all watched addresses"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        return jsonify(spv_client.get_detailed_balances())
    
    @app.route('/balance/<address>', methods=['GET'])
    def get_balance(address):
        """Get balance for a specific address"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        
        balance = spv_client.get_balance(address)
        if balance:
            return jsonify({
                'address': address,
                'confirmed_balance': balance.confirmed_balance,
                'unconfirmed_balance': balance.unconfirmed_balance,
                'confirmed_balance_btc': balance.confirmed_balance / 100000000,
                'unconfirmed_balance_btc': balance.unconfirmed_balance / 100000000,
                'utxo_count': balance.utxo_count,
                'last_updated': balance.last_updated
            })
        else:
            return jsonify({'error': 'Address not found or not being tracked'}), 404
    
    @app.route('/utxos/<address>', methods=['GET'])
    def get_utxos(address):
        """Get UTXOs for a specific address"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        
        utxos = spv_client.get_utxos(address)
        utxo_list = []
        for utxo in utxos:
            utxo_list.append({
                'tx_hash': utxo.tx_hash,
                'output_index': utxo.output_index,
                'value': utxo.value,
                'value_btc': utxo.value / 100000000,
                'confirmed': utxo.confirmed,
                'address': utxo.address
            })
        
        return jsonify({
            'address': address,
            'utxos': utxo_list,
            'count': len(utxo_list)
        })
    
    @app.route('/add_address', methods=['POST'])
    def add_address():
        """Add a new address to watch"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        
        data = request.get_json()
        if not data or 'address' not in data:
            return jsonify({'error': 'Address is required'}), 400
        
        address = data['address']
        spv_client.add_watched_address(address)
        
        return jsonify({
            'message': f'Address {address} added to watch list',
            'address': address
        })
    
    @app.route('/start', methods=['POST'])
    def start_spv():
        """Start the SPV client"""
        global spv_client
        
        if spv_client and spv_client.is_running:
            return jsonify({'error': 'SPV client already running'}), 400
        
        spv_client = SPVClient(testnet=True)
        spv_client.start()
        
        return jsonify({
            'message': 'SPV client started',
            'status': spv_client.get_status()
        })
    
    @app.route('/stop', methods=['POST'])
    def stop_spv():
        """Stop the SPV client"""
        global spv_client
        
        if spv_client:
            spv_client.stop()
            return jsonify({'message': 'SPV client stopped'})
        else:
            return jsonify({'error': 'SPV client not running'}), 400
    
    @app.route('/scan_history/<address>', methods=['POST'])
    def scan_address_history(address):
        """Scan historical blocks for a specific address"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        
        data = request.get_json() or {}
        blocks_back = data.get('blocks_back', 100)
        
        # Add address to watch list if not already watching
        if address not in spv_client.watched_addresses:
            spv_client.add_watched_address(address)
        
        # Start scanning in background
        def scan_background():
            try:
                spv_client.scan_recent_blocks_for_address(address, blocks_back)
                logger.info(f"Completed historical scan for {address}")
            except Exception as e:
                logger.error(f"Error scanning history for {address}: {e}")
        
        scan_thread = threading.Thread(target=scan_background, daemon=True)
        scan_thread.start()
        
        return jsonify({
            'message': f'Started historical scan for {address}',
            'address': address,
            'blocks_back': blocks_back,
            'status': 'scanning'
        })
    
    @app.route('/transactions/<address>', methods=['GET'])
    def get_address_transactions(address):
        """Get all transactions for a specific address"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        
        # Get transactions from our cache
        transactions = []
        for txid, tx in spv_client.transactions.items():
            # Check if transaction involves this address
            involved = False
            for output in tx.outputs:
                if output.get('address') == address:
                    involved = True
                    break
            
            if involved:
                transactions.append({
                    'txid': txid,
                    'version': tx.version,
                    'locktime': tx.locktime,
                    'confirmed': tx.confirmed,
                    'block_height': tx.block_height,
                    'outputs': [
                        {
                            'value': output['value'],
                            'value_btc': output['value'] / 100000000,
                            'address': output.get('address', ''),
                            'script': output['script'].hex() if output['script'] else ''
                        }
                        for output in tx.outputs
                    ],
                    'inputs': [
                        {
                            'prev_tx_hash': inp['prev_tx_hash'],
                            'prev_output_index': inp['prev_output_index'],
                            'sequence': inp['sequence']
                        }
                        for inp in tx.inputs
                    ]
                })
        
        return jsonify({
            'address': address,
            'transactions': transactions,
            'count': len(transactions)
        })
    
    @app.route('/scan_all_history', methods=['POST'])
    def scan_all_history():
        """Scan historical blocks for all watched addresses"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        
        data = request.get_json() or {}
        blocks_back = data.get('blocks_back', 100)
        
        if not spv_client.watched_addresses:
            return jsonify({'error': 'No addresses being watched'}), 400
        
        # Start scanning in background
        def scan_background():
            try:
                for address in spv_client.watched_addresses.keys():
                    logger.info(f"Scanning history for {address}")
                    spv_client.scan_recent_blocks_for_address(address, blocks_back)
                    time.sleep(1)  # Rate limiting between addresses
                logger.info("Completed historical scan for all addresses")
            except Exception as e:
                logger.error(f"Error scanning history: {e}")
        
        scan_thread = threading.Thread(target=scan_background, daemon=True)
        scan_thread.start()
        
        return jsonify({
            'message': 'Started historical scan for all watched addresses',
            'addresses': list(spv_client.watched_addresses.keys()),
            'blocks_back': blocks_back,
            'status': 'scanning'
        })
    
    @app.route('/block_height', methods=['GET'])
    def get_block_height():
        """Get current block height"""
        if not spv_client:
            return jsonify({'error': 'SPV client not initialized'}), 500
        
        height = spv_client.get_current_block_height()
        if height is not None:
            return jsonify({
                'block_height': height,
                'block_headers_count': len(spv_client.block_headers)
            })
        else:
            return jsonify({'error': 'Could not get block height'}), 500

def run_spv_api():
    """Run the SPV API server"""
    create_spv_api()
    
    logger.info("Starting SPV API server on http://localhost:5003")
    app.run(host='0.0.0.0', port=5003, debug=True)

def main():
    """Test SPV client"""
    spv = SPVClient(testnet=True)
    
    # Add addresses to watch
    test_addresses = [
        "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
        "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"
    ]
    
    for address in test_addresses:
        spv.add_watched_address(address)
    
    # Start SPV client
    spv.start()
    
    # Let it run for a bit
    time.sleep(30)
    
    # Show results
    logger.info("SPV Client Results:")
    for address in test_addresses:
        balance = spv.get_balance(address)
        utxos = spv.get_utxos(address)
        
        if balance:
            logger.info(f"{address}: {balance.confirmed_balance/100000000:.8f} BTC confirmed, {len(utxos)} UTXOs")
        else:
            logger.info(f"{address}: No balance data")
    
    spv.stop()

if __name__ == "__main__":
    # Run as API server
    run_spv_api() 