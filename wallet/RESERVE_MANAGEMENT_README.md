# Reserve Management System

This document describes the comprehensive reserve management system implemented for the wallet system, ensuring liquidity for swaps and trading operations.

## 🏦 Overview

The Reserve Management System maintains pools of fiat and crypto currencies to ensure immediate execution of swaps and trading operations. It provides:

- **Real-time liquidity monitoring** for all supported currencies
- **Automatic reserve allocation** for operations
- **Reserve protection** against over-utilization
- **Comprehensive analytics** and reporting
- **Admin controls** for reserve management

## 🎯 Key Features

### 1. **Reserve Accounts**
- **System-managed accounts** for each currency and type
- **Automatic creation** when needed
- **Dedicated labeling** (e.g., `RESERVE_USDT_CRYPTO`)
- **High-precision balance tracking**

### 2. **Reserve Monitoring**
- **Real-time balance status** with utilization percentages
- **Health indicators**: Healthy, Moderate, Warning, Critical
- **Caching system** for performance optimization
- **Automatic status updates**

### 3. **Reserve Operations**
- **Amount reservation** for pending operations
- **Automatic release** on completion or failure
- **Top-up and withdrawal** capabilities
- **Transaction tracking** for all operations

### 4. **Integration with Services**
- **Swap operations** check and reserve both currencies
- **Mobile money operations** reserve appropriate currencies
- **Automatic rollback** on operation failures
- **Seamless user experience**

## 🔧 Architecture

### ReserveService Class
```python
class ReserveService:
    def __init__(self, session: Session):
        self.session = session
        self.reserve_accounts = {}  # Cache for reserve accounts
        self.reserve_cache = {}     # Cache for balance data
        self.cache_ttl = 30        # 30 seconds cache TTL
```

### Key Methods
- `get_reserve_account()` - Get or create reserve account
- `get_reserve_balance()` - Get current balance and status
- `check_reserve_sufficiency()` - Check if operation can proceed
- `reserve_amount()` - Lock amount for operation
- `release_reserve()` - Release locked amount
- `top_up_reserve()` - Add funds to reserve
- `withdraw_from_reserve()` - Remove funds from reserve

## 📊 Reserve Status Levels

### Utilization Thresholds
- **Healthy**: 0-50% utilization
- **Moderate**: 50-75% utilization
- **Warning**: 75-90% utilization
- **Critical**: 90%+ utilization

### Status Calculation
```python
utilization = (locked_balance / total_balance * 100) if total_balance > 0 else 0

if utilization >= 90:
    status = "critical"
elif utilization >= 75:
    status = "warning"
elif utilization >= 50:
    status = "moderate"
else:
    status = "healthy"
```

## 🚀 API Endpoints

### Get All Reserves Status
```http
GET /wallet/reserves/status
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "reserves": {
    "crypto": {
      "USDT": {
        "currency": "USDT",
        "account_type": "crypto",
        "total_balance": 10000.0,
        "available_balance": 7500.0,
        "locked_balance": 2500.0,
        "utilization_percentage": 25.0,
        "status": "healthy",
        "account_id": 123,
        "account_number": "RUSDTc1234"
      }
    },
    "fiat": {
      "UGX": {
        "currency": "UGX",
        "account_type": "fiat",
        "total_balance": 50000000.0,
        "available_balance": 40000000.0,
        "locked_balance": 10000000.0,
        "utilization_percentage": 20.0,
        "status": "healthy",
        "account_id": 124,
        "account_number": "RUGXf5678"
      }
    },
    "summary": {
      "overall_status": "healthy",
      "critical_reserves": [],
      "warning_reserves": []
    }
  }
}
```

### Get Specific Reserve Balance
```http
GET /wallet/reserves/{currency}/{account_type}/balance
Authorization: Bearer {admin_token}
```

**Example:**
```http
GET /wallet/reserves/USDT/crypto/balance
```

### Top Up Reserve
```http
POST /wallet/reserves/{currency}/{account_type}/topup
Authorization: Bearer {admin_token}
```

**Request Body:**
```json
{
  "amount": 1000.0,
  "source_reference": "bank_transfer_12345"
}
```

**Response:**
```json
{
  "success": true,
  "topped_up_amount": 1000.0,
  "new_total_balance": 11000.0,
  "transaction_id": 456
}
```

### Withdraw from Reserve
```http
POST /wallet/reserves/{currency}/{account_type}/withdraw
Authorization: Bearer {admin_token}
```

**Request Body:**
```json
{
  "amount": 500.0,
  "destination_reference": "maintenance_withdrawal"
}
```

### Get Reserve Analytics
```http
GET /wallet/reserves/analytics?period_days=30
Authorization: Bearer {admin_token}
```

**Response:**
```json
{
  "success": true,
  "analytics": {
    "period_days": 30,
    "total_transactions": 150,
    "by_operation": {
      "reserve_lock": 45,
      "reserve_release": 45,
      "reserve_topup": 30,
      "reserve_withdrawal": 30
    },
    "by_currency": {
      "USDT": {
        "total_volume": 50000.0,
        "transaction_count": 60,
        "operations": {
          "reserve_lock": 20,
          "reserve_release": 20,
          "reserve_topup": 20
        }
      }
    }
  }
}
```

### Clear Reserve Cache
```http
POST /wallet/reserves/cache/clear
Authorization: Bearer {admin_token}
```

## 🔄 Integration with Swap Operations

### Reserve Check Process
1. **Check from currency reserve** for sufficient balance
2. **Check to currency reserve** for sufficient balance
3. **Reserve both amounts** with unique reference IDs
4. **Execute swap** with reserved amounts
5. **Release reserves** on completion or rollback on failure

### Example Integration
```python
# Check and reserve from currency
from_reserve_check = self.reserve_service.check_reserve_sufficiency(
    from_currency, from_amount, AccountType.CRYPTO, "swap"
)

if not from_reserve_check["is_sufficient"]:
    return {"error": "Insufficient system reserve"}

# Reserve amounts
from_reserve_result = self.reserve_service.reserve_amount(
    from_currency, from_amount, AccountType.CRYPTO, 
    f"{reference_id}_from", "swap"
)
```

## 📱 Integration with Mobile Money

### Buy Operations (Fiat → Crypto)
1. **Check crypto reserve** for sufficient balance
2. **Reserve crypto amount** for the operation
3. **Initiate mobile money payment**
4. **Release reserve** on payment completion or failure

### Sell Operations (Crypto → Fiat)
1. **Check fiat reserve** for sufficient balance
2. **Reserve fiat amount** for the operation
3. **Lock crypto amount** from user account
4. **Process mobile money payout**
5. **Release reserves** on completion

## 💰 Reserve Management

### Top-Up Strategies
- **Regular top-ups** based on usage patterns
- **Emergency top-ups** when reserves reach warning levels
- **Automated top-ups** from external sources
- **Manual top-ups** for maintenance

### Withdrawal Scenarios
- **Maintenance operations** (e.g., system upgrades)
- **Rebalancing** between different reserve types
- **Emergency situations** requiring fund movement
- **Audit and compliance** requirements

### Reserve Monitoring
- **Real-time alerts** for critical levels
- **Daily reports** on reserve utilization
- **Weekly analytics** on reserve performance
- **Monthly reviews** of reserve strategies

## 🛡️ Security Features

### Access Control
- **Admin-only endpoints** for reserve management
- **Token-based authentication** for all operations
- **Audit logging** for all reserve changes
- **Transaction tracking** with metadata

### Data Protection
- **Encrypted storage** for sensitive reserve data
- **Secure API endpoints** with proper validation
- **Input sanitization** for all parameters
- **SQL injection protection** through ORM

### Operational Safety
- **Amount validation** (positive numbers only)
- **Balance checks** before operations
- **Automatic rollback** on failures
- **Transaction isolation** for consistency

## 📈 Performance Optimization

### Caching Strategy
- **Reserve account cache** for frequent lookups
- **Balance data cache** with 30-second TTL
- **Automatic cache invalidation** on updates
- **Cache clearing** for maintenance operations

### Database Optimization
- **Indexed queries** on currency and account type
- **Efficient joins** for balance calculations
- **Batch operations** for bulk updates
- **Connection pooling** for high concurrency

## 🧪 Testing

### Test Coverage
- **Reserve management operations** (CRUD)
- **Integration with swap operations**
- **Integration with mobile money**
- **Edge cases and error handling**
- **Performance and load testing**

### Test Scripts
```bash
# Test reserve management system
python test_reserve_system.py

# Test swap and mobile money with reserves
python test_swap_and_mobile_money.py
```

### Test Scenarios
- **Normal operations** with sufficient reserves
- **Edge cases** with insufficient reserves
- **Error handling** for invalid operations
- **Performance testing** with high load
- **Integration testing** with other services

## 🚨 Error Handling

### Common Errors
- **Insufficient reserve balance**
- **Invalid currency or account type**
- **Negative or zero amounts**
- **Cache operation failures**
- **Database connection issues**

### Error Responses
```json
{
  "success": false,
  "error": "Insufficient reserve balance. Required: 1000.0, Available: 500.0",
  "reserve_status": {
    "is_sufficient": false,
    "required_amount": 1000.0,
    "available_amount": 500.0,
    "utilization_percentage": 80.0,
    "status": "warning"
  }
}
```

## 🔮 Future Enhancements

### Planned Features
- **Automated reserve management** based on usage patterns
- **Dynamic reserve allocation** for different operation types
- **Multi-currency reserve pools** for better efficiency
- **Reserve forecasting** and predictive analytics
- **Integration with external liquidity providers**

### Advanced Capabilities
- **Reserve optimization algorithms** for cost reduction
- **Real-time market data integration** for dynamic pricing
- **Automated rebalancing** between different reserve types
- **Advanced analytics dashboard** with visualizations
- **API rate limiting** and usage monitoring

## 📊 Monitoring and Alerts

### Key Metrics
- **Reserve utilization** by currency and type
- **Operation success rates** for swaps and trading
- **Reserve top-up frequency** and amounts
- **Cache hit rates** and performance metrics
- **Error rates** and failure patterns

### Alert Thresholds
- **Warning level**: 75% utilization
- **Critical level**: 90% utilization
- **Emergency level**: 95% utilization
- **Performance alerts**: Response time > 1 second
- **Error rate alerts**: > 5% failure rate

## 🚀 Getting Started

### 1. Prerequisites
- Wallet service running on port 3000
- Admin authentication token
- Database with proper schema
- Reserve service initialized

### 2. Initial Setup
```bash
# Check reserve status
curl -X GET "http://localhost:3000/wallet/reserves/status" \
  -H "Authorization: Bearer {admin_token}"

# Top up a reserve
curl -X POST "http://localhost:3000/wallet/reserves/USDT/crypto/topup" \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"amount": 10000.0, "source_reference": "initial_setup"}'
```

### 3. Monitor Reserves
```bash
# Get analytics
curl -X GET "http://localhost:3000/wallet/reserves/analytics?period_days=7" \
  -H "Authorization: Bearer {admin_token}"

# Clear cache if needed
curl -X POST "http://localhost:3000/wallet/reserves/cache/clear" \
  -H "Authorization: Bearer {admin_token}"
```

## 📞 Support

For technical support or questions about the reserve management system:

1. **Check the logs** for detailed error information
2. **Verify reserve balances** using the status endpoint
3. **Review analytics** for usage patterns
4. **Test with provided scripts** to isolate issues
5. **Check database schema** and table structure

## 📄 License

This functionality is part of the wallet system and follows the same licensing terms.

---

**Note**: The reserve management system is critical for maintaining liquidity in the wallet system. Always ensure sufficient reserves are maintained for smooth operation of swaps and trading functionality.
