#!/usr/bin/env python3
"""
Simple script to generate an Ethereum address at index 0 for receiving faucet tokens.
This script does NOT save anything to the database - it just displays the address.
"""

import os
import sys
from decouple import config

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.clients.eth import ETH
from shared.logger import setup_logging

logger = setup_logging()


def generate_master_eth_address(network: str = "testnet") -> dict:
    """
    Generate an Ethereum address at index 0 without saving to database
    
    Args:
        network: Ethereum network to use (testnet, mainnet, holesky)
        
    Returns:
        dict: Address information
    """
    try:
        # Get mnemonic from environment
        mnemonic_key = "ETH_MNEMONIC"
        mnemonic = config(mnemonic_key, default=None)
        
        if not mnemonic:
            raise ValueError(f"{mnemonic_key} environment variable is required")
        
        logger.info(f"🔧 Generating ETH address for {network} network")
        logger.info(f"📝 Using mnemonic: {mnemonic[:20]}...")
        
        # Create ETH wallet
        eth_wallet = ETH()
        wallet = eth_wallet.from_mnemonic(mnemonic=mnemonic)
        
        # Generate address at index 0 (master address for faucet)
        address, private_key, public_key = wallet.new_address(index=0)
        
        logger.info(f"✅ Successfully generated ETH address at index 0")
        logger.info(f"📍 Address: {address}")
        logger.info(f"🔗 Network: {network}")
        logger.info(f"🔑 Private Key: {private_key}")
        logger.info(f"🔑 Public Key: {public_key}")
        
        return {
            "address": address,
            "private_key": private_key,
            "public_key": public_key,
            "index": 0,
            "network": network,
            "mnemonic": mnemonic[:20] + "..."  # Show first 20 chars for reference
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to generate ETH address: {e}")
        raise


def main():
    """Main function to generate master ETH address"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate master Ethereum address for faucet tokens")
    parser.add_argument("--network", choices=["testnet", "mainnet", "holesky"], default="testnet", 
                       help="Ethereum network to use (default: testnet)")
    parser.add_argument("--show-private-key", action="store_true", help="Show private key (use with caution)")
    
    args = parser.parse_args()
    
    try:
        print(f"🚀 Generating master ETH address for {args.network}...")
        
        address_info = generate_master_eth_address(network=args.network)
        
        print(f"\n✅ Master ETH Address Generated Successfully!")
        print(f"📍 Address: {address_info['address']}")
        print(f"🌐 Network: {address_info['network']}")
        print(f"📊 Index: {address_info['index']}")
        print(f"📝 Mnemonic: {address_info['mnemonic']}")
        
        if args.show_private_key:
            print(f"🔑 Private Key: {address_info['private_key']}")
            print(f"🔑 Public Key: {address_info['public_key']}")
        else:
            print(f"🔑 Private Key: [HIDDEN] (use --show-private-key to display)")
            print(f"🔑 Public Key: [HIDDEN] (use --show-private-key to display)")
        
        print(f"\n💡 Use this address to receive faucet tokens for testing!")
        print(f"🔗 You can now distribute tokens from this master address to other indices.")
        print(f"⚠️  Keep your private key secure and never share it!")
        
    except Exception as e:
        logger.error(f"❌ Failed to generate master ETH address: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 