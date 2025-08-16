#!/usr/bin/env python3
"""
Simple test script for ETH client Kafka notification
"""

import os
import sys
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from shared.logger import setup_logging

logger = setup_logging()


def test_eth_client_kafka_notification():
    """Test the ETH client's Kafka notification functionality"""
    
    # Mock configuration
    mock_config = EthereumConfig.mainnet("test-api-key")
    
    # Mock session
    mock_session = Mock()
    
    # Create ETH wallet instance
    eth_wallet = ETHWallet(
        user_id=123,
        config=mock_config,
        session=mock_session,
        logger=logger
    )
    eth_wallet.account_id = 456
    
    # Test the notification method
    test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    
    # Mock the Kafka producer
    with patch('shared.crypto.clients.eth.get_kafka_producer') as mock_get_producer:
        mock_producer = Mock()
        mock_get_producer.return_value = mock_producer
        
        # Call the notification method
        eth_wallet._notify_address_created(test_address)
        
        # Verify producer was called
        mock_producer.send.assert_called_once()
        
        # Verify topic and message format
        call_args = mock_producer.send.call_args
        assert call_args[0][0] == "ethereum-address-events"  # topic
        
        import json
        message = json.loads(call_args[0][1])
        assert message["event_type"] == "ethereum_address_created"
        assert message["address_data"]["address"] == test_address
        assert message["address_data"]["currency_code"] == "ETH"
        assert message["address_data"]["account_id"] == 456
        assert message["address_data"]["user_id"] == 123
        
        print("✅ ETH client Kafka notification test passed!")
        print(f"📨 Sent message: {message}")


def test_eth_client_create_address_with_notification():
    """Test the create_address method with notification"""
    
    # Mock configuration
    mock_config = EthereumConfig.mainnet("test-api-key")
    
    # Mock session
    mock_session = Mock()
    
    # Create ETH wallet instance
    eth_wallet = ETHWallet(
        user_id=123,
        config=mock_config,
        session=mock_session,
        logger=logger
    )
    eth_wallet.account_id = 456
    
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
        with patch('shared.crypto.clients.eth.config') as mock_config_func:
            mock_config_func.return_value = "test mnemonic"
            
            # Mock the notification method
            with patch.object(eth_wallet, '_notify_address_created') as mock_notify:
                # Call create_address with notification enabled
                eth_wallet.create_address(notify=True)
                
                # Verify notification was called
                mock_notify.assert_called_once_with("0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6")
                
                print("✅ ETH client create_address with notification test passed!")


def test_eth_client_create_address_without_notification():
    """Test the create_address method without notification"""
    
    # Mock configuration
    mock_config = EthereumConfig.mainnet("test-api-key")
    
    # Mock session
    mock_session = Mock()
    
    # Create ETH wallet instance
    eth_wallet = ETHWallet(
        user_id=123,
        config=mock_config,
        session=mock_session,
        logger=logger
    )
    eth_wallet.account_id = 456
    
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
        with patch('shared.crypto.clients.eth.config') as mock_config_func:
            mock_config_func.return_value = "test mnemonic"
            
            # Mock the notification method
            with patch.object(eth_wallet, '_notify_address_created') as mock_notify:
                # Call create_address with notification disabled
                eth_wallet.create_address(notify=False)
                
                # Verify notification was not called
                mock_notify.assert_not_called()
                
                print("✅ ETH client create_address without notification test passed!")


if __name__ == "__main__":
    print("🧪 Running ETH client Kafka notification tests...")
    
    test_eth_client_kafka_notification()
    test_eth_client_create_address_with_notification()
    test_eth_client_create_address_without_notification()
    
    print("✅ All ETH client Kafka notification tests passed!") 