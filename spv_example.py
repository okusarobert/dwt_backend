#!/usr/bin/env python3
"""
Example usage of the SPV client
"""

import time
import logging
from spv_client import AdvancedSPVClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Example SPV client usage"""
    
    # Create SPV client
    # Note: You need a Bitcoin node running on localhost:8333
    # Or use a public Bitcoin node (be careful with public nodes)
    spv = AdvancedSPVClient(node_host="127.0.0.1", node_port=8333)
    
    # Connect to Bitcoin node
    logger.info("Connecting to Bitcoin node...")
    if not spv.connect():
        logger.error("Failed to connect to Bitcoin node")
        logger.info("Make sure you have a Bitcoin node running on localhost:8333")
        logger.info("Or modify the node_host and node_port to connect to a different node")
        return
    
    # Perform handshake
    logger.info("Performing handshake...")
    if not spv.handshake():
        logger.error("Handshake failed")
        spv.disconnect()
        return
    
    # Add addresses to watch
    addresses_to_watch = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Genesis block address
        "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",  # Example address
        # Add your own addresses here
    ]
    
    for address in addresses_to_watch:
        spv.add_watch_address(address)
    
    # Start listening for messages
    logger.info("Starting message listener...")
    listener_thread = spv.start_listening()
    
    try:
        logger.info("SPV client is running!")
        logger.info("Watching for transactions to the following addresses:")
        for address in spv.get_watched_addresses():
            logger.info(f"  - {address}")
        
        logger.info("\nPress Ctrl+C to stop the client")
        
        # Keep main thread alive and print stats
        while spv.connected:
            time.sleep(10)  # Print stats every 10 seconds
            
            # Print statistics
            logger.info("=" * 50)
            logger.info("SPV CLIENT STATISTICS")
            logger.info("=" * 50)
            logger.info(f"Connected: {spv.connected}")
            logger.info(f"Watched addresses: {len(spv.get_watched_addresses())}")
            logger.info(f"Cached transactions: {len(spv.get_transaction_cache())}")
            logger.info(f"Cached blocks: {len(spv.get_block_cache())}")
            
            # Print transactions for each watched address
            for address in spv.get_watched_addresses():
                transactions = spv.get_address_transactions(address)
                if transactions:
                    logger.info(f"\nAddress {address}:")
                    for tx in transactions[-5:]:  # Show last 5 transactions
                        logger.info(f"  - TX: {tx['txid'][:16]}... | Amount: {tx['amount']} sats | Type: {tx['type']}")
                else:
                    logger.info(f"\nAddress {address}: No transactions yet")
            
            logger.info("=" * 50)
            
    except KeyboardInterrupt:
        logger.info("\nStopping SPV client...")
    finally:
        spv.disconnect()
        logger.info("SPV client stopped")

if __name__ == "__main__":
    main() 