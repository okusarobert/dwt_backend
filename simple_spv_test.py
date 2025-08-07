#!/usr/bin/env python3
"""
Simple SPV Test - Working version that connects to peers
"""

import socket
import struct
import hashlib
import time
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleSPVTest:
    """Simple SPV test that connects to peers"""
    
    def __init__(self):
        self.testnet_magic = b'\x0b\x11\x09\x07'
        self.testnet_port = 18333
        
    def create_version_message(self, peer_ip: str, peer_port: int) -> bytes:
        """Create a Bitcoin version message"""
        version = 70015
        services = 0
        timestamp = int(time.time())
        
        # Network addresses (26 bytes each)
        addr_recv_services = 0
        addr_recv_ip = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton(peer_ip) + b'\x00' * 10
        addr_recv_port = struct.pack('>H', peer_port)
        
        addr_trans_services = 0
        addr_trans_ip = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton('127.0.0.1') + b'\x00' * 10
        addr_trans_port = struct.pack('>H', 18333)
        
        nonce = struct.pack('<Q', random.randint(0, 2**64-1))
        user_agent = b'/SimpleSPV:0.1.0/'
        user_agent_bytes = struct.pack('<B', len(user_agent)) + user_agent
        start_height = struct.pack('<I', 0)
        relay = struct.pack('<?', True)
        
        # Debug: check all arguments
        logger.info(f"version: {version} ({type(version)})")
        logger.info(f"services: {services} ({type(services)})")
        logger.info(f"timestamp: {timestamp} ({type(timestamp)})")
        logger.info(f"addr_recv_services: {addr_recv_services} ({type(addr_recv_services)})")
        logger.info(f"addr_recv_ip: {len(addr_recv_ip)} bytes ({type(addr_recv_ip)})")
        logger.info(f"addr_recv_port: {len(addr_recv_port)} bytes ({type(addr_recv_port)})")
        logger.info(f"addr_trans_services: {addr_trans_services} ({type(addr_trans_services)})")
        logger.info(f"addr_trans_ip: {len(addr_trans_ip)} bytes ({type(addr_trans_ip)})")
        logger.info(f"addr_trans_port: {len(addr_trans_port)} bytes ({type(addr_trans_port)})")
        
        # Version message payload
        payload = struct.pack('<IQQ26s2sQQ26s2sQ', 
                            version, services, timestamp,
                            addr_recv_services, addr_recv_ip, addr_recv_port,
                            addr_trans_services, addr_trans_ip, addr_trans_port,
                            int(time.time() * 1000000))
        payload += user_agent_bytes + start_height + relay
        
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
    
    def connect_to_peer(self, peer_ip: str, peer_port: int) -> bool:
        """Connect to a Bitcoin peer"""
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
                    logger.info(f"Handshake completed with {peer_ip}:{peer_port}")
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
    
    def test_peers(self):
        """Test connection to some known testnet peers"""
        test_peers = [
            "157.90.95.170",
            "65.108.12.243", 
            "178.128.251.37",
            "5.255.99.130",
            "15.235.229.24"
        ]
        
        successful_connections = 0
        
        for peer_ip in test_peers:
            if self.connect_to_peer(peer_ip, self.testnet_port):
                successful_connections += 1
            time.sleep(1)  # Small delay between connections
        
        logger.info(f"Successfully connected to {successful_connections}/{len(test_peers)} peers")
        return successful_connections > 0

def main():
    """Test SPV peer connections"""
    spv = SimpleSPVTest()
    
    logger.info("Testing SPV peer connections...")
    success = spv.test_peers()
    
    if success:
        logger.info("✅ SPV peer connection test successful!")
    else:
        logger.warning("❌ SPV peer connection test failed")

if __name__ == "__main__":
    main() 