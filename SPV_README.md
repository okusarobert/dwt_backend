# Bitcoin SPV (Simplified Payment Verification) Implementation

This project implements a Bitcoin SPV client that connects to the Bitcoin network, discovers peers, and monitors transactions for specific addresses.

## What is SPV?

SPV (Simplified Payment Verification) is a method that allows lightweight Bitcoin clients to verify transactions without downloading the entire blockchain. Instead, they:

1. **Connect to multiple Bitcoin nodes** (peers)
2. **Download block headers only** (not full blocks)
3. **Request specific transactions** they're interested in
4. **Verify transaction inclusion** using Merkle proofs

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   DNS Seeds     │    │   Peer Nodes    │    │   SPV Client    │
│                 │    │                 │    │                 │
│ • testnet-seed  │───▶│ • Node 1        │◀───│ • Peer Discovery│
│ • mainnet-seed  │    │ • Node 2        │    │ • Transaction   │
│                 │    │ • Node 3        │    │   Monitoring    │
└─────────────────┘    └─────────────────┘    │ • Address Watch │
                                             └─────────────────┘
```

## Files Overview

### 1. `test_nodes.py` - Simple SPV Client
- Basic Bitcoin network protocol implementation
- Single-node connection
- Simple transaction and block listening

### 2. `spv_client.py` - Advanced SPV Client
- Full transaction parsing
- Address watching and tracking
- P2PKH and P2SH address support
- Detailed transaction analysis

### 3. `spv_peer_discovery.py` - Peer Discovery SPV
- **DNS seed resolution** for peer discovery
- **Multiple peer connections**
- **Peer address exchange**
- **Testnet3 support**

### 4. `dns_seed_resolver.py` - DNS Seed Resolver
- Resolves Bitcoin DNS seeds
- Supports both testnet and mainnet
- Returns peer IP addresses

### 5. `spv_example.py` - Usage Example
- Demonstrates how to use the SPV client
- Shows address watching
- Real-time statistics

## How Peer Discovery Works

### Step 1: DNS Seed Resolution
```python
# Query DNS seeds for initial peers
seeds = [
    "testnet-seed.bitcoin.jonasschnelli.ch",
    "testnet-seed.bluematt.me",
    # ... more seeds
]

for seed in seeds:
    ips = socket.gethostbyname_ex(seed)[2]
    # Get IP addresses from DNS
```

### Step 2: Connect to Initial Peers
```python
# Connect to discovered peers
for peer_ip in discovered_ips:
    sock = socket.connect((peer_ip, 18333))  # Testnet port
    perform_handshake(sock)
```

### Step 3: Request More Peers
```python
# Send getaddr message to request more peers
getaddr_msg = create_message(MessageType.GETADDR)
send_message(sock, getaddr_msg)
```

### Step 4: Process Address Responses
```python
# Process addr messages to discover more peers
def process_addr_message(payload):
    count = parse_varint(payload)
    for i in range(count):
        timestamp, services, ip_bytes, port = parse_address_entry()
        new_peer = Peer(ip=ip, port=port, services=services)
        peers.add(new_peer)
```

## Bitcoin Network Protocol

### Message Structure
```
┌─────────┬──────────┬─────────┬──────────┬─────────┐
│ Magic   │ Command  │ Length  │ Checksum │ Payload │
│ 4 bytes │ 12 bytes │ 4 bytes │ 4 bytes  │ N bytes │
└─────────┴──────────┴─────────┴──────────┴─────────┘
```

### Handshake Process
1. **Send version message** to peer
2. **Receive version response** from peer
3. **Send verack message** to peer
4. **Receive verack response** from peer

### Message Types
- `version` - Protocol version negotiation
- `verack` - Version acknowledgment
- `ping`/`pong` - Keep-alive messages
- `getaddr` - Request peer addresses
- `addr` - Peer address list
- `inv` - Inventory (block/tx announcements)
- `getdata` - Request specific blocks/transactions
- `block` - Full block data
- `tx` - Transaction data

## Usage Examples

### Basic SPV Client
```python
from spv_client import AdvancedSPVClient

# Create client
spv = AdvancedSPVClient(node_host="127.0.0.1", node_port=8333)

# Connect and handshake
if spv.connect() and spv.handshake():
    # Add addresses to watch
    spv.add_watch_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    
    # Start listening
    spv.start_listening()
```

### Peer Discovery SPV
```python
from spv_peer_discovery import SPVPeerDiscovery

# Create client with peer discovery
spv = SPVPeerDiscovery()

# Add addresses to watch
spv.add_watch_address("2N1LGaGg836mqSQqitUBqUQKjVT8W7q5vN")  # Testnet

# Start with peer discovery
spv.start()
```

### DNS Seed Resolution
```python
from dns_seed_resolver import DNSSeedResolver

resolver = DNSSeedResolver()

# Resolve testnet peers
testnet_peers = resolver.resolve_testnet_seeds()
print(f"Found {len(testnet_peers)} testnet peers")

# Resolve mainnet peers
mainnet_peers = resolver.resolve_mainnet_seeds()
print(f"Found {len(mainnet_peers)} mainnet peers")
```

## Network Configuration

### Testnet3
- **Magic bytes**: `0x0b110907`
- **Default port**: `18333`
- **DNS seeds**: `testnet-seed.*`
- **Address prefix**: `tb1` (P2WPKH), `2` (P2SH)

### Mainnet
- **Magic bytes**: `0xf9beb4d9`
- **Default port**: `8333`
- **DNS seeds**: `seed.*`, `dnsseed.*`
- **Address prefix**: `bc1` (P2WPKH), `1` (P2PKH), `3` (P2SH)

## Transaction Monitoring

### Address Watching
```python
# Add addresses to watch
spv.add_watch_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
spv.add_watch_address("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")

# Get transactions for address
transactions = spv.get_address_transactions("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
```

### Transaction Processing
```python
def process_transaction(tx_data):
    # Parse transaction
    tx = parse_transaction(tx_data)
    
    # Check outputs for watched addresses
    for output in tx.outputs:
        if output.address in watched_addresses:
            logger.info(f"Watched address {output.address} received {output.value} sats")
```

## Security Considerations

### SPV Security Model
- **Trust but verify**: SPV clients trust peers but verify transaction inclusion
- **Multiple peers**: Connect to multiple peers to avoid single point of failure
- **Merkle proofs**: Verify transaction inclusion without downloading full blocks

### Limitations
- **Privacy**: SPV clients reveal which addresses they're watching
- **DoS resistance**: Limited compared to full nodes
- **Fee estimation**: Less accurate than full nodes

## Installation and Setup

### Requirements
```bash
pip install -r spv_requirements.txt
```

### Dependencies
- `base58` - For Bitcoin address encoding
- `socket` - For network connections
- `hashlib` - For cryptographic hashing
- `struct` - For binary data packing

### Running the Examples
```bash
# Test DNS seed resolution
python dns_seed_resolver.py

# Run simple SPV client
python test_nodes.py

# Run advanced SPV client
python spv_client.py

# Run peer discovery SPV
python spv_peer_discovery.py

# Run example
python spv_example.py
```

## Development Notes

### Protocol Version
- **Current**: 70015 (Bitcoin Core 0.21.0+)
- **Services**: 0 (no special services)
- **User Agent**: `/SPVClient:0.1.0/`

### Error Handling
- **Connection timeouts**: 10 seconds for initial connection
- **Message timeouts**: 0.1 seconds for non-blocking reads
- **Reconnection**: Automatic peer reconnection on failure

### Performance
- **Concurrent connections**: Up to 8 peers simultaneously
- **Message processing**: Non-blocking I/O with threading
- **Memory usage**: Transaction and block caching

## Future Enhancements

1. **Merkle proof verification** - Verify transaction inclusion in blocks
2. **Bloom filters** - Privacy-preserving address watching
3. **Compact block support** - More efficient block downloading
4. **Fee estimation** - Calculate transaction fees
5. **Wallet integration** - Create and manage Bitcoin addresses
6. **WebSocket support** - Real-time transaction notifications
7. **Database storage** - Persistent transaction and block storage

## Troubleshooting

### Common Issues

1. **Connection refused**: No Bitcoin node running on specified port
2. **DNS resolution failed**: Network connectivity issues
3. **Handshake failed**: Protocol version mismatch
4. **No peers found**: DNS seeds may be temporarily unavailable

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Network Testing
```bash
# Test DNS resolution
nslookup testnet-seed.bitcoin.jonasschnelli.ch

# Test port connectivity
telnet 127.0.0.1 18333
```

## References

- [Bitcoin Developer Documentation](https://bitcoin.org/en/developer-documentation)
- [Bitcoin Protocol Documentation](https://en.bitcoin.it/wiki/Protocol_documentation)
- [Bitcoin Testnet](https://en.bitcoin.it/wiki/Testnet)
- [SPV Security](https://en.bitcoin.it/wiki/Scalability#Simplified_payment_verification) 