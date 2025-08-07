#!/usr/bin/env python3
"""
Test script to debug block fetching
"""

import bitcoinlib
from bitcoinlib.services.services import Service

def test_block_fetching():
    """Test block fetching directly"""
    print("🔍 Testing Block Fetching")
    print("=" * 50)
    
    try:
        # Initialize service
        service = Service(network='testnet')
        print(f"✅ Service initialized")
        
        # Get current block height
        current_height = service.blockcount()
        print(f"✅ Current block height: {current_height}")
        
        # Test getting a block by height
        test_height = current_height
        print(f"\n🧪 Testing getblock with height {test_height}")
        
        try:
            block_info = service.getblock(test_height)
            print(f"✅ getblock returned: {type(block_info)}")
            
            if block_info:
                print(f"📊 Block info attributes:")
                for attr in dir(block_info):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(block_info, attr)
                            if not callable(value):
                                print(f"   {attr}: {value}")
                        except Exception as e:
                            print(f"   {attr}: Error accessing - {e}")
                
                # Try to access specific attributes
                print(f"\n🔍 Testing specific attributes:")
                
                # Test block_hash
                if hasattr(block_info, 'block_hash'):
                    print(f"   block_hash: {block_info.block_hash}")
                    print(f"   block_hash.hex(): {block_info.block_hash.hex()}")
                else:
                    print(f"   block_hash: Not available")
                
                # Test version
                if hasattr(block_info, 'version'):
                    print(f"   version: {block_info.version}")
                else:
                    print(f"   version: Not available")
                
                # Test time
                if hasattr(block_info, 'time'):
                    print(f"   time: {block_info.time}")
                else:
                    print(f"   time: Not available")
                
                # Test transactions
                if hasattr(block_info, 'transactions'):
                    print(f"   transactions: {len(block_info.transactions)} transactions")
                    if block_info.transactions:
                        for i, tx in enumerate(block_info.transactions[:3]):  # Show first 3
                            print(f"     tx[{i}]: {type(tx)}")
                            if hasattr(tx, 'txid'):
                                print(f"       txid: {tx.txid.hex()}")
                else:
                    print(f"   transactions: Not available")
                
                # Test raw data
                if hasattr(block_info, 'raw'):
                    raw_data = block_info.raw()
                    print(f"   raw data length: {len(raw_data)} bytes")
                else:
                    print(f"   raw data: Not available")
                
            else:
                print(f"❌ getblock returned None")
                
        except Exception as e:
            print(f"❌ Error getting block: {e}")
            import traceback
            traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_block_fetching() 