# Solana Webhook Implementation

This document describes the Solana webhook implementation for processing Alchemy webhook events.

## Overview

The Solana webhook implementation follows the same architecture as the existing BlockCypher webhook:

1. **API Service** - Acts as a proxy endpoint
2. **Wallet Service** - Handles the actual webhook processing and database operations

## Architecture Flow

```
Alchemy → API Service → Wallet Service → Database
```

### 1. API Service (Proxy)
- **Endpoint**: `/api/v1/wallet/sol/callbacks/address-webhook`
- **Role**: Receives webhook requests and forwards them to the wallet service
- **File**: `api/app.py` (proxy endpoint)

### 2. Wallet Service (Processor)
- **Endpoint**: `/sol/callbacks/address-webhook`
- **Role**: Processes webhook events and updates database
- **File**: `wallet/solana_webhook.py`

## Features

### ✅ Signature Verification
- HMAC-SHA256 signature verification using Alchemy's webhook key
- Configurable verification (can be disabled for testing)
- Uses `X-Alchemy-Signature` header

### ✅ Event Handling
- **`ADDRESS_ACTIVITY`** - Processes address activity notifications
  - Creates transaction records for monitored addresses
  - Handles both incoming (DEPOSIT) and outgoing (WITHDRAWAL) transactions
  - Creates reservations for incoming transactions to lock amounts
  - Updates account balances and locked amounts

### ✅ Database Integration
- Creates/updates `Transaction` records with proper status tracking
- Links transactions to `CryptoAddress` records
- Creates `Reservation` records for amount locking/unlocking
- Updates `Account.crypto_balance_smallest_unit` and `Account.crypto_locked_amount_smallest_unit`
- Stores metadata in `metadata_json` field
- Handles transaction confirmations and status updates

## Configuration

### Environment Variables
```bash
VERIFY_ALCHEMY_SIGNATURE=true  # Enable/disable signature verification
ALCHEMY_WEBHOOK_KEY=your_webhook_key  # Alchemy webhook signing key
```

### Webhook URL Configuration
The webhook URL should be configured in Alchemy to point to:
```
https://your-domain.com/api/v1/wallet/sol/callbacks/address-webhook
```

## Webhook Payload Format

### Address Activity Event
```json
{
  "webhook_id": "string",
  "id": 1,
  "created_at": "2024-01-01T00:00:00.000Z",
  "type": "ADDRESS_ACTIVITY",
  "event": {
    "activity": [
      {
        "fromAddress": "string",
        "toAddress": "string",
        "blockNum": "string",
        "hash": "string",
        "category": "external",
        "value": 0.001,
        "asset": "SOL",
        "erc721TokenId": null,
        "erc1155Metadata": null,
        "tokenId": null,
        "rawContract": {
          "value": "string",
          "address": "string",
          "decimal": "string"
        }
      }
    ]
  }
}
```

## Implementation Details

### Transaction Processing
1. **Incoming Transactions (DEPOSIT)**:
   - Creates `Transaction` record with `AWAITING_CONFIRMATION` status
   - Creates `Reservation` to lock the amount
   - Updates `Account.crypto_locked_amount_smallest_unit`

2. **Outgoing Transactions (WITHDRAWAL)**:
   - Creates `Transaction` record with `AWAITING_CONFIRMATION` status
   - No reservation needed (amount already deducted during withdrawal)

### Duplicate Prevention
- Uses unique constraint on `(blockchain_txid, address, type)`
- Checks for existing transactions before processing
- Prevents duplicate transaction processing

### Error Handling
- Comprehensive error handling with rollback on failures
- Logs all webhook events and errors
- Returns appropriate HTTP status codes

## Testing

### Test Script
Run the test script to verify the implementation:
```bash
python3 test_solana_webhook.py
```

### Test Cases
1. **Health Check** - Verifies webhook endpoint is accessible
2. **Address Activity Webhook** - Tests processing of address activity events
3. **No Signature Test** - Verifies rejection of unsigned requests
4. **Invalid Signature Test** - Verifies rejection of incorrectly signed requests

## Setup Instructions

### 1. Environment Configuration
```bash
# Add to your environment variables
export VERIFY_ALCHEMY_SIGNATURE=true
export ALCHEMY_WEBHOOK_KEY=your_alchemy_webhook_key
```

### 2. Database Setup
Ensure you have Solana addresses in the `crypto_addresses` table:
```sql
INSERT INTO crypto_addresses (account_id, address, currency_code, is_active)
VALUES (1, 'your_solana_address', 'SOL', true);
```

### 3. Alchemy Webhook Configuration
1. Go to Alchemy Dashboard
2. Navigate to Webhooks section
3. Create a new webhook for "Address Activity"
4. Set the URL to your API endpoint
5. Configure the webhook key for signature verification

### 4. Service Deployment
```bash
# Start the services
docker-compose up -d api wallet

# Check service health
curl http://localhost:3001/health
curl http://localhost:3000/sol/callbacks/health
```

## Monitoring

### Logs
Monitor the wallet service logs for webhook processing:
```bash
docker-compose logs -f wallet
```

### Database Queries
Check for processed transactions:
```sql
SELECT * FROM transactions WHERE currency_code = 'SOL' ORDER BY created_at DESC LIMIT 10;
```

Check reservations:
```sql
SELECT * FROM reservations WHERE currency_code = 'SOL' ORDER BY created_at DESC LIMIT 10;
```

## Troubleshooting

### Common Issues

1. **Webhook not received**:
   - Check if services are running
   - Verify webhook URL configuration in Alchemy
   - Check firewall/network connectivity

2. **Signature verification fails**:
   - Verify `ALCHEMY_WEBHOOK_KEY` environment variable
   - Check webhook key configuration in Alchemy dashboard

3. **Transactions not processed**:
   - Verify Solana addresses exist in database
   - Check logs for error messages
   - Verify webhook payload format

4. **Database errors**:
   - Check database connectivity
   - Verify table schema matches expected structure
   - Check for unique constraint violations

### Debug Mode
To enable debug logging, set the log level:
```python
import logging
logging.getLogger('wallet_service').setLevel(logging.DEBUG)
```

## Security Considerations

1. **Signature Verification**: Always verify webhook signatures in production
2. **HTTPS**: Use HTTPS for all webhook endpoints
3. **Rate Limiting**: Consider implementing rate limiting for webhook endpoints
4. **Input Validation**: Validate all webhook payload data
5. **Error Handling**: Don't expose sensitive information in error responses

## Future Enhancements

1. **Additional Event Types**: Support for `DROPPED_TRANSACTION` and `MINED_TRANSACTION` events
2. **SPL Token Support**: Handle SPL token transfers
3. **Batch Processing**: Process multiple activities in a single webhook
4. **Retry Logic**: Implement retry mechanism for failed webhook processing
5. **Metrics**: Add monitoring and metrics for webhook processing

