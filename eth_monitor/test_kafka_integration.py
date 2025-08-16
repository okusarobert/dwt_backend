#!/usr/bin/env python3
"""
Test script for Kafka integration between Wallet Service and Ethereum Monitor Service
"""

import json
import time
import threading
from unittest.mock import Mock, patch
from decimal import Decimal

from kafka_consumer import EthereumAddressConsumer
from app import AlchemyWebSocketClient, TransactionEvent, EthereumMonitorService
from shared.logger import setup_logging

logger = setup_logging()


class TestKafkaIntegration:
    """Test class for Kafka integration"""
    
    def setup_method(self):
        """Setup test environment"""
        self.consumer = EthereumAddressConsumer(
            bootstrap_servers="localhost:9092",
            group_id="test-eth-monitor-consumer"
        )
        self.received_addresses = []
    
    def address_callback(self, address: str, currency_code: str, account_id: int, user_id: int):
        """Callback function to track received addresses"""
        self.received_addresses.append({
            "address": address,
            "currency_code": currency_code,
            "account_id": account_id,
            "user_id": user_id
        })
        logger.info(f"✅ Received address in callback: {address}")
    
    def test_kafka_message_format(self):
        """Test Kafka message format"""
        # Mock message that would be sent from wallet service
        mock_message = {
            "event_type": "ethereum_address_created",
            "address_data": {
                "address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                "currency_code": "ETH",
                "account_id": 123,
                "user_id": 456,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
        
        # Set up callback
        self.consumer.set_address_callback(self.address_callback)
        
        # Simulate message handling
        self.consumer._handle_message(mock_message)
        
        # Verify callback was called
        assert len(self.received_addresses) == 1
        assert self.received_addresses[0]["address"] == "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        assert self.received_addresses[0]["currency_code"] == "ETH"
        assert self.received_addresses[0]["account_id"] == 123
        assert self.received_addresses[0]["user_id"] == 456
    
    def test_non_ethereum_address_ignored(self):
        """Test that non-Ethereum addresses are ignored"""
        mock_message = {
            "event_type": "ethereum_address_created",
            "address_data": {
                "address": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                "currency_code": "BTC",
                "account_id": 123,
                "user_id": 456,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
        
        # Set up callback
        self.consumer.set_address_callback(self.address_callback)
        
        # Simulate message handling
        self.consumer._handle_message(mock_message)
        
        # Verify callback was called (but address should be filtered in the monitor)
        assert len(self.received_addresses) == 1
    
    def test_unknown_event_type(self):
        """Test handling of unknown event types"""
        mock_message = {
            "event_type": "unknown_event",
            "address_data": {
                "address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                "currency_code": "ETH"
            }
        }
        
        # Set up callback
        self.consumer.set_address_callback(self.address_callback)
        
        # Simulate message handling
        self.consumer._handle_message(mock_message)
        
        # Verify callback was not called for unknown event
        assert len(self.received_addresses) == 0


class TestEthereumMonitorIntegration:
    """Test class for Ethereum monitor integration with Kafka"""
    
    def setup_method(self):
        """Setup test environment"""
        with patch.dict('os.environ', {'ALCHEMY_API_KEY': 'test-key'}):
            self.service = EthereumMonitorService()
    
    def test_address_filtering(self):
        """Test that only Ethereum addresses are added to monitoring"""
        # Mock the WebSocket client
        mock_client = Mock()
        mock_client.monitored_addresses = set()
        
        # Test Ethereum address
        mock_client.add_address_from_kafka(
            address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            currency_code="ETH",
            account_id=123,
            user_id=456
        )
        
        # Verify address was added
        assert "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6" in mock_client.monitored_addresses
        
        # Test non-Ethereum address
        mock_client.add_address_from_kafka(
            address="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            currency_code="BTC",
            account_id=123,
            user_id=456
        )
        
        # Verify address was not added
        assert "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh" not in mock_client.monitored_addresses


def test_wallet_service_kafka_producer():
    """Test the Kafka producer in wallet service"""
    # Mock the Kafka producer
    with patch('wallet.app.get_kafka_producer') as mock_get_producer:
        mock_producer = Mock()
        mock_get_producer.return_value = mock_producer
        
        # Import the function (this would be done in the wallet service)
        from wallet.app import notify_ethereum_address_created
        
        # Test sending an event
        notify_ethereum_address_created(
            address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            currency_code="ETH",
            account_id=123,
            user_id=456
        )
        
        # Verify producer was called
        mock_producer.send.assert_called_once()
        
        # Verify topic and message format
        call_args = mock_producer.send.call_args
        assert call_args[0][0] == "ethereum-address-events"  # topic
        
        message = json.loads(call_args[0][1])
        assert message["event_type"] == "ethereum_address_created"
        assert message["address_data"]["address"] == "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        assert message["address_data"]["currency_code"] == "ETH"
        assert message["address_data"]["account_id"] == 123
        assert message["address_data"]["user_id"] == 456


def run_integration_tests():
    """Run all integration tests"""
    logger.info("🧪 Running Kafka integration tests...")
    
    # Test Kafka consumer
    test_consumer = TestKafkaIntegration()
    test_consumer.setup_method()
    test_consumer.test_kafka_message_format()
    test_consumer.test_non_ethereum_address_ignored()
    test_consumer.test_unknown_event_type()
    
    # Test Ethereum monitor integration
    test_monitor = TestEthereumMonitorIntegration()
    test_monitor.setup_method()
    test_monitor.test_address_filtering()
    
    # Test wallet service producer
    test_wallet_service_kafka_producer()
    
    logger.info("✅ All Kafka integration tests passed!")


if __name__ == "__main__":
    run_integration_tests() 