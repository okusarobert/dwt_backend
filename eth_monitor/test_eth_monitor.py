#!/usr/bin/env python3
"""
Test script for Ethereum Transaction Monitor Service
"""

import asyncio
import json
import logging
from unittest.mock import Mock, patch
from decimal import Decimal

from app import AlchemyWebSocketClient, TransactionEvent, EthereumMonitorService
from shared.logger import setup_logging

logger = setup_logging()


class TestAlchemyWebSocketClient:
    """Test class for AlchemyWebSocketClient"""
    
    def setup_method(self):
        """Setup test environment"""
        self.api_key = "test-api-key"
        self.network = "sepolia"
        self.client = AlchemyWebSocketClient(self.api_key, self.network)
    
    def test_websocket_url_generation(self):
        """Test WebSocket URL generation"""
        expected_url = f"wss://eth-sepolia.g.alchemy.com/v2/{self.api_key}"
        assert self.client.ws_url == expected_url
    
    def test_address_management(self):
        """Test adding and removing addresses"""
        test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        
        # Test adding address
        self.client.add_address(test_address)
        assert test_address in self.client.monitored_addresses
        
        # Test removing address
        self.client.remove_address(test_address)
        assert test_address not in self.client.monitored_addresses
    
    def test_transaction_event_creation(self):
        """Test TransactionEvent creation"""
        event = TransactionEvent(
            tx_hash="0x1234567890abcdef",
            from_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            to_address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            value=Decimal("0.1"),
            block_number=12345,
            gas_price=20000000000,
            gas_used=21000,
            timestamp=1640995200
        )
        
        assert event.tx_hash == "0x1234567890abcdef"
        assert event.value == Decimal("0.1")
        assert event.block_number == 12345


class TestEthereumMonitorService:
    """Test class for EthereumMonitorService"""
    
    def setup_method(self):
        """Setup test environment"""
        with patch.dict('os.environ', {'ALCHEMY_API_KEY': 'test-key'}):
            self.service = EthereumMonitorService()
    
    def test_service_initialization(self):
        """Test service initialization"""
        assert self.service.api_key == "test-key"
        assert self.service.network == "mainnet"
        assert self.service.client is None


async def test_websocket_message_handling():
    """Test WebSocket message handling"""
    client = AlchemyWebSocketClient("test-key", "sepolia")
    
    # Mock transaction data
    mock_tx_data = {
        "hash": "0x1234567890abcdef",
        "from": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        "to": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
        "value": "0x16345785d8a0000",  # 0.1 ETH in wei
        "blockNumber": "0x3039",  # 12345
        "gasPrice": "0x4a817c800",  # 20 gwei
        "gas": "0x5208",  # 21000
        "timestamp": "0x61d4b800"  # 1640995200
    }
    
    # Add test address to monitored addresses
    test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    client.monitored_addresses.add(test_address)
    
    # Test transaction handling
    client._handle_new_transaction(mock_tx_data)
    
    # Verify the transaction was processed
    # (In a real test, you would check database records)


def test_subscription_message_format():
    """Test subscription message format"""
    client = AlchemyWebSocketClient("test-key", "sepolia")
    test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    
    # Mock WebSocket connection
    client.ws = Mock()
    client.is_connected = True
    
    # Test subscription
    client._subscribe_to_address(test_address)
    
    # Verify subscription message was sent
    client.ws.send.assert_called_once()
    sent_message = json.loads(client.ws.send.call_args[0][0])
    
    assert sent_message["method"] == "eth_subscribe"
    assert sent_message["params"][0] == "alchemy_pendingTransactions"
    assert sent_message["params"][1]["toAddress"] == test_address


def run_tests():
    """Run all tests"""
    logger.info("🧪 Running Ethereum Monitor Service tests...")
    
    # Run synchronous tests
    test_client = TestAlchemyWebSocketClient()
    test_client.setup_method()
    test_client.test_websocket_url_generation()
    test_client.test_address_management()
    test_client.test_transaction_event_creation()
    
    test_service = TestEthereumMonitorService()
    test_service.setup_method()
    test_service.test_service_initialization()
    
    # Run async tests
    asyncio.run(test_websocket_message_handling())
    
    # Run other tests
    test_subscription_message_format()
    
    logger.info("✅ All tests passed!")


if __name__ == "__main__":
    run_tests() 