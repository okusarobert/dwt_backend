#!/usr/bin/env python3
"""
Test script for remote Bitcoin RPC connections
Tests the BTCWallet RPC functionality with remote nodes
"""

import sys
import os
import logging
from typing import Dict, Any

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.clients.btc import BTCWallet, BitcoinConfig
from db.connection import get_session

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_remote_connection():
    """Test connection to remote Bitcoin node"""
    print("🌐 Testing Remote Bitcoin RPC Connection")
    print("=" * 50)
    
    try:
        # Create configuration (will use environment variables)
        config = BitcoinConfig.mainnet("test_api_key")
        
        # Create a session
        session = get_session()
        
        # Create BTCWallet instance
        btc_wallet = BTCWallet(
            user_id=999,  # Test user ID
            config=config,
            session=session,
            logger=logger
        )
        
        print(f"\n📡 Connection Details:")
        print(f"   Host: {config.rpc_host}")
        print(f"   Port: {config.rpc_port}")
        print(f"   SSL: {config.rpc_ssl}")
        print(f"   SSL Verify: {config.rpc_ssl_verify}")
        print(f"   Timeout: {config.rpc_timeout}s")
        
        print("\n1. Testing RPC Connection...")
        if btc_wallet.test_rpc_connection():
            print("   ✅ RPC connection successful!")
        else:
            print("   ❌ RPC connection failed!")
            print("   Check your environment variables:")
            print("   - BTC_RPC_HOST")
            print("   - BTC_RPC_PORT")
            print("   - BTC_RPC_USER")
            print("   - BTC_RPC_PASSWORD")
            return
        print()
        
        print("2. Getting Blockchain Information...")
        try:
            blockchain_info = btc_wallet.get_blockchain_info()
            if "error" in blockchain_info:
                print(f"   ❌ Error: {blockchain_info['error']}")
            else:
                result = blockchain_info.get("result", {})
                print(f"   ✅ Chain: {result.get('chain', 'unknown')}")
                print(f"   ✅ Blocks: {result.get('blocks', 'unknown'):,}")
                print(f"   ✅ Headers: {result.get('headers', 'unknown'):,}")
                print(f"   ✅ Pruned: {result.get('pruned', 'unknown')}")
                if result.get('pruned'):
                    print(f"   ✅ Prune height: {result.get('pruneheight', 'unknown'):,}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("3. Getting Sync Status...")
        try:
            sync_status = btc_wallet.get_sync_status()
            print(f"   ✅ Chain: {sync_status.get('chain', 'unknown')}")
            print(f"   ✅ Blocks: {sync_status.get('blocks', 0):,}")
            print(f"   ✅ Headers: {sync_status.get('headers', 0):,}")
            print(f"   ✅ Progress: {sync_status.get('verification_progress', 0.0):.2%}")
            print(f"   ✅ IBD: {sync_status.get('initial_block_download', True)}")
            print(f"   ✅ Fully synced: {btc_wallet.is_fully_synced()}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("4. Getting Network Information...")
        try:
            network_info = btc_wallet.get_network_info()
            if "error" in network_info:
                print(f"   ❌ Error: {network_info['error']}")
            else:
                result = network_info.get("result", {})
                print(f"   ✅ Version: {result.get('version', 'unknown')}")
                print(f"   ✅ Subversion: {result.get('subversion', 'unknown')}")
                print(f"   ✅ Connections: {result.get('connections', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("5. Getting Mempool Information...")
        try:
            mempool_info = btc_wallet.get_mempool_info()
            if "error" in mempool_info:
                print(f"   ❌ Error: {mempool_info['error']}")
            else:
                result = mempool_info.get("result", {})
                print(f"   ✅ Mempool size: {result.get('size', 'unknown')}")
                print(f"   ✅ Mempool bytes: {result.get('bytes', 'unknown'):,}")
                print(f"   ✅ Mempool usage: {result.get('usage', 'unknown'):,} bytes")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("6. Testing Address Validation...")
        test_address = "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"  # Genesis block address
        try:
            validation = btc_wallet.validate_address(test_address)
            if "error" in validation:
                print(f"   ❌ Error: {validation['error']}")
            else:
                result = validation.get("result", {})
                print(f"   ✅ Address: {test_address}")
                print(f"   ✅ Is valid: {result.get('isvalid', 'unknown')}")
                if result.get('isvalid'):
                    print(f"   ✅ Address type: {result.get('type', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("7. Testing Fee Estimation...")
        try:
            fee_estimate = btc_wallet.estimate_smart_fee(6, "CONSERVATIVE")
            if "error" in fee_estimate:
                print(f"   ❌ Error: {fee_estimate['error']}")
            else:
                result = fee_estimate.get("result", {})
                if result:
                    fee_rate = result.get('feerate', 'unknown')
                    print(f"   ✅ Estimated fee rate: {fee_rate} BTC/kB")
                else:
                    print("   ⚠️  No fee estimate available")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("8. Testing Node Information...")
        try:
            node_info = btc_wallet.get_node_info()
            print(f"   ✅ Is fully synced: {node_info.get('is_fully_synced', False)}")
            print(f"   ✅ Sync status available: {'sync_status' in node_info}")
            print(f"   ✅ Blockchain info available: {'blockchain' in node_info}")
            print(f"   ✅ Network info available: {'network' in node_info}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        print()
        
        print("✅ Remote Bitcoin RPC Test Complete!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"❌ Test failed: {e}")

def test_connection_with_custom_config():
    """Test connection with custom configuration"""
    print("\n🔧 Testing Custom Configuration")
    print("=" * 40)
    
    try:
        # Create custom configuration
        config = BitcoinConfig(
            endpoint="http://localhost:8332",
            headers={"Content-Type": "application/json"},
            rpc_host="localhost",
            rpc_port=8332,
            rpc_user="bitcoin",
            rpc_password="bitcoinpassword",
            rpc_ssl=False,
            rpc_ssl_verify=False,
            rpc_timeout=30
        )
        
        btc_wallet = BTCWallet(
            user_id=999,
            config=config,
            session=None,
            logger=logger
        )
        
        print(f"   Host: {config.rpc_host}:{config.rpc_port}")
        print(f"   SSL: {config.rpc_ssl}")
        
        if btc_wallet.test_rpc_connection():
            print("   ✅ Custom configuration works!")
        else:
            print("   ❌ Custom configuration failed!")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    """Main test function"""
    test_remote_connection()
    test_connection_with_custom_config()

if __name__ == "__main__":
    main() 