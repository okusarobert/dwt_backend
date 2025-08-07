#!/usr/bin/env python3
"""
Base Wallet Test Script
Tests the new BaseWallet class functionality
"""

import os
import logging
from decouple import config
from shared.crypto.clients.base import BaseWallet, BaseConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_base_wallet():
    """Test the Base wallet functionality"""
    logger.info("🚀 Starting Base wallet tests...")
    
    # Initialize Base configuration
    api_key = config('ALCHEMY_BASE_API_KEY', default='demo')
    base_config = BaseConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {base_config.network}")
    logger.info(f"🔗 Base URL: {base_config.base_url}")
    
    # Create a mock session (in real usage, this would be a database session)
    class MockSession:
        def add(self, obj):
            logger.info(f"Mock: Added {type(obj).__name__}")
        
        def flush(self):
            logger.info("Mock: Flushed session")
    
    mock_session = MockSession()
    
    # Initialize Base wallet
    user_id = 12345
    base_wallet = BaseWallet(
        user_id=user_id,
        config=base_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info(f"✅ Base wallet initialized for user {user_id}")
    
    # Test connection
    logger.info("\n🔍 Testing Base API connection...")
    if base_wallet.test_connection():
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed!")
        return
    
    # Test blockchain info
    logger.info("\n📊 Getting blockchain information...")
    blockchain_info = base_wallet.get_blockchain_info()
    logger.info(f"Network: {blockchain_info.get('network')}")
    logger.info(f"Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"Connection status: {blockchain_info.get('connection_status')}")
    
    # Test gas price
    logger.info("\n⛽ Getting current gas price...")
    gas_price = base_wallet.get_gas_price()
    if gas_price:
        logger.info(f"Gas price: {gas_price['gas_price_gwei']:.2f} gwei")
    
    # Test getting recent blocks
    logger.info("\n📋 Getting recent blocks...")
    recent_blocks = base_wallet.get_recent_blocks(3)
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
        is_valid = base_wallet.validate_address(addr)
        logger.info(f"Address {addr}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test getting balance for a known address
    logger.info("\n💰 Getting balance for a test address...")
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    balance = base_wallet.get_balance(test_address)
    if balance:
        logger.info(f"Balance: {balance['balance_base']:.6f} BASE ({balance['balance_wei']} wei)")
    
    # Test account info
    logger.info("\n👤 Getting account information...")
    account_info = base_wallet.get_account_info(test_address)
    if account_info:
        logger.info(f"Address: {account_info['address']}")
        logger.info(f"Transaction count: {account_info['transaction_count']}")
        logger.info(f"Is contract: {account_info['is_contract']}")
    
    # Test network info
    logger.info("\n🌐 Getting network information...")
    network_info = base_wallet.get_network_info()
    logger.info(f"Network: {network_info.get('network')}")
    logger.info(f"Latest block: {network_info.get('latest_block')}")
    
    # Test Base-specific info
    logger.info("\n🔧 Getting Base-specific information...")
    base_info = base_wallet.get_base_specific_info()
    logger.info(f"Network: {base_info.get('network')}")
    logger.info(f"Chain ID: {base_info.get('chain_id')}")
    logger.info(f"Is L2: {base_info.get('is_l2')}")
    logger.info(f"L1 Chain: {base_info.get('l1_chain')}")
    
    # Test token balance (if we have a token address)
    logger.info("\n🪙 Testing token balance functionality...")
    # Example USDC token on Base Sepolia
    usdc_token = "0x036CbD53842c5426634e7929541eC2318f3dCF7c"  # USDC on Base Sepolia
    token_balance = base_wallet.get_token_balance(usdc_token, test_address)
    if token_balance:
        logger.info(f"Token balance: {token_balance['balance']}")
        logger.info(f"Token address: {token_balance['token_address']}")
    else:
        logger.info("No token balance found or token not supported")
    
    logger.info("\n" + "="*50)
    logger.info("✅ All Base wallet tests completed!")
    logger.info("="*50)

def test_wallet_creation():
    """Test wallet creation functionality (mock)"""
    logger.info("\n🔧 Testing wallet creation functionality...")
    
    # This would normally require a database session
    # For testing, we'll just show the structure
    logger.info("📝 Wallet creation would:")
    logger.info("  1. Create Account record in database")
    logger.info("  2. Generate unique account number")
    logger.info("  3. Create BASE address using ETH HD wallet (Base uses Ethereum addresses)")
    logger.info("  4. Encrypt private key")
    logger.info("  5. Store CryptoAddress record")
    logger.info("  6. Set up webhooks (if needed)")
    
    logger.info("✅ Wallet creation test completed!")

def test_l2_features():
    """Test L2-specific features"""
    logger.info("\n🔧 Testing L2-specific features...")
    
    # Initialize Base wallet
    api_key = config('ALCHEMY_BASE_API_KEY', default='demo')
    base_config = BaseConfig.testnet(api_key)
    
    class MockSession:
        def add(self, obj):
            pass
        def flush(self):
            pass
    
    mock_session = MockSession()
    
    base_wallet = BaseWallet(
        user_id=12345,
        config=base_config,
        session=mock_session,
        logger=logger
    )
    
    # Test L2 specific features
    logger.info("📊 L2 Features:")
    logger.info("  - Faster finality than L1")
    logger.info("  - Lower gas fees")
    logger.info("  - Ethereum compatibility")
    logger.info("  - Token support (ERC-20)")
    logger.info("  - Smart contract support")
    
    # Get L2 specific info
    l2_info = base_wallet.get_base_specific_info()
    logger.info(f"  - Chain ID: {l2_info.get('chain_id')}")
    logger.info(f"  - L2 Block Number: {l2_info.get('l2_block_number')}")
    
    logger.info("✅ L2 features test completed!")

def main():
    """Main function"""
    print("🔧 Base Wallet Test Script")
    print("📡 Using Alchemy API with BaseWallet class")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_BASE_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_BASE_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using demo key for testing.")
        print()
    
    # Run tests
    test_base_wallet()
    test_wallet_creation()
    test_l2_features()

if __name__ == "__main__":
    main() 