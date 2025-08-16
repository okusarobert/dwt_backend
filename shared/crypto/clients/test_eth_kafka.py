#!/usr/bin/env python3
"""
Test script for Kafka notification functionality in ETH client
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from shared.logger import setup_logging

logger = setup_logging()


class TestETHWalletKafkaNotification:
    """Test class for ETH wallet Kafka notification functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        # Mock configuration
        mock_config = EthereumConfig.mainnet("test-api-key")
        
        # Mock session
        self.mock_session = Mock()
        
        # Create ETH wallet instance
        self.eth_wallet = ETHWallet(
            user_id=123,
            config=mock_config,
            session=self.mock_session,
            logger=logger
        )
        self.eth_wallet.account_id = 456
    
    def test_notify_address_created(self):
        """Test the _notify_address_created method"""
        test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Mock the Kafka producer
        with patch('shared.crypto.clients.eth.get_kafka_producer') as mock_get_producer:
            mock_producer = Mock()
            mock_get_producer.return_value = mock_producer
            
            # Call the notification method
            self.eth_wallet._notify_address_created(test_address)
            
            # Verify producer was called
            mock_producer.send.assert_called_once()
            
            # Verify topic and message format
            call_args = mock_producer.send.call_args
            assert call_args[0][0] == "ethereum-address-events"  # topic
            
            message = json.loads(call_args[0][1])
            assert message["event_type"] == "ethereum_address_created"
            assert message["address_data"]["address"] == test_address
            assert message["address_data"]["currency_code"] == "ETH"
            assert message["address_data"]["account_id"] == 456
            assert message["address_data"]["user_id"] == 123
            assert "timestamp" in message["address_data"]
    
    def test_notify_address_created_error_handling(self):
        """Test error handling in _notify_address_created method"""
        test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Mock the Kafka producer to raise an exception
        with patch('shared.crypto.clients.eth.get_kafka_producer') as mock_get_producer:
            mock_get_producer.side_effect = Exception("Kafka connection failed")
            
            # Call the notification method - should not raise exception
            try:
                self.eth_wallet._notify_address_created(test_address)
                # Should not reach here if exception was raised
                assert True  # Test passes if no exception was raised
            except Exception:
                assert False  # Test fails if exception was raised
    
    def test_create_address_with_notification(self):
        """Test create_address method with notification enabled"""
        # Mock the HD wallet
        with patch('shared.crypto.clients.eth.ETH') as mock_eth:
            mock_wallet = Mock()
            mock_wallet.from_mnemonic.return_value = mock_wallet
            mock_wallet.new_address.return_value = (
                "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                "private_key",
                "public_key"
            )
            mock_eth.return_value = mock_wallet
            
            # Mock config
            with patch('shared.crypto.clients.eth.config') as mock_config:
                mock_config.return_value = "test mnemonic"
                
                # Mock the notification method
                with patch.object(self.eth_wallet, '_notify_address_created') as mock_notify:
                    # Call create_address with notification enabled
                    self.eth_wallet.create_address(notify=True)
                    
                    # Verify notification was called
                    mock_notify.assert_called_once_with("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
    
    def test_create_address_without_notification(self):
        """Test create_address method with notification disabled"""
        # Mock the HD wallet
        with patch('shared.crypto.clients.eth.ETH') as mock_eth:
            mock_wallet = Mock()
            mock_wallet.from_mnemonic.return_value = mock_wallet
            mock_wallet.new_address.return_value = (
                "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
                "private_key",
                "public_key"
            )
            mock_eth.return_value = mock_wallet
            
            # Mock config
            with patch('shared.crypto.clients.eth.config') as mock_config:
                mock_config.return_value = "test mnemonic"
                
                # Mock the notification method
                with patch.object(self.eth_wallet, '_notify_address_created') as mock_notify:
                    # Call create_address with notification disabled
                    self.eth_wallet.create_address(notify=False)
                    
                    # Verify notification was not called
                    mock_notify.assert_not_called()
    
    def test_notify_existing_address(self):
        """Test the notify_existing_address method"""
        test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Mock the notification method
        with patch.object(self.eth_wallet, '_notify_address_created') as mock_notify:
            # Call notify_existing_address
            self.eth_wallet.notify_existing_address(test_address)
            
            # Verify _notify_address_created was called
            mock_notify.assert_called_once_with(test_address)
    
    def test_kafka_message_structure(self):
        """Test the structure of Kafka messages"""
        test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Mock the Kafka producer
        with patch('shared.crypto.clients.eth.get_kafka_producer') as mock_get_producer:
            mock_producer = Mock()
            mock_get_producer.return_value = mock_producer
            
            # Call the notification method
            self.eth_wallet._notify_address_created(test_address)
            
            # Get the sent message
            call_args = mock_producer.send.call_args
            message = json.loads(call_args[0][1])
            
            # Verify message structure
            assert "event_type" in message
            assert "address_data" in message
            assert message["event_type"] == "ethereum_address_created"
            
            address_data = message["address_data"]
            required_fields = ["address", "currency_code", "account_id", "user_id", "timestamp"]
            for field in required_fields:
                assert field in address_data
            
            # Verify data types
            assert isinstance(address_data["address"], str)
            assert isinstance(address_data["currency_code"], str)
            assert isinstance(address_data["account_id"], int)
            assert isinstance(address_data["user_id"], int)
            assert isinstance(address_data["timestamp"], str)
            
            # Verify timestamp format
            try:
                datetime.fromisoformat(address_data["timestamp"].replace('Z', '+00:00'))
                assert True  # Valid ISO format
            except ValueError:
                assert False  # Invalid timestamp format


def run_eth_kafka_tests():
    """Run all ETH Kafka notification tests"""
    logger.info("🧪 Running ETH wallet Kafka notification tests...")
    
    # Create test instance
    test_instance = TestETHWalletKafkaNotification()
    test_instance.setup_method()
    
    # Run tests
    test_instance.test_notify_address_created()
    test_instance.test_notify_address_created_error_handling()
    test_instance.test_create_address_with_notification()
    test_instance.test_create_address_without_notification()
    test_instance.test_notify_existing_address()
    test_instance.test_kafka_message_structure()
    
    logger.info("✅ All ETH wallet Kafka notification tests passed!")


if __name__ == "__main__":
    run_eth_kafka_tests() 