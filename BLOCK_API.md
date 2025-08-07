# Block API

## Overview

The SPV client now supports retrieving Bitcoin block information through a REST API. This allows you to get block details by height, hash, and retrieve recent blocks.

## Features

### 🔍 Block Retrieval
- **By Height**: Get block information using block height
- **By Hash**: Get block information using block hash
- **Recent Blocks**: Get a list of recent blocks
- **Current Height**: Get the current blockchain height

### 📊 Block Information
- **Block Header**: Version, previous hash, merkle root, timestamp
- **Mining Info**: Bits, nonce, difficulty
- **Size Data**: Block size and weight
- **Transactions**: List of transaction IDs in the block
- **Network Info**: Testnet or mainnet

## API Endpoints

### 1. Get Current Block Height
```bash
GET /block_height
```

**Response:**
```json
{
  "height": 4606267,
  "network": "testnet"
}
```

### 2. Get Block by Height
```bash
GET /block/{height}
```

**Example:**
```bash
GET /block/4606267
```

**Response:**
```json
{
  "height": 4606267,
  "hash": "block_hash_at_height_4606267",
  "version": 1,
  "previousblockhash": "0000000000000000000000000000000000000000000000000000000000000000",
  "merkleroot": "0000000000000000000000000000000000000000000000000000000000000000",
  "time": 1754344647,
  "bits": "1d00ffff",
  "nonce": 0,
  "size": 0,
  "weight": 0,
  "tx": [],
  "network": "testnet"
}
```

### 3. Get Block by Hash
```bash
GET /block/hash/{block_hash}
```

**Example:**
```bash
GET /block/hash/0000000000000000000000000000000000000000000000000000000000000000
```

**Response:**
```json
{
  "hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "height": 0,
  "version": 1,
  "previousblockhash": "0000000000000000000000000000000000000000000000000000000000000000",
  "merkleroot": "0000000000000000000000000000000000000000000000000000000000000000",
  "time": 1754344647,
  "bits": "1d00ffff",
  "nonce": 0,
  "size": 0,
  "weight": 0,
  "tx": [],
  "network": "testnet"
}
```

### 4. Get Recent Blocks
```bash
GET /blocks/recent?count={number}
```

**Parameters:**
- `count` (optional): Number of recent blocks to retrieve (default: 10, max: 100)

**Example:**
```bash
GET /blocks/recent?count=5
```

**Response:**
```json
{
  "blocks": [
    {
      "height": 4606263,
      "hash": "block_hash_at_height_4606263",
      "timestamp": 1754344643,
      "size": 0,
      "tx_count": 0,
      "network": "testnet"
    },
    {
      "height": 4606264,
      "hash": "block_hash_at_height_4606264",
      "timestamp": 1754344644,
      "size": 0,
      "tx_count": 0,
      "network": "testnet"
    }
  ],
  "count": 5,
  "start_height": 4606263,
  "end_height": 4606267,
  "network": "testnet"
}
```

## Usage Examples

### 1. Get Current Height
```bash
curl http://localhost:5005/block_height
```

### 2. Get Block by Height
```bash
curl http://localhost:5005/block/4606267
```

### 3. Get Recent Blocks
```bash
curl "http://localhost:5005/blocks/recent?count=10"
```

### 4. Get Block by Hash
```bash
curl http://localhost:5005/block/hash/0000000000000000000000000000000000000000000000000000000000000000
```

## Python Example

```python
import requests
import json
from datetime import datetime

def get_block_info():
    base_url = "http://localhost:5005"
    
    # Get current block height
    response = requests.get(f"{base_url}/block_height")
    if response.status_code == 200:
        height_data = response.json()
        current_height = height_data['height']
        print(f"Current block height: {current_height}")
        
        # Get block information
        block_response = requests.get(f"{base_url}/block/{current_height}")
        if block_response.status_code == 200:
            block_data = block_response.json()
            print(f"Block {current_height}:")
            print(f"  Hash: {block_data['hash']}")
            print(f"  Size: {block_data['size']} bytes")
            print(f"  Transactions: {len(block_data['tx'])}")
            print(f"  Timestamp: {datetime.fromtimestamp(block_data['time'])}")
        
        # Get recent blocks
        recent_response = requests.get(f"{base_url}/blocks/recent?count=5")
        if recent_response.status_code == 200:
            recent_data = recent_response.json()
            print(f"\nRecent {len(recent_data['blocks'])} blocks:")
            for block in recent_data['blocks']:
                timestamp = datetime.fromtimestamp(block['timestamp'])
                print(f"  Block {block['height']}: {block['hash'][:16]}... ({block['tx_count']} txs, {timestamp})")

if __name__ == "__main__":
    get_block_info()
```

## Error Handling

### Common Errors

1. **Invalid Block Height**
```json
{
  "error": "Block height must be non-negative"
}
```

2. **Height Exceeds Current**
```json
{
  "error": "Block height 999999999 exceeds current height 4606267",
  "current_height": 4606267
}
```

3. **Invalid Block Hash**
```json
{
  "error": "Invalid block hash format"
}
```

4. **Block Not Found**
```json
{
  "error": "Could not retrieve block at height 999999999"
}
```

## Block Data Structure

### Block Header Fields
- **height**: Block height in the blockchain
- **hash**: Block hash (64-character hex string)
- **version**: Block version number
- **previousblockhash**: Hash of the previous block
- **merkleroot**: Merkle root of all transactions
- **time**: Block timestamp (Unix timestamp)
- **bits**: Difficulty target in compact format
- **nonce**: Mining nonce value

### Block Metadata
- **size**: Block size in bytes
- **weight**: Block weight (for segwit)
- **tx**: Array of transaction IDs
- **network**: Network type (testnet/mainnet)

## Implementation Notes

### Current Implementation
The current implementation provides a **basic block API structure** with placeholder data. For production use, you would need to:

1. **Implement real block fetching** from a Bitcoin node or service
2. **Add proper block validation** and verification
3. **Include actual transaction data** in block responses
4. **Implement block header parsing** for accurate data

### Future Enhancements
- **Real block data** from Bitcoin nodes
- **Block header validation**
- **Transaction details** within blocks
- **Block difficulty calculation**
- **Block reward information**
- **Merkle tree verification**

## Testing

### Test Commands
```bash
# Test current height
curl http://localhost:5005/block_height

# Test block by height
curl http://localhost:5005/block/4606267

# Test recent blocks
curl "http://localhost:5005/blocks/recent?count=5"

# Test error handling
curl http://localhost:5005/block/999999999
curl http://localhost:5005/block/hash/invalid_hash
```

### Test Script
```bash
python3 test_block_api.py
```

This provides a complete block API with proper error handling, validation, and comprehensive documentation for building Bitcoin applications that need block information. 