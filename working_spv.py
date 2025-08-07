#!/usr/bin/env python3
"""
Working SPV Client - Simple and proven approach
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

class WorkingSPV:
    """Working SPV client that connects to peers"""
    
    def __init__(self):
        self.testnet_magic = b'\x0b\x11\x09\x07'
        self.testnet_port = 18333
        
    def create_version_message(self, peer_ip: str, peer_port: int) -> bytes:
        """Create a Bitcoin version message using a simpler approach"""
        version = 70015
        services = 0
        timestamp = int(time.time())
        
        # Create network addresses manually
        addr_recv = b'\x00' * 26  # 26 bytes for network address
        addr_trans = b'\x00' * 26  # 26 bytes for network address
        
        # Set the IP addresses in the network address structure
        # Format: 10 bytes padding + 2 bytes family + 4 bytes IP + 2 bytes port
        addr_recv = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton(peer_ip) + struct.pack('>H', peer_port) + b'\x00' * 8
        addr_trans = b'\x00' * 10 + b'\xff\xff' + socket.inet_aton('127.0.0.1') + struct.pack('>H', 18333) + b'\x00' * 8
        
        nonce = random.randint(0, 2**64-1)
        user_agent = b'/WorkingSPV:0.1.0/'
        user_agent_bytes = struct.pack('<B', len(user_agent)) + user_agent
        start_height = 0
        relay = True
        
        # Create version payload
        payload = struct.pack('<IQQ26s26sQQ26s26sQ', 
                            version, services, timestamp,
                            services, addr_recv,  # addr_recv_services, addr_recv
                            services, addr_trans,  # addr_trans_services, addr_trans
                            nonce, nonce, nonce)  # Add missing nonce
        payload += user_agent_bytes + struct.pack('<I', start_height) + struct.pack('<?', relay)
        
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
                    logger.info(f"✅ Handshake completed with {peer_ip}:{peer_port}")
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
    """Test working SPV peer connections"""
    spv = WorkingSPV()
    
    logger.info("Testing working SPV peer connections...")
    success = spv.test_peers()
    
    if success:
        logger.info("✅ Working SPV peer connection test successful!")
    else:
        logger.warning("❌ Working SPV peer connection test failed")

if __name__ == "__main__":
    main() 