# Enhanced Transfer System with Ledger Tracking & Portfolio Management

## 🚀 Overview

This document describes the enhanced transfer system that replaces the basic user ID-based transfer with a comprehensive currency-aware, email-based transfer system that includes:

- **Currency-based wallet lookup** instead of user ID
- **Email-based recipient identification** for better UX
- **Comprehensive ledger tracking** for all financial transactions
- **Portfolio aggregation** with 24h, weekly, and monthly analysis
- **Crypto price recording** at transaction time for accurate portfolio valuation

## 🔄 Enhanced Transfer Flow

### Before (Old System)
```
User A → User ID → Transfer Amount → User B
```

### After (New System)
```
User A → Currency + Email → Validate Wallets → Transfer → Ledger Entries → Portfolio Update
```

## 📊 New Database Models

### 1. LedgerEntry
Tracks every financial transaction with before/after balances and prices:

```sql
CREATE TABLE ledger_entries (
    id SERIAL PRIMARY KEY,
    transaction_id INTEGER REFERENCES transactions(id),
    user_id INTEGER REFERENCES users(id),
    account_id INTEGER REFERENCES accounts(id),
    amount NUMERIC(20,8),
    currency VARCHAR(16),
    entry_type VARCHAR(32), -- 'debit' or 'credit'
    transaction_type transactiontype,
    balance_before NUMERIC(20,8),
    balance_after NUMERIC(20,8),
    price_usd NUMERIC(20,8), -- For crypto transactions
    price_timestamp TIMESTAMP,
    description TEXT,
    reference_id VARCHAR(64),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 2. PortfolioSnapshot
Historical portfolio snapshots for analysis:

```sql
CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    snapshot_type VARCHAR(16), -- 'daily', 'weekly', 'monthly'
    snapshot_date DATE,
    total_value_usd NUMERIC(20,2),
    total_change_24h NUMERIC(20,2),
    total_change_7d NUMERIC(20,2),
    total_change_30d NUMERIC(20,2),
    change_percent_24h NUMERIC(10,4),
    change_percent_7d NUMERIC(10,4),
    change_percent_30d NUMERIC(10,4),
    currency_count INTEGER,
    asset_details JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 3. CryptoPriceHistory
Historical crypto prices for portfolio valuation:

```sql
CREATE TABLE crypto_price_history (
    id SERIAL PRIMARY KEY,
    currency VARCHAR(16),
    price_usd NUMERIC(20,8),
    source VARCHAR(32), -- 'alchemy', 'manual', etc.
    price_timestamp TIMESTAMP,
    volume_24h NUMERIC(20,2),
    market_cap NUMERIC(20,2),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 🛠️ API Endpoints

### Enhanced Transfer Endpoint

**POST** `/wallet/transfer`

**Request Body:**
```json
{
    "currency": "BTC",
    "to_email": "recipient@example.com",
    "amount": 0.001,
    "reference_id": "tx_12345",
    "description": "Payment for services"
}
```

**Response:**
```json
{
    "success": true,
    "transaction_id": 12345,
    "reference_id": "tx_12345",
    "from_user_id": 1,
    "to_user_id": 2,
    "to_email": "recipient@example.com",
    "amount": 0.001,
    "currency": "BTC",
    "price_usd": 45000.00,
    "status": "completed"
}
```

### Portfolio Endpoints

#### 1. Portfolio Summary
**GET** `/wallet/portfolio/summary`

Returns comprehensive portfolio overview with current values and recent changes.

#### 2. Portfolio Analysis
**GET** `/wallet/portfolio/analysis/{period}`

Periods: `24h`, `7d`, `30d`, `90d`

Returns detailed analysis including performance metrics and asset allocation.

#### 3. Ledger History
**GET** `/wallet/portfolio/ledger?currency=BTC&limit=100`

Returns transaction history with optional currency filtering.

#### 4. Portfolio Snapshot
**GET** `/wallet/portfolio/snapshot/{snapshot_type}`

Snapshot types: `daily`, `weekly`, `monthly`

Returns specific portfolio snapshot with historical data.

## 🔧 Implementation Details

### Transfer Service (`wallet/transfer_service.py`)

The `TransferService` class handles:

1. **Wallet Validation**: Ensures sender has sufficient balance in specified currency
2. **Recipient Lookup**: Finds recipient by email address
3. **Wallet Creation**: Automatically creates recipient wallet if it doesn't exist
4. **Price Recording**: Captures crypto prices at transaction time
5. **Ledger Creation**: Creates debit/credit entries for both parties
6. **Portfolio Updates**: Updates portfolio snapshots for both users

### Portfolio Service (`wallet/portfolio_service.py`)

The `PortfolioService` class provides:

1. **Portfolio Calculation**: Real-time portfolio value calculation
2. **Performance Metrics**: Return calculations, volatility, best/worst days
3. **Asset Allocation**: Breakdown by crypto vs. fiat assets
4. **Historical Analysis**: Time-based portfolio performance analysis

## 📈 Portfolio Aggregation Features

### Time-Based Analysis
- **24h Changes**: Daily portfolio performance
- **7-Day Changes**: Weekly performance tracking
- **30-Day Changes**: Monthly performance analysis
- **90-Day Changes**: Quarterly performance overview

### Performance Metrics
- **Total Return**: Absolute and percentage returns
- **Volatility**: Standard deviation of daily returns
- **Best/Worst Days**: Peak and trough performance
- **Asset Allocation**: Crypto vs. fiat distribution

### Asset Details
- **Balance**: Current holdings in each currency
- **Price USD**: Current market price
- **Value USD**: USD equivalent value
- **Percentage**: Portfolio allocation percentage

## 🚀 Usage Examples

### 1. Transfer BTC to Another User

```bash
curl -X POST http://localhost:5000/wallet/transfer \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "currency": "BTC",
    "to_email": "alice@example.com",
    "amount": 0.001,
    "description": "Payment for consulting"
  }'
```

### 2. Get Portfolio Summary

```bash
curl -X GET http://localhost:5000/wallet/portfolio/summary \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Get 7-Day Portfolio Analysis

```bash
curl -X GET http://localhost:5000/wallet/portfolio/analysis/7d \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Get Ledger History for BTC

```bash
curl -X GET "http://localhost:5000/wallet/portfolio/ledger?currency=BTC&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔒 Security Features

1. **Authentication Required**: All endpoints require valid JWT tokens
2. **User Isolation**: Users can only access their own portfolio data
3. **Input Validation**: Comprehensive validation of all input parameters
4. **Transaction Rollback**: Automatic rollback on any failure
5. **Audit Trail**: Complete ledger history for compliance

## 📊 Database Migration

To deploy the new system:

```bash
# Run the migration
alembic upgrade head

# Verify tables were created
psql -d your_database -c "\dt ledger_entries"
psql -d your_database -c "\dt portfolio_snapshots"
psql -d your_database -c "\dt crypto_price_history"
```

## 🧪 Testing

### Test Transfer Flow

1. **Create Test Users**: Ensure both sender and recipient exist
2. **Fund Sender Wallet**: Add BTC to sender's wallet
3. **Execute Transfer**: Send BTC using email lookup
4. **Verify Ledger**: Check ledger entries were created
5. **Check Portfolio**: Verify portfolio snapshots updated

### Test Portfolio Endpoints

1. **Portfolio Summary**: Verify current values and recent changes
2. **Portfolio Analysis**: Test different time periods
3. **Ledger History**: Verify transaction history
4. **Portfolio Snapshots**: Check snapshot creation and retrieval

## 🔄 Integration Points

### Existing Systems
- **Crypto Price Cache**: Integrates with existing Alchemy price service
- **User Authentication**: Uses existing JWT token system
- **Database Models**: Extends existing Account and Transaction models

### New Dependencies
- **Ledger Tracking**: New service for financial transaction logging
- **Portfolio Management**: New service for portfolio aggregation
- **Price History**: New service for historical price tracking

## 🚨 Error Handling

### Common Error Scenarios

1. **Insufficient Balance**: Sender doesn't have enough funds
2. **Invalid Currency**: Unsupported currency code
3. **Recipient Not Found**: Email doesn't match any user
4. **Wallet Creation Failed**: Database error during wallet creation
5. **Price Fetch Failed**: Unable to get current crypto prices

### Error Responses

```json
{
    "error": "Insufficient BTC balance",
    "details": "Required: 0.001 BTC, Available: 0.0005 BTC"
}
```

## 📈 Performance Considerations

1. **Database Indexes**: Optimized indexes for ledger queries
2. **Portfolio Caching**: Consider Redis caching for portfolio calculations
3. **Batch Updates**: Portfolio snapshots updated in batches
4. **Async Processing**: Consider async processing for portfolio updates

## 🔮 Future Enhancements

1. **Real-time Portfolio Updates**: WebSocket integration for live updates
2. **Advanced Analytics**: Risk metrics, Sharpe ratio, correlation analysis
3. **Portfolio Rebalancing**: Automated portfolio optimization
4. **Tax Reporting**: Capital gains/losses calculation
5. **Multi-currency Support**: Support for more fiat currencies

## 📝 API Documentation

### Swagger/OpenAPI
The enhanced endpoints are documented in the API specification and can be tested using:

- Swagger UI at `/swagger`
- Postman collections
- API testing tools

### Rate Limiting
- **Transfer Endpoints**: 10 requests per minute per user
- **Portfolio Endpoints**: 60 requests per minute per user
- **Ledger Endpoints**: 100 requests per minute per user

## 🆘 Troubleshooting

### Common Issues

1. **Migration Failures**: Check database permissions and existing schema
2. **Price Fetch Errors**: Verify Alchemy API key and network connectivity
3. **Portfolio Calculation Errors**: Check for missing price data
4. **Performance Issues**: Verify database indexes are properly created

### Debug Mode

Enable debug logging in the wallet service:

```python
import logging
logging.getLogger('wallet.transfer_service').setLevel(logging.DEBUG)
logging.getLogger('wallet.portfolio_service').setLevel(logging.DEBUG)
```

## 📞 Support

For technical support or questions about the enhanced transfer system:

1. **Documentation**: Check this README and inline code comments
2. **Logs**: Review application logs for detailed error information
3. **Database**: Verify database schema and data integrity
4. **API Testing**: Use provided test endpoints to verify functionality

---

**Version**: 1.0.0  
**Last Updated**: December 19, 2024  
**Author**: Development Team  
**Status**: Production Ready
