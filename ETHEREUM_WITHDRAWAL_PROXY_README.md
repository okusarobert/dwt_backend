# Ethereum Withdrawal Proxy

This document describes the Ethereum withdrawal proxy functionality implemented in the API gateway.

## Overview

The API gateway now includes proxy endpoints for Ethereum withdrawal operations, allowing clients to interact with the wallet service through a unified API interface.

## Proxy Endpoints

### 1. Ethereum Withdrawal Request

**Endpoint:** `POST /api/v1/wallet/withdraw/ethereum`

**Description:** Initiates an Ethereum withdrawal transaction

**Request Headers:**
```
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
  "amount": 0.01,
  "reference_id": "unique_reference_id",
  "description": "Withdrawal description",
  "gas_limit": 21000
}
```

**Response (201 Created):**
```json
{
  "message": "Ethereum withdrawal prepared successfully",
  "transaction_info": {
    "reference_id": "unique_reference_id",
    "amount_eth": 0.01,
    "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
    "estimated_cost_eth": 0.00042,
    "status": "prepared"
  }
}
```

### 2. Ethereum Withdrawal Status

**Endpoint:** `GET /api/v1/wallet/withdraw/ethereum/status/<reference_id>`

**Description:** Checks the status of an Ethereum withdrawal transaction

**Request Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "status": "success",
  "transaction_info": {
    "reference_id": "unique_reference_id",
    "tx_hash": "0x1234567890abcdef...",
    "status": "success",
    "gas_used": 21000,
    "block_number": 19000000
  }
}
```

## Architecture

```
Client → API Gateway → Wallet Service → Blockchain
```

### Flow Diagram

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌─────────────┐
│   Client    │───▶│ API Gateway  │───▶│Wallet Service│───▶│ Blockchain  │
│             │    │              │    │              │    │             │
│ POST /api/  │    │ Proxy        │    │ ETH Client   │    │ Ethereum    │
│ withdraw    │    │ Endpoints    │    │              │    │ Network     │
└─────────────┘    └──────────────┘    └──────────────┘    └─────────────┘
```

## Implementation Details

### API Gateway Proxy (`api/app.py`)

The proxy endpoints are implemented in the API gateway with the following features:

#### 1. Request Forwarding
- **Headers Forwarding**: All request headers are forwarded to the wallet service
- **Host Header Removal**: Prevents conflicts with internal service communication
- **Timeout Configuration**: 60 seconds for withdrawal requests, 30 seconds for status checks

#### 2. Error Handling
- **Network Errors**: Returns 503 Service Unavailable for connection issues
- **Internal Errors**: Returns 500 Internal Server Error for processing issues
- **Logging**: Comprehensive logging for debugging and monitoring

#### 3. Response Handling
- **Status Code Preservation**: Maintains original response status codes
- **Response Body Forwarding**: Passes through wallet service responses
- **Content-Type Preservation**: Maintains proper content types

### Code Structure

```python
@api.route('/wallet/withdraw/ethereum', methods=['POST'])
def ethereum_withdraw_proxy():
    """
    Proxy endpoint for Ethereum withdrawals.
    Forwards requests to the wallet service for processing.
    """
    try:
        # Forward the request to wallet service
        wallet_url = f"{WALLET_SERVICE_URL}/wallet/withdraw/ethereum"
        
        # Forward headers and body
        headers = dict(request.headers)
        headers.pop('Host', None)  # Remove host header
        
        response = requests.post(
            wallet_url,
            json=request.get_json(),
            headers=headers,
            timeout=60
        )
        
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Wallet service unavailable"}), 503
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
```

## Usage Examples

### 1. Initiate Withdrawal

```bash
curl -X POST http://localhost:3030/api/v1/wallet/withdraw/ethereum \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token_here" \
  -d '{
    "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
    "amount": 0.01,
    "reference_id": "withdrawal_123",
    "description": "Test withdrawal",
    "gas_limit": 21000
  }'
```

### 2. Check Withdrawal Status

```bash
curl -X GET http://localhost:3030/api/v1/wallet/withdraw/ethereum/status/withdrawal_123 \
  -H "Authorization: Bearer your_token_here"
```

### 3. Python Client Example

```python
import requests

# Initiate withdrawal
withdrawal_data = {
    "to_address": "0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7",
    "amount": 0.01,
    "reference_id": "withdrawal_123",
    "description": "Test withdrawal",
    "gas_limit": 21000
}

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer your_token_here"
}

response = requests.post(
    "http://localhost:3030/api/v1/wallet/withdraw/ethereum",
    json=withdrawal_data,
    headers=headers
)

if response.status_code == 201:
    print("Withdrawal initiated successfully!")
    reference_id = response.json()["transaction_info"]["reference_id"]
    
    # Check status
    status_response = requests.get(
        f"http://localhost:3030/api/v1/wallet/withdraw/ethereum/status/{reference_id}",
        headers=headers
    )
    
    print(f"Status: {status_response.json()}")
```

## Testing

### Test Script

Use the provided test script to verify the proxy functionality:

```bash
python test_ethereum_withdrawal_proxy.py
```

### Manual Testing

1. **Health Check:**
   ```bash
   curl http://localhost:3030/api/v1/health
   ```

2. **Withdrawal Test:**
   ```bash
   curl -X POST http://localhost:3030/api/v1/wallet/withdraw/ethereum \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer your_token" \
     -d '{"to_address":"0x742d35cc6634c0532925a3b8d4c9db96c4b4d8b7","amount":0.01,"reference_id":"test_123"}'
   ```

3. **Status Check:**
   ```bash
   curl http://localhost:3030/api/v1/wallet/withdraw/ethereum/status/test_123 \
     -H "Authorization: Bearer your_token"
   ```

## Error Responses

### 1. Service Unavailable (503)
```json
{
  "error": "Wallet service unavailable"
}
```

### 2. Internal Server Error (500)
```json
{
  "error": "Internal server error"
}
```

### 3. Validation Errors (400)
```json
{
  "error": [
    {
      "to_address": "Invalid Ethereum address format"
    }
  ]
}
```

### 4. Authentication Errors (401)
```json
{
  "error": "Invalid or missing token"
}
```

## Monitoring and Logging

### API Gateway Logs

The proxy endpoints include comprehensive logging:

```
INFO: Proxying Ethereum withdrawal request to wallet service
INFO: Proxying Ethereum withdrawal status check for reference: withdrawal_123
ERROR: Error forwarding Ethereum withdrawal to wallet service: Connection timeout
```

### Health Monitoring

Monitor the API gateway health endpoint:

```bash
curl http://localhost:3030/api/v1/health
```

Expected response:
```json
{
  "status": "ok"
}
```

## Security Considerations

### 1. Authentication
- All withdrawal requests require valid authentication tokens
- Tokens are forwarded to the wallet service for validation

### 2. Input Validation
- Address format validation
- Amount validation (positive values)
- Reference ID uniqueness

### 3. Rate Limiting
- Consider implementing rate limiting for withdrawal requests
- Monitor for suspicious activity

### 4. Logging
- Log all withdrawal attempts
- Monitor for failed requests
- Track response times

## Performance Considerations

### 1. Timeouts
- **Withdrawal Requests**: 60 seconds (blockchain operations can be slow)
- **Status Checks**: 30 seconds (faster response expected)

### 2. Connection Pooling
- The API gateway uses connection pooling for efficient service communication
- Consider tuning connection pool settings for high load

### 3. Caching
- Consider caching withdrawal status responses
- Implement appropriate cache invalidation strategies

## Troubleshooting

### Common Issues

1. **503 Service Unavailable**
   - Check if wallet service is running
   - Verify network connectivity between services
   - Check service URLs in configuration

2. **Timeout Errors**
   - Increase timeout values for slow blockchain operations
   - Check network latency between services
   - Monitor blockchain network congestion

3. **Authentication Errors**
   - Verify token format and validity
   - Check token expiration
   - Ensure proper Authorization header

### Debug Steps

1. **Check Service Health:**
   ```bash
   curl http://localhost:3030/api/v1/health
   ```

2. **Check Wallet Service Directly:**
   ```bash
   curl http://localhost:3000/wallet/withdraw/ethereum
   ```

3. **Check Logs:**
   ```bash
   docker logs dwt_backend-api-1
   docker logs dwt_backend-wallet-1
   ```

## Future Enhancements

### 1. Additional Cryptocurrencies
- Extend proxy to support other cryptocurrencies (BTC, SOL, etc.)
- Implement currency-specific validation and handling

### 2. Enhanced Monitoring
- Add metrics collection for withdrawal operations
- Implement alerting for failed withdrawals
- Add performance monitoring

### 3. Caching Layer
- Cache withdrawal status responses
- Implement smart cache invalidation
- Add response compression

### 4. Rate Limiting
- Implement per-user rate limiting
- Add withdrawal amount limits
- Implement cooldown periods

## Conclusion

The Ethereum withdrawal proxy provides a clean, secure, and efficient way to access wallet functionality through the API gateway. It maintains the same interface as direct wallet service calls while adding the benefits of centralized API management, logging, and error handling. 