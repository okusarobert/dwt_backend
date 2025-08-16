# DT Exchange Trading System

A comprehensive cryptocurrency trading platform with multiple payment methods, real-time updates, and beautiful PayPal-style UI.

## 🚀 Features

### **Multi-Payment Support**
- **Mobile Money** (MTN, Airtel) via Relworx integration
- **Bank Deposits** with manual verification
- **Vouchers** (UGX/USD) with secure validation
- **Crypto-to-Crypto** trading

### **Real-Time Features**
- **Live price updates** via WebSocket
- **Instant trade notifications**
- **Real-time transaction status**
- **Live trading activity feed**

### **Security & Compliance**
- **6-digit OTP verification** for email
- **Secure voucher system** with expiration
- **Webhook verification** for mobile money
- **Transaction audit trail**
- **Rate limiting** and fraud prevention

### **Beautiful UI/UX**
- **PayPal-style design** with modern aesthetics
- **Responsive layout** for all devices
- **Smooth animations** and transitions
- **Intuitive trading interface**
- **Real-time feedback** and notifications

## 🏗️ Architecture

### **Backend Services**

#### **1. Wallet Service** (`wallet/`)
- **Trading endpoints** for buy/sell operations
- **Account management** and balance tracking
- **Transaction processing** and ledger entries
- **Webhook handling** for payment providers

#### **2. Auth Service** (`auth/`)
- **Email verification** with Resend integration
- **Voucher management** system
- **Trade notifications** via email
- **User authentication** and session management

#### **3. WebSocket Service** (`websocket/`)
- **Real-time updates** for trading activity
- **Price broadcasting** to all connected clients
- **User-specific notifications**
- **System-wide announcements**

### **Frontend Components**

#### **1. Trading Interface** (`client/app/trading/`)
- **Buy/Sell forms** with dynamic calculation
- **Payment method selection** with validation
- **Real-time price display** and updates
- **Trade history** and status tracking

#### **2. WebSocket Integration** (`client/hooks/use-websocket.ts`)
- **Automatic reconnection** handling
- **Event-driven updates** for real-time data
- **Error handling** and fallback mechanisms

## 📊 Database Schema

### **Core Trading Tables**

```sql
-- Trades table for all trading operations
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    trade_type VARCHAR(10) NOT NULL, -- 'buy' or 'sell'
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    crypto_currency VARCHAR(10) NOT NULL,
    crypto_amount NUMERIC(20, 8) NOT NULL,
    fiat_currency VARCHAR(3) NOT NULL,
    fiat_amount NUMERIC(15, 2) NOT NULL,
    exchange_rate NUMERIC(20, 8) NOT NULL,
    fee_amount NUMERIC(15, 2),
    payment_method VARCHAR(20) NOT NULL,
    payment_provider VARCHAR(20),
    payment_reference VARCHAR(128),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Vouchers table for voucher payments
CREATE TABLE vouchers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(16) UNIQUE NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL, -- 'UGX' or 'USD'
    status VARCHAR(20) DEFAULT 'active',
    user_id INTEGER REFERENCES users(id),
    used_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

## 🔧 API Endpoints

### **Trading Endpoints**

```bash
# Get current crypto prices
GET /api/trading/prices?crypto=BTC&fiat=USD

# Calculate trade amounts with fees
POST /api/trading/calculate
{
  "crypto_currency": "BTC",
  "fiat_currency": "USD",
  "amount": 100,
  "trade_type": "buy",
  "payment_method": "mobile_money"
}

# Execute buy order
POST /api/trading/buy
{
  "crypto_currency": "BTC",
  "fiat_currency": "USD",
  "amount": 100,
  "payment_method": "mobile_money",
  "payment_details": {
    "phone_number": "+256700000000"
  }
}

# Execute sell order
POST /api/trading/sell
{
  "crypto_currency": "BTC",
  "fiat_currency": "USD",
  "amount": 0.001,
  "payment_method": "mobile_money",
  "payment_details": {
    "phone_number": "+256700000000"
  }
}

# Get user trade history
GET /api/trading/trades?limit=50

# Get specific trade details
GET /api/trading/trades/{trade_id}

# Cancel pending trade
POST /api/trading/trades/{trade_id}/cancel

# Validate voucher code
POST /api/trading/vouchers/validate
{
  "voucher_code": "ABC123DEF456",
  "currency": "USD"
}

# Get available payment methods
GET /api/trading/payment-methods
```

### **WebSocket Events**

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:5000/ws/trading');

// Authenticate user
ws.send(JSON.stringify({
  type: 'authenticate',
  token: 'user-jwt-token'
}));

// Listen for trade updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'trade_update':
      // Handle trade status updates
      break;
    case 'price_update':
      // Handle price changes
      break;
    case 'notification':
      // Handle user notifications
      break;
  }
};
```

## 💳 Payment Methods

### **1. Mobile Money (Relworx)**
- **Providers**: MTN, Airtel
- **Fee**: 2.5%
- **Processing**: Instant
- **Webhook**: Real-time status updates

### **2. Bank Deposit**
- **Fee**: 1.5%
- **Processing**: 1-2 hours
- **Verification**: Manual review
- **Reference**: Auto-generated deposit codes

### **3. Vouchers**
- **Currencies**: UGX, USD
- **Fee**: 1.0%
- **Processing**: Instant
- **Security**: 6-digit codes with expiration

### **4. Crypto-to-Crypto**
- **Fee**: 0.5%
- **Processing**: Instant
- **Supported**: BTC, ETH, SOL, TRX

## 🔐 Security Features

### **Authentication & Authorization**
- **JWT tokens** for API access
- **WebSocket authentication** for real-time features
- **Role-based access** control
- **Session management** with expiration

### **Payment Security**
- **Webhook signature verification** for Relworx
- **Voucher code encryption** and validation
- **Transaction signing** for crypto operations
- **Rate limiting** to prevent abuse

### **Data Protection**
- **Encrypted storage** for sensitive data
- **Audit logging** for all transactions
- **Backup and recovery** procedures
- **GDPR compliance** measures

## 📧 Email Notifications

### **Trade Completion Emails**
- **Beautiful HTML templates** with PayPal styling
- **Detailed trade summaries** with all relevant information
- **Security notices** and support contact
- **Mobile-responsive** design

### **Email Types**
1. **Buy Completion**: Confirms crypto purchase
2. **Sell Completion**: Confirms fiat receipt
3. **Trade Failed**: Explains failure and next steps
4. **Email Verification**: 6-digit OTP codes

## 🚀 Deployment

### **Environment Variables**

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/dbname

# JWT Secret
SECRET_KEY=your-super-secret-jwt-key

# Resend Email
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
RESEND_FROM_EMAIL=no-reply@badix.io

# Relworx Mobile Money
RELWORX_API_KEY=your-relworx-api-key
RELWORX_WEBHOOK_SECRET=your-webhook-secret

# WebSocket
WS_URL=ws://localhost:5000

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

### **Docker Compose Setup**

```yaml
version: '3.8'
services:
  wallet:
    build: ./wallet
    ports:
      - "5001:5000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
      - kafka

  auth:
    build: ./auth
    ports:
      - "5002:5000"
    environment:
      - RESEND_API_KEY=${RESEND_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres
      - kafka

  websocket:
    build: ./websocket
    ports:
      - "5003:5000"
    environment:
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}

  client:
    build: ./client
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_BACKEND_URL=http://localhost:5001
      - NEXT_PUBLIC_WS_URL=ws://localhost:5003
```

## 🧪 Testing

### **Backend Testing**

```bash
# Test trading service
cd wallet
python -m pytest tests/test_trading.py

# Test email notifications
cd auth
python -m pytest tests/test_notifications.py

# Test WebSocket connections
cd websocket
python -m pytest tests/test_websocket.py
```

### **Frontend Testing**

```bash
# Test trading interface
cd client
npm run test:trading

# Test WebSocket integration
npm run test:websocket

# E2E testing
npm run test:e2e
```

## 📈 Monitoring & Analytics

### **Key Metrics**
- **Trade volume** by payment method
- **Success rates** for different currencies
- **User engagement** and retention
- **System performance** and uptime

### **Logging**
- **Structured JSON logging** for all services
- **Error tracking** and alerting
- **Performance monitoring** with metrics
- **Audit trails** for compliance

## 🔄 Workflow Examples

### **Buy Crypto with Mobile Money**

1. **User selects** BTC and enters $100
2. **System calculates** fees and crypto amount
3. **User provides** phone number
4. **System creates** Relworx payment request
5. **User receives** mobile money prompt
6. **Payment confirmed** via webhook
7. **Crypto transferred** from reserve to user
8. **Email notification** sent to user
9. **Real-time update** via WebSocket

### **Sell Crypto for Fiat**

1. **User selects** BTC and enters amount
2. **System validates** user has sufficient balance
3. **System calculates** fiat amount and fees
4. **Crypto transferred** from user to reserve
5. **Fiat credited** to user account
6. **Email notification** sent to user
7. **Real-time update** via WebSocket

## 🛠️ Development

### **Local Development Setup**

```bash
# Clone repository
git clone https://github.com/your-org/dt-exchange.git
cd dt-exchange

# Install dependencies
pip install -r requirements.txt
npm install

# Setup database
alembic upgrade head

# Start services
docker-compose up -d

# Run development servers
npm run dev  # Frontend
python wallet/app.py  # Wallet service
python auth/app.py  # Auth service
python websocket/app.py  # WebSocket service
```

### **Code Structure**

```
dt-exchange/
├── wallet/                 # Trading service
│   ├── app.py             # Main application
│   ├── trading_service.py # Business logic
│   └── tests/             # Unit tests
├── auth/                  # Authentication service
│   ├── app.py             # Main application
│   ├── jobs.py            # Email processing
│   └── trade_notification_service.py
├── websocket/             # Real-time service
│   ├── app.py             # WebSocket server
│   └── tests/             # WebSocket tests
├── client/                # Frontend application
│   ├── app/trading/       # Trading interface
│   ├── hooks/             # React hooks
│   └── components/        # UI components
└── shared/                # Shared utilities
    ├── crypto/            # Crypto utilities
    └── kafka_producer.py  # Message queuing
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Add** tests for new functionality
5. **Submit** a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Email**: support@badix.io
- **Documentation**: [docs.dtexchange.com](https://docs.dtexchange.com)
- **Issues**: [GitHub Issues](https://github.com/your-org/dt-exchange/issues)

---

**Built with ❤️ by the DT Exchange Team**
