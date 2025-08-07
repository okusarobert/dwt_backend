import json
import logging
import socket
import uuid
from datetime import datetime
from confluent_kafka import Producer
import os

logger = logging.getLogger("shared.kafka_producer")

class KafkaProducer:
    def __init__(self, bootstrap_servers=None, client_id=None):
        self.bootstrap_servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
        self.client_id = client_id or socket.gethostname()
        self.producer = Producer({
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': self.client_id
        })

    def send(self, topic, message: dict):
        # Add timestamp and message_id if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        if "message_id" not in message:
            message["message_id"] = str(uuid.uuid4())
        try:
            self.producer.produce(topic, json.dumps(message).encode("utf-8"))
            self.producer.flush()
            logger.info(f"Produced message to {topic}: {message}")
        except Exception as e:
            logger.error(f"Failed to produce message to {topic}: {e}")
            raise

def get_kafka_producer():
    return KafkaProducer() 