#!/usr/bin/env python3
"""
Get Reserved Addresses at Index 0
Retrieves the reserved addresses at index 0 for TRX, ETH, SOLANA, and BTC
"""

import os
import sys
from decouple import config

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.HD import BTC, ETH, TRX

# Solana imports
try:
    from solders.keypair import Keypair
    SOLANA_AVAILABLE = True
except ImportError:
    SOLANA_AVAILABLE = False

def get_btc_address_at_index_0():
    """Get BTC address at index 0"""
    try:
        mnemonic = config('BTC_MNEMONIC', default=None)
        if not mnemonic:
            print("❌ BTC_MNEMONIC not configured")
            return None
            
        btc_wallet = BTC()
        btc_wallet.from_mnemonic(mnemonic=mnemonic)
        address, priv_key, pub_key = btc_wallet.new_address(index=0)
        
        return {
            'currency': 'BTC',
            'address': address,
            'index': 0,
            'network': 'testnet'
        }
    except Exception as e:
        print(f"❌ Error getting BTC address: {e}")
        return None

def get_eth_address_at_index_0():
    """Get ETH address at index 0"""
    try:
        mnemonic = config('ETH_MNEMONIC', default=None)
        if not mnemonic:
            print("❌ ETH_MNEMONIC not configured")
            return None
            
        eth_wallet = ETH()
        eth_wallet.from_mnemonic(mnemonic=mnemonic)
        address, priv_key, pub_key = eth_wallet.new_address(index=0)
        
        return {
            'currency': 'ETH',
            'address': address,
            'index': 0,
            'network': 'mainnet'
        }
    except Exception as e:
        print(f"❌ Error getting ETH address: {e}")
        return None

def get_trx_address_at_index_0():
    """Get TRX address at index 0"""
    try:
        mnemonic = config('TRX_MNEMONIC', default=None)
        if not mnemonic:
            print("❌ TRX_MNEMONIC not configured")
            return None
            
        trx_wallet = TRX()
        trx_wallet.from_mnemonic(mnemonic=mnemonic)
        address, priv_key, pub_key = trx_wallet.new_address(index=0)
        
        return {
            'currency': 'TRX',
            'address': address,
            'index': 0,
            'network': 'mainnet'
        }
    except Exception as e:
        print(f"❌ Error getting TRX address: {e}")
        return None

def get_sol_address_at_index_0():
    """Get SOL address at index 0 using deterministic seed (reserve address)"""
    try:
        if not SOLANA_AVAILABLE:
            print("❌ Solana SDK not available")
            return None
            
        # Generate deterministic seed for reserve address (user_id = 0, index = 0)
        # This matches the pattern used in the updated SOL client
        base_seed = b'dwt_solana_wallet_seed_v1'
        user_bytes = (0).to_bytes(8, 'big')  # Reserve user_id = 0
        index_bytes = (0).to_bytes(4, 'big')  # Index 0
        
        import hashlib
        combined_seed = base_seed + user_bytes + index_bytes
        seed_hash = hashlib.sha256(combined_seed).digest()
        
        # Create keypair from the 32-byte seed
        keypair = Keypair.from_seed(seed_hash)
        public_key = keypair.pubkey()
        
        return {
            'currency': 'SOL',
            'address': str(public_key),
            'index': 0,
            'network': 'mainnet',
            'method': 'deterministic_seed'
        }
            
    except Exception as e:
        print(f"❌ Error getting SOL address: {e}")
        return None

def main():
    print("🔐 Getting Reserved Addresses at Index 0")
    print("=" * 50)
    
    addresses = []
    
    # Get BTC address
    print("\n🟠 Bitcoin (BTC):")
    btc_addr = get_btc_address_at_index_0()
    if btc_addr:
        addresses.append(btc_addr)
        print(f"✅ Address: {btc_addr['address']}")
        print(f"   Network: {btc_addr['network']}")
    
    # Get ETH address
    print("\n🔵 Ethereum (ETH):")
    eth_addr = get_eth_address_at_index_0()
    if eth_addr:
        addresses.append(eth_addr)
        print(f"✅ Address: {eth_addr['address']}")
        print(f"   Network: {eth_addr['network']}")
    
    # Get TRX address
    print("\n🔴 Tron (TRX):")
    trx_addr = get_trx_address_at_index_0()
    if trx_addr:
        addresses.append(trx_addr)
        print(f"✅ Address: {trx_addr['address']}")
        print(f"   Network: {trx_addr['network']}")
    
    # Get SOL address
    print("\n🟣 Solana (SOL):")
    sol_addr = get_sol_address_at_index_0()
    if sol_addr:
        addresses.append(sol_addr)
        print(f"✅ Address: {sol_addr['address']}")
        print(f"   Network: {sol_addr['network']}")
        print(f"   Method: {sol_addr['method']}")
    
    print("\n" + "=" * 50)
    print(f"📊 Summary: Retrieved {len(addresses)}/4 addresses")
    
    if addresses:
        print("\n🎯 Reserved Addresses (Index 0):")
        for addr in addresses:
            print(f"  {addr['currency']}: {addr['address']}")
    
    return addresses

if __name__ == "__main__":
    main()
