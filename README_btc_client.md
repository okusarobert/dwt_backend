# Bitcoin Client for GetBlock API

A comprehensive Python client for interacting with Bitcoin nodes through the GetBlock API. This client provides methods for getting blocks, transactions, and network information from a **read-only Bitcoin node**.

## ⚠️ Important Note

**This is a READ-ONLY Bitcoin client.** GetBlock's Bitcoin API does not support wallet operations (sending transactions, managing addresses, etc.). For wallet operations, you would need a full Bitcoin node with wallet enabled or a different service.

## Features

- **Block Operations**: Get block information by hash or height
- **Transaction Operations**: Get transaction details and raw transaction data
- **Network Information**: Get blockchain info, network stats, mempool data
- **Address Validation**: Validate Bitcoin addresses
- **Fee Estimation**: Estimate transaction fees
- **Mempool Information**: Get mempool statistics and transaction relationships

## Installation

1. Install the required dependencies:
```bash
pip install requests
```

2. Get your GetBlock API key from [GetBlock Dashboard](https://getblock.io/)

## Usage

### Basic Setup

```python
from btc_client import BitcoinClient, BitcoinConfig

# Initialize client
api_key = "your_api_key_here"
config = BitcoinConfig.testnet(api_key)  # Use mainnet for production
client = BitcoinClient(config)
```

### Getting Blockchain Information

```python
# Get blockchain info
blockchain_info = client.get_blockchain_info()
print(f"Chain: {blockchain_info['result']['chain']}")
print(f"Blocks: {blockchain_info['result']['blocks']}")

# Get current block count
block_count = client.get_block_count()
print(f"Current block count: {block_count}")

# Get best block hash
best_hash = client.get_best_block_hash()
print(f"Best block hash: {best_hash}")
```

### Block Operations

```python
# Get block by hash
block_info = client.get_block("block_hash_here", verbosity=1)
print(f"Block height: {block_info['result']['height']}")

# Get block by height
block_info = client.get_block_by_height(12345, verbosity=1)

# Get block hash by height
block_hash = client.get_block_hash(12345)

# Get block header
header_info = client.get_block_header("block_hash_here")
```

### Transaction Operations

```python
# Get raw transaction
tx_info = client.get_raw_transaction("txid_here", verbose=True)
print(f"Transaction: {tx_info['result']['txid']}")

# Get transaction from a specific block
tx_info = client.get_transaction_from_block("block_hash", 0)

# Get latest transactions from the most recent block
latest_txs = client.get_latest_transactions(10)
for tx in latest_txs:
    print(f"Transaction: {tx['txid']}")
```

### Network Information

```python
# Get network info
network_info = client.get_network_info()
print(f"Connections: {network_info['result']['connections']}")

# Get mempool info
mempool_info = client.get_mempool_info()
print(f"Mempool size: {mempool_info['result']['size']}")

# Get difficulty
difficulty = client.get_difficulty()
print(f"Difficulty: {difficulty}")

# Get mining info
mining_info = client.get_mining_info()
print(f"Blocks: {mining_info['result']['blocks']}")
```

### Fee Estimation

```python
# Estimate smart fee
fee_estimate = client.estimate_smart_fee(6, "CONSERVATIVE")
if fee_estimate['result']:
    fee_rate = fee_estimate['result'].get('feerate', 'unknown')
    print(f"Fee rate: {fee_rate} BTC/kB")
```

### Address Validation

```python
# Validate address
validation = client.validate_address("address_here")
print(f"Is valid: {validation['result']['isvalid']}")
```

## Configuration

The client supports both testnet and mainnet configurations:

```python
# Testnet (for testing)
config = BitcoinConfig.testnet(api_key)

# Mainnet (for production)
config = BitcoinConfig.mainnet(api_key)
```

## Error Handling

The client includes comprehensive error handling:

```python
try:
    result = client.get_blockchain_info()
    print(result)
except Exception as e:
    print(f"Error: {e}")
```

## API Methods Available

Based on the [GetBlock Bitcoin API documentation](https://docs.getblock.io/api-reference/bitcoin-btc), the client implements the following **supported** methods:

### ✅ Block Methods (WORKING)
- `getblockchaininfo()` - Get blockchain information
- `getblockcount()` - Get current block count
- `getbestblockhash()` - Get best block hash
- `getblock()` - Get block information
- `getblockhash()` - Get block hash by height
- `getblockheader()` - Get block header

### ✅ Transaction Methods (WORKING)
- `getrawtransaction()` - Get raw transaction
- `get_transaction_from_block()` - Get transaction from block
- `get_latest_transactions()` - Get latest transactions

### ✅ Network Methods (WORKING)
- `getnetworkinfo()` - Get network information
- `getconnectioncount()` - Get connection count
- `getdifficulty()` - Get current difficulty
- `getmininginfo()` - Get mining information

### ✅ Mempool Methods (WORKING)
- `getmempoolinfo()` - Get mempool information
- `getmempoolancestors()` - Get mempool ancestors
- `getmempooldescendants()` - Get mempool descendants

### ✅ Fee Methods (WORKING)
- `estimatesmartfee()` - Estimate smart fee

### ✅ Address Methods (WORKING)
- `validateaddress()` - Validate Bitcoin address

### ❌ Wallet Methods (NOT SUPPORTED)
- `getbalance()` - Get wallet balance
- `getnewaddress()` - Generate new address
- `getaddressinfo()` - Get address information
- `sendtoaddress()` - Send to address
- `gettransaction()` - Get transaction details
- `getreceivedbyaddress()` - Get received amount

## Running the Example

Run the example script to see the client in action:

```bash
python3 btc_example.py
```

Make sure to replace `"your_api_key_here"` with your actual GetBlock API key.

## Notes

- **Read-only node**: GetBlock's Bitcoin API is read-only and doesn't support wallet operations
- **No wallet operations**: You cannot send transactions, generate addresses, or manage wallets
- **Transaction viewing only**: You can view transaction details but cannot create or sign transactions
- **JSON-RPC 2.0**: The client uses JSON-RPC 2.0 protocol as required by GetBlock
- **Error handling**: All methods return the raw JSON-RPC response with `result` and `error` fields
- **Network connectivity**: Requires proper network connectivity to GetBlock's servers

## Alternative for Wallet Operations

If you need wallet functionality (sending transactions, managing addresses), consider:

1. **Running your own Bitcoin node** with wallet enabled
2. **Using a different service** that supports wallet operations
3. **Using a Bitcoin wallet library** like `bit` or `bitcoinlib` with your own node 