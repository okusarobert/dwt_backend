#!/usr/bin/env python3
"""
Enhanced SPV Tracker - Listens for real Bitcoin transactions
"""

import socket
import struct
import hashlib
import time
import random
import logging
import threading
from dataclasses import dataclass
from typing import List, Optional, Dict, Set
import base58

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

class EnhancedSPVTracker:
    """Enhanced SPV client that listens for real transactions"""
    
    def __init__(self):
        self.testnet_magic = b'\x0b\x11\x09\x07'
        self.testnet_port = 18333
        self.peers: List[str] = []
        self.watched_addresses: Dict[str, AddressBalance] = {}
        self.utxos: Dict[str, List[UTXO]] = {}  # address -> list of UTXOs
        self.transaction_cache: Dict[str, bytes] = {}
        self.is_running = False
        self.active_connections: Dict[str, socket.socket] = {}
        
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
        user_agent = b'/EnhancedSPV:0.1.0/'
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
    
    def listen_for_transactions(self, peer_ip: str):
        """Listen for transactions from a specific peer"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((peer_ip, self.testnet_port))
            
            # Perform handshake
            version_payload = self.create_version_message(peer_ip, self.testnet_port)
            version_msg = self.create_message('version', version_payload)
            sock.send(version_msg)
            
            # Wait for version response
            response = sock.recv(1024)
            if response:
                # Send verack
                verack_msg = self.create_message('verack')
                sock.send(verack_msg)
                
                # Wait for verack response
                verack_response = sock.recv(1024)
                if verack_response:
                    logger.info(f"✅ Connected to {peer_ip} for transaction listening")
                    
                    # Send getaddr to request peer addresses
                    getaddr_msg = self.create_message('getaddr')
                    sock.send(getaddr_msg)
                    
                    # Listen for messages
                    while self.is_running:
                        try:
                            # Read message header (24 bytes)
                            header = sock.recv(24)
                            if len(header) < 24:
                                break
                            
                            # Parse header
                            magic, command, length, checksum = struct.unpack('<I12sI4s', header)
                            command_str = command.strip(b'\x00').decode()
                            
                            logger.info(f"Received {command_str} message from {peer_ip}")
                            
                            # Read payload
                            payload = b''
                            if length > 0:
                                payload = sock.recv(length)
                                while len(payload) < length:
                                    chunk = sock.recv(length - len(payload))
                                    if not chunk:
                                        break
                                    payload += chunk
                            
                            # Process message
                            if command_str == 'tx':
                                logger.info(f"Received transaction from {peer_ip}")
                                self.process_transaction(payload, confirmed=False)
                            elif command_str == 'inv':
                                # Handle inventory message (list of transaction hashes)
                                logger.info(f"Received inventory from {peer_ip}")
                                # Could request specific transactions here
                            elif command_str == 'addr':
                                # Handle address message
                                logger.info(f"Received address list from {peer_ip}")
                            
                        except socket.timeout:
                            # Send ping to keep connection alive
                            ping_msg = self.create_message('ping', struct.pack('<Q', random.randint(0, 2**64-1)))
                            sock.send(ping_msg)
                            continue
                        except Exception as e:
                            logger.error(f"Error reading from {peer_ip}: {e}")
                            break
                    
                    sock.close()
                    
        except Exception as e:
            logger.error(f"Failed to listen for transactions from {peer_ip}: {e}")
    
    def start_transaction_listening(self):
        """Start listening for transactions from all peers"""
        logger.info("Starting transaction listening...")
        
        # Start listening threads for each peer
        for peer_ip in self.peers[:3]:  # Use first 3 peers
            thread = threading.Thread(target=self.listen_for_transactions, args=(peer_ip,), daemon=True)
            thread.start()
            logger.info(f"Started transaction listener for {peer_ip}")
    
    def get_balance(self, address: str) -> Optional[AddressBalance]:
        """Get balance for a specific address"""
        return self.watched_addresses.get(address)
    
    def add_watched_address(self, address: str):
        """Add an address to watch for balance tracking"""
        if address not in self.watched_addresses:
            self.watched_addresses[address] = AddressBalance(address=address)
            self.utxos[address] = []
            logger.info(f"Added watched address: {address}")
    
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
    
    def start(self):
        """Start the enhanced SPV tracker"""
        logger.info("Starting enhanced SPV tracker...")
        self.is_running = True
        
        # Discover peers
        self.discover_peers()
        
        # Start transaction listening
        self.start_transaction_listening()
        
        # Keep main thread alive
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping enhanced SPV tracker...")
            self.stop()
    
    def stop(self):
        """Stop the enhanced SPV tracker"""
        logger.info("Stopping enhanced SPV tracker...")
        self.is_running = False

def main():
    """Test enhanced SPV tracker"""
    tracker = EnhancedSPVTracker()
    
    # Add addresses to watch
    test_addresses = [
        "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
        "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7",
        "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"
    ]
    
    for address in test_addresses:
        tracker.add_watched_address(address)
    
    logger.info("Starting enhanced SPV tracker...")
    tracker.start()

if __name__ == "__main__":
    main() 