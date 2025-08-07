# Solana Wallet Class

A comprehensive Solana (SOL) wallet implementation using the official Solana Python SDK and Alchemy API, similar to the existing BTC, ETH, Base, and AVAX wallet classes.

## Features

- **Official Solana SDK**: Uses the official `solana` and `solders` Python libraries
- **Alchemy API Integration**: Leverages Alchemy's API for Solana blockchain interactions
- **Database Integration**: Stores wallet and address information in the database
- **Private Key Encryption**: Encrypts private keys using APP_SECRET
- **High Performance**: Optimized for Solana's high throughput and fast finality
- **SPL Token Support**: Built-in SPL token balance checking and management
- **Keypair Generation**: Uses Solana's native Keypair for address generation
- **Slot-based Architecture**: Leverages Solana's slot-based consensus mechanism

## Files Created

1. **`shared/crypto/clients/sol.py`** - Main Solana wallet class
2. **`sol_wallet_test.py`** - Test script for the wallet functionality
3. **`sol_wallet_example.py`** - Usage examples and patterns
4. **`SOLANA_WALLET_README.md`** - This documentation

## Quick Start

### 1. Install Dependencies

```bash
pip install solana solders
```

### 2. Set up Environment Variables

```bash
export ALCHEMY_SOLANA_API_KEY="your-alchemy-solana-api-key"
export APP_SECRET="your-app-secret-key"
```

### 3. Basic Usage

```python
from shared.crypto.clients.sol import SOLWallet, SolanaConfig
from sqlalchemy.orm import Session

# Create configuration
api_key = "your-alchemy-solana-api-key"
sol_config = SolanaConfig.testnet(api_key)  # or .mainnet()

# Create wallet instance
sol_wallet = SOLWallet(
    user_id=12345,
    config=sol_config,
    session=database_session,
    logger=logger
)

# Create wallet in database
sol_wallet.create_wallet()

# Test connection
if sol_wallet.test_connection():
    print("✅ Connected to Solana API")
```

### 4. Get Account Information

```python
# Get balance
balance = sol_wallet.get_balance("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM")
if balance:
    print(f"Balance: {balance['sol_balance']:.9f} SOL")

# Get account info
account_info = sol_wallet.get_account_info("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM")
if account_info:
    print(f"Owner: {account_info['owner']}")
    print(f"Executable: {account_info['executable']}")
```

## Configuration

### Network Options

- **Mainnet**: `SolanaConfig.mainnet(api_key)`
- **Devnet**: `SolanaConfig.testnet(api_key)`

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ALCHEMY_SOLANA_API_KEY` | Your Alchemy Solana API key | Yes |
| `APP_SECRET` | Secret for encrypting private keys | Yes |

## API Methods

### Wallet Management

- `create_wallet()` - Create new wallet account in database
- `create_address()` - Generate new Solana address using Keypair
- `encrypt_private_key()` - Encrypt private key
- `decrypt_private_key()` - Decrypt private key

### Blockchain Operations

- `test_connection()` - Test Solana API connection
- `get_latest_slot()` - Get latest slot number
- `get_balance()` - Get account balance in lamports and SOL
- `get_account_info()` - Get comprehensive account information
- `get_token_accounts()` - Get SPL token accounts for an address
- `get_recent_blocks()` - Get recent blocks information
- `get_block_by_slot()` - Get block information by slot
- `get_block_by_signature()` - Get block information by signature
- `get_signature_status()` - Get transaction signature status
- `get_transaction()` - Get transaction details
- `get_transaction_count()` - Get transaction count for an address
- `get_supply()` - Get current supply information
- `get_version()` - Get Solana version information
- `get_cluster_nodes()` - Get cluster nodes information
- `get_leader_schedule()` - Get leader schedule

### Solana-Specific Methods

- `get_token_balance()` - Get SPL token balance for a specific token
- `get_solana_specific_info()` - Get Solana-specific information
- `get_network_info()` - Get network information
- `validate_address()` - Validate Solana address format
- `get_account_info_comprehensive()` - Get comprehensive account information
- `get_blockchain_info()` - Get blockchain status
- `get_solana_features()` - Get Solana-specific features
- `get_spl_token_info()` - Get SPL token information

## Database Integration

The wallet integrates with the existing database models:

- **Account**: Stores wallet account information
- **CryptoAddress**: Stores Solana addresses and encrypted private keys

### Database Schema

```python
# Account record
crypto_account = Account(
    user_id=user_id,
    balance=0,
    locked_amount=0,
    currency="SOL",
    account_type=AccountType.CRYPTO,
    account_number=account_number,
    label="SOL Wallet"
)

# CryptoAddress record
crypto_address = CryptoAddress(
    account_id=account_id,
    address=str(public_key),
    label="SOL Wallet",
    is_active=True,
    currency_code="SOL",
    address_type="keypair",
    private_key=encrypted_private_key,
    public_key=str(public_key)
)
```

## Solana Network Features

### Network Characteristics

- **Consensus**: Proof of Stake
- **Block Time**: ~400ms
- **Finality**: ~400ms
- **Throughput**: 65,000+ TPS
- **Native Token**: SOL
- **Address Format**: Base58 encoded (44 characters)

### Solana-Specific Information

```python
sol_info = sol_wallet.get_solana_specific_info()
print(f"Network: {sol_info['network']}")
print(f"Latest slot: {sol_info['latest_slot']}")
print(f"Consensus: {sol_info['consensus']}")
print(f"Block Time: {sol_info['block_time']}")
print(f"Finality: {sol_info['finality']}")
print(f"Native Token: {sol_info['native_token']}")
```

## SPL Token Support

### SPL Token Balance

```python
# Get token balance
token_balance = sol_wallet.get_token_balance(
    token_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    wallet_address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
)

if token_balance:
    print(f"Token balance: {token_balance['amount']}")
```

### Common SPL Tokens on Solana

- **USDC**: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` (Mainnet)
- **USDT**: `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` (Mainnet)
- **RAY**: `4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R` (Mainnet)
- **SRM**: `SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt` (Mainnet)

### SPL Token Information

```python
token_info = sol_wallet.get_spl_token_info("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
if token_info:
    print(f"Mint: {token_info['mint']}")
    print(f"Decimals: {token_info['decimals']}")
    print(f"Supply: {token_info['supply']}")
    print(f"Is Initialized: {token_info['is_initialized']}")
```

## Security Features

### Private Key Encryption

Private keys are encrypted using the `APP_SECRET` environment variable:

```python
# Encryption
encrypted_key = sol_wallet.encrypt_private_key(private_key)

# Decryption
decrypted_key = sol_wallet.decrypt_private_key(encrypted_key)
```

### Address Validation

Built-in Solana address validation using the official SDK:

```python
is_valid = sol_wallet.validate_address("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM")
```

## Error Handling

The wallet includes comprehensive error handling:

- Connection failures
- Invalid API responses
- Database errors
- Encryption/decryption errors
- Solana-specific errors
- SDK availability checks

All errors are logged and can be handled by the calling application.

## Testing

Run the test script to verify functionality:

```bash
python sol_wallet_test.py
```

Run the example script to see usage patterns:

```bash
python sol_wallet_example.py
```

## Dependencies

- `solana` - Official Solana Python SDK
- `solders` - Solana data structures
- `requests` - HTTP client for API calls
- `cryptography` - For private key encryption
- `base58` - For Base58 encoding/decoding
- `pydantic` - For configuration models

## Comparison with Other Wallets

| Feature | BTC Wallet | ETH Wallet | Base Wallet | AVAX Wallet | SOL Wallet |
|---------|------------|------------|-------------|-------------|------------|
| API Provider | Bitcoin RPC | Alchemy API | Alchemy API | Alchemy API | Alchemy API |
| SDK | ❌ | ❌ | ❌ | ❌ | ✅ (Official) |
| HD Wallet | ✅ | ✅ | ✅ | ✅ | ❌ (Keypair) |
| Private Key Encryption | ✅ | ✅ | ✅ | ✅ | ✅ |
| Database Integration | ✅ | ✅ | ✅ | ✅ | ✅ |
| Multiple Networks | ✅ | ✅ | ✅ | ✅ | ✅ |
| Address Validation | ✅ | ✅ | ✅ | ✅ | ✅ |
| Balance Checking | ✅ | ✅ | ✅ | ✅ | ✅ |
| Transaction Monitoring | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gas Estimation | ❌ | ✅ | ✅ | ✅ | ❌ |
| Contract Interaction | ❌ | ✅ | ✅ | ✅ | ✅ |
| Token Support | ❌ | ❌ | ✅ | ✅ | ✅ |
| L2 Network | ❌ | ❌ | ✅ | ❌ | ❌ |
| High Performance | ❌ | ❌ | ❌ | ✅ | ✅ |
| Slot-based | ❌ | ❌ | ❌ | ❌ | ✅ |
| SPL Tokens | ❌ | ❌ | ❌ | ❌ | ✅ |

## Migration from solana_client.py

The new `SOLWallet` class consolidates the functionality from `solana_client.py`:

- **SolanaClient** → **SOLWallet** (with database integration)
- **SolanaWebSocketClient** → Can be added as WebSocket support
- **Configuration** → **SolanaConfig** class
- **API Methods** → Integrated into **SOLWallet** class
- **Official SDK** → Added Solana SDK integration

## Solana Advantages

### Performance Benefits

- **High Throughput**: 65,000+ TPS
- **Fast Finality**: ~400ms
- **Low Fees**: Significantly lower than Ethereum
- **Parallel Processing**: Multiple transactions processed simultaneously
- **Slot-based Consensus**: Efficient slot-based validation

### Developer Benefits

- **Official SDK**: Full Python SDK support
- **SPL Tokens**: Native token standard
- **Programs**: Smart contracts (Rust)
- **Cross-Program Invocation**: Inter-program communication
- **Comprehensive Tooling**: Rich ecosystem of tools

## Solana Architecture

### Key Concepts

- **Slots**: Time units for consensus (400ms each)
- **Epochs**: Groups of slots (432,000 slots per epoch)
- **Validators**: Network participants
- **Programs**: Smart contracts (Rust)
- **SPL Tokens**: Token standard
- **Keypairs**: Public/private key pairs

### Account Model

- **System Accounts**: Owned by System Program
- **Program Accounts**: Owned by specific programs
- **Token Accounts**: Owned by Token Program
- **Data Accounts**: Store program data

## Future Enhancements

- WebSocket support for real-time updates
- Transaction signing and broadcasting
- Program interaction (smart contracts)
- NFT support (Metaplex)
- Multi-signature wallet support
- Cross-chain bridges
- DeFi protocol integration
- Solana Program deployment
- Stake management
- Validator information 