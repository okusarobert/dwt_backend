# Solana Webhook Implementation

This document describes the implementation of Solana address activity webhooks using Alchemy's Notify API v2.

## Overview

Based on [Alchemy's Notify v2 documentation](https://www.alchemy.com/docs/building-a-dapp-with-real-time-transaction-notifications), this implementation provides real-time transaction notifications for Solana addresses through webhooks.

## Architecture

```
Alchemy Notify API → Webhook → Our Server → Database/Processing
```

### Components

1. **Alchemy Notify API**: Monitors Solana addresses for activity
2. **Webhook Endpoint**: `/api/v1/wallet/sol/callbacks/address-webhook`
3. **Signature Verification**: HMAC-SHA256 with multiple fallback methods
4. **Transaction Processing**: Creates database records and reservations

## Configuration

### Environment Variables

```bash
# Required for webhook verification
ALCHEMY_AUTH_KEY=your_auth_key_from_dashboard
ALCHEMY_WEBHOOK_ID=wh_your_webhook_id

# Optional: Bypass signature verification for testing
BYPASS_SIGNATURE_VERIFICATION=false

# Optional: Disable signature verification entirely
VERIFY_ALCHEMY_SIGNATURE=true
```

### Alchemy Dashboard Setup

1. **Create Webhook**:
   - Go to Alchemy Dashboard → Notify
   - Select "Address Activity" 
   - Click "Create Webhook"
   - Enter webhook URL: `https://yourdomain.com/api/v1/wallet/sol/callbacks/address-webhook`
   - Select Solana network (mainnet/testnet)
   - Add test addresses

2. **Get Credentials**:
   - **Auth Key**: Found on top right of notify page (used for signature verification)
   - **Webhook ID**: Found in webhook panel (used for additional validation)

## Webhook Signature Verification

The implementation uses Alchemy's Auth Key for signature verification:

### Auth Key Verification
```python
hmac.new(auth_key.encode('utf-8'), request_body, hashlib.sha256).hexdigest()
```

This is the **official method** recommended by Alchemy for webhook signature verification.

## Webhook Request Format

### Signature Header
Alchemy sends signatures in timestamped format:
```
X-Alchemy-Signature: t=1234567890,v1=signature_hash
```

### Request Body
```json
{
  "webhookId": "wh_your_webhook_id",
  "type": "ADDRESS_ACTIVITY",
  "event": {
    "activity": [
      {
        "hash": "transaction_hash",
        "fromAddress": "sender_address",
        "toAddress": "recipient_address", 
        "value": 1000000,
        "blockNumber": 12345,
        "timestamp": 1234567890
      }
    ]
  }
}
```

## API Endpoints

### Webhook Endpoint
```
POST /api/v1/wallet/sol/callbacks/address-webhook
```

**Headers:**
- `Content-Type: application/json`
- `X-Alchemy-Signature: t=timestamp,v1=signature`

**Response:**
```json
{
  "status": "success",
  "type": "ADDRESS_ACTIVITY"
}
```

### Webhook Management Endpoints

#### Register Address with Webhook
```
POST /api/v1/wallet/sol/register-webhook
```

#### Register All Addresses
```
POST /api/v1/wallet/sol/register-all-webhooks
```

#### Unregister Address
```
POST /api/v1/wallet/sol/unregister-webhook
```

## Database Integration

### Transaction Records
- Creates `Transaction` records for each activity
- Tracks confirmations and status
- Stores metadata (block number, gas, etc.)

### Reservations
- Creates `Reservation` records to lock amounts
- Prevents double-spending during processing
- Releases reservations after confirmation

### Account Updates
- Updates account balances in smallest units
- Tracks locked amounts for withdrawals
- Maintains precision for crypto amounts

## Error Handling

### Signature Verification Failures
- Logs detailed verification attempts
- Returns 401 for invalid signatures
- Supports bypass mode for testing

### Database Errors
- Handles duplicate transaction prevention
- Uses unique constraints for data integrity
- Implements proper rollback on errors

### Network Errors
- Graceful handling of malformed requests
- Timeout protection for external calls
- Retry logic for transient failures

## Testing

### Manual Testing
```bash
# Test with valid signature
curl -X POST http://localhost:3030/api/v1/wallet/sol/callbacks/address-webhook \
  -H "Content-Type: application/json" \
  -H "X-Alchemy-Signature: t=1234567890,v1=calculated_signature" \
  -d '{"webhookId": "wh_test", "type": "ADDRESS_ACTIVITY", "event": {"activity": [{"hash": "test_hash", "fromAddress": "test_from", "toAddress": "test_to", "value": 1000000}]}}'

# Test with bypass mode
BYPASS_SIGNATURE_VERIFICATION=true
```

### Automated Testing
```bash
# Run webhook registration tests
python test_solana_webhook_registration.py

# Run complete system tests
python test_complete_system.py
```

## Monitoring

### Logs
- Signature verification attempts
- Webhook processing status
- Database operation results
- Error details with stack traces

### Metrics
- Webhook request count
- Signature verification success rate
- Transaction processing time
- Error rates by type

## Security Considerations

### Signature Verification
- Uses `hmac.compare_digest()` for timing attack protection
- Multiple verification methods for compatibility
- Configurable bypass for testing only

### Webhook ID Verification
- Validates webhook ID in request body
- Prevents unauthorized webhook processing
- Logs verification attempts

### Rate Limiting
- Consider implementing rate limiting
- Monitor for abuse patterns
- Set appropriate timeouts

## Troubleshooting

### Common Issues

1. **Signature Verification Fails**
   - Check webhook key configuration
   - Verify signature format parsing
   - Enable bypass mode for testing

2. **Webhook Not Received**
   - Verify endpoint URL in Alchemy dashboard
   - Check network connectivity
   - Review server logs for errors

3. **Database Errors**
   - Check unique constraints
   - Verify account existence
   - Review transaction status

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG

# Bypass signature verification
export BYPASS_SIGNATURE_VERIFICATION=true
```

## Best Practices

1. **Always verify signatures** in production
2. **Use HTTPS** for webhook endpoints
3. **Implement idempotency** for webhook processing
4. **Monitor webhook health** regularly
5. **Test with real Alchemy webhooks** before production
6. **Keep webhook keys secure** and rotate regularly

## References

- [Alchemy Notify v2 Documentation](https://www.alchemy.com/docs/building-a-dapp-with-real-time-transaction-notifications)
- [Alchemy Webhook Security](https://www.alchemy.com/docs/reference/webhooks-overview)
- [Solana RPC API](https://docs.solana.com/developing/clients/json-rpc-api)
