#!/usr/bin/env python3
"""
Test script for BTCWallet RPC integration
Demonstrates the new Bitcoin RPC client functionality
"""

import sys
import os
import logging
from typing import Dict, Any

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.clients.btc import BTCWallet, BitcoinConfig
from db.connection import get_session
from shared.logger import setup_logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_btc_wallet_rpc():
    """Test the BTCWallet RPC functionality"""
    print("🧪 Testing BTCWallet RPC Integration")
    print("=" * 50)
    
    try:
        # Create a test configuration
        config = BitcoinConfig.testnet("test_api_key")
        
        # Create a session (you might need to adjust this based on your setup)
        session = get_session()
        
        # Create BTCWallet instance
        btc_wallet = BTCWallet(
            user_id=999,  # Test user ID
            config=config,
            session=session,
            logger=logger
        )
        
        print("\n1. Testing RPC Connection...")
        if btc_wallet.test_rpc_connection():
            print("   ✅ RPC connection successful!")
        else:
            print("   ❌ RPC connection failed!")
            print("   Make sure the Bitcoin node is running:")
            print("   docker-compose up -d bitcoin")
            return
        print()
        
        print("2. Getting Blockchain Information...")
        try:
            blockchain_info = btc_wallet.get_blockchain_info()
            result = blockchain_info.get("result", {})
            print(f"   ✅ Chain: {result.get('chain', 'unknown')}")
            print(f"   ✅ Blocks: {result.get('blocks', 'unknown')}")
            print(f"   ✅ Headers: {result.get('headers', 'unknown')}")
            print(f"   ✅ Pruned: {result.get('pruned', 'unknown')}")
            if result.get('pruned'):
                print(f"   ✅ Prune height: {result.get('pruneheight', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("3. Getting Block Count...")
        try:
            block_count = btc_wallet.get_block_count()
            print(f"   ✅ Current block count: {block_count}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("4. Getting Best Block Hash...")
        try:
            best_hash = btc_wallet.get_best_block_hash()
            print(f"   ✅ Best block hash: {best_hash[:32]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("5. Getting Network Information...")
        try:
            network_info = btc_wallet.get_network_info()
            result = network_info.get("result", {})
            print(f"   ✅ Version: {result.get('version', 'unknown')}")
            print(f"   ✅ Subversion: {result.get('subversion', 'unknown')}")
            print(f"   ✅ Connections: {result.get('connections', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("6. Getting Mempool Information...")
        try:
            mempool_info = btc_wallet.get_mempool_info()
            result = mempool_info.get("result", {})
            print(f"   ✅ Mempool size: {result.get('size', 'unknown')}")
            print(f"   ✅ Mempool bytes: {result.get('bytes', 'unknown')}")
            print(f"   ✅ Mempool usage: {result.get('usage', 'unknown')} bytes")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("7. Getting Sync Status...")
        try:
            sync_status = btc_wallet.get_sync_status()
            print(f"   ✅ Chain: {sync_status.get('chain', 'unknown')}")
            print(f"   ✅ Blocks: {sync_status.get('blocks', 'unknown')}")
            print(f"   ✅ Headers: {sync_status.get('headers', 'unknown')}")
            print(f"   ✅ Progress: {sync_status.get('verification_progress', 0.0):.2%}")
            print(f"   ✅ IBD: {sync_status.get('initial_block_download', True)}")
            print(f"   ✅ Fully synced: {btc_wallet.is_fully_synced()}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("8. Getting Node Information...")
        try:
            node_info = btc_wallet.get_node_info()
            print(f"   ✅ Is fully synced: {node_info.get('is_fully_synced', False)}")
            print(f"   ✅ Sync status available: {'sync_status' in node_info}")
            print(f"   ✅ Blockchain info available: {'blockchain' in node_info}")
            print(f"   ✅ Network info available: {'network' in node_info}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("9. Testing Address Validation...")
        test_address = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"  # Testnet address
        try:
            validation = btc_wallet.validate_address(test_address)
            result = validation.get("result", {})
            print(f"   ✅ Address: {test_address}")
            print(f"   ✅ Is valid: {result.get('isvalid', 'unknown')}")
            if result.get('isvalid'):
                print(f"   ✅ Address type: {result.get('type', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("10. Testing New Address Generation...")
        try:
            new_address = btc_wallet.get_new_address()
            if new_address:
                print(f"   ✅ New address: {new_address}")
            else:
                print("   ⚠️  No new address generated")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("11. Testing Wallet Management...")
        try:
            wallets = btc_wallet.list_wallets()
            print(f"   ✅ Available wallets: {wallets}")
            
            # Test watch-only wallet setup
            if btc_wallet.setup_watch_only_wallet("test_watchonly"):
                print("   ✅ Watch-only wallet setup successful")
            else:
                print("   ⚠️  Watch-only wallet setup failed or already exists")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("12. Testing UTXO Functionality...")
        test_address = "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"
        try:
            utxos = btc_wallet.get_utxos_for_address(test_address, "test_watchonly")
            if utxos:
                print(f"   ✅ Found {len(utxos)} UTXO(s) for address {test_address}")
                for i, utxo in enumerate(utxos[:3], 1):  # Show first 3
                    print(f"      UTXO {i}: {utxo.get('amount', 'unknown')} BTC")
            else:
                print(f"   ℹ️  No UTXOs found for address {test_address}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("13. Testing Fee Estimation...")
        try:
            fee_estimate = btc_wallet.estimate_smart_fee(6, "CONSERVATIVE")
            result = fee_estimate.get("result", {})
            if result:
                fee_rate = result.get('feerate', 'unknown')
                print(f"   ✅ Estimated fee rate: {fee_rate} BTC/kB")
            else:
                print("   ⚠️  No fee estimate available")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("14. Testing Block Generation (for testing)...")
        try:
            # Get a new address for mining
            mining_address = btc_wallet.get_new_address()
            if mining_address:
                print(f"   ✅ Mining address: {mining_address}")
                
                # Generate 1 block (for testing purposes)
                block_hashes = btc_wallet.generate_to_address(mining_address, 1)
                if block_hashes:
                    print(f"   ✅ Generated block: {block_hashes[0]}")
                else:
                    print("   ⚠️  Block generation failed")
            else:
                print("   ⚠️  Could not get mining address")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("✅ BTCWallet RPC Integration Test Complete!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")

def main():
    """Main test function"""
    test_btc_wallet_rpc()

if __name__ == "__main__":
    main() 