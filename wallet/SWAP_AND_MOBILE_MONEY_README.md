# Swap and Mobile Money Functionality

This document describes the comprehensive swap and mobile money functionality implemented in the wallet system.

## 🚀 Features Overview

### 1. Crypto-to-Crypto Swapping
- **Real-time pricing** from CoinGecko API
- **Slippage protection** with configurable tolerance
- **Automatic fee calculation** (0.3% swap fee)
- **Idempotent operations** to prevent duplicate swaps
- **Comprehensive transaction tracking**

### 2. Mobile Money Integration
- **Fiat-to-Crypto Buy**: Deposit mobile money, receive crypto
- **Crypto-to-Fiat Sell**: Sell crypto, receive mobile money
- **Multiple providers**: MPESA (Kenya/Tanzania), Relworx (Uganda)
- **Real-time exchange rates** and fee calculations
- **Secure payment processing** with webhook support

## 📋 API Endpoints

### Swap Endpoints

#### Calculate Swap
```http
POST /wallet/swap/calculate
```

**Request Body:**
```json
{
  "from_currency": "ETH",
  "to_currency": "USDC",
  "from_amount": 1.0,
  "slippage_tolerance": 0.01
}
```

**Response:**
```json
{
  "success": true,
  "calculation": {
    "from_amount": 1.0,
    "to_amount": 3000.0,
    "rate": 3000.0,
    "swap_fee": 0.003,
    "slippage_tolerance": 0.01,
    "min_output": 2970.0,
    "max_output": 3030.0,
    "price_change_24h": -2.5,
    "estimated_usd_value": 3000.0
  }
}
```

#### Execute Swap
```http
POST /wallet/swap/execute
```

**Request Body:**
```json
{
  "from_currency": "ETH",
  "to_currency": "USDC",
  "from_amount": 1.0,
  "reference_id": "swap_12345",
  "slippage_tolerance": 0.01
}
```

**Response:**
```json
{
  "success": true,
  "swap_id": 123,
  "reference_id": "swap_12345",
  "from_currency": "ETH",
  "to_currency": "USDC",
  "from_amount": 1.0,
  "to_amount": 3000.0,
  "rate": 3000.0,
  "swap_fee": 0.003,
  "status": "completed",
  "transaction_ids": [456, 789]
}
```

#### Get Swap History
```http
GET /wallet/swap/history?limit=50
```

**Response:**
```json
{
  "success": true,
  "swaps": [
    {
      "id": 123,
      "from_currency": "ETH",
      "to_currency": "USDC",
      "from_amount": 1.0,
      "to_amount": 3000.0,
      "rate": 3000.0,
      "fee_amount": 0.003,
      "status": "completed",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ]
}
```

### Mobile Money Endpoints

#### Get Supported Providers
```http
GET /wallet/mobile-money/providers?country=UG
```

**Response:**
```json
{
  "success": true,
  "providers": [
    {
      "provider_id": "relworx",
      "name": "Relworx",
      "supported_countries": ["UG"],
      "currencies": ["UGX"],
      "min_amount": 1000,
      "max_amount": 50000000,
      "fee_rate": 0.015,
      "processing_time": "instant"
    }
  ]
}
```

#### Calculate Buy Amounts
```http
POST /wallet/mobile-money/buy/calculate
```

**Request Body:**
```json
{
  "fiat_amount": 1000,
  "fiat_currency": "UGX",
  "crypto_currency": "USDT",
  "provider": "relworx",
  "slippage_tolerance": 0.02
}
```

**Response:**
```json
{
  "success": true,
  "calculation": {
    "fiat_amount": 1000,
    "crypto_amount": 0.263,
    "provider_fee": 15.0,
    "net_fiat_amount": 985.0,
    "crypto_price_usd": 1.0,
    "slippage_tolerance": 0.02,
    "min_crypto": 0.258,
    "max_crypto": 0.268,
    "provider": "relworx",
    "processing_time": "instant"
  }
}
```

#### Initiate Buy Order
```http
POST /wallet/mobile-money/buy/initiate
```

**Request Body:**
```json
{
  "fiat_amount": 1000,
  "fiat_currency": "UGX",
  "crypto_currency": "USDT",
  "provider": "relworx",
  "phone_number": "256700000000",
  "reference_id": "buy_12345",
  "slippage_tolerance": 0.02
}
```

**Response:**
```json
{
  "success": true,
  "reference_id": "buy_12345",
  "status": "payment_initiated",
  "transaction_id": 123,
  "reservation_id": 456,
  "payment_details": {
    "status": "initiated",
    "provider_reference": "relworx_1234567890",
    "message": "Payment request sent",
    "expires_in": 600
  },
  "buy_calculation": {...},
  "next_steps": "Complete mobile money payment to receive crypto"
}
```

#### Calculate Sell Amounts
```http
POST /wallet/mobile-money/sell/calculate
```

**Request Body:**
```json
{
  "crypto_amount": 10,
  "crypto_currency": "USDT",
  "fiat_currency": "UGX",
  "provider": "relworx",
  "slippage_tolerance": 0.02
}
```

**Response:**
```json
{
  "success": true,
  "calculation": {
    "crypto_amount": 10,
    "fiat_amount": 38000,
    "net_fiat_amount": 37430,
    "provider_fee": 570,
    "crypto_price_usd": 1.0,
    "slippage_tolerance": 0.02,
    "min_fiat": 36681.4,
    "max_fiat": 38178.6,
    "provider": "relworx",
    "processing_time": "instant"
  }
}
```

#### Initiate Sell Order
```http
POST /wallet/mobile-money/sell/initiate
```

**Request Body:**
```json
{
  "crypto_amount": 10,
  "crypto_currency": "USDT",
  "fiat_currency": "UGX",
  "provider": "relworx",
  "phone_number": "256700000000",
  "reference_id": "sell_12345",
  "slippage_tolerance": 0.02
}
```

**Response:**
```json
{
  "success": true,
  "reference_id": "sell_12345",
  "status": "order_created",
  "transaction_id": 123,
  "reservation_id": 456,
  "sell_calculation": {...},
  "next_steps": "Crypto amount locked. Processing withdrawal to mobile money."
}
```

#### Confirm Payment
```http
POST /wallet/mobile-money/confirm-payment
```

**Request Body:**
```json
{
  "reference_id": "buy_12345",
  "payment_status": "completed",
  "provider_reference": "relworx_1234567890",
  "additional_data": {
    "phone_number": "256700000000",
    "transaction_time": 1704110400
  }
}
```

**Response:**
```json
{
  "success": true,
  "status": "completed",
  "transaction_id": 123,
  "message": "Successfully purchased 0.263 USDT"
}
```

#### Get Transaction History
```http
GET /wallet/mobile-money/history?limit=50
```

**Response:**
```json
{
  "success": true,
  "transactions": [
    {
      "id": 123,
      "reference_id": "buy_12345",
      "type": "deposit",
      "amount": 0.263,
      "currency": "USDT",
      "status": "completed",
      "provider": "relworx",
      "description": "Buy USDT with UGX via relworx",
      "created_at": "2024-01-01T12:00:00Z",
      "metadata": {...}
    }
  ]
}
```

## 🔧 Service Architecture

### SwapService
- **Real-time pricing** from CoinGecko API
- **Slippage protection** with configurable tolerance
- **Automatic fee calculation** and balance updates
- **Idempotency checks** using reference_id
- **Comprehensive transaction tracking**

### MobileMoneyService
- **Provider management** for different mobile money services
- **Fee calculation** based on provider rates
- **Payment initiation** and confirmation
- **Balance locking** for sell orders
- **Transaction history** and status tracking

## 💰 Fee Structure

### Swap Fees
- **Standard swap fee**: 0.3% of the amount being swapped
- **Fee is deducted** from the source currency before conversion
- **No additional fees** for the destination currency

### Mobile Money Fees
- **MPESA (Kenya/Tanzania)**: 1.0% of transaction amount
- **Relworx (Uganda)**: 1.5% of transaction amount
- **Fees are deducted** from the fiat amount before crypto conversion

## 🛡️ Security Features

### Idempotency
- **Unique reference_id** required for all operations
- **Duplicate request detection** prevents double processing
- **Consistent responses** for repeated requests

### Balance Protection
- **Sufficient balance checks** before processing
- **Amount locking** for pending transactions
- **Automatic rollback** on failures

### Provider Integration
- **Secure webhook handling** for payment confirmations
- **Provider signature verification** (where applicable)
- **Timeout handling** for payment requests

## 📱 Mobile Money Providers

### MPESA
- **Countries**: Kenya (KE), Tanzania (TZ)
- **Currencies**: KES, TZS
- **Limits**: 10 - 1,000,000
- **Processing**: Instant
- **Fee**: 1.0%

### Relworx
- **Countries**: Uganda (UG)
- **Currencies**: UGX
- **Limits**: 1,000 - 50,000,000
- **Processing**: Instant
- **Fee**: 1.5%

## 🧪 Testing

### Test Script
Use the comprehensive test script to verify functionality:

```bash
cd wallet
python test_swap_and_mobile_money.py
```

### Test Coverage
- ✅ Swap calculation and execution
- ✅ Mobile money buy/sell operations
- ✅ Payment confirmation workflows
- ✅ Idempotency verification
- ✅ Error handling scenarios

## 🚀 Getting Started

### 1. Prerequisites
- Wallet service running on port 3000
- Valid authentication token
- Database with proper schema (Swap, Reservation tables)

### 2. Basic Usage

#### Swap ETH to USDC
```python
import requests

# Calculate swap
calc_response = requests.post("http://localhost:3000/wallet/swap/calculate", json={
    "from_currency": "ETH",
    "to_currency": "USDC",
    "from_amount": 1.0
})

# Execute swap
swap_response = requests.post("http://localhost:3000/wallet/swap/execute", json={
    "from_currency": "ETH",
    "to_currency": "USDC",
    "from_amount": 1.0,
    "reference_id": "my_swap_123"
})
```

#### Buy USDT with Mobile Money
```python
# Calculate buy
calc_response = requests.post("http://localhost:3000/wallet/mobile-money/buy/calculate", json={
    "fiat_amount": 1000,
    "fiat_currency": "UGX",
    "crypto_currency": "USDT",
    "provider": "relworx"
})

# Initiate buy
buy_response = requests.post("http://localhost:3000/wallet/mobile-money/buy/initiate", json={
    "fiat_amount": 1000,
    "fiat_currency": "UGX",
    "crypto_currency": "USDT",
    "provider": "relworx",
    "phone_number": "256700000000",
    "reference_id": "my_buy_123"
})
```

## 🔍 Monitoring and Debugging

### Logs
- All operations are logged with detailed information
- Use `app.logger` to track swap and mobile money operations
- Monitor for failed transactions and payment confirmations

### Database Tables
- **swaps**: Records all swap operations
- **reservations**: Tracks amount reservations for mobile money
- **transactions**: Standard transaction records with metadata

### Status Tracking
- **Pending**: Initial state for all operations
- **Completed**: Successfully processed
- **Failed**: Failed operations with error details
- **Idempotent**: Duplicate request detected

## 🚨 Error Handling

### Common Errors
- **Insufficient balance**: User doesn't have enough funds
- **Invalid provider**: Unsupported mobile money provider
- **Amount limits**: Transaction amount outside provider limits
- **Network issues**: API timeouts or connection failures

### Error Responses
```json
{
  "error": "Insufficient ETH balance for swap"
}
```

## 🔮 Future Enhancements

### Planned Features
- **Additional providers**: More mobile money services
- **Advanced slippage protection**: Dynamic tolerance adjustment
- **Batch operations**: Multiple swaps in single transaction
- **Price alerts**: Notifications for favorable rates
- **Analytics dashboard**: Swap and mobile money insights

### Integration Opportunities
- **DEX integration**: Direct blockchain swaps
- **Liquidity pools**: Automated market making
- **Cross-chain swaps**: Multi-blockchain support
- **Fiat on-ramps**: Additional payment methods

## 📞 Support

For technical support or questions about the swap and mobile money functionality:

1. Check the logs for detailed error information
2. Verify database schema and table structure
3. Test with the provided test script
4. Review API endpoint documentation above

## 📄 License

This functionality is part of the wallet system and follows the same licensing terms.
