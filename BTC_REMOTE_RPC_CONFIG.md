# Bitcoin Remote RPC Configuration

## Overview

The BTCWallet class now supports connecting to remote Bitcoin nodes over HTTP/HTTPS instead of requiring local Docker access. This makes it suitable for production environments where the Bitcoin node is on a separate server or cloud infrastructure.

## Environment Variables

Configure your remote Bitcoin node connection using these environment variables:

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

## Configuration Examples

### 1. Remote Mainnet Node (HTTPS)
```bash
BTC_RPC_HOST=bitcoin.example.com
BTC_RPC_PORT=8332
BTC_RPC_USER=bitcoinuser
BTC_RPC_PASSWORD=securepassword123
BTC_RPC_SSL=true
BTC_RPC_SSL_VERIFY=true
```

### 2. Remote Testnet Node (HTTP)
```bash
BTC_RPC_HOST=testnet.example.com
BTC_RPC_PORT=18332
BTC_RPC_USER=testnetuser
BTC_RPC_PASSWORD=testpassword
BTC_RPC_SSL=false
BTC_RPC_SSL_VERIFY=false
```

### 3. Local Development (HTTP)
```bash
BTC_RPC_HOST=localhost
BTC_RPC_PORT=18332
BTC_RPC_USER=bitcoin
BTC_RPC_PASSWORD=bitcoinpassword
BTC_RPC_SSL=false
BTC_RPC_SSL_VERIFY=false
```

## Bitcoin Node Configuration

Your remote Bitcoin node needs to be configured to accept RPC connections:

### bitcoin.conf Configuration
```ini
# Enable RPC server
server=1
rpcuser=your-rpc-username
rpcpassword=your-rpc-password

# Allow RPC connections from your application server
rpcallowip=your-app-server-ip/32

# For remote connections, bind to all interfaces
rpcbind=0.0.0.0:8332

# Optional: Enable SSL/TLS
# rpcssl=1
# rpcsslcertificatechainfile=/path/to/cert.pem
# rpcsslprivatekeyfile=/path/to/key.pem
```

### Security Considerations

1. **Network Security**: Use firewalls to restrict access to RPC port
2. **Strong Passwords**: Use strong, unique passwords for RPC authentication
3. **SSL/TLS**: Enable SSL for production environments
4. **IP Restrictions**: Use `rpcallowip` to limit access to trusted IPs
5. **VPN**: Consider using VPN for additional security

## Usage Examples

### Basic Remote Connection
```python
from shared.crypto.clients.btc import BTCWallet, BitcoinConfig
from db.connection import get_session

# Configuration will be loaded from environment variables
config = BitcoinConfig.mainnet("your_api_key")
session = get_session()

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
from shared.crypto.clients.btc import BitcoinConfig

# Create custom configuration
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

## Error Handling

The RPC client includes comprehensive error handling for network issues:

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

## Common Issues

### 1. Connection Timeout
```
Error: RPC request timed out after 30 seconds
```
**Solution**: Increase `BTC_RPC_TIMEOUT` or check network connectivity

### 2. Authentication Failed
```
Error: RPC Error: {'code': -28, 'message': 'Loading block index...'}
```
**Solution**: Check `BTC_RPC_USER` and `BTC_RPC_PASSWORD`

### 3. SSL Certificate Issues
```
Error: SSL certificate verification failed
```
**Solution**: Set `BTC_RPC_SSL_VERIFY=false` for self-signed certificates

### 4. Connection Refused
```
Error: Connection error: Connection refused
```
**Solution**: Check if Bitcoin node is running and RPC is enabled

## Testing Remote Connection

Use the test script to verify your remote connection:

```bash
python test_btc_rpc_integration.py
```

Or create a simple test:

```python
from shared.crypto.clients.btc import BTCWallet, BitcoinConfig

config = BitcoinConfig.mainnet("test")
btc_wallet = BTCWallet(user_id=999, config=config, session=None)

# Test connection
if btc_wallet.test_rpc_connection():
    print("✅ Remote connection successful")
    
    # Get sync status
    sync_status = btc_wallet.get_sync_status()
    print(f"Progress: {sync_status.get('verification_progress', 0.0):.2%}")
else:
    print("❌ Remote connection failed")
```

## Production Deployment

For production environments:

1. **Use HTTPS**: Set `BTC_RPC_SSL=true`
2. **Verify Certificates**: Set `BTC_RPC_SSL_VERIFY=true`
3. **Strong Authentication**: Use strong RPC passwords
4. **Network Security**: Restrict RPC access with firewalls
5. **Monitoring**: Monitor connection health and sync status
6. **Backup Nodes**: Consider multiple Bitcoin nodes for redundancy

## Benefits of Remote RPC

1. **Scalability**: No need to run Bitcoin node on application server
2. **Security**: Bitcoin node can be isolated in secure network
3. **Performance**: Dedicated Bitcoin node with optimized resources
4. **Maintenance**: Bitcoin node can be managed separately
5. **Flexibility**: Can connect to different networks (mainnet/testnet) 