# Bitcart-Style Worker System

This document describes the implementation of a proper Bitcart-style worker system for real-time cryptocurrency updates, based on the [Bitcart worker.py](https://github.com/bitcart/bitcart/blob/master/worker.py) architecture.

## Overview

The worker system follows Bitcart's architecture by:
- **Connecting to individual cryptocurrency daemons** via WebSocket
- **Listening for real-time events** from each daemon
- **Processing events** and broadcasting them to clients
- **Managing connections** with automatic reconnection

## Architecture

### Core Components

1. **Worker** (`worker.py`)
   - Connects to cryptocurrency daemons
   - Processes real-time events
   - Manages WebSocket client connections
   - Broadcasts events to clients

2. **Daemon Connections**
   - Individual connections to each cryptocurrency daemon
   - Automatic reconnection on failure
   - Event subscription and processing

3. **Client WebSocket Server**
   - Provides WebSocket endpoint for clients
   - Handles client subscriptions
   - Broadcasts events to connected clients

## Key Features

### Real-Time Event Processing
```python
# Worker connects to daemons and processes events
async def _handle_new_transaction(self, coin_name: str, params: List):
    tx_hash = params[0]
    # Process transaction in database
    # Broadcast to WebSocket clients
```

### Automatic Reconnection
```python
# Worker automatically reconnects to daemons
while self.running:
    if not daemon.connected:
        await self._connect_to_daemon(daemon)
    await self._listen_to_daemon(daemon)
```

### Event Broadcasting
```python
# Events are broadcast to all connected clients
await self._broadcast_event({
    'event': 'new_transaction',
    'coin': coin_name,
    'tx_hash': tx_hash,
    'data': tx_data
})
```

## Installation and Setup

### 1. Install Dependencies
```bash
pip install websockets aiohttp
```

### 2. Start the Worker
```bash
# Start the crypto worker
python crypto/main.py
```

### 3. Test the Worker
```bash
# Run test client
python crypto/test_worker_client.py
```

## Configuration

### Environment Variables
```bash
# Database configuration
DB_USER=your_db_user
DB_PASS=your_db_password
POSTGRES_DB=your_database

# Cryptocurrency daemon settings
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

### Worker API

#### `start_worker(coins: List[str])`
Start the worker and connect to specified cryptocurrencies.

```python
await start_worker(["BTC", "ETH", "LTC"])
```

#### `stop_worker()`
Stop the worker gracefully.

```python
await stop_worker()
```

#### `get_worker() -> CryptoWorker`
Get the global worker instance.

```python
worker = get_worker()
status = worker.running
```

### WebSocket API

#### Connection
```
ws://localhost:8082
```

#### Subscribe to Events
```json
{
    "type": "subscribe",
    "events": ["new_transaction", "new_block", "new_payment"]
}
```

#### Get Worker Status
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
        "coin": "BTC",
        "tx_hash": "abc123...",
        "data": {
            "amount": "0.001",
            "from_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
            "to_address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
            "confirmations": 6,
            "contract": null
        }
    },
    "timestamp": 1640995200.123
}
```

#### New Block Event
```json
{
    "type": "event",
    "data": {
        "event": "new_block",
        "coin": "BTC",
        "height": 800000
    },
    "timestamp": 1640995200.123
}
```

## Comparison with Bitcart

### Similarities
- **Worker Architecture**: Central worker that connects to daemons
- **WebSocket Communication**: Real-time event streaming
- **Event Processing**: Similar event handling patterns
- **Reconnection Logic**: Automatic daemon reconnection

### Differences
- **Database Integration**: Tight integration with PostgreSQL
- **Address Management**: Database-driven address monitoring
- **Deployment**: Single worker vs distributed services
- **Client Management**: Centralized WebSocket server

## Performance Considerations

### Connection Management
- Automatic reconnection to daemons
- Connection pooling for efficiency
- Graceful error handling

### Event Processing
- Asynchronous event processing
- Database transaction batching
- Memory-efficient event broadcasting

### Scalability
- Horizontal scaling support
- Load balancing ready
- Microservice architecture compatible

## Monitoring and Debugging

### Logging
```python
# Worker logs
[WORKER] Starting worker for coins: ['BTC', 'ETH']
[WORKER] Connected to BTC
[WORKER] New transaction: abc123... for BTC
[WORKER] New WebSocket client connected. Total: 3
```

### Health Checks
```bash
# Check worker status via WebSocket
{
    "type": "get_status"
}
```

### Error Handling
- Connection failure recovery
- Event processing error handling
- Client disconnection management

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

## Troubleshooting

### Common Issues

#### Worker Not Starting
```bash
# Check database connection
python -c "from db.connection import session; print('DB OK')"

# Check cryptocurrency daemon connectivity
python crypto/test_btc_connection.py
```

#### Daemon Connection Issues
```bash
# Check daemon status
curl http://localhost:5000/spec

# Test WebSocket connection
python crypto/test_worker_client.py
```

#### Event Not Received
```bash
# Check worker status
{
    "type": "get_status"
}

# Check daemon connections
[WORKER] Connected daemons: 2/3
```

## Development

### Adding New Cryptocurrencies
1. Add coin configuration to environment
2. Update coin_info function
3. Test daemon connectivity
4. Verify event processing

### Custom Event Handlers
```python
# Add custom event handler
async def custom_transaction_handler(coin_name: str, tx_data: dict):
    # Custom processing logic
    pass

# Register handler
worker.add_event_handler("new_transaction", custom_transaction_handler)
```

### Testing
```bash
# Run worker tests
python -m pytest crypto/tests/test_worker.py

# Run integration tests
python -m pytest crypto/tests/test_integration.py
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY crypto/ ./crypto/
COPY shared/ ./shared/
COPY db/ ./db/

CMD ["python", "crypto/main.py"]
```

### Environment Configuration
```bash
# Production environment
export DB_USER=prod_user
export DB_PASS=prod_password
export BTC_NETWORK=mainnet
export BTC_HOST=btc-daemon
export BTC_PORT=5000
```

## Future Enhancements

### Planned Features
- **Lightning Network Support**: Bitcoin Lightning integration
- **Multi-Signature Wallets**: Advanced wallet support
- **Advanced Filtering**: Event filtering options
- **Mobile Push Notifications**: Real-time mobile alerts

### Performance Improvements
- **Redis Caching**: Event caching and deduplication
- **Database Connection Pooling**: Improved database performance
- **Async Transaction Processing**: Parallel transaction processing
- **Load Balancing**: Horizontal scaling support

## Contributing

### Development Setup
1. Clone the repository
2. Install dependencies
3. Set up database
4. Configure cryptocurrency daemons
5. Run tests

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Add comprehensive docstrings
- Include error handling

### Testing
```bash
# Run worker tests
python -m pytest crypto/tests/test_worker.py

# Run integration tests
python -m pytest crypto/tests/test_integration.py

# Run performance tests
python -m pytest crypto/tests/test_performance.py
```

## License

This implementation is based on the Bitcart architecture and follows similar patterns while being adapted for our specific use case.

## References

- [Bitcart Repository](https://github.com/bitcart/bitcart)
- [Bitcart Worker Architecture](https://github.com/bitcart/bitcart/blob/master/worker.py)
- [WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [Asyncio Documentation](https://docs.python.org/3/library/asyncio.html) 