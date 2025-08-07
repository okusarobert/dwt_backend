#!/usr/bin/env python3
"""
Ethereum Wallet Test Script
Tests the new ETHWallet class functionality
"""

import os
import logging
from decouple import config
from shared.crypto.clients.eth import ETHWallet, EthereumConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_ethereum_wallet():
    """Test the Ethereum wallet functionality"""
    logger.info("🚀 Starting Ethereum wallet tests...")
    
    # Initialize Ethereum configuration
    api_key = config('ALCHEMY_API_KEY', default='demo')
    eth_config = EthereumConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {eth_config.network}")
    logger.info(f"🔗 Base URL: {eth_config.base_url}")
    
    # Create a mock session (in real usage, this would be a database session)
    class MockSession:
        def add(self, obj):
            logger.info(f"Mock: Added {type(obj).__name__}")
        
        def flush(self):
            logger.info("Mock: Flushed session")
    
    mock_session = MockSession()
    
    # Initialize ETH wallet
    user_id = 12345
    eth_wallet = ETHWallet(
        user_id=user_id,
        config=eth_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info(f"✅ ETH wallet initialized for user {user_id}")
    
    # Test connection
    logger.info("\n🔍 Testing Alchemy API connection...")
    if eth_wallet.test_connection():
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed!")
        return
    
    # Test blockchain info
    logger.info("\n📊 Getting blockchain information...")
    blockchain_info = eth_wallet.get_blockchain_info()
    logger.info(f"Network: {blockchain_info.get('network')}")
    logger.info(f"Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"Connection status: {blockchain_info.get('connection_status')}")
    
    # Test gas price
    logger.info("\n⛽ Getting current gas price...")
    gas_price = eth_wallet.get_gas_price()
    if gas_price:
        logger.info(f"Gas price: {gas_price['gas_price_gwei']:.2f} gwei")
    
    # Test getting recent blocks
    logger.info("\n📋 Getting recent blocks...")
    recent_blocks = eth_wallet.get_recent_blocks(3)
    logger.info(f"Retrieved {len(recent_blocks)} recent blocks")
    
    # Test address validation
    logger.info("\n🔍 Testing address validation...")
    test_addresses = [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",  # Valid
        "0x1234567890123456789012345678901234567890",  # Valid
        "invalid_address",  # Invalid
        "0x123",  # Invalid
    ]
    
    for addr in test_addresses:
        is_valid = eth_wallet.validate_address(addr)
        logger.info(f"Address {addr}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test getting balance for a known address (Vitalik's address)
    logger.info("\n💰 Getting balance for Vitalik's address...")
    vitalik_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    balance = eth_wallet.get_balance(vitalik_address)
    if balance:
        logger.info(f"Balance: {balance['balance_eth']:.6f} ETH ({balance['balance_wei']} wei)")
    
    # Test account info
    logger.info("\n👤 Getting account information...")
    account_info = eth_wallet.get_account_info(vitalik_address)
    if account_info:
        logger.info(f"Address: {account_info['address']}")
        logger.info(f"Transaction count: {account_info['transaction_count']}")
        logger.info(f"Is contract: {account_info['is_contract']}")
    
    # Test network info
    logger.info("\n🌐 Getting network information...")
    network_info = eth_wallet.get_network_info()
    logger.info(f"Network: {network_info.get('network')}")
    logger.info(f"Latest block: {network_info.get('latest_block')}")
    
    logger.info("\n" + "="*50)
    logger.info("✅ All Ethereum wallet tests completed!")
    logger.info("="*50)

def test_wallet_creation():
    """Test wallet creation functionality (mock)"""
    logger.info("\n🔧 Testing wallet creation functionality...")
    
    # This would normally require a database session
    # For testing, we'll just show the structure
    logger.info("📝 Wallet creation would:")
    logger.info("  1. Create Account record in database")
    logger.info("  2. Generate unique account number")
    logger.info("  3. Create ETH address using HD wallet")
    logger.info("  4. Encrypt private key")
    logger.info("  5. Store CryptoAddress record")
    logger.info("  6. Set up webhooks (if needed)")
    
    logger.info("✅ Wallet creation test completed!")

def main():
    """Main function"""
    print("🔧 Ethereum Wallet Test Script")
    print("📡 Using Alchemy API with ETHWallet class")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using demo key for testing.")
        print()
    
    # Run tests
    test_ethereum_wallet()
    test_wallet_creation()

if __name__ == "__main__":
    main() 