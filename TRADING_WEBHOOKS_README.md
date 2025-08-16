# Trading Webhook System

This document describes the comprehensive webhook system implemented for buy and sell trading operations, following the same secure pattern as the Relworx mobile money webhooks.

## 🎯 Overview

The trading webhook system provides secure, real-time notifications for trade status updates, buy completions, and sell completions. All webhooks use HMAC-SHA256 signature verification for security.

## 🔐 Security Features

- **HMAC-SHA256 Signature Verification**: All webhooks require valid signatures
- **Environment-based Secrets**: Separate secrets for different webhook types
- **Header-based Authentication**: Signature verification via HTTP headers
- **Audit Logging**: Comprehensive logging of all webhook events

## 📋 Webhook Endpoints

### 1. Buy Completion Webhook
**Endpoint**: `POST /api/webhooks/buy-complete`

**Purpose**: Notify when a buy trade is completed (crypto transferred to user)

**Headers**:
```
Content-Type: application/json
X-Buy-Webhook-Signature: <hmac-sha256-signature>
```

**Payload**:
```json
{
  "trade_id": 123,
  "status": "completed",
  "crypto_amount": 0.001,
  "transaction_hash": "0x1234567890abcdef",
  "timestamp": "2024-01-15T10:30:00Z",
  "webhook_type": "buy_completion"
}
```

### 2. Sell Completion Webhook
**Endpoint**: `POST /api/webhooks/sell-complete`

**Purpose**: Notify when a sell trade is completed (fiat payment sent to user)

**Headers**:
```
Content-Type: application/json
X-Sell-Webhook-Signature: <hmac-sha256-signature>
```

**Payload**:
```json
{
  "trade_id": 124,
  "status": "completed",
  "fiat_amount": 100.0,
  "payment_reference": "PAY_REF_123456",
  "timestamp": "2024-01-15T10:30:00Z",
  "webhook_type": "sell_completion"
}
```

### 3. Trade Status Webhook
**Endpoint**: `POST /api/webhooks/trade-status`

**Purpose**: General trade status updates (processing, failed, etc.)

**Headers**:
```
Content-Type: application/json
X-Trade-Webhook-Signature: <hmac-sha256-signature>
```

**Payload**:
```json
{
  "trade_id": 125,
  "status": "processing",
  "metadata": {
    "processing_stage": "crypto_transfer",
    "estimated_completion": "5 minutes"
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "webhook_type": "trade_status"
}
```

## ⚙️ Configuration

### Environment Variables

Add these environment variables to your configuration:

```bash
# Webhook Secrets
BUY_WEBHOOK_SECRET=your-buy-webhook-secret
SELL_WEBHOOK_SECRET=your-sell-webhook-secret
TRADE_WEBHOOK_SECRET=your-trade-webhook-secret
RELWORX_WEBHOOK_SECRET=your-relworx-webhook-secret

# Service URLs
WALLET_SERVICE_URL=http://wallet:8000
API_SERVICE_URL=http://api:8000
```

### API Gateway Configuration

The webhook endpoints are available through the API gateway:

```bash
# Direct wallet service endpoints
POST http://wallet:8000/api/webhooks/buy-complete
POST http://wallet:8000/api/webhooks/sell-complete
POST http://wallet:8000/api/webhooks/trade-status
POST http://wallet:8000/api/webhooks/relworx

# API gateway endpoints (recommended)
POST http://api:8000/api/v1/webhooks/buy-complete
POST http://api:8000/api/v1/webhooks/sell-complete
POST http://api:8000/api/v1/webhooks/trade-status
POST http://api:8000/api/v1/webhooks/relworx
```

## 🔧 Implementation Details

### Webhook Processing Flow

1. **Signature Verification**: Verify HMAC-SHA256 signature
2. **Payload Validation**: Validate required fields
3. **Trade Lookup**: Find trade by ID
4. **Status Update**: Update trade status and metadata
5. **Transaction Update**: Update related transactions
6. **Notification**: Send Kafka notification
7. **Response**: Return success/error response

### Database Updates

When webhooks are processed, the following database updates occur:

- **Trade Status**: Updated to new status
- **Metadata**: Webhook information stored
- **Timestamps**: Completion timestamps set
- **Transaction Metadata**: Blockchain hashes and payment references stored

### Kafka Notifications

All webhook events trigger Kafka notifications to the `trade-notifications` topic:

```json
{
  "user_id": 123,
  "trade_id": 456,
  "status": "completed",
  "trade_type": "buy",
  "crypto_amount": 0.001,
  "crypto_currency": "BTC"
}
```

## 🧪 Testing

### Using WebhookTester

The `WebhookTester` class provides utilities for testing webhooks:

```python
from wallet.webhook_utils import WebhookTester

# Test buy completion webhook
test_data = WebhookTester.test_buy_completion_webhook(
    trade_id=123,
    crypto_amount=0.001,
    transaction_hash="0x1234567890abcdef",
    status="completed"
)

# Test sell completion webhook
test_data = WebhookTester.test_sell_completion_webhook(
    trade_id=124,
    fiat_amount=100.0,
    payment_reference="PAY_REF_123456",
    status="completed"
)

# Test trade status webhook
test_data = WebhookTester.test_trade_status_webhook(
    trade_id=125,
    status="processing",
    metadata={
        "processing_stage": "payment_verification",
        "estimated_completion": "2 minutes"
    }
)
```

### Manual Testing with curl

```bash
# Test buy completion webhook
curl -X POST http://localhost:8000/api/webhooks/buy-complete \
  -H "Content-Type: application/json" \
  -H "X-Buy-Webhook-Signature: <generated-signature>" \
  -d '{
    "trade_id": 123,
    "status": "completed",
    "crypto_amount": 0.001,
    "transaction_hash": "0x1234567890abcdef"
  }'

# Test sell completion webhook
curl -X POST http://localhost:8000/api/webhooks/sell-complete \
  -H "Content-Type: application/json" \
  -H "X-Sell-Webhook-Signature: <generated-signature>" \
  -d '{
    "trade_id": 124,
    "status": "completed",
    "fiat_amount": 100.0,
    "payment_reference": "PAY_REF_123456"
  }'
```

### Signature Generation

```python
from wallet.webhook_utils import WebhookUtils
import json

# Generate signature for payload
payload = {
    "trade_id": 123,
    "status": "completed",
    "crypto_amount": 0.001
}

payload_str = json.dumps(payload)
signature = WebhookUtils.generate_signature(payload_str, "your-secret")

print(f"Signature: {signature}")
```

## 📊 Monitoring and Logging

### Log Messages

The webhook system logs the following events:

- **Webhook Received**: `Received buy completion webhook: {data}`
- **Signature Verification**: `Invalid buy webhook signature: {signature}`
- **Trade Updates**: `Buy trade {trade_id} completed via webhook`
- **Errors**: `Error processing buy completion webhook: {e}`

### Kafka Topics

- **trade-notifications**: Real-time trade status updates
- **webhook-events**: Webhook processing events (optional)

## 🔄 Integration Examples

### External Payment Provider Integration

```python
# Example: External payment provider sending webhook
import requests
import hmac
import hashlib
import json

def send_payment_completion_webhook(trade_id, amount, reference):
    payload = {
        "trade_id": trade_id,
        "status": "completed",
        "fiat_amount": amount,
        "payment_reference": reference
    }
    
    # Generate signature
    payload_str = json.dumps(payload)
    signature = hmac.new(
        "your-secret".encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Send webhook
    response = requests.post(
        "http://api:8000/api/v1/webhooks/sell-complete",
        headers={
            "Content-Type": "application/json",
            "X-Sell-Webhook-Signature": signature
        },
        json=payload
    )
    
    return response.json()
```

### Blockchain Integration

```python
# Example: Blockchain listener sending webhook
def send_crypto_transfer_webhook(trade_id, amount, tx_hash):
    payload = {
        "trade_id": trade_id,
        "status": "completed",
        "crypto_amount": amount,
        "transaction_hash": tx_hash
    }
    
    # Generate signature
    payload_str = json.dumps(payload)
    signature = hmac.new(
        "your-secret".encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Send webhook
    response = requests.post(
        "http://api:8000/api/v1/webhooks/buy-complete",
        headers={
            "Content-Type": "application/json",
            "X-Buy-Webhook-Signature": signature
        },
        json=payload
    )
    
    return response.json()
```

## 🚨 Error Handling

### Common Error Responses

```json
// Invalid signature
{
  "success": false,
  "error": "Invalid signature"
}

// Missing required fields
{
  "success": false,
  "error": "Missing required fields"
}

// Trade not found
{
  "success": false,
  "error": "Trade not found"
}

// Invalid status
{
  "success": false,
  "error": "Invalid status"
}
```

### Retry Logic

Webhook senders should implement retry logic:

- **Retry on 5xx errors**: Server errors
- **Don't retry on 4xx errors**: Client errors (invalid signature, etc.)
- **Exponential backoff**: 1s, 2s, 4s, 8s delays
- **Maximum retries**: 3-5 attempts

## 🔒 Security Best Practices

1. **Use Strong Secrets**: Generate cryptographically secure secrets
2. **Rotate Secrets**: Regularly rotate webhook secrets
3. **HTTPS Only**: Always use HTTPS in production
4. **Validate Payloads**: Verify all required fields
5. **Rate Limiting**: Implement rate limiting on webhook endpoints
6. **Monitor Logs**: Monitor webhook logs for suspicious activity

## 📈 Performance Considerations

- **Async Processing**: Webhooks are processed asynchronously
- **Database Transactions**: All updates are wrapped in transactions
- **Kafka Integration**: Notifications sent via Kafka for scalability
- **Connection Pooling**: Database connections are pooled
- **Error Recovery**: Failed webhooks can be retried

## 🎯 Use Cases

### Buy Trade Flow
1. User initiates buy order
2. Payment processed (mobile money, voucher, etc.)
3. Payment provider sends webhook to `/api/webhooks/relworx`
4. Crypto transfer initiated
5. Blockchain sends webhook to `/api/webhooks/buy-complete`
6. Trade marked as completed
7. User receives crypto

### Sell Trade Flow
1. User initiates sell order
2. Crypto transferred from user to reserve
3. Fiat payment initiated
4. Payment provider sends webhook to `/api/webhooks/sell-complete`
5. Trade marked as completed
6. User receives fiat payment

### Status Updates
1. Trade processing stages updated via `/api/webhooks/trade-status`
2. Real-time status updates sent to frontend
3. User notifications triggered
4. Audit trail maintained

## 🔧 Troubleshooting

### Common Issues

1. **Invalid Signature**: Check webhook secret configuration
2. **Trade Not Found**: Verify trade ID exists
3. **Database Errors**: Check database connectivity
4. **Kafka Errors**: Verify Kafka configuration

### Debug Commands

```bash
# Check webhook logs
docker logs wallet-service | grep webhook

# Test webhook endpoint
curl -X POST http://localhost:8000/api/webhooks/buy-complete \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Check database for trade
docker exec -it postgres psql -U postgres -d dwt_backend -c "SELECT * FROM trades WHERE id = 123;"
```

---

**Built with ❤️ by the DT Exchange Team**
