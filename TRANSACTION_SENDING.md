# Transaction Sending API

## Overview

The SPV client now supports sending Bitcoin transactions through a REST API. This allows you to create, sign, and broadcast transactions programmatically.

## Features

### 💰 Transaction Creation
- **UTXO Selection**: Automatically selects appropriate UTXOs for the transaction
- **Fee Calculation**: Estimates and applies transaction fees
- **Change Handling**: Automatically creates change outputs
- **Transaction Signing**: Signs transactions with private keys
- **Broadcasting**: Sends transactions to the Bitcoin network

### 🔧 API Endpoints

#### 1. Estimate Transaction Fee
```bash
POST /estimate_fee
```

**Request Body:**
```json
{
  "from_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
  "to_address": "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
  "amount_satoshi": 10000
}
```

**Response:**
```json
{
  "success": true,
  "estimated_fee_satoshi": 1400,
  "estimated_fee_btc": 0.000014,
  "num_inputs": 2,
  "total_available": 313588,
  "amount_requested": 10000,
  "total_needed": 11400
}
```

#### 2. Send Transaction
```bash
POST /send_transaction
```

**Request Body:**
```json
{
  "from_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
  "to_address": "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
  "amount_satoshi": 10000,
  "fee_satoshi": 1400,
  "private_key": "YOUR_PRIVATE_KEY_WIF",
  "change_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"
}
```

**Response:**
```json
{
  "success": true,
  "txid": "abc123...",
  "from_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
  "to_address": "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
  "amount_satoshi": 10000,
  "amount_btc": 0.0001,
  "fee_satoshi": 1400,
  "fee_btc": 0.000014,
  "total_satoshi": 11400,
  "total_btc": 0.000114,
  "change_satoshi": 302188,
  "change_btc": 0.00302188,
  "network": "testnet"
}
```

## Usage Examples

### 1. Estimate Fee
```bash
curl -X POST http://localhost:5005/estimate_fee \
  -H "Content-Type: application/json" \
  -d '{
    "from_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
    "to_address": "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
    "amount_satoshi": 10000
  }'
```

### 2. Send Transaction
```bash
curl -X POST http://localhost:5005/send_transaction \
  -H "Content-Type: application/json" \
  -d '{
    "from_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
    "to_address": "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
    "amount_satoshi": 10000,
    "fee_satoshi": 1400,
    "private_key": "YOUR_PRIVATE_KEY_WIF"
  }'
```

## Python Example

```python
import requests
import json

def send_bitcoin_transaction():
    base_url = "http://localhost:5005"
    
    # Step 1: Estimate fee
    fee_response = requests.post(f"{base_url}/estimate_fee", json={
        "from_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
        "to_address": "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
        "amount_satoshi": 10000
    })
    
    if fee_response.status_code == 200:
        fee_data = fee_response.json()
        estimated_fee = fee_data['estimated_fee_satoshi']
        print(f"Estimated fee: {estimated_fee} satoshis")
        
        # Step 2: Send transaction
        tx_response = requests.post(f"{base_url}/send_transaction", json={
            "from_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
            "to_address": "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
            "amount_satoshi": 10000,
            "fee_satoshi": estimated_fee,
            "private_key": "YOUR_PRIVATE_KEY_WIF"
        })
        
        if tx_response.status_code == 200:
            tx_data = tx_response.json()
            print(f"Transaction sent: {tx_data['txid']}")
            print(f"Amount: {tx_data['amount_btc']} BTC")
            print(f"Fee: {tx_data['fee_btc']} BTC")
        else:
            print(f"Transaction failed: {tx_response.text}")
    else:
        print(f"Fee estimation failed: {fee_response.text}")

if __name__ == "__main__":
    send_bitcoin_transaction()
```

## Error Handling

### Common Errors

1. **Insufficient Balance**
```json
{
  "error": "Insufficient balance. Available: 1000 satoshis, Needed: 5000 satoshis",
  "success": false
}
```

2. **Invalid Private Key**
```json
{
  "error": "Transaction creation failed: Invalid private key format",
  "success": false
}
```

3. **No UTXOs Found**
```json
{
  "error": "No UTXOs found for the source address",
  "success": false
}
```

4. **Missing Required Fields**
```json
{
  "error": "Missing required field: private_key",
  "success": false
}
```

## Security Considerations

### Private Key Handling
- **Never store private keys in plain text**
- **Use environment variables** for private keys
- **Implement proper key management** in production
- **Consider using hardware wallets** for large amounts

### Network Selection
- **Testnet**: Safe for testing, no real value
- **Mainnet**: Real Bitcoin transactions, use with caution

### Fee Management
- **Always estimate fees** before sending
- **Use appropriate fees** for timely confirmation
- **Monitor network conditions** for optimal fees

## Production Deployment

### Security Checklist
- [ ] Use HTTPS for all API calls
- [ ] Implement authentication and authorization
- [ ] Use secure key management
- [ ] Add rate limiting
- [ ] Monitor transaction status
- [ ] Implement proper error handling
- [ ] Use production WSGI server

### Example Production Setup
```bash
# Install production dependencies
pip install gunicorn eventlet

# Run with Gunicorn
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5005 spv_simple_fixed:app

# Use environment variables for private keys
export PRIVATE_KEY_WIF="your_private_key_here"
```

## Testing

### Testnet Addresses
- **Source**: `mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh` (has funds)
- **Destination**: `msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T` (empty)

### Test Commands
```bash
# Test fee estimation
python3 test_send_transaction.py

# Test with real transaction (replace with actual private key)
curl -X POST http://localhost:5005/send_transaction \
  -H "Content-Type: application/json" \
  -d '{
    "from_address": "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",
    "to_address": "msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T",
    "amount_satoshi": 1000,
    "fee_satoshi": 1000,
    "private_key": "YOUR_ACTUAL_PRIVATE_KEY"
  }'
```

This provides a complete transaction sending solution with proper error handling, fee estimation, and security considerations. 