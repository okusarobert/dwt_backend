# Cryptocurrency Event System

This document describes the implementation of a Bitcart-style event listening system for real-time cryptocurrency transaction monitoring.

## Overview

The event system provides real-time monitoring of cryptocurrency transactions using a WebSocket-based architecture inspired by [Bitcart](https://github.com/bitcart/bitcart). It replaces the previous polling-based approach with an efficient event-driven system.

## Architecture

### Core Components

1. **Event Listener** (`event_system.py`)
   - Monitors cryptocurrency addresses for new transactions
   - Processes transaction events in real-time
   - Manages WebSocket connections for client notifications

2. **WebSocket Service** (`websocket_service.py`)
   - Provides WebSocket endpoints for real-time event streaming
   - Handles client subscriptions and message routing
   - Exposes system status and health checks

3. **Event Types**
   - `new_transaction`: New transaction detected
   - `new_block`: New block mined
   - `new_payment`: Payment received
   - `verified_tx`: Transaction verified
   - `address_update`: Address status updated

## Key Features

### Real-time Transaction Monitoring
```python
# Transaction events include:
{
    "event": "new_transaction",
    "tx_hash": "abc123...",
    "currency": "BTC",
    "from_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
    "to_address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
    "amount": "0.001",
    "confirmations": 6,
    "contract": null,
    "block_height": 800000,
    "timestamp": 1640995200
}
```

### WebSocket Client Support
```python
# Connect to WebSocket service
ws = websocket.connect("ws://localhost:8081/ws/events")

# Subscribe to events
ws.send(json.dumps({
    "type": "subscribe",
    "events": ["new_transaction", "new_block"]
}))
```

### Database Integration
- Automatic transaction processing and storage
- Duplicate transaction detection
- Account balance updates
- Transaction status tracking

## Installation and Setup

### 1. Install Dependencies
```bash
pip install aiohttp websockets
```

### 2. Start the Event Listener
```bash
# Start the crypto service with event listening
python crypto/main.py
```

### 3. Start the WebSocket Service
```bash
# Start the WebSocket service
python api/websocket_service.py
```

### 4. Run Example Client
```bash
# Test the event system
python crypto/example_client.py
```

## Configuration

### Environment Variables
```bash
# Database configuration
DB_USER=your_db_user
DB_PASS=your_db_password
POSTGRES_DB=your_database

# Cryptocurrency node settings
BTC_HOST=localhost
BTC_PORT=5000
BTC_NETWORK=testnet
BTC_LOGIN=electrum
BTC_PASSWORD=electrumz
```

### Supported Cryptocurrencies
- Bitcoin (BTC)
- Ethereum (ETH)
- Litecoin (LTC)
- Bitcoin Cash (BCH)
- Tron (TRX)
- And more...

## API Reference

### Event Listener API

#### `start_event_listener(currencies: List[str])`
Start monitoring specified cryptocurrencies.

```python
await start_event_listener(["BTC", "ETH", "LTC"])
```

#### `stop_event_listener()`
Stop the event listener gracefully.

```python
await stop_event_listener()
```

#### `get_event_listener() -> EventListener`
Get the global event listener instance.

```python
listener = get_event_listener()
status = listener.running
```

### WebSocket API

#### Connection
```
ws://localhost:8081/ws/events
```

#### Subscribe to Events
```json
{
    "type": "subscribe",
    "events": ["new_transaction", "new_block"]
}
```

#### Get System Status
```json
{
    "type": "get_status"
}
```

#### Ping/Pong
```json
{
    "type": "ping"
}
```

### Event Format

#### New Transaction Event
```json
{
    "type": "event",
    "data": {
        "event": "new_transaction",
        "tx_hash": "abc123...",
        "currency": "BTC",
        "from_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        "to_address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
        "amount": "0.001",
        "confirmations": 6,
        "contract": null,
        "block_height": 800000,
        "timestamp": 1640995200
    },
    "timestamp": 1640995200.123
}
```

## Comparison with Bitcart

### Similarities
- Event-driven architecture
- WebSocket-based real-time notifications
- Support for multiple cryptocurrencies
- Transaction event processing

### Differences
- **Centralized vs Distributed**: Our system uses a centralized event listener vs Bitcart's distributed daemon services
- **Database Integration**: Tight integration with PostgreSQL database
- **Address Management**: Database-driven address monitoring vs wallet-based tracking
- **Deployment**: Single service vs multiple coin-specific containers

## Performance Considerations

### Rate Limiting
- 10-second polling intervals per currency
- 1-second delays between address checks
- Configurable polling caps

### Memory Management
- Efficient WebSocket connection management
- Automatic cleanup of closed connections
- Transaction deduplication

### Scalability
- Horizontal scaling support
- Load balancing ready
- Microservice architecture compatible

## Monitoring and Debugging

### Logging
```python
# Event listener logs
[EVENT_LISTENER] New transaction: abc123... for BTC
[EVENT_LISTENER] New websocket connection. Total: 5
[EVENT_LISTENER] Error processing transaction event: ...
```

### Health Checks
```bash
curl http://localhost:8081/health
```

### Status Monitoring
```python
# Get system status via WebSocket
{
    "type": "get_status"
}
```

## Error Handling

### Connection Failures
- Automatic reconnection attempts
- Exponential backoff
- Graceful degradation

### Transaction Processing Errors
- Error logging and monitoring
- Retry mechanisms
- Fallback to polling mode

### WebSocket Errors
- Connection cleanup
- Client notification
- Error reporting

## Security Considerations

### Authentication
- WebSocket authentication support
- API key validation
- Rate limiting

### Data Validation
- Input sanitization
- Transaction verification
- Address validation

### Network Security
- TLS/SSL support
- Firewall configuration
- DDoS protection

## Future Enhancements

### Planned Features
- Lightning Network support
- Multi-signature wallet support
- Advanced filtering options
- Mobile push notifications

### Performance Improvements
- Redis caching integration
- Database connection pooling
- Async transaction processing
- Load balancing

## Troubleshooting

### Common Issues

#### Event Listener Not Starting
```bash
# Check database connection
python -c "from db.connection import session; print('DB OK')"

# Check cryptocurrency node connectivity
python crypto/test_btc_connection.py
```

#### WebSocket Connection Issues
```bash
# Check WebSocket service
curl http://localhost:8081/health

# Test WebSocket connection
python crypto/example_client.py
```

#### Transaction Not Detected
```bash
# Check address monitoring
python -c "from crypto.util import get_all_addresses_for_crypto; print(get_all_addresses_for_crypto('BTC'))"

# Check transaction processing
python -c "from crypto.util import check_address_txns; import asyncio; asyncio.run(check_address_txns('address', 'BTC'))"
```

## Contributing

### Development Setup
1. Clone the repository
2. Install dependencies
3. Set up database
4. Configure cryptocurrency nodes
5. Run tests

### Testing
```bash
# Run event system tests
python -m pytest crypto/tests/test_event_system.py

# Run integration tests
python -m pytest crypto/tests/test_integration.py
```

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Add comprehensive docstrings
- Include error handling

## License

This implementation is based on the Bitcart architecture and follows similar patterns while being adapted for our specific use case. 