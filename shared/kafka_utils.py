#!/usr/bin/env python3
"""
Kafka utility functions for topic management and consumer setup
"""

import logging
from typing import List, Optional
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic, ConfigResource, ResourceType
from confluent_kafka.error import KafkaException, KafkaError

logger = logging.getLogger(__name__)

class KafkaTopicManager:
    """Utility class for managing Kafka topics and ensuring they exist before consumption"""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = AdminClient({
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'kafka-topic-manager'
        })
    
    def topic_exists(self, topic_name: str) -> bool:
        """Check if a topic exists"""
        try:
            metadata = self.admin_client.list_topics(timeout=10)
            return topic_name in metadata.topics
        except KafkaException as e:
            logger.error(f"Error checking if topic {topic_name} exists: {e}")
            return False
    
    def create_topic(self, topic_name: str, num_partitions: int = 1, replication_factor: int = 1) -> bool:
        """Create a topic if it doesn't exist"""
        try:
            if self.topic_exists(topic_name):
                logger.info(f"Topic {topic_name} already exists")
                return True
            
            topic = NewTopic(
                topic=topic_name,
                num_partitions=num_partitions,
                replication_factor=replication_factor,
                config={
                    'cleanup.policy': 'delete',
                    'retention.ms': '604800000',  # 7 days
                    'segment.ms': '86400000'      # 1 day
                }
            )
            
            futures = self.admin_client.create_topics([topic])
            
            # Wait for topic creation
            for topic_name, future in futures.items():
                try:
                    future.result(timeout=10)
                    logger.info(f"Successfully created topic: {topic_name}")
                    return True
                except KafkaException as e:
                    if e.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                        logger.info(f"Topic {topic_name} already exists")
                        return True
                    else:
                        logger.error(f"Failed to create topic {topic_name}: {e}")
                        return False
                        
        except Exception as e:
            logger.error(f"Error creating topic {topic_name}: {e}")
            return False
    
    def ensure_topics_exist(self, topics: List[str], num_partitions: int = 1, replication_factor: int = 1) -> bool:
        """Ensure multiple topics exist, creating them if necessary"""
        all_created = True
        for topic in topics:
            if not self.create_topic(topic, num_partitions, replication_factor):
                all_created = False
        return all_created

def create_safe_consumer(
    topics: List[str],
    group_id: str,
    bootstrap_servers: str = "localhost:9092",
    auto_offset_reset: str = "latest",
    num_partitions: int = 1,
    replication_factor: int = 1
) -> Optional[Consumer]:
    """
    Create a Kafka consumer with automatic topic creation
    
    Args:
        topics: List of topic names to subscribe to
        group_id: Consumer group ID
        bootstrap_servers: Kafka bootstrap servers
        auto_offset_reset: Where to start reading ('earliest' or 'latest')
        num_partitions: Number of partitions for new topics
        replication_factor: Replication factor for new topics
    
    Returns:
        Consumer instance or None if creation failed
    """
    try:
        # Ensure topics exist
        topic_manager = KafkaTopicManager(bootstrap_servers)
        if not topic_manager.ensure_topics_exist(topics, num_partitions, replication_factor):
            logger.error("Failed to ensure all topics exist")
            return None
        
        # Create consumer configuration
        consumer_config = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 1000,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 10000,
            'max.poll.interval.ms': 300000,
            'fetch.min.bytes': 1,
            'fetch.wait.max.ms': 500
        }
        
        # Create consumer
        consumer = Consumer(consumer_config)
        
        # Subscribe to topics
        consumer.subscribe(topics)
        logger.info(f"Successfully created consumer for topics: {topics}")
        
        return consumer
        
    except Exception as e:
        logger.error(f"Failed to create safe consumer: {e}")
        return None

def create_safe_producer(bootstrap_servers: str = "localhost:9092") -> Optional[Producer]:
    """
    Create a Kafka producer with proper configuration
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
    
    Returns:
        Producer instance or None if creation failed
    """
    try:
        producer_config = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'notification-producer',
            'acks': 'all',
            'retries': 3,
            'retry.backoff.ms': 100,
            'linger.ms': 5,
            'batch.size': 16384,
            'compression.type': 'snappy'
        }
        
        producer = Producer(producer_config)
        logger.info("Successfully created Kafka producer")
        return producer
        
    except Exception as e:
        logger.error(f"Failed to create producer: {e}")
        return None

# Predefined topics for the notification system
NOTIFICATION_TOPICS = [
    'crypto_notifications',
    'trade_notifications', 
    'system_notifications'
]

def ensure_notification_topics(bootstrap_servers: str = "localhost:9092") -> bool:
    """Ensure all notification topics exist"""
    topic_manager = KafkaTopicManager(bootstrap_servers)
    return topic_manager.ensure_topics_exist(NOTIFICATION_TOPICS)
