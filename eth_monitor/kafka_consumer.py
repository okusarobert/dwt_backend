#!/usr/bin/env python3
"""
Kafka Consumer for Ethereum Monitor Service
Listens for new Ethereum address creation events and adds them to monitoring
"""

import json
import logging
import os
import threading
from typing import Optional, Dict, Any
from confluent_kafka import Consumer, KafkaError
from decouple import config

from shared.logger import setup_logging

logger = setup_logging()


class EthereumAddressConsumer:
    """Kafka consumer for Ethereum address creation events"""
    
    def __init__(self, bootstrap_servers: str = None, group_id: str = None):
        self.bootstrap_servers = bootstrap_servers or config('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092')
        self.group_id = group_id or 'eth-monitor-consumer'
        self.topic = config('ETH_ADDRESS_TOPIC', default='ethereum-address-events')
        self.consumer = None
        self.is_running = False
        self.address_callback = None
        
        logger.info(f"🔧 Initialized Ethereum Address Consumer")
        logger.info(f"📡 Bootstrap servers: {self.bootstrap_servers}")
        logger.info(f"👥 Group ID: {self.group_id}")
        logger.info(f"📋 Topic: {self.topic}")
    
    def set_address_callback(self, callback):
        """Set callback function to be called when new addresses are received"""
        self.address_callback = callback
        logger.info("✅ Address callback set")
    
    def _create_consumer(self):
        """Create Kafka consumer with proper configuration"""
        consumer_config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'session.timeout.ms': 30000,
            'heartbeat.interval.ms': 10000,
            'max.poll.interval.ms': 300000,
            'fetch.min.bytes': 1,
            'fetch.wait.max.ms': 500
        }
        
        self.consumer = Consumer(consumer_config)
        logger.info("✅ Kafka consumer created")
    
    def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming Kafka message"""
        try:
            logger.info(f"📨 Received message: {message}")
            
            # Parse the message
            event_type = message.get('event_type')
            address_data = message.get('address_data', {})
            
            if event_type == 'ethereum_address_created':
                # Extract address information
                address = address_data.get('address')
                currency_code = address_data.get('currency_code', 'ETH')
                account_id = address_data.get('account_id')
                user_id = address_data.get('user_id')
                
                if not address:
                    logger.warning("⚠️ No address found in message")
                    return
                
                logger.info(f"💰 New Ethereum address detected: {address}")
                logger.info(f"   Currency: {currency_code}")
                logger.info(f"   Account ID: {account_id}")
                logger.info(f"   User ID: {user_id}")
                
                # Call the callback to add address to monitoring
                if self.address_callback:
                    self.address_callback(address, currency_code, account_id, user_id)
                else:
                    logger.warning("⚠️ No address callback set")
            
            elif event_type == 'ethereum_address_deactivated':
                # Handle address deactivation
                address = address_data.get('address')
                if address and self.address_callback:
                    # You could add a remove_address_callback if needed
                    logger.info(f"🚫 Ethereum address deactivated: {address}")
            
            else:
                logger.info(f"ℹ️ Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"❌ Error handling Kafka message: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    def start_consuming(self):
        """Start consuming messages from Kafka"""
        try:
            self._create_consumer()
            self.consumer.subscribe([self.topic])
            self.is_running = True
            
            logger.info(f"🚀 Started consuming from topic: {self.topic}")
            
            while self.is_running:
                try:
                    msg = self.consumer.poll(timeout=1.0)
                    
                    if msg is None:
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            logger.info(f"📖 Reached end of partition: {msg.topic()}[{msg.partition()}] at offset {msg.offset()}")
                        else:
                            logger.error(f"❌ Kafka error: {msg.error()}")
                        continue
                    
                    # Parse message
                    try:
                        message_data = json.loads(msg.value().decode('utf-8'))
                        self._handle_message(message_data)
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse message: {e}")
                        logger.error(f"❌ Raw message: {msg.value()}")
                    except Exception as e:
                        logger.error(f"❌ Error processing message: {e}")
                
                except KeyboardInterrupt:
                    logger.info("🛑 Received interrupt signal")
                    break
                except Exception as e:
                    logger.error(f"❌ Error in consumer loop: {e}")
                    import traceback
                    logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        except Exception as e:
            logger.error(f"❌ Error starting consumer: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the consumer"""
        logger.info("🛑 Stopping Kafka consumer")
        self.is_running = False
        
        if self.consumer:
            self.consumer.close()
            logger.info("✅ Kafka consumer closed")
    
    def start_in_background(self):
        """Start consumer in a background thread"""
        consumer_thread = threading.Thread(
            target=self.start_consuming,
            daemon=True,
            name="EthereumAddressConsumer"
        )
        consumer_thread.start()
        logger.info("🔄 Started Kafka consumer in background thread")
        return consumer_thread


# Global consumer instance
_consumer_instance = None


def get_ethereum_address_consumer() -> EthereumAddressConsumer:
    """Get the global consumer instance"""
    global _consumer_instance
    if _consumer_instance is None:
        _consumer_instance = EthereumAddressConsumer()
    return _consumer_instance


def start_ethereum_address_consumer(address_callback=None) -> EthereumAddressConsumer:
    """Start the Ethereum address consumer"""
    consumer = get_ethereum_address_consumer()
    
    if address_callback:
        consumer.set_address_callback(address_callback)
    
    consumer.start_in_background()
    return consumer


def stop_ethereum_address_consumer():
    """Stop the Ethereum address consumer"""
    global _consumer_instance
    if _consumer_instance:
        _consumer_instance.stop()
        _consumer_instance = None
        logger.info("✅ Ethereum address consumer stopped") 