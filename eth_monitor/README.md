# Ethereum Transaction Monitor Service

A microservice for monitoring Ethereum addresses and processing new transactions using Alchemy's WebSocket API.

## Overview

This service provides real-time monitoring of Ethereum addresses for new transactions. It integrates with your existing DWT Backend architecture and follows the same microservice patterns as other services in your project.

## Features

- **Real-time Transaction Monitoring**: Uses Alchemy WebSocket API for instant transaction notifications
- **Database Integration**: Automatically creates transaction records and updates account balances
- **Multi-Network Support**: Supports mainnet, sepolia, and holesky networks
- **Address Management**: Dynamically loads addresses from database and manages subscriptions
- **Kafka Integration**: Listens for new Ethereum address creation events from wallet service
- **Duplicate Prevention**: Prevents processing the same transaction multiple times
- **Error Handling**: Robust error handling and logging
- **Health Checks**: Built-in health check endpoints
- **Kubernetes Ready**: Complete Kubernetes deployment manifests

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Alchemy API   │    │  ETH Monitor     │    │   Database      │
│   WebSocket     │◄──►│   Service        │◄──►│   (PostgreSQL)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Notifications │
                       │   (Kafka/WS)    │
                       └─────────────────┘
```

## Prerequisites

- Python 3.11+
- PostgreSQL database
- Alchemy API key
- Docker (for containerization)
- Kubernetes (for deployment)

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ALCHEMY_API_KEY` | Your Alchemy API key | - | Yes |
| `ETH_NETWORK` | Ethereum network (mainnet/sepolia/holesky) | mainnet | No |
| `DB_HOST` | Database host | localhost | No |
| `DB_PORT` | Database port | 5432 | No |
| `DB_NAME` | Database name | dwt_backend | No |
| `DB_USER` | Database user | postgres | No |
| `DB_PASSWORD` | Database password | - | Yes |
| `APP_SECRET` | Application secret for encryption | - | Yes |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka bootstrap servers | kafka:9092 | No |
| `ETH_ADDRESS_TOPIC` | Kafka topic for Ethereum address events | ethereum-address-events | No |

## Installation

### Local Development

1. Clone the repository and navigate to the service directory:
```bash
cd eth_monitor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export ALCHEMY_API_KEY="your-alchemy-api-key"
export DB_PASSWORD="your-db-password"
export APP_SECRET="your-app-secret"
```

4. Run the service:
```bash
python app.py
```

### Docker

1. Build the Docker image:
```bash
docker build -t eth-monitor .
```

2. Run the container:
```bash
docker run -d \
  --name eth-monitor \
  -e ALCHEMY_API_KEY="your-alchemy-api-key" \
  -e DB_PASSWORD="your-db-password" \
  -e APP_SECRET="your-app-secret" \
  eth-monitor
```

### Kubernetes

1. Create the namespace (if not exists):
```bash
kubectl create namespace default
```

2. Apply the Kubernetes manifests:
```bash
# Apply ConfigMap
kubectl apply -f manifests/eth-monitor-config.yaml

# Apply Secret (update with your actual values)
kubectl apply -f manifests/eth-monitor-secret.yaml

# Apply Service
kubectl apply -f manifests/service.yaml

# Apply Deployment
kubectl apply -f manifests/eth-monitor.deploy.yaml
```

## Configuration

### Network Selection

The service supports multiple Ethereum networks:

- **Mainnet**: Production Ethereum network
- **Sepolia**: Testnet for development
- **Holesky**: Testnet for development

Set the `ETH_NETWORK` environment variable to choose the network.

### Database Configuration

The service automatically connects to your existing database and uses the same models as other services:

- `CryptoAddress`: Stores monitored addresses
- `Transaction`: Stores processed transactions
- `Account`: Updates account balances

### Transaction Processing

The service processes transactions as follows:

1. **Detection**: Receives transaction notifications via WebSocket
2. **Validation**: Checks if transaction involves monitored addresses
3. **Deduplication**: Prevents processing duplicate transactions
4. **Database Update**: Creates transaction record and updates balance
5. **Notification**: Sends notification about new transaction

### Address Management

The service manages Ethereum addresses through multiple sources:

1. **Database Loading**: Loads existing addresses from database on startup
2. **Kafka Events**: Listens for new address creation events from wallet service
3. **Dynamic Addition**: Automatically adds new addresses to monitoring
4. **WebSocket Subscription**: Subscribes to new addresses via Alchemy WebSocket

## API Endpoints

The service provides the following endpoints:

### Health Check
```
GET /health
```
Returns service health status.

### Status
```
GET /status
```
Returns current monitoring status and statistics.

## Monitoring and Logging

### Log Levels

- `INFO`: General service information
- `WARNING`: Non-critical issues
- `ERROR`: Critical errors
- `DEBUG`: Detailed debugging information

### Key Metrics

- Number of monitored addresses
- Transaction processing rate
- WebSocket connection status
- Database connection status

## Testing

Run the test suite:

```bash
python test_eth_monitor.py
```

Run Kafka integration tests:

```bash
python test_kafka_integration.py
```

The tests cover:
- WebSocket URL generation
- Address management
- Transaction event creation
- Service initialization
- Message handling
- Kafka consumer functionality
- Address filtering (Ethereum only)
- Kafka producer integration

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check your Alchemy API key
   - Verify network connectivity
   - Ensure API key has WebSocket permissions

2. **Database Connection Failed**
   - Verify database credentials
   - Check database server status
   - Ensure database schema is up to date

3. **No Transactions Detected**
   - Verify addresses are active in database
   - Check if addresses have recent activity
   - Ensure WebSocket subscription is active

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python app.py
```

## Security Considerations

- **API Key Protection**: Store Alchemy API key securely
- **Database Security**: Use strong database passwords
- **Network Security**: Use HTTPS for external communications
- **Access Control**: Limit service access to necessary resources

## Performance

### Resource Requirements

- **CPU**: 250m (request) / 500m (limit)
- **Memory**: 256Mi (request) / 512Mi (limit)
- **Storage**: Minimal (logs only)

### Scaling

The service is designed to run as a single instance. For high availability:

1. **Horizontal Scaling**: Run multiple instances
2. **Load Balancing**: Use Kubernetes service
3. **Monitoring**: Implement proper monitoring and alerting

## Integration

### With Other Services

The service integrates with:

- **Wallet Service**: Uses same database models
- **WebSocket Service**: Can send real-time notifications
- **API Gateway**: Can be accessed via API
- **Admin Panel**: Can be monitored via admin interface

### Event System

The service can be extended to:

- Send notifications to Kafka
- Update WebSocket clients
- Trigger webhooks
- Send email notifications

## Contributing

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Submit pull requests

## License

This service is part of the DWT Backend project and follows the same licensing terms.

## Support

For issues and questions:

1. Check the logs for error messages
2. Review the troubleshooting section
3. Contact the development team
4. Create an issue in the project repository 