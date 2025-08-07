# Base Wallet Class

A comprehensive Base (Coinbase's L2 network) wallet implementation using Alchemy API, similar to the existing BTC and ETH wallet classes.

## Features

- **HD Wallet Support**: Uses the existing HD wallet infrastructure for address generation
- **Alchemy API Integration**: Leverages Alchemy's API for Base blockchain interactions
- **Database Integration**: Stores wallet and address information in the database
- **Private Key Encryption**: Encrypts private keys using APP_SECRET
- **L2 Network Support**: Optimized for Base L2 network with faster finality and lower fees
- **Token Support**: ERC-20 token balance checking
- **Ethereum Compatibility**: Uses Ethereum addresses and standards

## Files Created

1. **`shared/crypto/clients/base.py`** - Main Base wallet class
2. **`base_wallet_test.py`** - Test script for the wallet functionality
3. **`base_wallet_example.py`** - Usage examples and patterns
4. **`BASE_WALLET_README.md`** - This documentation

## Quick Start

### 1. Set up Environment Variables

```bash
export ALCHEMY_BASE_API_KEY="your-alchemy-base-api-key"
export APP_SECRET="your-app-secret-key"
export BASE_MNEMONIC="your-base-mnemonic-phrase"
```

### 2. Basic Usage

```python
from shared.crypto.clients.base import BaseWallet, BaseConfig
from sqlalchemy.orm import Session

# Create configuration
api_key = "your-alchemy-base-api-key"
base_config = BaseConfig.testnet(api_key)  # or .mainnet()

# Create wallet instance
base_wallet = BaseWallet(
    user_id=12345,
    config=base_config,
    session=database_session,
    logger=logger
)

# Create wallet in database
base_wallet.create_wallet()

# Test connection
if base_wallet.test_connection():
    print("✅ Connected to Base API")
```

### 3. Get Account Information

```python
# Get balance
balance = base_wallet.get_balance("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
if balance:
    print(f"Balance: {balance['balance_base']:.6f} BASE")

# Get account info
account_info = base_wallet.get_account_info("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
if account_info:
    print(f"Transaction count: {account_info['transaction_count']}")
    print(f"Is contract: {account_info['is_contract']}")
```

## Configuration

### Network Options

- **Mainnet**: `BaseConfig.mainnet(api_key)`
- **Sepolia Testnet**: `BaseConfig.testnet(api_key)`

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ALCHEMY_BASE_API_KEY` | Your Alchemy Base API key | Yes |
| `APP_SECRET` | Secret for encrypting private keys | Yes |
| `BASE_MNEMONIC` | Mnemonic phrase for HD wallet | Yes |

## API Methods

### Wallet Management

- `create_wallet()` - Create new wallet account in database
- `create_address()` - Generate new Base address
- `encrypt_private_key()` - Encrypt private key
- `decrypt_private_key()` - Decrypt private key

### Blockchain Operations

- `test_connection()` - Test Base API connection
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

### Base-Specific Methods

- `get_token_balance()` - Get ERC-20 token balance
- `get_base_specific_info()` - Get L2-specific information
- `validate_address()` - Validate Base address format
- `get_account_info()` - Get comprehensive account information
- `get_blockchain_info()` - Get blockchain status
- `get_network_info()` - Get network information

## Database Integration

The wallet integrates with the existing database models:

- **Account**: Stores wallet account information
- **CryptoAddress**: Stores Base addresses and encrypted private keys

### Database Schema

```python
# Account record
crypto_account = Account(
    user_id=user_id,
    balance=0,
    locked_amount=0,
    currency="BASE",
    account_type=AccountType.CRYPTO,
    account_number=account_number,
    label="BASE Wallet"
)

# CryptoAddress record
crypto_address = CryptoAddress(
    account_id=account_id,
    address=user_address,
    label="BASE Wallet",
    is_active=True,
    currency_code="BASE",
    address_type="hd_wallet",
    private_key=encrypted_private_key,
    public_key=pub_key
)
```

## L2 Network Features

### Base Network Characteristics

- **Chain ID**: 8453 (mainnet), 84532 (testnet)
- **L1 Chain**: Ethereum
- **Consensus**: Optimistic Rollup
- **Finality**: ~12 seconds
- **Gas Fees**: Significantly lower than Ethereum L1

### L2-Specific Information

```python
l2_info = base_wallet.get_base_specific_info()
print(f"Network: {l2_info['network']}")
print(f"Chain ID: {l2_info['chain_id']}")
print(f"Is L2: {l2_info['is_l2']}")
print(f"L1 Chain: {l2_info['l1_chain']}")
```

## Token Support

### ERC-20 Token Balance

```python
# Get token balance
token_balance = base_wallet.get_token_balance(
    token_address="0x036CbD53842c5426634e7929541eC2318f3dCF7c",  # USDC
    wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
)

if token_balance:
    print(f"Token balance: {token_balance['balance']}")
```

### Common Tokens on Base

- **USDC**: `0x036CbD53842c5426634e7929541eC2318f3dCF7c` (Sepolia)
- **USDT**: `0x7169D38820dfd117C3FA1f22a697dBA58d90BA06` (Sepolia)
- **WETH**: `0x4200000000000000000000000000000000000006` (Sepolia)

## Security Features

### Private Key Encryption

Private keys are encrypted using the `APP_SECRET` environment variable:

```python
# Encryption
encrypted_key = base_wallet.encrypt_private_key(private_key)

# Decryption
decrypted_key = base_wallet.decrypt_private_key(encrypted_key)
```

### Address Validation

Built-in Base address validation (same as Ethereum):

```python
is_valid = base_wallet.validate_address("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
```

## Error Handling

The wallet includes comprehensive error handling:

- Connection failures
- Invalid API responses
- Database errors
- Encryption/decryption errors
- L2-specific errors

All errors are logged and can be handled by the calling application.

## Testing

Run the test script to verify functionality:

```bash
python base_wallet_test.py
```

Run the example script to see usage patterns:

```bash
python base_wallet_example.py
```

## Dependencies

- `requests` - HTTP client for API calls
- `cryptography` - For private key encryption
- `hdwallet` - For HD wallet functionality
- `eth_utils` - For Ethereum utilities
- `pydantic` - For configuration models

## Comparison with Other Wallets

| Feature | BTC Wallet | ETH Wallet | Base Wallet |
|---------|------------|------------|-------------|
| API Provider | Bitcoin RPC | Alchemy API | Alchemy API |
| HD Wallet | ✅ | ✅ | ✅ |
| Private Key Encryption | ✅ | ✅ | ✅ |
| Database Integration | ✅ | ✅ | ✅ |
| Multiple Networks | ✅ | ✅ | ✅ |
| Address Validation | ✅ | ✅ | ✅ |
| Balance Checking | ✅ | ✅ | ✅ |
| Transaction Monitoring | ✅ | ✅ | ✅ |
| Gas Estimation | ❌ | ✅ | ✅ |
| Contract Interaction | ❌ | ✅ | ✅ |
| Token Support | ❌ | ❌ | ✅ |
| L2 Network | ❌ | ❌ | ✅ |
| L1 Chain | Bitcoin | Ethereum | Ethereum |

## Migration from base_client.py

The new `BaseWallet` class consolidates the functionality from `base_client.py`:

- **BaseClient** → **BaseWallet** (with database integration)
- **BaseWebSocketClient** → Can be added as WebSocket support
- **Configuration** → **BaseConfig** class
- **API Methods** → Integrated into **BaseWallet** class

## L2 Advantages

### Performance Benefits

- **Faster Finality**: ~12 seconds vs ~12 minutes on Ethereum
- **Lower Gas Fees**: Significantly reduced transaction costs
- **Higher Throughput**: More transactions per second
- **Ethereum Security**: Inherits Ethereum's security model

### Developer Benefits

- **Ethereum Compatibility**: Same tools and standards
- **Smart Contracts**: Full EVM compatibility
- **Token Standards**: ERC-20, ERC-721, etc.
- **Existing Infrastructure**: Works with existing Ethereum tooling

## Future Enhancements

- WebSocket support for real-time updates
- Transaction signing and broadcasting
- Smart contract interaction
- NFT support (ERC-721, ERC-1155)
- Multi-signature wallet support
- Cross-chain bridge integration
- DeFi protocol integration 