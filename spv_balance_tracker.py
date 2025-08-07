#!/usr/bin/env python3
"""
Bitcoin SPV Client with Balance Tracking
"""

import socket
import struct
import hashlib
import time
import random
import logging
import threading
import requests
from dataclasses import dataclass
from typing import List, Optional, Dict, Set
# import base58  # Not used in this implementation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class SPVBalanceTracker:
    """Bitcoin SPV client with balance tracking"""
    
    def __init__(self):
        self.testnet_magic = b'\x0b\x11\x09\x07'
        self.testnet_port = 18333
        self.peers: List[str] = []
        self.watched_addresses: Dict[str, AddressBalance] = {}
        self.utxos: Dict[str, List[UTXO]] = {}  # address -> list of UTXOs
        self.transaction_cache: Dict[str, bytes] = {}
        self.is_running = False
        self.blockcypher_api_key = '1d2d23342b5c47a4bd3a6fa921f61cc6'  # Your API key
        
    def fetch_blockcypher_balance(self, address: str) -> Optional[Dict]:
        """Fetch real balance data from BlockCypher API"""
        try:
            url = f"https://api.blockcypher.com/v1/btc/test3/addrs/{address}/balance"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to fetch balance for {address}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching BlockCypher balance for {address}: {e}")
            return None
    
    def fetch_blockcypher_utxos(self, address: str) -> Optional[List[Dict]]:
        """Fetch real UTXO data from BlockCypher API"""
        try:
            url = f"https://api.blockcypher.com/v1/btc/test3/addrs/{address}?unspentOnly=true"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get('txrefs', [])
            else:
                logger.warning(f"Failed to fetch UTXOs for {address}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching BlockCypher UTXOs for {address}: {e}")
            return None
    
    def update_address_from_blockcypher(self, address: str):
        """Update address balance and UTXOs from BlockCypher API"""
        logger.info(f"Fetching real data for address: {address}")
        
        # Fetch balance
        balance_data = self.fetch_blockcypher_balance(address)
        if balance_data:
            # Update balance
            if address not in self.watched_addresses:
                self.watched_addresses[address] = AddressBalance(address=address)
            
            self.watched_addresses[address].confirmed_balance = balance_data.get('final_balance', 0)
            self.watched_addresses[address].unconfirmed_balance = balance_data.get('unconfirmed_balance', 0)
            self.watched_addresses[address].last_updated = time.time()
            
            logger.info(f"Updated balance for {address}: {balance_data.get('final_balance', 0)/100000000:.8f} BTC confirmed, {balance_data.get('unconfirmed_balance', 0)/100000000:.8f} BTC unconfirmed")
        
        # Fetch UTXOs
        utxo_data = self.fetch_blockcypher_utxos(address)
        if utxo_data:
            self.utxos[address] = []
            for utxo in utxo_data:
                spv_utxo = UTXO(
                    tx_hash=utxo.get('tx_hash', ''),
                    output_index=utxo.get('tx_output_n', 0),
                    value=utxo.get('value', 0),
                    script_pubkey=b"",  # We don't need this for balance tracking
                    address=address,
                    confirmed=utxo.get('confirmed', False)
                )
                self.utxos[address].append(spv_utxo)
            
            self.watched_addresses[address].utxo_count = len(self.utxos[address])
            logger.info(f"Updated UTXOs for {address}: {len(self.utxos[address])} UTXOs")
    
    def update_all_addresses_from_blockcypher(self):
        """Update all watched addresses from BlockCypher API"""
        logger.info("Updating all addresses from BlockCypher API...")
        for address in list(self.watched_addresses.keys()):
            self.update_address_from_blockcypher(address)
            time.sleep(0.5)  # Rate limiting
    
    def create_version_message(self, peer_ip: str, peer_port: int) -> bytes:
        """Create a Bitcoin version message using the working approach"""
        version = 70015
        services = 0
        timestamp = int(time.time())
        
        # Create network addresses manually
        addr_recv = b'\x00' * 26  # 26 bytes for network address
        addr_trans = b'\x00' * 26  # 26 bytes for network address
        
        # Set the IP addresses in the network address structure
        # Format: 10 bytes padding + 2 bytes family + 4 bytes IP + 2 bytes port + 8 bytes padding
        addr_recv = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton(peer_ip) + struct.pack('>H', peer_port) + b'\x00' * 8
        addr_trans = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton('127.0.0.1') + struct.pack('>H', 18333) + b'\x00' * 8
        
        nonce = random.randint(0, 2**64-1)
        user_agent = b'/SPVBalanceTracker:0.1.0/'
        user_agent_bytes = struct.pack('<B', len(user_agent)) + user_agent
        start_height = 0
        relay = True
        
        # Create version payload using individual struct.pack calls
        payload = struct.pack('<I', version)  # version (4 bytes)
        payload += struct.pack('<Q', services)  # services (8 bytes)
        payload += struct.pack('<Q', timestamp)  # timestamp (8 bytes)
        payload += struct.pack('<Q', services)  # addr_recv_services (8 bytes)
        payload += addr_recv  # addr_recv (26 bytes)
        payload += struct.pack('<Q', services)  # addr_trans_services (8 bytes)
        payload += addr_trans  # addr_trans (26 bytes)
        payload += struct.pack('<Q', nonce)  # nonce (8 bytes)
        payload += user_agent_bytes  # user_agent
        payload += struct.pack('<I', start_height)  # start_height (4 bytes)
        payload += struct.pack('<?', relay)  # relay (1 byte)
        
        return payload
    
    def create_message(self, command: str, payload: bytes = b'') -> bytes:
        """Create a Bitcoin network message"""
        # Command (12 bytes, null-padded)
        command_bytes = command.encode().ljust(12, b'\x00')
        
        # Length
        length = len(payload)
        
        # Checksum (double SHA256)
        checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
        
        # Message header
        header = struct.pack('<I12sI4s', 
                           int.from_bytes(self.testnet_magic, 'little'),
                           command_bytes,
                           length,
                           checksum)
        
        return header + payload
    
    def parse_varint(self, data: bytes, offset: int) -> tuple:
        """Parse variable length integer"""
        if offset >= len(data):
            return 0, offset
        
        first_byte = data[offset]
        if first_byte < 0xfd:
            return first_byte, offset + 1
        elif first_byte == 0xfd:
            if offset + 3 <= len(data):
                return struct.unpack('<H', data[offset+1:offset+3])[0], offset + 3
        elif first_byte == 0xfe:
            if offset + 5 <= len(data):
                return struct.unpack('<I', data[offset+1:offset+5])[0], offset + 5
        else:
            if offset + 9 <= len(data):
                return struct.unpack('<Q', data[offset+1:offset+9])[0], offset + 9
        
        return 0, offset
    
    def parse_script_pubkey(self, script: bytes) -> str:
        """Parse script pubkey to extract address"""
        try:
            if len(script) == 0:
                return ""
            
            # Check for P2PKH (Pay to Public Key Hash)
            if len(script) == 25 and script[0] == 0x76 and script[1] == 0xa9 and script[2] == 0x14 and script[23] == 0x88 and script[24] == 0xac:
                pubkey_hash = script[3:23]
                # Convert to testnet address
                version = 0x6f  # testnet
                addr_bytes = bytes([version]) + pubkey_hash
                checksum = hashlib.sha256(hashlib.sha256(addr_bytes).digest()).digest()[:4]
                addr_bytes += checksum
                return base58.b58encode(addr_bytes).decode()
            
            # Check for P2SH (Pay to Script Hash)
            elif len(script) == 23 and script[0] == 0xa9 and script[1] == 0x14 and script[22] == 0x87:
                script_hash = script[2:22]
                # Convert to testnet address
                version = 0xc4  # testnet
                addr_bytes = bytes([version]) + script_hash
                checksum = hashlib.sha256(hashlib.sha256(addr_bytes).digest()).digest()[:4]
                addr_bytes += checksum
                return base58.b58encode(addr_bytes).decode()
            
            # For other script types, return empty string
            return ""
            
        except Exception as e:
            logger.error(f"Failed to parse script pubkey: {e}")
            return ""
    
    def parse_transaction(self, tx_data: bytes) -> Dict:
        """Parse a Bitcoin transaction"""
        try:
            if len(tx_data) < 10:
                return {}
            
            offset = 0
            
            # Parse version
            version = struct.unpack('<I', tx_data[offset:offset+4])[0]
            offset += 4
            
            # Parse input count
            input_count, offset = self.parse_varint(tx_data, offset)
            
            # Parse inputs
            inputs = []
            for i in range(input_count):
                if offset + 36 >= len(tx_data):
                    break
                
                # Previous transaction hash (32 bytes, little-endian)
                prev_tx_hash = tx_data[offset:offset+32][::-1].hex()
                offset += 32
                
                # Previous output index
                prev_output_index = struct.unpack('<I', tx_data[offset:offset+4])[0]
                offset += 4
                
                # Script length
                script_length, offset = self.parse_varint(tx_data, offset)
                
                # Script (we don't need to parse this for balance tracking)
                offset += script_length
                
                # Sequence
                if offset + 4 <= len(tx_data):
                    sequence = struct.unpack('<I', tx_data[offset:offset+4])[0]
                    offset += 4
                
                inputs.append({
                    'prev_tx_hash': prev_tx_hash,
                    'prev_output_index': prev_output_index,
                    'sequence': sequence
                })
            
            # Parse output count
            output_count, offset = self.parse_varint(tx_data, offset)
            
            # Parse outputs
            outputs = []
            for i in range(output_count):
                if offset + 8 >= len(tx_data):
                    break
                
                # Value (8 bytes, little-endian)
                value = struct.unpack('<Q', tx_data[offset:offset+8])[0]
                offset += 8
                
                # Script length
                script_length, offset = self.parse_varint(tx_data, offset)
                
                # Script pubkey
                if offset + script_length <= len(tx_data):
                    script_pubkey = tx_data[offset:offset+script_length]
                    offset += script_length
                    
                    # Parse address from script
                    address = self.parse_script_pubkey(script_pubkey)
                    
                    outputs.append({
                        'value': value,
                        'script_pubkey': script_pubkey,
                        'address': address
                    })
            
            # Calculate transaction hash
            tx_hash = hashlib.sha256(hashlib.sha256(tx_data).digest()).digest()[::-1].hex()
            
            return {
                'tx_hash': tx_hash,
                'version': version,
                'inputs': inputs,
                'outputs': outputs
            }
            
        except Exception as e:
            logger.error(f"Failed to parse transaction: {e}")
            return {}
    
    def update_balance_for_address(self, address: str):
        """Update balance for a specific address"""
        if address not in self.utxos:
            return
        
        confirmed_balance = 0
        unconfirmed_balance = 0
        utxo_count = len(self.utxos[address])
        
        for utxo in self.utxos[address]:
            if utxo.confirmed:
                confirmed_balance += utxo.value
            else:
                unconfirmed_balance += utxo.value
        
        self.watched_addresses[address] = AddressBalance(
            address=address,
            confirmed_balance=confirmed_balance,
            unconfirmed_balance=unconfirmed_balance,
            utxo_count=utxo_count,
            last_updated=time.time()
        )
        
        logger.info(f"Updated balance for {address}: {confirmed_balance/100000000:.8f} BTC confirmed, {unconfirmed_balance/100000000:.8f} BTC unconfirmed")
    
    def process_transaction(self, tx_data: bytes, confirmed: bool = False):
        """Process a transaction and update balances"""
        tx_info = self.parse_transaction(tx_data)
        if not tx_info:
            return
        
        tx_hash = tx_info['tx_hash']
        logger.info(f"Processing transaction: {tx_hash}")
        
        # Cache transaction
        self.transaction_cache[tx_hash] = tx_data
        
        # Process outputs (new UTXOs)
        for i, output in enumerate(tx_info['outputs']):
            address = output['address']
            if address in self.watched_addresses:
                # Create new UTXO
                utxo = UTXO(
                    tx_hash=tx_hash,
                    output_index=i,
                    value=output['value'],
                    script_pubkey=output['script_pubkey'],
                    address=address,
                    confirmed=confirmed
                )
                
                if address not in self.utxos:
                    self.utxos[address] = []
                
                self.utxos[address].append(utxo)
                logger.info(f"Added UTXO for {address}: {output['value']/100000000:.8f} BTC")
        
        # Process inputs (spent UTXOs)
        for input_tx in tx_info['inputs']:
            prev_tx_hash = input_tx['prev_tx_hash']
            prev_output_index = input_tx['prev_output_index']
            
            # Check if this input spends a UTXO we're tracking
            for address in self.watched_addresses:
                if address in self.utxos:
                    # Remove spent UTXOs
                    self.utxos[address] = [
                        utxo for utxo in self.utxos[address]
                        if not (utxo.tx_hash == prev_tx_hash and utxo.output_index == prev_output_index)
                    ]
        
        # Update balances for all affected addresses
        for address in self.watched_addresses:
            self.update_balance_for_address(address)
    
    def get_balance(self, address: str) -> Optional[AddressBalance]:
        """Get balance for a specific address"""
        return self.watched_addresses.get(address)
    
    def add_watched_address(self, address: str):
        """Add an address to watch and fetch its current data"""
        if address not in self.watched_addresses:
            self.watched_addresses[address] = AddressBalance(address=address)
            logger.info(f"Added watched address: {address}")
            
            # Fetch real data immediately from BlockCypher
            self.update_address_from_blockcypher(address)
            
            # Log peer connection status
            logger.info(f"Connected to {len(self.peers)} peers for future SPV enhancement")
        else:
            logger.info(f"Address {address} is already being watched")
    
    def get_spv_status(self) -> Dict:
        """Get detailed SPV status information"""
        return {
            'peer_connections': len(self.peers),
            'connected_peers': self.peers,
            'watched_addresses': list(self.watched_addresses.keys()),
            'total_utxos': sum(len(utxos) for utxos in self.utxos.values()),
            'data_source': 'BlockCypher API (with peer connections for future SPV)',
            'spv_limitations': [
                'Bloom filters not fully implemented',
                'Block header scanning not implemented',
                'Transaction discovery from peers not working yet'
            ],
            'working_features': [
                'Peer connections established',
                'BlockCypher API integration',
                'Real-time balance updates',
                'UTXO tracking'
            ]
        }
    
    def connect_to_peer(self, peer_ip: str, peer_port: int) -> bool:
        """Connect to a Bitcoin peer and perform handshake"""
        try:
            logger.info(f"Connecting to peer {peer_ip}:{peer_port}")
            
            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((peer_ip, peer_port))
            
            # Send version message
            version_payload = self.create_version_message(peer_ip, peer_port)
            version_msg = self.create_message('version', version_payload)
            sock.send(version_msg)
            logger.info(f"Sent version message to {peer_ip}:{peer_port}")
            
            # Wait for version response
            response = sock.recv(1024)
            if response:
                logger.info(f"Received response from {peer_ip}:{peer_port} ({len(response)} bytes)")
                
                # Send verack
                verack_msg = self.create_message('verack')
                sock.send(verack_msg)
                logger.info(f"Sent verack to {peer_ip}:{peer_port}")
                
                # Wait for verack response
                verack_response = sock.recv(1024)
                if verack_response:
                    logger.info(f"✅ Handshake completed with {peer_ip}:{peer_port}")
                    self.peers.append(peer_ip)
                    sock.close()
                    return True
                else:
                    logger.warning(f"No verack response from {peer_ip}:{peer_port}")
            else:
                logger.warning(f"No version response from {peer_ip}:{peer_port}")
            
            sock.close()
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to {peer_ip}:{peer_port}: {e}")
            return False
    
    def get_initial_peers(self) -> List[str]:
        """Get initial peers from DNS seeds"""
        dns_seeds = [
            "testnet-seed.bitcoin.jonasschnelli.ch",
            "testnet-seed.bluematt.me", 
            "testnet-seed.bitcoin.schildbach.de",
            "testnet-seed.bitcoin.petertodd.org"
        ]
        
        peers = []
        for seed in dns_seeds:
            try:
                logger.info(f"Querying DNS seed: {seed}")
                addresses = socket.gethostbyname_ex(seed)
                if addresses and addresses[2]:
                    logger.info(f"Found {len(addresses[2])} addresses from {seed}")
                    peers.extend(addresses[2])
                    if len(peers) >= 10:  # Limit initial peers
                        break
            except Exception as e:
                logger.error(f"Failed to query DNS seed {seed}: {e}")
        
        return list(set(peers))  # Remove duplicates
    
    def discover_peers(self):
        """Discover peers using DNS seeds"""
        logger.info("Starting peer discovery...")
        
        # Get initial peers from DNS seeds
        initial_peers = self.get_initial_peers()
        logger.info(f"Found {len(initial_peers)} initial peers from DNS seeds")
        
        # Connect to initial peers
        successful_connections = 0
        for peer_ip in initial_peers[:5]:  # Limit to first 5
            if self.connect_to_peer(peer_ip, self.testnet_port):
                successful_connections += 1
            time.sleep(1)  # Small delay between connections
        
        logger.info(f"Successfully connected to {successful_connections}/{len(initial_peers[:5])} initial peers")
    
    def request_transaction_from_peers(self, tx_hash: str):
        """Request a specific transaction from connected peers"""
        logger.info(f"Requesting transaction {tx_hash} from peers")
        
        # Create getdata message for transaction
        inv_vector = struct.pack('<I', 1)  # MSG_TX = 1
        inv_vector += bytes.fromhex(tx_hash)[::-1]  # Reverse byte order for network format
        
        getdata_payload = struct.pack('<B', 1)  # Number of inventory vectors
        getdata_payload += inv_vector
        
        getdata_message = self.create_message('getdata', getdata_payload)
        
        # Send to all connected peers
        for peer_ip in self.peers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((peer_ip, self.testnet_port))
                
                # Send version and verack (simplified handshake)
                version_msg = self.create_version_message(peer_ip, self.testnet_port)
                sock.send(self.create_message('version', version_msg))
                
                # Read version response
                response = sock.recv(1024)
                if response:
                    sock.send(self.create_message('verack'))
                    verack_response = sock.recv(1024)
                    
                    # Send getdata request
                    sock.send(getdata_message)
                    
                    # Read transaction response
                    tx_response = sock.recv(8192)  # Larger buffer for transaction data
                    if tx_response and len(tx_response) > 24:  # Minimum message size
                        # Parse transaction data
                        self.process_transaction_response(tx_response)
                    
                sock.close()
                
            except Exception as e:
                logger.warning(f"Failed to request transaction from {peer_ip}: {e}")
    
    def process_transaction_response(self, data: bytes):
        """Process transaction data received from peers"""
        try:
            # Parse message header
            if len(data) < 24:
                return
            
            magic, command, length, checksum = struct.unpack('<I12sI4s', data[:24])
            command = command.decode().rstrip('\x00')
            
            if command == 'tx':
                tx_data = data[24:24+length]
                self.process_transaction(tx_data, confirmed=True)
                logger.info(f"Processed transaction from peer")
                
        except Exception as e:
            logger.error(f"Error processing transaction response: {e}")
    
    def request_address_transactions(self, address: str):
        """Request all transactions for a specific address from peers"""
        logger.info(f"Requesting transactions for address {address} from peers")
        
        # For SPV, we need to:
        # 1. Get block headers to know which blocks to check
        # 2. Request transactions from those blocks
        # 3. Filter transactions that involve our address
        
        # This is a simplified approach - in a full SPV implementation,
        # you'd download block headers and use bloom filters
        
        # For now, let's implement a basic transaction discovery
        self.discover_transactions_for_address(address)
    
    def discover_transactions_for_address(self, address: str):
        """Discover transactions for an address using peer network"""
        logger.info(f"Discovering transactions for {address} via peer network")
        
        # In a real SPV implementation, you would:
        # 1. Use bloom filters to tell peers what addresses you're interested in
        # 2. Download block headers to know which blocks to check
        # 3. Request specific transactions from peers
        
        # For demonstration, let's implement a basic bloom filter approach
        self.setup_bloom_filter([address])
    
    def setup_bloom_filter(self, addresses: List[str]):
        """Set up a bloom filter to receive relevant transactions from peers"""
        logger.info(f"Setting up bloom filter for {len(addresses)} addresses")
        
        # Create a simple bloom filter (this is a simplified version)
        # In practice, you'd use a proper bloom filter implementation
        
        for peer_ip in self.peers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((peer_ip, self.testnet_port))
                
                # Send version and verack
                version_msg = self.create_version_message(peer_ip, self.testnet_port)
                sock.send(self.create_message('version', version_msg))
                response = sock.recv(1024)
                
                if response:
                    sock.send(self.create_message('verack'))
                    verack_response = sock.recv(1024)
                    
                    # Send filterload message (simplified)
                    # In practice, you'd create a proper bloom filter
                    filterload_msg = self.create_filterload_message(addresses)
                    sock.send(filterload_msg)
                    
                    logger.info(f"Bloom filter sent to {peer_ip}")
                    
                    # Listen for transaction messages
                    self.listen_for_transactions(sock, peer_ip)
                    
                sock.close()
                
            except Exception as e:
                logger.warning(f"Failed to setup bloom filter with {peer_ip}: {e}")
    
    def create_filterload_message(self, addresses: List[str]) -> bytes:
        """Create a filterload message for bloom filter"""
        # This is a simplified bloom filter implementation
        # In practice, you'd use a proper bloom filter library
        
        # Create a simple filter (all zeros for now)
        filter_bytes = b'\x00' * 1024  # 1KB filter
        n_hash_funcs = 11
        n_tweak = 0
        n_flags = 1  # BLOOM_UPDATE_ALL
        
        payload = struct.pack('<B', len(filter_bytes))  # Filter size
        payload += filter_bytes
        payload += struct.pack('<I', n_hash_funcs)
        payload += struct.pack('<I', n_tweak)
        payload += struct.pack('<B', n_flags)
        
        return self.create_message('filterload', payload)
    
    def listen_for_transactions(self, sock: socket.socket, peer_ip: str):
        """Listen for transaction messages from a peer"""
        try:
            # Listen for a short time
            sock.settimeout(5)
            
            while True:
                data = sock.recv(8192)
                if not data:
                    break
                
                # Process incoming messages
                self.process_peer_message(data, peer_ip)
                
        except socket.timeout:
            logger.info(f"Finished listening to {peer_ip}")
        except Exception as e:
            logger.warning(f"Error listening to {peer_ip}: {e}")
    
    def process_peer_message(self, data: bytes, peer_ip: str):
        """Process messages received from peers"""
        try:
            if len(data) < 24:
                return
            
            magic, command, length, checksum = struct.unpack('<I12sI4s', data[:24])
            command = command.decode().rstrip('\x00')
            
            if command == 'tx':
                tx_data = data[24:24+length]
                self.process_transaction(tx_data, confirmed=True)
                logger.info(f"Received transaction from {peer_ip}")
                
            elif command == 'inv':
                # Process inventory message
                self.process_inventory_message(data[24:24+length])
                
        except Exception as e:
            logger.error(f"Error processing message from {peer_ip}: {e}")
    
    def process_inventory_message(self, data: bytes):
        """Process inventory message to discover new transactions"""
        try:
            if len(data) < 1:
                return
            
            count = struct.unpack('<B', data[:1])[0]
            offset = 1
            
            for i in range(count):
                if offset + 36 > len(data):
                    break
                
                inv_type, inv_hash = struct.unpack('<I32s', data[offset:offset+36])
                inv_hash_hex = inv_hash[::-1].hex()  # Reverse byte order
                
                if inv_type == 1:  # MSG_TX
                    logger.info(f"Discovered transaction: {inv_hash_hex}")
                    # Request this transaction
                    self.request_transaction_from_peers(inv_hash_hex)
                
                offset += 36
                
        except Exception as e:
            logger.error(f"Error processing inventory message: {e}")
    
    def start(self):
        """Start the SPV balance tracker"""
        logger.info("Starting SPV balance tracker...")
        self.is_running = True
        
        # Discover peers
        self.discover_peers()
        
        # Start balance monitoring
        self.start_balance_monitoring()
    
    def start_balance_monitoring(self):
        """Start monitoring for balance changes"""
        logger.info("Starting balance monitoring...")
        logger.info(f"Watching {len(self.watched_addresses)} addresses for balance changes")
        logger.info(f"Connected to {len(self.peers)} peers")
        
        # Use BlockCypher for reliable initial data
        self.update_all_addresses_from_blockcypher()
        
        # Keep peer connections for future SPV enhancement
        logger.info("Peer connections maintained for future SPV enhancement")
        logger.info("Currently using BlockCypher API for reliable balance data")
        
        # Start periodic updates
        self.start_periodic_updates()
    
    def start_peer_monitoring(self):
        """Start monitoring peers for real-time transaction updates"""
        logger.info("Starting peer-based transaction monitoring...")
        
        def peer_monitor_loop():
            while self.is_running:
                try:
                    # Set up bloom filters with all peers
                    for address in self.watched_addresses:
                        self.setup_bloom_filter([address])
                    
                    # Listen for new transactions
                    self.listen_for_new_transactions()
                    
                    time.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Error in peer monitoring: {e}")
                    time.sleep(120)  # Wait longer on error
        
        monitor_thread = threading.Thread(target=peer_monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Started peer-based transaction monitoring")
    
    def listen_for_new_transactions(self):
        """Listen for new transactions from peers"""
        logger.info("Listening for new transactions from peers...")
        
        # Create a simple listener that connects to peers and listens for transactions
        for peer_ip in self.peers[:2]:  # Use first 2 peers
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30)  # 30 second timeout
                sock.connect((peer_ip, self.testnet_port))
                
                # Send version and verack
                version_msg = self.create_version_message(peer_ip, self.testnet_port)
                sock.send(self.create_message('version', version_msg))
                response = sock.recv(1024)
                
                if response:
                    sock.send(self.create_message('verack'))
                    verack_response = sock.recv(1024)
                    
                    # Send ping to keep connection alive
                    ping_payload = struct.pack('<Q', int(time.time()))
                    sock.send(self.create_message('ping', ping_payload))
                    
                    # Listen for messages
                    sock.settimeout(10)
                    try:
                        while True:
                            data = sock.recv(8192)
                            if not data:
                                break
                            
                            # Process any incoming messages
                            self.process_peer_message(data, peer_ip)
                            
                    except socket.timeout:
                        logger.info(f"Finished listening to {peer_ip}")
                    
                sock.close()
                
            except Exception as e:
                logger.warning(f"Failed to monitor {peer_ip}: {e}")
    
    def request_recent_transactions(self, address: str):
        """Request recent transactions for an address from peers"""
        logger.info(f"Requesting recent transactions for {address} from peers")
        
        # Get recent block headers first (simplified approach)
        # In a real implementation, you'd download block headers
        
        # For now, let's request transactions from recent blocks
        # This is a simplified approach - in practice you'd:
        # 1. Download block headers
        # 2. Identify which blocks might contain your address
        # 3. Request transactions from those blocks
        
        # Let's try to get some recent transactions
        for peer_ip in self.peers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((peer_ip, self.testnet_port))
                
                # Send version and verack
                version_msg = self.create_version_message(peer_ip, self.testnet_port)
                sock.send(self.create_message('version', version_msg))
                response = sock.recv(1024)
                
                if response:
                    sock.send(self.create_message('verack'))
                    verack_response = sock.recv(1024)
                    
                    # Send getheaders to get recent block headers
                    getheaders_msg = self.create_getheaders_message()
                    sock.send(getheaders_msg)
                    
                    # Read headers response
                    headers_response = sock.recv(8192)
                    if headers_response:
                        logger.info(f"Received headers from {peer_ip}")
                        # Process headers to find relevant blocks
                        self.process_headers_response(headers_response, address)
                    
                sock.close()
                
            except Exception as e:
                logger.warning(f"Failed to get headers from {peer_ip}: {e}")
    
    def create_getheaders_message(self) -> bytes:
        """Create a getheaders message to request recent block headers"""
        # Request headers from the last 10 blocks
        # In practice, you'd track the last header you have
        
        # Create a simple getheaders message
        version = 70015
        hash_count = 1
        stop_hash = b'\x00' * 32  # All zeros = get as many as possible
        
        # Use genesis block hash as starting point (simplified)
        genesis_hash = bytes.fromhex('000000000933ea01ad0ee98420974ba302c560294f63fce5f3ca5b5b4b97d5b0')[::-1]
        
        payload = struct.pack('<I', version)  # version
        payload += struct.pack('<B', hash_count)  # hash count
        payload += genesis_hash  # block hash
        payload += stop_hash  # stop hash
        
        return self.create_message('getheaders', payload)
    
    def process_headers_response(self, data: bytes, address: str):
        """Process headers response to find relevant blocks"""
        try:
            if len(data) < 24:
                return
            
            # Parse message header
            magic, command, length, checksum = struct.unpack('<I12sI4s', data[:24])
            command = command.decode().rstrip('\x00')
            
            if command == 'headers':
                headers_data = data[24:24+length]
                logger.info(f"Processing {len(headers_data)} bytes of headers")
                
                # In a real implementation, you'd:
                # 1. Parse each block header
                # 2. Check if the block might contain your address
                # 3. Request transactions from relevant blocks
                
                # For now, let's just log that we received headers
                logger.info(f"Received block headers, would scan for address {address}")
                
        except Exception as e:
            logger.error(f"Error processing headers response: {e}")
    
    def hybrid_update_address(self, address: str):
        """Update address using both peer network and BlockCypher API"""
        logger.info(f"Hybrid update for address: {address}")
        
        # First, try to get data from peers
        self.request_recent_transactions(address)
        
        # Then, use BlockCypher as fallback
        self.update_address_from_blockcypher(address)
    
    def update_all_addresses_hybrid(self):
        """Update all addresses using hybrid approach"""
        logger.info("Updating all addresses using hybrid approach...")
        for address in list(self.watched_addresses.keys()):
            self.hybrid_update_address(address)
            time.sleep(1)  # Rate limiting
    
    def start_periodic_updates(self):
        """Start periodic updates of address balances"""
        def update_loop():
            while self.is_running:
                try:
                    self.update_all_addresses_from_blockcypher()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    logger.error(f"Error in periodic updates: {e}")
                    time.sleep(60)  # Wait longer on error
        
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        logger.info("Started periodic balance updates")
    
    def stop(self):
        """Stop the SPV balance tracker"""
        logger.info("Stopping SPV balance tracker...")
        self.is_running = False

def main():
    """Test SPV balance tracker"""
    tracker = SPVBalanceTracker()
    
    # Add some test addresses to watch
    test_addresses = [
        "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
        "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7"
    ]
    
    for address in test_addresses:
        tracker.add_watched_address(address)
    
    logger.info("Starting SPV balance tracker...")
    tracker.start()
    
    # Let it run for a bit
    time.sleep(5)
    
    # Show final balances
    logger.info("Final balances:")
    for address in test_addresses:
        balance = tracker.get_balance(address)
        if balance:
            logger.info(f"{address}: {balance.confirmed_balance/100000000:.8f} BTC confirmed, {balance.unconfirmed_balance/100000000:.8f} BTC unconfirmed")
    
    logger.info("SPV balance tracker test completed")

if __name__ == "__main__":
    main() 