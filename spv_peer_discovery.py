#!/usr/bin/env python3
"""
Bitcoin SPV Client with Peer Discovery
"""

import socket
import struct
import hashlib
import time
import random
import logging
import threading
from dataclasses import dataclass
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BitcoinMessage:
    """Bitcoin network message structure"""
    magic: bytes
    command: str
    length: int
    checksum: bytes
    payload: bytes

@dataclass
class Peer:
    """Bitcoin peer information"""
    ip: str
    port: int
    services: int = 0
    last_seen: float = 0.0
    is_active: bool = False

class SPVClient:
    """Bitcoin SPV client with peer discovery"""
    
    def __init__(self):
        self.testnet_magic = b'\x0b\x11\x09\x07'
        self.testnet_port = 18333
        self.peers: List[Peer] = []
        self.watched_addresses: List[str] = []
        self.is_running = False
        
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
        user_agent = b'/SPVClient:0.1.0/'
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
    
    def query_dns_seed(self, seed: str) -> List[str]:
        """Query a DNS seed for peer addresses"""
        try:
            logger.info(f"Querying DNS seed: {seed}")
            addresses = socket.gethostbyname_ex(seed)
            if addresses and addresses[2]:
                logger.info(f"Found {len(addresses[2])} addresses from {seed}")
                return addresses[2]
        except Exception as e:
            logger.error(f"Failed to query DNS seed {seed}: {e}")
        return []
    
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
            addresses = self.query_dns_seed(seed)
            peers.extend(addresses)
            if len(peers) >= 10:  # Limit initial peers
                break
        
        return list(set(peers))  # Remove duplicates
    
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
                    
                    # Add peer to our list
                    peer = Peer(ip=peer_ip, port=peer_port, last_seen=time.time(), is_active=True)
                    self.peers.append(peer)
                    
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
    
    def request_peer_addresses(self, sock: socket.socket) -> bool:
        """Request peer addresses from a connected peer"""
        try:
            # Send getaddr message
            getaddr_msg = self.create_message('getaddr')
            sock.send(getaddr_msg)
            logger.info("Sent getaddr message")
            
            # Wait for addr response
            response = sock.recv(4096)
            if response:
                logger.info(f"Received addr response ({len(response)} bytes)")
                return self.process_addr_message(response)
            
            return False
        except Exception as e:
            logger.error(f"Failed to request peer addresses: {e}")
            return False
    
    def process_addr_message(self, data: bytes) -> bool:
        """Process addr message to extract peer addresses"""
        try:
            # Parse addr message (simplified)
            # In a real implementation, you'd parse the full message structure
            logger.info("Processing addr message")
            
            # For now, just log that we received addresses
            # In a full implementation, you'd extract IP addresses from the payload
            return True
        except Exception as e:
            logger.error(f"Failed to process addr message: {e}")
            return False
    
    def discover_peers(self):
        """Discover peers using DNS seeds and peer exchange"""
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
        
        # Request more peers from connected peers
        for peer in self.peers[:3]:  # Use first 3 connected peers
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((peer.ip, peer.port))
                
                # Perform handshake
                version_payload = self.create_version_message(peer.ip, peer.port)
                version_msg = self.create_message('version', version_payload)
                sock.send(version_msg)
                sock.recv(1024)  # Wait for version response
                
                verack_msg = self.create_message('verack')
                sock.send(verack_msg)
                sock.recv(1024)  # Wait for verack response
                
                # Request peer addresses
                self.request_peer_addresses(sock)
                sock.close()
                
            except Exception as e:
                logger.error(f"Failed to request addresses from {peer.ip}: {e}")
    
    def add_watched_address(self, address: str):
        """Add an address to watch for transactions"""
        if address not in self.watched_addresses:
            self.watched_addresses.append(address)
            logger.info(f"Added watched address: {address}")
    
    def start(self):
        """Start the SPV client"""
        logger.info("Starting SPV client...")
        self.is_running = True
        
        # Discover peers
        self.discover_peers()
        
        # Start listening for transactions
        self.start_transaction_listening()
    
    def start_transaction_listening(self):
        """Start listening for transactions from peers"""
        logger.info("Starting transaction listening...")
        
        # For now, just log that we're listening
        # In a full implementation, you'd maintain persistent connections
        # and listen for inv/getdata messages
        logger.info(f"Watching {len(self.watched_addresses)} addresses for transactions")
        logger.info(f"Connected to {len(self.peers)} peers")
    
    def stop(self):
        """Stop the SPV client"""
        logger.info("Stopping SPV client...")
        self.is_running = False

def main():
    """Test SPV client with peer discovery"""
    spv = SPVClient()
    
    # Add some test addresses to watch
    spv.add_watched_address("tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    spv.add_watched_address("tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7")
    
    logger.info("Starting SPV client with peer discovery...")
    spv.start()
    
    # Let it run for a bit
    time.sleep(10)
    
    logger.info("SPV client test completed")

if __name__ == "__main__":
    main() 