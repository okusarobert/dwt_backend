#!/usr/bin/env python3
"""
Generate a new Bitcoin testnet address for testing.
"""

import sys
import os
from decouple import config

# Add the current directory to Python path
sys.path.append('/app')

from shared.crypto.HD import BTC
from shared.logger import setup_logging

logger = setup_logging()

def generate_new_btc_address():
    """Generate a new Bitcoin testnet address"""
    
    try:
        # Get the mnemonic from environment
        mnemonic = config('BTC_MNEMONIC', default=None)
        if not mnemonic:
            logger.error("No BTC_MNEMONIC configured in environment")
            return None
        
        logger.info("Creating BTC wallet from mnemonic...")
        
        # Create BTC wallet
        wallet = BTC()
        wallet = wallet.from_mnemonic(mnemonic=mnemonic)
        
        # Generate a new address with a random index
        import random
        index = random.randint(1000, 9999)  # Random index for testing
        
        logger.info(f"Generating new BTC address with index: {index}")
        
        address_gen, priv_key, pub_key = wallet.new_address(index=index)
        
        logger.info(f"✅ Generated new BTC testnet address: {address_gen}")
        logger.info(f"Private key: {priv_key}")
        logger.info(f"Public key: {pub_key}")
        
        return {
            'address': address_gen,
            'private_key': priv_key,
            'public_key': pub_key,
            'index': index
        }
        
    except Exception as e:
        logger.error(f"Error generating BTC address: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def generate_multiple_addresses(count=5):
    """Generate multiple Bitcoin addresses"""
    
    logger.info(f"Generating {count} new BTC addresses...")
    
    addresses = []
    for i in range(count):
        logger.info(f"Generating address {i+1}/{count}...")
        result = generate_new_btc_address()
        if result:
            addresses.append(result)
            logger.info(f"✅ Address {i+1}: {result['address']}")
        else:
            logger.error(f"❌ Failed to generate address {i+1}")
    
    logger.info(f"Generated {len(addresses)} addresses successfully")
    return addresses

if __name__ == "__main__":
    logger.info("🚀 Starting BTC address generation...")
    
    # Generate a single address
    result = generate_new_btc_address()
    
    if result:
        print("\n" + "="*50)
        print("🎉 NEW BITCOIN ADDRESS GENERATED!")
        print("="*50)
        print(f"Address: {result['address']}")
        print(f"Index: {result['index']}")
        print("="*50)
        
        # Ask if user wants to generate more
        try:
            response = input("\nGenerate more addresses? (y/n): ").lower().strip()
            if response == 'y':
                count = int(input("How many more addresses? (1-10): "))
                count = max(1, min(10, count))  # Limit to 1-10
                generate_multiple_addresses(count)
        except (ValueError, KeyboardInterrupt):
            logger.info("Address generation completed.")
    else:
        logger.error("Failed to generate BTC address") 