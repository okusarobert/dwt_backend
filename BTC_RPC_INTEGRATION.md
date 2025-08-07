# Bitcoin RPC Integration in BTCWallet

## Overview

The `BTCWallet` class has been enhanced with comprehensive Bitcoin RPC (Remote Procedure Call) functionality, allowing direct interaction with remote Bitcoin nodes over HTTP/HTTPS. This integration provides real-time blockchain data, wallet management, and transaction monitoring capabilities for production environments.

## Features Added

### 🔗 **RPC Connection Management**
- **`test_rpc_connection()`** - Test connection to remote Bitcoin node
- **`_make_rpc_request()`** - Internal method for making HTTP/HTTPS RPC calls

### 📊 **Blockchain Information**
- **`get_blockchain_info()`** - Get comprehensive blockchain status
- **`get_block_count()`** - Get current block count
- **`get_best_block_hash()`** - Get the hash of the best block
- **`get_block()`** - Get block information by hash
- **`get_block_hash()`** - Get block hash by height
- **`get_raw_transaction()`** - Get raw transaction data

### 🌐 **Network Information**
- **`get_network_info()`** - Get network status and connections
- **`get_mempool_info()`** - Get mempool statistics
- **`get_difficulty()`** - Get current mining difficulty
- **`get_mining_info()`** - Get mining-related information

### 💰 **Wallet Management**
- **`list_wallets()`** - List all available wallets
- **`create_wallet_rpc()`** - Create a new wallet via RPC
- **`load_wallet()`** - Load a wallet
- **`import_address()`** - Import an address to a wallet
- **`import_descriptors()`** - Import descriptors to a wallet

### 🔍 **UTXO and Address Management**
- **`list_unspent()`** - List unspent transaction outputs
- **`get_utxos_for_address()`** - Get UTXOs for a specific address
- **`setup_watch_only_wallet()`** - Setup watch-only wallet for monitoring
- **`validate_address()`** - Validate Bitcoin addresses

### 🆕 **Address and Transaction Features**
- **`get_new_address()`** - Generate new Bitcoin addresses
- **`generate_to_address()`** - Generate blocks to a specific address (for testing)
- **`estimate_smart_fee()`** - Estimate transaction fees

### 📈 **Sync Status and Monitoring**
- **`get_sync_status()`** - Get detailed sync status
- **`is_fully_synced()`** - Check if node is fully synced
- **`get_node_info()`** - Get comprehensive node information

## Configuration

The `BitcoinConfig` class has been enhanced with RPC-specific configuration for remote nodes:

```python
@dataclass
class BitcoinConfig:
    endpoint: str
    headers: Dict[str, str]
    rpc_host: str = "localhost"
    rpc_port: int = 18332  # 8332 for mainnet
    rpc_user: str = "bitcoin"
    rpc_password: str = "bitcoinpassword"
    rpc_timeout: int = 30
    rpc_ssl: bool = False
    rpc_ssl_verify: bool = True
```

### Environment Variables

You can configure RPC settings via environment variables:

```bash
# Remote Bitcoin Node Configuration
BTC_RPC_HOST=your-bitcoin-node.com
BTC_RPC_PORT=8332                    # 8332 for mainnet, 18332 for testnet
BTC_RPC_USER=your-rpc-username
BTC_RPC_PASSWORD=your-rpc-password
BTC_RPC_TIMEOUT=30                   # Request timeout in seconds
BTC_RPC_SSL=true                     # Use HTTPS (true/false)
BTC_RPC_SSL_VERIFY=true              # Verify SSL certificates (true/false)
```

## Usage Examples

### Basic Remote Setup

```python
from shared.crypto.clients.btc import BTCWallet, BitcoinConfig
from db.connection import get_session

# Create configuration (uses environment variables)
config = BitcoinConfig.mainnet("your_api_key")
session = get_session()

# Create BTCWallet instance
btc_wallet = BTCWallet(
    user_id=123,
    config=config,
    session=session
)

# Test connection
if btc_wallet.test_rpc_connection():
    print("✅ Connected to remote Bitcoin node")
else:
    print("❌ Connection failed")
```

### Custom Configuration

```python
# Create custom configuration for remote node
config = BitcoinConfig(
    endpoint="https://bitcoin.example.com:8332",
    headers={"Content-Type": "application/json"},
    rpc_host="bitcoin.example.com",
    rpc_port=8332,
    rpc_user="customuser",
    rpc_password="custompassword",
    rpc_ssl=True,
    rpc_ssl_verify=True,
    rpc_timeout=30
)
```

### Get Sync Status

```python
# Get detailed sync status
sync_status = btc_wallet.get_sync_status()
print(f"Chain: {sync_status.get('chain')}")
print(f"Blocks: {sync_status.get('blocks'):,}")
print(f"Progress: {sync_status.get('verification_progress'):.2%}")
print(f"Fully synced: {btc_wallet.is_fully_synced()}")
```

### Monitor Addresses

```python
# Setup watch-only wallet
btc_wallet.setup_watch_only_wallet("watchonly")

# Import address for monitoring
btc_wallet.import_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", wallet="watchonly")

# Get UTXOs for address
utxos = btc_wallet.get_utxos_for_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "watchonly")
for utxo in utxos:
    print(f"Amount: {utxo.get('amount')} BTC")
    print(f"Confirmations: {utxo.get('confirmations')}")
```

### Get Node Information

```python
# Get comprehensive node info
node_info = btc_wallet.get_node_info()

print(f"Blockchain: {node_info.get('blockchain', {}).get('chain')}")
print(f"Network connections: {node_info.get('network', {}).get('connections')}")
print(f"Mempool size: {node_info.get('mempool', {}).get('size')}")
print(f"Fully synced: {node_info.get('is_fully_synced')}")
```

## Error Handling

The RPC methods include comprehensive error handling for network issues:

```python
try:
    blockchain_info = btc_wallet.get_blockchain_info()
    if "error" in blockchain_info:
        print(f"RPC Error: {blockchain_info['error']}")
    else:
        result = blockchain_info.get("result", {})
        print(f"Blocks: {result.get('blocks')}")
except Exception as e:
    print(f"Connection error: {e}")
```

## Network Communication

The RPC functionality uses HTTP/HTTPS to communicate with remote Bitcoin nodes:

```python
# Internal implementation uses:
url = f"{protocol}://{self.config.rpc_host}:{self.config.rpc_port}"
response = self.session_request.post(
    url,
    json=payload,
    auth=(self.config.rpc_user, self.config.rpc_password),
    headers=headers,
    timeout=self.config.rpc_timeout,
    verify=self.config.rpc_ssl_verify
)
```

## Testing

Run the remote RPC test script to verify functionality:

```bash
python test_btc_remote_rpc.py
```

Or run the integration test:

```bash
python test_btc_rpc_integration.py
```

## Benefits

1. **Remote Access**: Connect to Bitcoin nodes on separate servers
2. **Production Ready**: Suitable for cloud and distributed environments
3. **SSL Support**: Secure HTTPS connections for production
4. **Network Resilient**: Comprehensive error handling for network issues
5. **Scalable**: No need to run Bitcoin node on application server
6. **Flexible**: Support for both HTTP and HTTPS connections

## Requirements

- Remote Bitcoin node with RPC enabled
- Network connectivity to the Bitcoin node
- Proper RPC authentication credentials
- SSL certificates (for HTTPS connections)

## Security Notes

- RPC credentials are stored in environment variables
- SSL/TLS encryption for secure connections
- Private keys are encrypted before storage
- Watch-only wallets are used for monitoring
- Network-level security controls recommended

## Integration with Existing Code

The RPC functionality integrates seamlessly with the existing `BTCWallet` class:

- Original wallet creation and address generation still work
- New RPC methods are additive and don't break existing functionality
- Database integration remains unchanged
- BlockCypher webhook functionality is preserved

## Production Deployment

For production environments:

1. **Use HTTPS**: Set `BTC_RPC_SSL=true`
2. **Verify Certificates**: Set `BTC_RPC_SSL_VERIFY=true`
3. **Strong Authentication**: Use strong RPC passwords
4. **Network Security**: Restrict RPC access with firewalls
5. **Monitoring**: Monitor connection health and sync status
6. **Backup Nodes**: Consider multiple Bitcoin nodes for redundancy 