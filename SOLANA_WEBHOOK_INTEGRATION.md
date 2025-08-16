# Solana Webhook Integration

This document describes the Solana webhook integration with Alchemy API for real-time transaction monitoring.

## Overview

The Solana webhook integration automatically registers newly created addresses with Alchemy's webhook service for real-time transaction monitoring. The system uses an efficient approach of **one webhook per network** and adds addresses to the existing webhook rather than creating a new webhook for each address.

## Architecture

### Webhook Management Strategy

1. **Single Webhook Per Network**: One webhook is created per network (devnet/mainnet)
2. **Address Addition**: New addresses are added to the existing webhook
3. **Automatic Registration**: Addresses are automatically registered when created
4. **Manual Management**: API endpoints for manual webhook management

### Components

- **Solana Client** (`shared/crypto/clients/sol.py`): Handles webhook registration
- **Wallet Service** (`wallet/app.py`): Provides API endpoints for webhook management
- **Webhook Handler** (`wallet/solana_webhook.py`): Processes incoming webhook events
- **API Proxy** (`api/app.py`): Proxies webhook requests to wallet service

## Features

### Automatic Webhook Registration

When a new Solana address is created:

1. **Check for existing webhook** - Look for existing webhooks on the network
2. **Create webhook if needed** - Create new webhook if none exists
3. **Add address to webhook** - Add the new address to the existing webhook
4. **Log the operation** - Record success/failure for monitoring

### Manual Webhook Management

API endpoints for manual webhook management:

- `POST /wallet/sol/register-webhook` - Register a specific address
- `POST /wallet/sol/register-all-webhooks` - Register all user's addresses
- `POST /wallet/sol/unregister-webhook` - Remove an address from webhook

### Webhook Event Processing

The system processes `ADDRESS_ACTIVITY` webhook events from Alchemy:

1. **Signature Verification** - Verify webhook authenticity using HMAC-SHA256
2. **Transaction Processing** - Create transaction records for incoming/outgoing transactions
3. **Reservation Management** - Lock amounts for deposits and track withdrawals
4. **Account Updates** - Update account balances and locked amounts

## Configuration

### Environment Variables

```bash
# Required
ALCHEMY_API_KEY=your_alchemy_api_key

# Optional (defaults shown)
WEBHOOK_BASE_URL=http://localhost:3030
VERIFY_ALCHEMY_SIGNATURE=true
ALCHEMY_WEBHOOK_KEY=your_webhook_secret_key
```

### Network Configuration

The system supports both Solana networks:

- **Devnet**: `https://solana-devnet.g.alchemy.com/v2/{api_key}`
- **Mainnet**: `https://solana-mainnet.g.alchemy.com/v2/{api_key}`

## API Endpoints

### Webhook Registration

#### Register Single Address
```http
POST /wallet/sol/register-webhook
Content-Type: application/json
Authorization: Bearer <token>

{
  "address": "11111111111111111111111111111111"
}
```

**Response:**
```json
{
  "message": "Address registered with webhook successfully",
  "address": "11111111111111111111111111111111",
  "status": "registered"
}
```

#### Register All Addresses
```http
POST /wallet/sol/register-all-webhooks
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Webhook registration completed",
  "results": {
    "total_addresses": 2,
    "registered_count": 2,
    "failed_count": 0,
    "results": [
      {"address": "addr1", "status": "registered"},
      {"address": "addr2", "status": "registered"}
    ]
  }
}
```

#### Unregister Address
```http
POST /wallet/sol/unregister-webhook
Content-Type: application/json
Authorization: Bearer <token>

{
  "address": "11111111111111111111111111111111"
}
```

### Webhook Endpoint

#### Receive Webhook Events
```http
POST /api/v1/wallet/sol/callbacks/address-webhook
Content-Type: application/json
X-Alchemy-Signature: <signature>

{
  "type": "ADDRESS_ACTIVITY",
  "data": {
    "activity": [...]
  }
}
```

## Implementation Details

### Webhook Registration Flow

```python
def register_address_with_webhook(self, address: str) -> bool:
    # 1. Get Alchemy API key and determine network URL
    # 2. Check for existing webhooks
    existing_webhooks = self._get_existing_webhooks(alchemy_url)
    
    if existing_webhooks:
        # 3a. Add address to existing webhook
        webhook_id = existing_webhooks[0]['id']
        return self._add_address_to_webhook(alchemy_url, webhook_id, address)
    else:
        # 3b. Create new webhook with address
        return self._create_webhook_with_address(alchemy_url, webhook_endpoint, address)
```

### Address Creation with Webhook

```python
def create_address(self):
    # 1. Create unique address
    new_address = self.ensure_address_uniqueness()
    
    if new_address:
        # 2. Register with webhook automatically
        webhook_registered = self.register_address_with_webhook(new_address['address'])
        
        if webhook_registered:
            logger.info(f"Address {new_address['address']} registered with webhook")
        else:
            logger.warning(f"Failed to register address {new_address['address']} with webhook")
```

### Webhook Event Processing

```python
@solana_webhook.route('/sol/callbacks/address-webhook', methods=['POST'])
def handle_solana_webhook():
    # 1. Verify signature
    if not verify_alchemy_signature(request_body, signature_header, webhook_key):
        return jsonify({"error": "Invalid signature"}), 401
    
    # 2. Process webhook data
    webhook_data = request.get_json()
    
    if webhook_data.get('type') == 'ADDRESS_ACTIVITY':
        handle_solana_address_activity(webhook_data)
    
    return jsonify({"status": "success"}), 200
```

## Testing

### Test Script

Run the test script to verify webhook functionality:

```bash
python3 test_solana_webhook_registration.py
```

The test script covers:
- Basic webhook registration
- Adding addresses to existing webhooks
- Address creation with automatic webhook registration
- Webhook management functionality

### Manual Testing

Test webhook registration:

```bash
# Register a test address
curl -X POST http://localhost:3030/api/v1/wallet/sol/register-webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"address": "11111111111111111111111111111111"}'

# Register all addresses
curl -X POST http://localhost:3030/api/v1/wallet/sol/register-all-webhooks \
  -H "Authorization: Bearer <token>"
```

Test webhook endpoint:

```bash
# Send test webhook event
curl -X POST http://localhost:3030/api/v1/wallet/sol/callbacks/address-webhook \
  -H "Content-Type: application/json" \
  -H "X-Alchemy-Signature: test-signature" \
  -d '{"type": "ADDRESS_ACTIVITY", "data": {"test": "data"}}'
```

## Monitoring and Troubleshooting

### Logs

Monitor webhook operations in the wallet service logs:

```bash
docker-compose logs wallet | grep -i webhook
```

### Common Issues

1. **ALCHEMY_API_KEY not configured**
   - Solution: Set the `ALCHEMY_API_KEY` environment variable

2. **Webhook registration failed**
   - Check Alchemy API key validity
   - Verify network configuration (devnet/mainnet)
   - Check webhook URL accessibility

3. **Signature verification failed**
   - Ensure `ALCHEMY_WEBHOOK_KEY` is set correctly
   - Verify webhook signature in Alchemy dashboard

4. **Address not found**
   - Verify the address belongs to the authenticated user
   - Check if the address exists in the database

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

Check webhook status in Alchemy dashboard:
- Go to Alchemy Dashboard
- Navigate to Webhooks section
- Verify webhook is active and receiving events

## Security Considerations

1. **Signature Verification**: All webhook events are verified using HMAC-SHA256
2. **Authentication**: API endpoints require valid authentication tokens
3. **Address Ownership**: Only addresses belonging to the authenticated user can be registered
4. **Rate Limiting**: Consider implementing rate limiting for webhook registration endpoints

## Future Enhancements

1. **Webhook Health Monitoring**: Add health checks for webhook endpoints
2. **Retry Logic**: Implement retry logic for failed webhook registrations
3. **Bulk Operations**: Add support for bulk address registration
4. **Webhook Analytics**: Track webhook performance and success rates
5. **Multi-Network Support**: Extend to support multiple Solana networks simultaneously

## Dependencies

- **Alchemy API**: For webhook management and transaction monitoring
- **Solana SDK**: For address generation and validation
- **Flask**: For webhook endpoint handling
- **SQLAlchemy**: For database operations
- **Requests**: For HTTP API calls to Alchemy

## Related Files

- `shared/crypto/clients/sol.py` - Solana client with webhook management
- `wallet/solana_webhook.py` - Webhook event handler
- `wallet/app.py` - API endpoints for webhook management
- `api/app.py` - Webhook proxy endpoint
- `test_solana_webhook_registration.py` - Test script
