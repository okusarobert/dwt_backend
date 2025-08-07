#!/usr/bin/env python3
"""
DNS Seed Resolver for Bitcoin Testnet3
Resolves DNS seeds to get peer addresses
"""

import socket
import struct
import random
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class DNSSeedResolver:
    """Resolve Bitcoin DNS seeds to get peer addresses"""
    
    def __init__(self):
        # Testnet3 DNS seeds
        self.testnet_seeds = [
            "testnet-seed.bitcoin.jonasschnelli.ch",
            "testnet-seed.bluematt.me", 
            "testnet-seed.bitcoin.schildbach.de",
            "testnet-seed.bitcoin.petertodd.org",
            "testnet-seed.alexykot.me",
            "testnet-seed.bitcoin.sprovoost.nl"
        ]
        
        # Mainnet DNS seeds (for reference)
        self.mainnet_seeds = [
            "seed.bitcoin.sipa.be",
            "dnsseed.bluematt.me",
            "dnsseed.bitcoin.dashjr.org",
            "seed.bitcoinstats.com",
            "seed.bitcoin.jonasschnelli.ch",
            "seed.btc.petertodd.org",
            "seed.bitcoin.sprovoost.nl",
            "dnsseed.emzy.de",
            "seed.bitcoin.wiz.biz"
        ]
    
    def resolve_seed(self, seed_host: str, port: int = 18333) -> List[str]:
        """Resolve a DNS seed to get peer IP addresses"""
        try:
            logger.info(f"Resolving DNS seed: {seed_host}")
            
            # Get all IP addresses for the seed
            ips = socket.gethostbyname_ex(seed_host)[2]
            logger.info(f"Found {len(ips)} IPs for {seed_host}: {ips}")
            
            # Return list of IP:port combinations
            return [f"{ip}:{port}" for ip in ips]
            
        except socket.gaierror as e:
            logger.warning(f"Failed to resolve {seed_host}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error resolving {seed_host}: {e}")
            return []
    
    def resolve_testnet_seeds(self) -> List[str]:
        """Resolve all testnet DNS seeds"""
        all_peers = []
        
        for seed in self.testnet_seeds:
            peers = self.resolve_seed(seed, 18333)  # Testnet port
            all_peers.extend(peers)
            logger.info(f"Resolved {len(peers)} peers from {seed}")
        
        # Remove duplicates while preserving order
        unique_peers = []
        seen = set()
        for peer in all_peers:
            if peer not in seen:
                unique_peers.append(peer)
                seen.add(peer)
        
        logger.info(f"Total unique testnet peers found: {len(unique_peers)}")
        return unique_peers
    
    def resolve_mainnet_seeds(self) -> List[str]:
        """Resolve all mainnet DNS seeds"""
        all_peers = []
        
        for seed in self.mainnet_seeds:
            peers = self.resolve_seed(seed, 8333)  # Mainnet port
            all_peers.extend(peers)
            logger.info(f"Resolved {len(peers)} peers from {seed}")
        
        # Remove duplicates while preserving order
        unique_peers = []
        seen = set()
        for peer in all_peers:
            if peer not in seen:
                unique_peers.append(peer)
                seen.add(peer)
        
        logger.info(f"Total unique mainnet peers found: {len(unique_peers)}")
        return unique_peers
    
    def get_random_peers(self, peers: List[str], count: int = 10) -> List[str]:
        """Get a random subset of peers"""
        if len(peers) <= count:
            return peers
        return random.sample(peers, count)
    
    def parse_peer_string(self, peer_str: str) -> tuple:
        """Parse peer string 'ip:port' to (ip, port)"""
        try:
            ip, port = peer_str.split(':')
            return ip, int(port)
        except ValueError:
            logger.error(f"Invalid peer string: {peer_str}")
            return None, None

def main():
    """Test DNS seed resolution"""
    resolver = DNSSeedResolver()
    
    print("Resolving testnet seeds...")
    testnet_peers = resolver.resolve_testnet_seeds()
    
    print(f"\nFound {len(testnet_peers)} testnet peers:")
    for i, peer in enumerate(testnet_peers[:10]):  # Show first 10
        print(f"  {i+1}. {peer}")
    
    if len(testnet_peers) > 10:
        print(f"  ... and {len(testnet_peers) - 10} more")
    
    print(f"\nResolving mainnet seeds...")
    mainnet_peers = resolver.resolve_mainnet_seeds()
    
    print(f"\nFound {len(mainnet_peers)} mainnet peers:")
    for i, peer in enumerate(mainnet_peers[:10]):  # Show first 10
        print(f"  {i+1}. {peer}")
    
    if len(mainnet_peers) > 10:
        print(f"  ... and {len(mainnet_peers) - 10} more")

if __name__ == "__main__":
    main() 