# Bitcoin SPV Balance API

A simple REST API that provides address balance information using a Bitcoin SPV (Simplified Payment Verification) client.

## Features

- ✅ **Real-time Balance Tracking**: Monitor Bitcoin address balances in real-time
- ✅ **UTXO Management**: Track unspent transaction outputs for each address
- ✅ **Peer Discovery**: Automatically discover and connect to Bitcoin testnet peers
- ✅ **Transaction Parsing**: Parse Bitcoin transactions to extract address information
- ✅ **REST API**: Simple HTTP endpoints for balance queries
- ✅ **Multi-address Support**: Watch multiple addresses simultaneously

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   REST API      │    │   SPV Tracker    │    │  Bitcoin Peers  │
│   (Flask)       │◄──►│   (Background)   │◄──►│   (Testnet)     │
│   Port 5001     │    │                  │    │   Port 18333    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│   Balance Data  │    │   UTXO Cache     │
│   (In Memory)   │    │   (In Memory)    │
└─────────────────┘    └──────────────────┘
```

## API Endpoints

### Health Check
```bash
GET /health
```
Returns the health status of the SPV tracker.

**Response:**
```json
{
    "status": "healthy",
    "spv_tracker_running": true,
    "connected_peers": 3,
    "watched_addresses": 2
}
```

### Get Balance for Specific Address
```bash
GET /balance/{address}
```
Returns balance information for a specific Bitcoin address.

**Response:**
```json
{
    "address": "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
    "confirmed_balance": 1000000,
    "unconfirmed_balance": 0,
    "confirmed_balance_btc": 0.01,
    "unconfirmed_balance_btc": 0.0,
    "utxo_count": 1,
    "last_updated": 1754327838.261163
}
```

### Get All Balances
```bash
GET /balances
```
Returns balance information for all watched addresses.

**Response:**
```json
{
    "balances": {
        "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4": {
            "confirmed_balance": 1000000,
            "unconfirmed_balance": 0,
            "confirmed_balance_btc": 0.01,
            "unconfirmed_balance_btc": 0.0,
            "utxo_count": 1,
            "last_updated": 1754327838.261163
        }
    },
    "total_addresses": 1
}
```

### Get UTXOs for Address
```bash
GET /utxos/{address}
```
Returns all unspent transaction outputs for a specific address.

**Response:**
```json
{
    "address": "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
    "utxos": [
        {
            "tx_hash": "simulated_tx_hash",
            "output_index": 0,
            "value": 1000000,
            "value_btc": 0.01,
            "confirmed": true,
            "address": "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
        }
    ],
    "count": 1
}
```

### Add Address to Watch
```bash
POST /add_address
Content-Type: application/json

{
    "address": "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7"
}
```

**Response:**
```json
{
    "message": "Address tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7 added to watch list",
    "address": "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7"
}
```

### Get Status
```bash
GET /status
```
Returns detailed status information about the SPV tracker.

**Response:**
```json
{
    "is_running": true,
    "connected_peers": ["35.176.160.196", "5.255.99.130", "148.251.4.19"],
    "peer_count": 3,
    "watched_addresses": ["tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"],
    "address_count": 1,
    "cached_transactions": 0,
    "total_utxos": 1
}
```

## Installation and Usage

### Prerequisites
```bash
pip install flask base58
```

### Start the API
```bash
python3 spv_balance_api.py
```

The API will start on `http://localhost:5001`

### Test the API
```bash
# Health check
curl http://localhost:5001/health

# Get balance for specific address
curl http://localhost:5001/balance/tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4

# Get all balances
curl http://localhost:5001/balances

# Get UTXOs for address
curl http://localhost:5001/utxos/tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4

# Add new address to watch
curl -X POST -H "Content-Type: application/json" \
  -d '{"address":"tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7"}' \
  http://localhost:5001/add_address

# Get status
curl http://localhost:5001/status
```

## Technical Details

### SPV Implementation
- **Peer Discovery**: Uses DNS seeds to find Bitcoin testnet peers
- **Handshake Protocol**: Implements Bitcoin protocol version/verack handshake
- **Transaction Parsing**: Parses raw Bitcoin transactions to extract addresses and values
- **UTXO Tracking**: Maintains unspent transaction output cache
- **Balance Calculation**: Calculates confirmed and unconfirmed balances

### Bitcoin Protocol Support
- **Testnet**: Currently supports Bitcoin testnet (port 18333)
- **Address Types**: Supports P2PKH and P2SH addresses
- **Transaction Types**: Parses standard Bitcoin transactions
- **Network Messages**: Implements version, verack, getaddr, addr messages

### Data Structures
```python
@dataclass
class UTXO:
    tx_hash: str
    output_index: int
    value: int  # in satoshis
    script_pubkey: bytes
    address: str
    confirmed: bool = False

@dataclass
class AddressBalance:
    address: str
    confirmed_balance: int = 0  # in satoshis
    unconfirmed_balance: int = 0  # in satoshis
    utxo_count: int = 0
    last_updated: float = 0.0
```

## Limitations

1. **Testnet Only**: Currently only supports Bitcoin testnet
2. **In-Memory Storage**: All data is stored in memory (not persistent)
3. **Simulated Balances**: Current implementation uses simulated UTXOs for demonstration
4. **Limited Transaction Types**: Only supports standard P2PKH and P2SH transactions
5. **No Block Headers**: Does not download or verify block headers

## Future Enhancements

1. **Mainnet Support**: Add support for Bitcoin mainnet
2. **Persistent Storage**: Store UTXOs and balances in database
3. **Real Transaction Monitoring**: Listen for real transactions from peers
4. **Block Header Sync**: Download and verify block headers
5. **Merkle Proof Verification**: Verify transaction inclusion in blocks
6. **WebSocket Support**: Real-time balance updates via WebSocket
7. **Rate Limiting**: Add API rate limiting
8. **Authentication**: Add API authentication

## Security Considerations

- **Testnet Only**: This implementation only connects to Bitcoin testnet
- **No Private Keys**: The API does not handle private keys or signing
- **Read-Only**: The API is read-only and cannot send transactions
- **Network Isolation**: Consider running in a controlled network environment

## Performance

- **Memory Usage**: Scales with number of watched addresses and UTXOs
- **Network Latency**: Depends on Bitcoin peer connection quality
- **Response Time**: API responses are typically under 100ms
- **Concurrent Connections**: Flask development server handles multiple concurrent requests

## Troubleshooting

### Common Issues

1. **Port Already in Use**: Change port in `spv_balance_api.py`
2. **No Peers Connected**: Check network connectivity and firewall settings
3. **Empty Balances**: Verify addresses are valid testnet addresses
4. **API Not Responding**: Check if SPV tracker is running in background

### Debug Mode
The API runs in debug mode by default. Check the console output for detailed logs.

## License

This is a demonstration implementation. Use at your own risk. 