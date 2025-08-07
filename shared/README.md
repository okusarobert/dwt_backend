# Shared Kafka Producer

This module provides a reusable KafkaProducer for emitting events from any microservice.

## Usage
```python
from shared.kafka_producer import get_kafka_producer

producer = get_kafka_producer()
producer.send('topic-name', {'key': 'value'})
```

- Automatically adds `timestamp` and `message_id` if not present.
- Handles JSON serialization and error logging.

## Environment Variables
- `KAFKA_BOOTSTRAP_SERVERS` (default: `kafka:9092`)

## Integration
- Import and use in any service (betting, wallet, etc.)
- No need to instantiate `confluent_kafka.Producer` directly.

## Testing
- Unit tests mock the Kafka producer, no real broker required.
- See `test_kafka_producer.py` for examples. 