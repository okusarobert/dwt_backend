# Ethereum Webhook Migration Guide

This guide documents the migration from polling-based Ethereum transaction monitoring to webhook-based monitoring using Alchemy webhooks.

## Overview

The new webhook-based system provides:
- **Real-time transaction detection** instead of polling every 5 minutes
- **Reduced API usage** and better rate limit compliance
- **Lower latency** for transaction processing
- **Better scalability** as the system grows
- **Consistent architecture** with Solana webhook implementation

## Architecture

### Components

1. **Ethereum Webhook Handler** (`wallet/ethereum_webhook.py`)
   - Processes incoming webhook events from Alchemy
   - Verifies webhook signatures for security
   - Handles ADDRESS_ACTIVITY events
   - Creates transaction records and accounting entries

2. **Ethereum Webhook Manager** (`wallet/ethereum_webhook_manager.py`)
   - Manages Alchemy webhook subscriptions
   - Adds/removes addresses from webhook monitoring
   - Syncs database addresses with webhook configuration

3. **Ethereum Webhook Integration** (`wallet/ethereum_webhook_integration.py`)
   - Service layer for webhook operations
   - Integrates with address creation process
   - Provides convenience functions for webhook management

4. **Webhook Monitor** (`eth_monitor/webhook_monitor.py`)
   - Replaces the polling-based monitor
   - Handles periodic sync tasks
   - Monitors webhook health and status

## Setup Instructions

### 1. Environment Variables

Add these environment variables to your `.env` file:

```bash
# Alchemy Auth Key (required for webhook management)
ALCHEMY_AUTH_KEY=your_alchemy_auth_key

# App host URL (webhook endpoint)
APP_HOST=https://your-domain.com

# Webhook credentials (generated during setup)
ALCHEMY_ETH_WEBHOOK_ID=webhook_id_here
ALCHEMY_WEBHOOK_SIGNING_KEY=signing_key_here
```

### 2. Initial Setup

Run the setup script to create and configure the webhook:

```bash
cd wallet
python setup_ethereum_webhooks.py setup
```

This will:
- Create a new Alchemy webhook for ADDRESS_ACTIVITY
- Sync all existing ETH addresses to the webhook
- Verify the webhook configuration
- Provide the webhook credentials to add to your environment

### 3. Update Environment

After running setup, add the provided webhook credentials to your environment:

```bash
ALCHEMY_ETH_WEBHOOK_ID=wh_abcd1234...
ALCHEMY_WEBHOOK_SIGNING_KEY=whsec_xyz789...
```

### 4. Restart Services

Restart your wallet service to load the new webhook endpoint:

```bash
docker-compose restart wallet
```

### 5. Start Webhook Monitor

The webhook monitor replaces the old polling monitor:

```bash
cd eth_monitor
python webhook_monitor.py
```

## Webhook Endpoint

The webhook endpoint is available at:
```
POST /api/v1/wallet/eth/callbacks/address-webhook
```

### Security

- All webhook requests are verified using HMAC-SHA256 signatures
- The signing key is provided by Alchemy during webhook creation
- Invalid signatures are rejected with 401 status

### Payload Format

Alchemy sends ADDRESS_ACTIVITY webhooks with this structure:

```json
{
  "webhookId": "wh_abc123",
  "id": "whevt_xyz789",
  "createdAt": "2024-01-01T00:00:00.000Z",
  "type": "ADDRESS_ACTIVITY",
  "event": {
    "network": "ETH_MAINNET",
    "activity": [
      {
        "hash": "0x123...",
        "fromAddress": "0xabc...",
        "toAddress": "0xdef...",
        "value": "1.5",
        "blockNum": "0x123456",
        "category": "external"
      }
    ]
  }
}
```

## Address Management

### Automatic Registration

New ETH addresses are automatically registered for webhook monitoring when created:

```python
# ETH wallet creation automatically registers address
eth_wallet = ETHWallet(user_id=123, session=db_session)
eth_wallet.create_wallet()  # Address automatically added to webhook
```

### Manual Registration

You can manually register addresses:

```bash
# Register single address
python ethereum_webhook_integration.py register 0x123... 456

# Sync all addresses
python ethereum_webhook_integration.py sync
```

### Webhook Management

```bash
# List all webhooks
python ethereum_webhook_manager.py list

# Get webhook info
python ethereum_webhook_manager.py info

# Add address to webhook
python ethereum_webhook_manager.py add 0x123...

# Remove address from webhook
python ethereum_webhook_manager.py remove 0x123...
```

## Migration from Polling

### Old System (Polling)
- `eth_monitor/app.py` - WebSocket + polling hybrid
- Scanned blocks every 5 minutes
- High API usage
- Potential for missed transactions during downtime

### New System (Webhooks)
- `wallet/ethereum_webhook.py` - Pure webhook handler
- Real-time transaction detection
- Minimal API usage
- Reliable delivery with retry mechanisms

### Migration Steps

1. **Setup webhooks** (as described above)
2. **Test webhook functionality** with new addresses
3. **Verify all existing addresses** are registered
4. **Stop old polling monitor**
5. **Start new webhook monitor**
6. **Monitor logs** for successful transaction processing

## Testing

### Create Test Address

```bash
# Create new ETH address (should auto-register for webhooks)
curl -X POST http://localhost:3030/api/v1/wallet/eth/create \
  -H "Authorization: Bearer your_token"
```

### Check Webhook Status

```bash
python ethereum_webhook_integration.py status
```

### Send Test Transaction

Send a small amount of ETH to a monitored address and verify:
1. Webhook receives the event
2. Transaction is processed and stored
3. User receives notification
4. Accounting entry is created

## Monitoring and Troubleshooting

### Health Check

```bash
curl http://localhost:3030/api/v1/wallet/eth/callbacks/health
```

### Common Issues

1. **Missing webhook credentials**
   - Ensure `ALCHEMY_ETH_WEBHOOK_ID` and `ALCHEMY_WEBHOOK_SIGNING_KEY` are set
   - Run setup script if credentials are missing

2. **Signature verification failures**
   - Check that signing key matches the webhook
   - Verify webhook endpoint URL is correct

3. **Addresses not monitored**
   - Run sync command to update webhook with all addresses
   - Check webhook address count vs database count

4. **Webhook not receiving events**
   - Verify webhook URL is accessible from internet
   - Check Alchemy dashboard for webhook status
   - Ensure firewall allows incoming connections

### Logs

Monitor these log files:
- Wallet service: Transaction processing and webhook handling
- Webhook monitor: Address sync and health checks
- ETH monitor: Legacy system (during transition)

## Performance Benefits

### Before (Polling)
- API calls: ~288 requests/day (every 5 minutes)
- Latency: Up to 5 minutes for transaction detection
- Resource usage: Continuous WebSocket connection + periodic polling

### After (Webhooks)
- API calls: Only for address management (~10 requests/day)
- Latency: Near real-time (seconds)
- Resource usage: Minimal, event-driven processing

## Security Considerations

1. **Webhook signature verification** prevents unauthorized requests
2. **HTTPS endpoints** ensure encrypted communication
3. **Rate limiting** on webhook endpoints prevents abuse
4. **Input validation** on all webhook payloads
5. **Error handling** prevents information leakage

## Future Enhancements

1. **Multi-chain webhook support** (BNB, Polygon, etc.)
2. **ERC-20 token transaction detection**
3. **Advanced filtering** for specific transaction types
4. **Webhook retry mechanisms** for failed deliveries
5. **Real-time dashboard** for webhook monitoring

## Support

For issues or questions:
1. Check logs for error messages
2. Verify environment configuration
3. Test webhook connectivity
4. Review Alchemy dashboard for webhook status
5. Run diagnostic commands from this guide
