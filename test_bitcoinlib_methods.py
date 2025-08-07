#!/usr/bin/env python3
"""
Test script to explore bitcoinlib service methods
"""

import bitcoinlib
from bitcoinlib.services.services import Service

def explore_bitcoinlib_service():
    """Explore what methods are available in the bitcoinlib service"""
    print("🔍 Exploring bitcoinlib Service Methods")
    print("=" * 50)
    
    try:
        # Initialize service
        service = Service(network='testnet')
        print(f"✅ Service initialized: {service}")
        
        # Get current block height
        current_height = service.blockcount()
        print(f"✅ Current block height: {current_height}")
        
        # List all available methods
        print(f"\n📋 Available methods:")
        methods = [method for method in dir(service) if not method.startswith('_')]
        for method in sorted(methods):
            print(f"   - {method}")
        
        # Test some common methods
        print(f"\n🧪 Testing common methods:")
        
        # Test getbalance
        try:
            balance = service.getbalance("mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh")
            print(f"   ✅ getbalance: {balance}")
        except Exception as e:
            print(f"   ❌ getbalance failed: {e}")
        
        # Test getutxos
        try:
            utxos = service.getutxos("mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh")
            print(f"   ✅ getutxos: {len(utxos) if utxos else 0} UTXOs")
        except Exception as e:
            print(f"   ❌ getutxos failed: {e}")
        
        # Test gettransactions
        try:
            txs = service.gettransactions("mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh")
            print(f"   ✅ gettransactions: {len(txs) if txs else 0} transactions")
        except Exception as e:
            print(f"   ❌ gettransactions failed: {e}")
        
        # Test if getblockhash exists
        if hasattr(service, 'getblockhash'):
            try:
                block_hash = service.getblockhash(current_height)
                print(f"   ✅ getblockhash: {block_hash}")
            except Exception as e:
                print(f"   ❌ getblockhash failed: {e}")
        else:
            print(f"   ❌ getblockhash method not available")
        
        # Test if getblock exists
        if hasattr(service, 'getblock'):
            try:
                # Try with a known block hash or height
                block_info = service.getblock(current_height)
                print(f"   ✅ getblock: {type(block_info)}")
                if block_info:
                    print(f"      Block info keys: {list(block_info.keys()) if hasattr(block_info, 'keys') else 'No keys'}")
            except Exception as e:
                print(f"   ❌ getblock failed: {e}")
        else:
            print(f"   ❌ getblock method not available")
        
        # Test other potential methods
        potential_methods = ['getblockheader', 'getblockinfo', 'getrawblock', 'getblockdata']
        for method_name in potential_methods:
            if hasattr(service, method_name):
                print(f"   ✅ {method_name} method available")
            else:
                print(f"   ❌ {method_name} method not available")
        
        print(f"\n📊 Service type: {type(service)}")
        print(f"📊 Service class: {service.__class__}")
        
    except Exception as e:
        print(f"❌ Error exploring service: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    explore_bitcoinlib_service() 