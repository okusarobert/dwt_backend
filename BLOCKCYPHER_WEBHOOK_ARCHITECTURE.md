# BlockCypher Webhook Architecture

## Overview

The BlockCypher webhook implementation follows a proxy architecture where:

1. **API Service** - Acts as a proxy endpoint
2. **Wallet Service** - Handles the actual webhook processing and database operations

## Architecture Flow

```
BlockCypher → API Service → Wallet Service → Database
```

### 1. API Service (Proxy)
- **Endpoint**: `/api/v1/wallet/btc/callbacks/address-webhook`
- **Role**: Receives webhook requests and forwards them to the wallet service
- **File**: `api/app.py` (proxy endpoint)

### 2. Wallet Service (Processor)
- **Endpoint**: `/btc/callbacks/address-webhook`
- **Role**: Processes webhook events and updates database
- **File**: `wallet/blockcypher_webhook.py`

## Features

### ✅ Signature Verification
- ECDSA signature verification using BlockCypher's public key
- SHA256 hashing of request body
- Configurable verification (can be disabled for testing)

### ✅ Event Handling
- **`unconfirmed-tx`** - Creates new transaction records with `AWAITING_CONFIRMATION` status
- **`confirmed-tx`** - Locks amount in account and creates reservation
- **`tx-confirmation`** - Credits wallet after 2 confirmations and releases reservation
- **`tx-confidence`** - Updates confidence score in metadata
- **`double-spend-tx`** - Fails transaction, removes locked amount, and creates failed reservation

### ✅ Database Integration
- Creates/updates `Transaction` records with proper status tracking
- Links transactions to `CryptoAddress` records
- Creates `Reservation` records for amount locking/unlocking
- Updates `Account.locked_amount` and `Account.balance`
- Stores metadata in `metadata_json` field
- Handles transaction confirmations and confidence scores
- **Webhook Management**: Stores BlockCypher webhook IDs in `CryptoAddress.webhook_ids` as JSON array

## Configuration

### Environment Variables
```bash
VERIFY_BLOCKCYPHER_SIGNATURE=true  # Enable/disable signature verification
BLOCKCYPHER_API_KEY=your_api_key   # Your BlockCypher API key
APP_HOST=http://your-domain.com     # Your app's host URL
```

### Docker Services
- **API Service**: Port 3000 (proxy)
- **Wallet Service**: Port 3000 (processor)

## Testing

### Test Script
```bash
python test_blockcypher_webhook.py
```

### Manual Testing
```bash
curl -X POST http://localhost:3000/api/v1/wallet/btc/callbacks/address-webhook \
  -H "Content-Type: application/json" \
  -H "X-BlockCypher-Signature: keyId=\"test\",algorithm=\"sha256-ecdsa\",signature=\"test\"" \
  -d '{
    "event": "unconfirmed-tx",
    "hash": "test_hash_123",
    "address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
    "confirmations": 0
  }'
```

## Transaction Flow

### 🔄 Complete Flow
1. **Unconfirmed Transaction** → Creates transaction with `AWAITING_CONFIRMATION` status
2. **First Confirmation** → Locks amount in account, creates reservation
3. **Second Confirmation** → Credits wallet, releases reservation, updates status to `COMPLETED`
4. **Address Forwarding** → BlockCypher automatically forwards payments to master address
5. **Double Spend** → Fails transaction, removes locked amount, creates failed reservation

### 💰 Amount Management
- **Locked Amount**: Temporarily locked during confirmation period
- **Reservations**: Track amount movements with `RESERVE` and `RELEASE` types
- **Balance Updates**: Only credited after 2 confirmations for security

### 🔗 Webhook Management
- **Webhook IDs**: Stored in `CryptoAddress.webhook_ids` as JSON array
- **Automatic Creation**: Webhooks created when addresses are generated
- **Cleanup**: Inactive addresses have webhooks automatically removed
- **Management**: `WebhookManager` class for centralized webhook operations

### 🔄 Address Forwarding
- **BlockCypher Service**: Uses BlockCypher's built-in address forwarding service
- **Master Address**: Configured via `BTC_MASTER_ADDRESS` environment variable
- **Automatic Forwarding**: BlockCypher handles forwarding automatically
- **Custodial Model**: All funds consolidated to master address for security
- **No Database Storage**: Master addresses not stored in database

## Benefits

1. **Separation of Concerns** - API handles routing, wallet handles business logic
2. **Scalability** - Wallet service can be scaled independently
3. **Security** - Signature verification in wallet service
4. **Database Access** - Direct database access for transaction processing
5. **Error Handling** - Proper error handling and logging
6. **Transaction Safety** - Amount locking prevents double-spending issues
7. **Audit Trail** - Reservation records provide complete transaction history
8. **Webhook Management** - Centralized webhook ID tracking and cleanup

## File Structure

```
├── api/
│   └── app.py                    # Proxy endpoint
├── wallet/
│   ├── app.py                    # Main wallet service
│   ├── blockcypher_webhook.py   # Webhook processor
│   └── webhook_manager.py       # Webhook management utility
├── shared/crypto/
│   └── btc.py                   # BTC wallet with forwarding logic
├── db/
│   └── wallet.py                # Database models (updated with webhook_ids)
├── alembic/versions/
│   └── e2f84217a6be_add_webhook_id_to_crypto_addresses.py  # Migration
├── test_crypto_transaction_flow.py  # Test script
└── test_forwarding_setup.py     # Forwarding test script
``` 