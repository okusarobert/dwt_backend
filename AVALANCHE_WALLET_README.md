# Avalanche Wallet Class

A comprehensive Avalanche (AVAX) wallet implementation using Alchemy API, similar to the existing BTC, ETH, and Base wallet classes.

## Features

- **HD Wallet Support**: Uses the existing HD wallet infrastructure for address generation
- **Alchemy API Integration**: Leverages Alchemy's API for Avalanche blockchain interactions
- **Database Integration**: Stores wallet and address information in the database
- **Private Key Encryption**: Encrypts private keys using APP_SECRET
- **High Performance**: Optimized for Avalanche's fast finality and high throughput
- **Token Support**: ERC-20 token balance checking
- **Ethereum Compatibility**: Uses Ethereum addresses and EVM standards
- **Subnet Support**: C-Chain (EVM-compatible) focus with subnet information

## Files Created

1. **`shared/crypto/clients/avax.py`** - Main Avalanche wallet class
2. **`avax_wallet_test.py`** - Test script for the wallet functionality
3. **`avax_wallet_example.py`** - Usage examples and patterns
4. **`AVALANCHE_WALLET_README.md`** - This documentation

## Quick Start

### 1. Set up Environment Variables

```bash
export ALCHEMY_AVALANCHE_API_KEY="your-alchemy-avalanche-api-key"
export APP_SECRET="your-app-secret-key"
export AVAX_MNEMONIC="your-avalanche-mnemonic-phrase"
```

### 2. Basic Usage

```python
from shared.crypto.clients.avax import AVAXWallet, AvalancheConfig
from sqlalchemy.orm import Session

# Create configuration
api_key = "your-alchemy-avalanche-api-key"
avax_config = AvalancheConfig.testnet(api_key)  # or .mainnet()

# Create wallet instance
avax_wallet = AVAXWallet(
    user_id=12345,
    config=avax_config,
    session=database_session,
    logger=logger
)

# Create wallet in database
avax_wallet.create_wallet()

# Test connection
if avax_wallet.test_connection():
    print("✅ Connected to Avalanche API")
```

### 3. Get Account Information

```python
# Get balance
balance = avax_wallet.get_balance("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
if balance:
    print(f"Balance: {balance['balance_avax']:.6f} AVAX")

# Get account info
account_info = avax_wallet.get_account_info("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
if account_info:
    print(f"Transaction count: {account_info['transaction_count']}")
    print(f"Is contract: {account_info['is_contract']}")
```

## Configuration

### Network Options

- **Mainnet**: `AvalancheConfig.mainnet(api_key)`
- **Testnet**: `AvalancheConfig.testnet(api_key)`

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ALCHEMY_AVALANCHE_API_KEY` | Your Alchemy Avalanche API key | Yes |
| `APP_SECRET` | Secret for encrypting private keys | Yes |
| `AVAX_MNEMONIC` | Mnemonic phrase for HD wallet | Yes |

## API Methods

### Wallet Management

- `create_wallet()` - Create new wallet account in database
- `create_address()` - Generate new Avalanche address
- `encrypt_private_key()` - Encrypt private key
- `decrypt_private_key()` - Decrypt private key

### Blockchain Operations

- `test_connection()` - Test Avalanche API connection
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

### Avalanche-Specific Methods

- `get_token_balance()` - Get ERC-20 token balance
- `get_avalanche_specific_info()` - Get Avalanche-specific information
- `get_subnet_info()` - Get subnet information
- `validate_address()` - Validate Avalanche address format
- `get_account_info()` - Get comprehensive account information
- `get_blockchain_info()` - Get blockchain status
- `get_network_info()` - Get network information

## Database Integration

The wallet integrates with the existing database models:

- **Account**: Stores wallet account information
- **CryptoAddress**: Stores Avalanche addresses and encrypted private keys

### Database Schema

```python
# Account record
crypto_account = Account(
    user_id=user_id,
    balance=0,
    locked_amount=0,
    currency="AVAX",
    account_type=AccountType.CRYPTO,
    account_number=account_number,
    label="AVAX Wallet"
)

# CryptoAddress record
crypto_address = CryptoAddress(
    account_id=account_id,
    address=user_address,
    label="AVAX Wallet",
    is_active=True,
    currency_code="AVAX",
    address_type="hd_wallet",
    private_key=encrypted_private_key,
    public_key=pub_key
)
```

## Avalanche Network Features

### Network Characteristics

- **Chain ID**: 43114 (mainnet), 43113 (testnet)
- **Consensus**: Proof of Stake
- **Block Time**: ~2 seconds
- **Finality**: ~3 seconds
- **Gas Limit**: 8,000,000
- **Subnet**: C-Chain (EVM-compatible)

### Avalanche-Specific Information

```python
avax_info = avax_wallet.get_avalanche_specific_info()
print(f"Network: {avax_info['network']}")
print(f"Chain ID: {avax_info['chain_id']}")
print(f"Consensus: {avax_info['consensus']}")
print(f"Subnet: {avax_info['subnet']}")
print(f"Native Token: {avax_info['native_token']}")
```

## Subnet Information

### C-Chain Details

```python
subnet_info = avax_wallet.get_subnet_info()
print(f"Subnet: {subnet_info['subnet']}")
print(f"Description: {subnet_info['description']}")
print(f"Block Time: {subnet_info['block_time']}")
print(f"Finality: {subnet_info['finality']}")
```

## Token Support

### ERC-20 Token Balance

```python
# Get token balance
token_balance = avax_wallet.get_token_balance(
    token_address="0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",  # USDC
    wallet_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
)

if token_balance:
    print(f"Token balance: {token_balance['balance']}")
```

### Common Tokens on Avalanche

- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` (Mainnet)
- **USDT**: `0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7` (Mainnet)
- **WETH**: `0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB` (Mainnet)

## Security Features

### Private Key Encryption

Private keys are encrypted using the `APP_SECRET` environment variable:

```python
# Encryption
encrypted_key = avax_wallet.encrypt_private_key(private_key)

# Decryption
decrypted_key = avax_wallet.decrypt_private_key(encrypted_key)
```

### Address Validation

Built-in Avalanche address validation (same as Ethereum):

```python
is_valid = avax_wallet.validate_address("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
```

## Error Handling

The wallet includes comprehensive error handling:

- Connection failures
- Invalid API responses
- Database errors
- Encryption/decryption errors
- Avalanche-specific errors

All errors are logged and can be handled by the calling application.

## Testing

Run the test script to verify functionality:

```bash
python avax_wallet_test.py
```

Run the example script to see usage patterns:

```bash
python avax_wallet_example.py
```

## Dependencies

- `requests` - HTTP client for API calls
- `cryptography` - For private key encryption
- `hdwallet` - For HD wallet functionality
- `eth_utils` - For Ethereum utilities
- `pydantic` - For configuration models

## Comparison with Other Wallets

| Feature | BTC Wallet | ETH Wallet | Base Wallet | AVAX Wallet |
|---------|------------|------------|-------------|-------------|
| API Provider | Bitcoin RPC | Alchemy API | Alchemy API | Alchemy API |
| HD Wallet | ✅ | ✅ | ✅ | ✅ |
| Private Key Encryption | ✅ | ✅ | ✅ | ✅ |
| Database Integration | ✅ | ✅ | ✅ | ✅ |
| Multiple Networks | ✅ | ✅ | ✅ | ✅ |
| Address Validation | ✅ | ✅ | ✅ | ✅ |
| Balance Checking | ✅ | ✅ | ✅ | ✅ |
| Transaction Monitoring | ✅ | ✅ | ✅ | ✅ |
| Gas Estimation | ❌ | ✅ | ✅ | ✅ |
| Contract Interaction | ❌ | ✅ | ✅ | ✅ |
| Token Support | ❌ | ❌ | ✅ | ✅ |
| L2 Network | ❌ | ❌ | ✅ | ❌ |
| High Performance | ❌ | ❌ | ❌ | ✅ |
| Subnet Support | ❌ | ❌ | ❌ | ✅ |

## Migration from avalanche_client.py

The new `AVAXWallet` class consolidates the functionality from `avalanche_client.py`:

- **AvalancheClient** → **AVAXWallet** (with database integration)
- **AvalancheWebSocketClient** → Can be added as WebSocket support
- **Configuration** → **AvalancheConfig** class
- **API Methods** → Integrated into **AVAXWallet** class

## Avalanche Advantages

### Performance Benefits

- **Fast Finality**: ~3 seconds vs ~12 minutes on Ethereum
- **High Throughput**: 4,500+ TPS
- **Low Gas Fees**: Significantly lower than Ethereum
- **Ethereum Security**: Inherits Ethereum's security model
- **EVM Compatibility**: Full Ethereum tooling support

### Developer Benefits

- **Ethereum Compatibility**: Same tools and standards
- **Smart Contracts**: Full EVM compatibility
- **Token Standards**: ERC-20, ERC-721, etc.
- **Existing Infrastructure**: Works with existing Ethereum tooling
- **Multiple Subnets**: C-Chain, X-Chain, P-Chain

## Subnet Architecture

### Avalanche Subnets

- **C-Chain**: EVM-compatible smart contract platform
- **X-Chain**: Exchange chain for asset transfers
- **P-Chain**: Platform chain for subnet management

### C-Chain Focus

The wallet focuses on the C-Chain (Contract Chain) which provides:

- EVM compatibility
- Smart contract support
- ERC-20 token support
- Fast finality
- Low gas fees

## Future Enhancements

- WebSocket support for real-time updates
- Transaction signing and broadcasting
- Smart contract interaction
- NFT support (ERC-721, ERC-1155)
- Multi-signature wallet support
- Cross-subnet transfers
- DeFi protocol integration
- Subnet-specific features 