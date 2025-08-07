#!/usr/bin/env python3
"""
Simple example of using BTCWallet RPC functionality
"""

import sys
import os
import logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.clients.btc import BTCWallet, BitcoinConfig
from db.connection import get_session

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Example usage of BTCWallet RPC functionality"""
    print("🚀 BTCWallet RPC Example")
    print("=" * 30)
    
    try:
        # Create configuration
        config = BitcoinConfig.testnet("your_api_key")
        
        # Create session
        session = get_session()
        
        # Create BTCWallet instance
        btc_wallet = BTCWallet(
            user_id=123,
            config=config,
            session=session,
            logger=logger
        )
        
        # Test connection
        if not btc_wallet.test_rpc_connection():
            print("❌ Cannot connect to Bitcoin node")
            print("Make sure the Bitcoin node is running:")
            print("docker-compose up -d bitcoin")
            return
        
        print("✅ Connected to Bitcoin node")
        
        # Get sync status
        sync_status = btc_wallet.get_sync_status()
        print(f"\n📊 Sync Status:")
        print(f"   Chain: {sync_status.get('chain', 'unknown')}")
        print(f"   Blocks: {sync_status.get('blocks', 0):,}")
        print(f"   Headers: {sync_status.get('headers', 0):,}")
        print(f"   Progress: {sync_status.get('verification_progress', 0.0):.2%}")
        print(f"   Fully synced: {btc_wallet.is_fully_synced()}")
        
        # Get blockchain info
        blockchain_info = btc_wallet.get_blockchain_info()
        result = blockchain_info.get("result", {})
        
        print(f"\n🔗 Blockchain Info:")
        print(f"   Best block hash: {result.get('bestblockhash', 'unknown')[:32]}...")
        print(f"   Difficulty: {result.get('difficulty', 'unknown')}")
        print(f"   Size on disk: {result.get('size_on_disk', 0):,} bytes")
        
        # Get network info
        network_info = btc_wallet.get_network_info()
        network_result = network_info.get("result", {})
        
        print(f"\n🌐 Network Info:")
        print(f"   Version: {network_result.get('version', 'unknown')}")
        print(f"   Connections: {network_result.get('connections', 'unknown')}")
        print(f"   Subversion: {network_result.get('subversion', 'unknown')}")
        
        # Get mempool info
        mempool_info = btc_wallet.get_mempool_info()
        mempool_result = mempool_info.get("result", {})
        
        print(f"\n📦 Mempool Info:")
        print(f"   Size: {mempool_result.get('size', 'unknown')} transactions")
        print(f"   Bytes: {mempool_result.get('bytes', 'unknown'):,} bytes")
        print(f"   Usage: {mempool_result.get('usage', 'unknown'):,} bytes")
        
        # Test address validation
        test_address = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
        validation = btc_wallet.validate_address(test_address)
        validation_result = validation.get("result", {})
        
        print(f"\n✅ Address Validation:")
        print(f"   Address: {test_address}")
        print(f"   Is valid: {validation_result.get('isvalid', 'unknown')}")
        if validation_result.get('isvalid'):
            print(f"   Type: {validation_result.get('type', 'unknown')}")
        
        # Get a new address
        new_address = btc_wallet.get_new_address()
        if new_address:
            print(f"\n🆕 New Address:")
            print(f"   {new_address}")
        
        # Test wallet management
        wallets = btc_wallet.list_wallets()
        print(f"\n💼 Available Wallets:")
        for wallet in wallets:
            print(f"   - {wallet}")
        
        # Setup watch-only wallet
        if btc_wallet.setup_watch_only_wallet("example_watchonly"):
            print(f"\n👀 Watch-only wallet 'example_watchonly' ready")
        
        print(f"\n✅ Example completed successfully!")
        
    except Exception as e:
        logger.error(f"Example failed: {e}")
        print(f"❌ Example failed: {e}")

if __name__ == "__main__":
    main() 