# Crypto Account Credit/Debit Script

This script allows you to credit or debit crypto accounts with precision using the new smallest unit system.

## Features

- **Precision Handling**: Uses smallest units (wei, satoshis, etc.) for accurate calculations
- **Multiple Currencies**: Supports ETH, BTC, SOL, XRP, XLM, TRX, BNB, OPTIMISM, POLYGON, AVAX, WORLD
- **Account Management**: List accounts, show details, credit, and debit operations
- **Transaction Records**: Creates proper transaction records for all operations
- **Balance Validation**: Checks available balance before debiting

## Usage

### List All Crypto Accounts
```bash
python wallet/credit_crypto_account.py --list
```

### Show Account Details
```bash
python wallet/credit_crypto_account.py --show 1
```

### Credit an Account (by Account ID)
```bash
python wallet/credit_crypto_account.py --credit 1 --amount 0.5 --currency ETH --description "Test credit"
```

### Credit an Account (by User ID and Currency)
```bash
python wallet/credit_crypto_account.py --credit 1 --amount 0.1 --currency ETH --user 123 --description "User credit"
```

### Debit an Account (by Account ID)
```bash
python wallet/credit_crypto_account.py --debit 1 --amount 0.1 --currency ETH --description "Test debit"
```

### Debit an Account (by User ID and Currency)
```bash
python wallet/credit_crypto_account.py --debit 1 --amount 0.05 --currency ETH --user 123 --description "User debit"
```

## Examples

### Credit 1 ETH to Account ID 1
```bash
python wallet/credit_crypto_account.py --credit 1 --amount 1.0 --currency ETH --description "Initial funding"
```

### Credit 0.001 BTC to User 456's BTC Account
```bash
python wallet/credit_crypto_account.py --credit 1 --amount 0.001 --currency BTC --user 456 --description "BTC funding"
```

### Debit 0.1 ETH from Account ID 2
```bash
python wallet/credit_crypto_account.py --debit 2 --amount 0.1 --currency ETH --description "Withdrawal"
```

### List All Crypto Accounts
```bash
python wallet/credit_crypto_account.py --list
```

## Supported Currencies

- **ETH** (Ethereum) - Wei
- **BTC** (Bitcoin) - Satoshis
- **SOL** (Solana) - Lamports
- **XRP** (Ripple) - Drops
- **XLM** (Stellar) - Stroops
- **TRX** (Tron) - Sun
- **BNB** (Binance Coin) - Wei
- **OPTIMISM** (Optimism) - Wei
- **POLYGON** (Polygon) - Wei
- **AVAX** (Avalanche) - nAVAX
- **WORLD** (World Chain) - Wei

## Precision Examples

### ETH Precision
- 1 ETH = 1,000,000,000,000,000,000 wei
- 0.000000000000000001 ETH = 1 wei

### BTC Precision
- 1 BTC = 100,000,000 satoshis
- 0.00000001 BTC = 1 satoshi

### SOL Precision
- 1 SOL = 1,000,000,000 lamports
- 0.000000001 SOL = 1 lamport

## Output Examples

### Credit Operation
```
✅ Successfully credited account 1
   User: 123
   Currency: ETH
   Amount: 0.5 ETH
   Previous Balance: 0.0 ETH
   New Balance: 0.5 ETH
   Transaction ID: 456
```

### Debit Operation
```
✅ Successfully debited account 1
   User: 123
   Currency: ETH
   Amount: 0.1 ETH
   Previous Balance: 0.5 ETH
   New Balance: 0.4 ETH
   Transaction ID: 457
```

### Account Listing
```
📋 Crypto Accounts:
--------------------------------------------------------------------------------
ID    User ID  Currency   Balance         Locked          Available
--------------------------------------------------------------------------------
1     123      ETH        0.50000000      0.00000000      0.50000000
2     456      BTC        0.00100000      0.00000000      0.00100000
3     789      SOL        1.00000000      0.00000000      1.00000000
--------------------------------------------------------------------------------
```

## Error Handling

### Insufficient Balance
```
❌ Insufficient available balance
   Available: 0.1 ETH
   Requested: 0.5 ETH
```

### Invalid Currency
```
❌ Unsupported currency: XYZ
   Supported currencies: ETH, BTC, SOL, XRP, XLM, TRX, BNB, OPTIMISM, POLYGON, AVAX, WORLD
```

### Account Not Found
```
❌ Account 999 not found
```

## Database Integration

The script integrates with the existing database models:

- **Account Model**: Updates `crypto_balance_smallest_unit` and `crypto_locked_amount_smallest_unit`
- **Transaction Model**: Creates transaction records with proper metadata
- **Precision System**: Uses `CryptoPrecisionManager` for conversions

## Safety Features

- **Transaction Rollback**: Automatic rollback on errors
- **Balance Validation**: Checks available balance before debiting
- **Currency Validation**: Ensures account currency matches operation
- **Precision Maintenance**: All calculations use smallest units
- **Metadata Tracking**: Stores operation details in transaction metadata

## Running in Docker

To run the script inside the wallet container:

```bash
docker exec -it dwt_backend-wallet-1 python /app/credit_crypto_account.py --list
```

```bash
docker exec -it dwt_backend-wallet-1 python /app/credit_crypto_account.py --credit 1 --amount 0.5 --currency ETH
``` 