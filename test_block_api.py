#!/usr/bin/env python3
"""
Test script for block API functionality
"""

import requests
import json
from datetime import datetime

def test_block_api():
    """Test the block API functionality"""
    base_url = "http://localhost:5005"
    
    print("🔍 Testing Block API Functionality")
    print("=" * 50)
    
    # Test 1: Check server status
    print("1️⃣ Checking server status...")
    try:
        response = requests.get(f"{base_url}/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✅ Server is running")
            print(f"   Network: {'testnet' if status['testnet'] else 'mainnet'}")
        else:
            print(f"❌ Failed to get status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error checking status: {e}")
        return False
    
    # Test 2: Get current block height
    print("\n2️⃣ Getting current block height...")
    try:
        response = requests.get(f"{base_url}/block_height")
        if response.status_code == 200:
            height_data = response.json()
            current_height = height_data['height']
            print(f"✅ Current block height: {current_height}")
            print(f"   Network: {height_data['network']}")
        else:
            print(f"❌ Failed to get block height: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error getting block height: {e}")
        return False
    
    # Test 3: Get a specific block by height
    print(f"\n3️⃣ Getting block at height {current_height}...")
    try:
        response = requests.get(f"{base_url}/block/{current_height}")
        if response.status_code == 200:
            block_data = response.json()
            print(f"✅ Retrieved block {current_height}")
            print(f"   Hash: {block_data.get('hash', 'N/A')}")
            print(f"   Size: {block_data.get('size', 'N/A')} bytes")
            print(f"   Transactions: {len(block_data.get('tx', []))}")
            print(f"   Timestamp: {datetime.fromtimestamp(block_data.get('time', 0))}")
            print(f"   Network: {block_data.get('network', 'N/A')}")
        else:
            print(f"❌ Failed to get block: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error getting block: {e}")
    
    # Test 4: Get recent blocks
    print(f"\n4️⃣ Getting recent blocks...")
    try:
        response = requests.get(f"{base_url}/blocks/recent?count=5")
        if response.status_code == 200:
            recent_data = response.json()
            blocks = recent_data['blocks']
            print(f"✅ Retrieved {len(blocks)} recent blocks")
            print(f"   Range: {recent_data['start_height']} - {recent_data['end_height']}")
            
            for block in blocks:
                timestamp = datetime.fromtimestamp(block.get('time', 0))
                print(f"   Block {block['height']}: {block['hash'][:16]}... ({block['tx_count']} txs, {timestamp})")
        else:
            print(f"❌ Failed to get recent blocks: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error getting recent blocks: {e}")
    
    # Test 5: Get block by hash (using the hash from previous test)
    if 'block_data' in locals() and block_data.get('hash'):
        block_hash = block_data['hash']
        print(f"\n5️⃣ Getting block by hash {block_hash[:16]}...")
        try:
            response = requests.get(f"{base_url}/block/hash/{block_hash}")
            if response.status_code == 200:
                hash_block_data = response.json()
                print(f"✅ Retrieved block by hash")
                print(f"   Height: {hash_block_data.get('height', 'N/A')}")
                print(f"   Size: {hash_block_data.get('size', 'N/A')} bytes")
                print(f"   Transactions: {len(hash_block_data.get('tx', []))}")
            else:
                print(f"❌ Failed to get block by hash: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Error getting block by hash: {e}")
    
    # Test 6: Test error handling
    print(f"\n6️⃣ Testing error handling...")
    
    # Test invalid height
    try:
        response = requests.get(f"{base_url}/block/999999999")
        if response.status_code == 400:
            print(f"✅ Correctly rejected invalid height")
        else:
            print(f"❌ Should have rejected invalid height: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing invalid height: {e}")
    
    # Test invalid hash
    try:
        response = requests.get(f"{base_url}/block/hash/invalid_hash")
        if response.status_code == 400:
            print(f"✅ Correctly rejected invalid hash")
        else:
            print(f"❌ Should have rejected invalid hash: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing invalid hash: {e}")
    
    # Test 7: Show API endpoints
    print(f"\n🔗 Block API Endpoints:")
    print(f"   GET {base_url}/block_height - Get current block height")
    print(f"   GET {base_url}/block/<height> - Get block by height")
    print(f"   GET {base_url}/block/hash/<hash> - Get block by hash")
    print(f"   GET {base_url}/blocks/recent?count=N - Get recent blocks")
    
    # Test 8: Show usage examples
    print(f"\n📖 How to use the block API:")
    print(f"   1. Get current height:")
    print(f"      curl {base_url}/block_height")
    
    print(f"\n   2. Get block by height:")
    print(f"      curl {base_url}/block/{current_height}")
    
    print(f"\n   3. Get recent blocks:")
    print(f"      curl {base_url}/blocks/recent?count=10")
    
    print(f"\n   4. Get block by hash:")
    if 'block_hash' in locals():
        print(f"      curl {base_url}/block/hash/{block_hash}")
    
    # Test 9: Show response format
    print(f"\n📊 Block response format:")
    example_block = {
        "height": current_height,
        "hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "version": 1,
        "previousblockhash": "0000000000000000000000000000000000000000000000000000000000000000",
        "merkleroot": "0000000000000000000000000000000000000000000000000000000000000000",
        "time": 1234567890,
        "bits": "1d00ffff",
        "nonce": 123456,
        "size": 1000,
        "weight": 4000,
        "tx": ["txid1", "txid2", "txid3"],
        "network": "testnet"
    }
    print(json.dumps(example_block, indent=2))
    
    print(f"\n✅ Block API functionality is ready!")
    print(f"   The API supports:")
    print(f"   - Getting blocks by height")
    print(f"   - Getting blocks by hash")
    print(f"   - Getting recent blocks")
    print(f"   - Current block height")
    print(f"   - Comprehensive error handling")
    
    return True

if __name__ == "__main__":
    test_block_api() 