# Ethereum Wallet Class

A comprehensive Ethereum wallet implementation using Alchemy API, similar to the existing BTC wallet class.

## Features

- **HD Wallet Support**: Uses the existing HD wallet infrastructure for address generation
- **Alchemy API Integration**: Leverages Alchemy's API for blockchain interactions
- **Database Integration**: Stores wallet and address information in the database
- **Private Key Encryption**: Encrypts private keys using APP_SECRET
- **Multiple Networks**: Support for mainnet, Sepolia testnet, and Holesky testnet
- **Comprehensive API**: Full set of Ethereum blockchain operations

## Files Created

1. **`shared/crypto/clients/eth.py`** - Main Ethereum wallet class
2. **`eth_wallet_test.py`** - Test script for the wallet functionality
3. **`eth_wallet_example.py`** - Usage examples and patterns
4. **`ETH_WALLET_README.md`** - This documentation

## Quick Start

### 1. Set up Environment Variables

```bash
export ALCHEMY_API_KEY="your-alchemy-api-key"
export APP_SECRET="your-app-secret-key"
export ETH_MNEMONIC="your-ethereum-mnemonic-phrase"
```

### 2. Basic Usage

```python
from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from sqlalchemy.orm import Session

# Create configuration
api_key = "your-alchemy-api-key"
eth_config = EthereumConfig.testnet(api_key)  # or .mainnet() or .holesky()

# Create wallet instance
eth_wallet = ETHWallet(
    user_id=12345,
    config=eth_config,
    session=database_session,
    logger=logger
)

# Create wallet in database
eth_wallet.create_wallet()

# Test connection
if eth_wallet.test_connection():
    print("✅ Connected to Alchemy API")
```

### 3. Get Account Information

```python
# Get balance
balance = eth_wallet.get_balance("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
if balance:
    print(f"Balance: {balance['balance_eth']:.6f} ETH")

# Get account info
account_info = eth_wallet.get_account_info("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
if account_info:
    print(f"Transaction count: {account_info['transaction_count']}")
    print(f"Is contract: {account_info['is_contract']}")
```

## Configuration

### Network Options

- **Mainnet**: `EthereumConfig.mainnet(api_key)`
- **Sepolia Testnet**: `EthereumConfig.testnet(api_key)`
- **Holesky Testnet**: `EthereumConfig.holesky(api_key)`

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ALCHEMY_API_KEY` | Your Alchemy API key | Yes |
| `APP_SECRET` | Secret for encrypting private keys | Yes |
| `ETH_MNEMONIC` | Mnemonic phrase for HD wallet | Yes |

## API Methods

### Wallet Management

- `create_wallet()` - Create new wallet account in database
- `create_address()` - Generate new Ethereum address
- `encrypt_private_key()` - Encrypt private key
- `decrypt_private_key()` - Decrypt private key

### Blockchain Operations

- `test_connection()` - Test Alchemy API connection
- `get_latest_block_number()` - Get latest block number
- `get_block_by_number()` - Get block by number
- `get_block_by_hash()` - Get block by hash
- `get_balance()` - Get account balance
- `get_gas_price()` - Get current gas price
- `get_transaction()` - Get transaction details
- `get_transaction_receipt()` - Get transaction receipt
- `get_recent_blocks()` - Get recent blocks
- `estimate_gas()` - Estimate gas for transaction
- `get_transaction_count()` - Get transaction count (nonce)
- `get_code()` - Get contract code
- `get_storage_at()` - Get storage at position
- `get_logs()` - Get event logs

### Utility Methods

- `validate_address()` - Validate Ethereum address format
- `get_account_info()` - Get comprehensive account information
- `get_blockchain_info()` - Get blockchain status
- `get_network_info()` - Get network information

## Database Integration

The wallet integrates with the existing database models:

- **Account**: Stores wallet account information
- **CryptoAddress**: Stores Ethereum addresses and encrypted private keys

### Database Schema

```python
# Account record
crypto_account = Account(
    user_id=user_id,
    balance=0,
    locked_amount=0,
    currency="ETH",
    account_type=AccountType.CRYPTO,
    account_number=account_number,
    label="ETH Wallet"
)

# CryptoAddress record
crypto_address = CryptoAddress(
    account_id=account_id,
    address=user_address,
    label="ETH Wallet",
    is_active=True,
    currency_code="ETH",
    address_type="hd_wallet",
    private_key=encrypted_private_key,
    public_key=pub_key
)
```

## Security Features

### Private Key Encryption

Private keys are encrypted using the `APP_SECRET` environment variable:

```python
# Encryption
encrypted_key = eth_wallet.encrypt_private_key(private_key)

# Decryption
decrypted_key = eth_wallet.decrypt_private_key(encrypted_key)
```

### Address Validation

Built-in Ethereum address validation:

```python
is_valid = eth_wallet.validate_address("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
```

## Error Handling

The wallet includes comprehensive error handling:

- Connection failures
- Invalid API responses
- Database errors
- Encryption/decryption errors

All errors are logged and can be handled by the calling application.

## Testing

Run the test script to verify functionality:

```bash
python eth_wallet_test.py
```

Run the example script to see usage patterns:

```bash
python eth_wallet_example.py
```

## Dependencies

- `requests` - HTTP client for API calls
- `cryptography` - For private key encryption
- `hdwallet` - For HD wallet functionality
- `eth_utils` - For Ethereum utilities
- `pydantic` - For configuration models

## Comparison with BTC Wallet

| Feature | BTC Wallet | ETH Wallet |
|---------|------------|------------|
| API Provider | Bitcoin RPC | Alchemy API |
| HD Wallet | ✅ | ✅ |
| Private Key Encryption | ✅ | ✅ |
| Database Integration | ✅ | ✅ |
| Multiple Networks | ✅ | ✅ |
| Address Validation | ✅ | ✅ |
| Balance Checking | ✅ | ✅ |
| Transaction Monitoring | ✅ | ✅ |
| Gas Estimation | ❌ | ✅ |
| Contract Interaction | ❌ | ✅ |

## Migration from eth_test.py

The new `ETHWallet` class consolidates the functionality from `eth_test.py`:

- **AlchemyEthereumClient** → **ETHWallet** (with database integration)
- **SimpleWebSocketClient** → Can be added as WebSocket support
- **Configuration** → **EthereumConfig** class
- **API Methods** → Integrated into **ETHWallet** class

## Future Enhancements

- WebSocket support for real-time updates
- Transaction signing and broadcasting
- Smart contract interaction
- Token balance checking (ERC-20)
- NFT support
- Multi-signature wallet support 