# Real-Time Transaction Monitoring

## Overview

The SPV client now supports real-time transaction monitoring using WebSocket connections. This allows you to receive instant notifications when Bitcoin addresses receive new transactions or experience balance changes.

## Features

### 🔌 WebSocket Support
- Real-time balance change notifications
- New transaction alerts
- Address subscription/unsubscription
- Automatic reconnection handling

### 📊 Monitoring Capabilities
- **Balance Changes**: Detect when addresses receive or spend Bitcoin
- **New Transactions**: Get notified of incoming transactions
- **Multiple Addresses**: Monitor multiple addresses simultaneously
- **Automatic Detection**: Checks every 10 seconds for changes

## Quick Start

### 1. Start the Server
```bash
python3 spv_simple_fixed.py
```

### 2. Start Real-Time Monitoring
```bash
curl -X POST http://localhost:5005/start
```

### 3. Add Addresses to Watch
```bash
curl -X POST http://localhost:5005/add_address \
  -H "Content-Type: application/json" \
  -d '{"address": "n43gfthwVPBopwaTMjmpMAT4Nqzf95NKcy"}'
```

### 4. Use the Web Client
Open `realtime_client.html` in your browser and subscribe to addresses.

## API Endpoints

### REST API
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | Get server status and monitoring info |
| `POST` | `/start` | Start real-time monitoring |
| `POST` | `/stop` | Stop real-time monitoring |
| `POST` | `/add_address` | Add address to watch list |
| `GET` | `/balance/{address}` | Get current balance |
| `GET` | `/transactions/{address}` | Get transaction history |
| `GET` | `/utxos/{address}` | Get UTXOs for address |
| `POST` | `/scan_history/{address}` | Scan historical blocks |

### WebSocket Events

#### Client → Server
| Event | Data | Description |
|-------|------|-------------|
| `subscribe_address` | `{"address": "..."}` | Subscribe to address updates |
| `unsubscribe_address` | `{"address": "..."}` | Unsubscribe from address updates |

#### Server → Client
| Event | Data | Description |
|-------|------|-------------|
| `connected` | `{"message": "..."}` | Connection established |
| `subscribed` | `{"address": "...", "message": "..."}` | Address subscription confirmed |
| `unsubscribed` | `{"address": "...", "message": "..."}` | Address unsubscription confirmed |
| `balance_change` | Balance change data | Real-time balance update |
| `new_transactions` | Transaction data | New transaction notification |

## WebSocket Event Details

### Balance Change Event
```json
{
  "address": "n43gfthwVPBopwaTMjmpMAT4Nqzf95NKcy",
  "old_balance": 0,
  "new_balance": 1788761965,
  "old_balance_btc": 0.0,
  "new_balance_btc": 17.88761965,
  "timestamp": 1754336318.173377
}
```

### New Transactions Event
```json
{
  "address": "n43gfthwVPBopwaTMjmpMAT4Nqzf95NKcy",
  "transactions": [...],
  "count": 1,
  "timestamp": 1754336318.173377
}
```

## JavaScript Client Example

```javascript
// Connect to WebSocket server
const socket = io('http://localhost:5005');

// Handle connection
socket.on('connect', () => {
    console.log('Connected to SPV server');
});

// Subscribe to address updates
socket.emit('subscribe_address', { 
    address: 'n43gfthwVPBopwaTMjmpMAT4Nqzf95NKcy' 
});

// Listen for balance changes
socket.on('balance_change', (data) => {
    console.log(`Balance changed for ${data.address}:`);
    console.log(`  Old: ${data.old_balance_btc} BTC`);
    console.log(`  New: ${data.new_balance_btc} BTC`);
});

// Listen for new transactions
socket.on('new_transactions', (data) => {
    console.log(`New transactions for ${data.address}:`);
    console.log(`  Count: ${data.count}`);
    console.log(`  Transactions:`, data.transactions);
});
```

## Python Client Example

```python
import socketio
import time

# Create SocketIO client
sio = socketio.Client()

@sio.event
def connect():
    print('Connected to SPV server')
    # Subscribe to address
    sio.emit('subscribe_address', {'address': 'n43gfthwVPBopwaTMjmpMAT4Nqzf95NKcy'})

@sio.event
def balance_change(data):
    print(f"Balance changed for {data['address']}:")
    print(f"  Old: {data['old_balance_btc']} BTC")
    print(f"  New: {data['new_balance_btc']} BTC")

@sio.event
def new_transactions(data):
    print(f"New transactions for {data['address']}:")
    print(f"  Count: {data['count']}")

# Connect to server
sio.connect('http://localhost:5005')

# Keep connection alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    sio.disconnect()
```

## Configuration

### Monitoring Interval
The server checks for changes every 10 seconds. This can be adjusted in the `monitor_addresses_realtime()` method.

### Maximum Addresses
There's no hard limit on the number of addresses you can monitor, but performance may degrade with too many addresses.

### Network Selection
The server runs on testnet by default. Change `testnet=True` to `testnet=False` in the `SimpleSPVClient` constructor for mainnet.

## Troubleshooting

### Connection Issues
- Ensure the server is running on port 5005
- Check firewall settings
- Verify WebSocket support in your client

### No Updates
- Verify the address has transactions
- Check server logs for errors
- Ensure real-time monitoring is started

### Performance
- Monitor fewer addresses for better performance
- Increase monitoring interval if needed
- Check server resources

## Security Considerations

- The server runs in debug mode by default
- WebSocket connections are not authenticated
- Use HTTPS in production
- Implement rate limiting for production use

## Production Deployment

1. **Disable debug mode** in production
2. **Use HTTPS** for secure WebSocket connections
3. **Implement authentication** for WebSocket connections
4. **Add rate limiting** to prevent abuse
5. **Use a production WSGI server** like Gunicorn
6. **Monitor server resources** and adjust accordingly

## Example Deployment

```bash
# Install production dependencies
pip install gunicorn eventlet

# Run with Gunicorn
gunicorn --worker-class eventlet -w 1 -b 0.0.0.0:5005 spv_simple_fixed:app
```

This provides a robust, scalable real-time transaction monitoring solution for Bitcoin addresses. 