#!/usr/bin/env python3
"""
Avalanche Wallet Test Script
Tests the new AVAXWallet class functionality
"""

import os
import logging
from decouple import config
from shared.crypto.clients.avax import AVAXWallet, AvalancheConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_avalanche_wallet():
    """Test the Avalanche wallet functionality"""
    logger.info("🚀 Starting Avalanche wallet tests...")
    
    # Initialize Avalanche configuration
    api_key = config('ALCHEMY_AVALANCHE_API_KEY', default='demo')
    avax_config = AvalancheConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {avax_config.network}")
    logger.info(f"🔗 Base URL: {avax_config.base_url}")
    
    # Create a mock session (in real usage, this would be a database session)
    class MockSession:
        def add(self, obj):
            logger.info(f"Mock: Added {type(obj).__name__}")
        
        def flush(self):
            logger.info("Mock: Flushed session")
    
    mock_session = MockSession()
    
    # Initialize AVAX wallet
    user_id = 12345
    avax_wallet = AVAXWallet(
        user_id=user_id,
        config=avax_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info(f"✅ AVAX wallet initialized for user {user_id}")
    
    # Test connection
    logger.info("\n🔍 Testing Avalanche API connection...")
    if avax_wallet.test_connection():
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed!")
        return
    
    # Test blockchain info
    logger.info("\n📊 Getting blockchain information...")
    blockchain_info = avax_wallet.get_blockchain_info()
    logger.info(f"Network: {blockchain_info.get('network')}")
    logger.info(f"Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"Connection status: {blockchain_info.get('connection_status')}")
    
    # Test gas price
    logger.info("\n⛽ Getting current gas price...")
    gas_price = avax_wallet.get_gas_price()
    if gas_price:
        logger.info(f"Gas price: {gas_price['gas_price_navax']:.2f} nAVAX")
    
    # Test getting recent blocks
    logger.info("\n📋 Getting recent blocks...")
    recent_blocks = avax_wallet.get_recent_blocks(3)
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
        is_valid = avax_wallet.validate_address(addr)
        logger.info(f"Address {addr}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test getting balance for a known address
    logger.info("\n💰 Getting balance for a test address...")
    test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    balance = avax_wallet.get_balance(test_address)
    if balance:
        logger.info(f"Balance: {balance['balance_avax']:.6f} AVAX ({balance['balance_wei']} wei)")
    
    # Test account info
    logger.info("\n👤 Getting account information...")
    account_info = avax_wallet.get_account_info(test_address)
    if account_info:
        logger.info(f"Address: {account_info['address']}")
        logger.info(f"Transaction count: {account_info['transaction_count']}")
        logger.info(f"Is contract: {account_info['is_contract']}")
    
    # Test network info
    logger.info("\n🌐 Getting network information...")
    network_info = avax_wallet.get_network_info()
    logger.info(f"Network: {network_info.get('network')}")
    logger.info(f"Latest block: {network_info.get('latest_block')}")
    
    # Test Avalanche-specific info
    logger.info("\n🔧 Getting Avalanche-specific information...")
    avax_info = avax_wallet.get_avalanche_specific_info()
    logger.info(f"Network: {avax_info.get('network')}")
    logger.info(f"Chain ID: {avax_info.get('chain_id')}")
    logger.info(f"Consensus: {avax_info.get('consensus')}")
    logger.info(f"Subnet: {avax_info.get('subnet')}")
    logger.info(f"Native Token: {avax_info.get('native_token')}")
    
    # Test subnet info
    logger.info("\n🔧 Getting subnet information...")
    subnet_info = avax_wallet.get_subnet_info()
    logger.info(f"Subnet: {subnet_info.get('subnet')}")
    logger.info(f"Description: {subnet_info.get('description')}")
    logger.info(f"Block Time: {subnet_info.get('block_time')}")
    logger.info(f"Finality: {subnet_info.get('finality')}")
    
    # Test token balance (if we have a token address)
    logger.info("\n🪙 Testing token balance functionality...")
    # Example USDC token on Avalanche Testnet
    usdc_token = "0x5425890298aed601595a70AB815c96711a31Bc65"  # USDC on Avalanche Testnet
    token_balance = avax_wallet.get_token_balance(usdc_token, test_address)
    if token_balance:
        logger.info(f"Token balance: {token_balance['balance']}")
        logger.info(f"Token address: {token_balance['token_address']}")
    else:
        logger.info("No token balance found or token not supported")
    
    logger.info("\n" + "="*50)
    logger.info("✅ All Avalanche wallet tests completed!")
    logger.info("="*50)

def test_wallet_creation():
    """Test wallet creation functionality (mock)"""
    logger.info("\n🔧 Testing wallet creation functionality...")
    
    # This would normally require a database session
    # For testing, we'll just show the structure
    logger.info("📝 Wallet creation would:")
    logger.info("  1. Create Account record in database")
    logger.info("  2. Generate unique account number")
    logger.info("  3. Create AVAX address using ETH HD wallet (Avalanche uses Ethereum addresses)")
    logger.info("  4. Encrypt private key")
    logger.info("  5. Store CryptoAddress record")
    logger.info("  6. Set up webhooks (if needed)")
    
    logger.info("✅ Wallet creation test completed!")

def test_avalanche_features():
    """Test Avalanche-specific features"""
    logger.info("\n🔧 Testing Avalanche-specific features...")
    
    # Initialize Avalanche wallet
    api_key = config('ALCHEMY_AVALANCHE_API_KEY', default='demo')
    avax_config = AvalancheConfig.testnet(api_key)
    
    class MockSession:
        def add(self, obj):
            pass
        def flush(self):
            pass
    
    mock_session = MockSession()
    
    avax_wallet = AVAXWallet(
        user_id=12345,
        config=avax_config,
        session=mock_session,
        logger=logger
    )
    
    # Test Avalanche specific features
    logger.info("📊 Avalanche Features:")
    logger.info("  - Fast finality (~3 seconds)")
    logger.info("  - High throughput")
    logger.info("  - Low gas fees")
    logger.info("  - EVM compatibility")
    logger.info("  - Multiple subnets")
    logger.info("  - Proof of Stake consensus")
    
    # Get Avalanche specific info
    avax_info = avax_wallet.get_avalanche_specific_info()
    logger.info(f"  - Chain ID: {avax_info.get('chain_id')}")
    logger.info(f"  - Subnet: {avax_info.get('subnet')}")
    
    # Get subnet info
    subnet_info = avax_wallet.get_subnet_info()
    logger.info(f"  - Block Time: {subnet_info.get('block_time')}")
    logger.info(f"  - Finality: {subnet_info.get('finality')}")
    
    logger.info("✅ Avalanche features test completed!")

def main():
    """Main function"""
    print("🔧 Avalanche Wallet Test Script")
    print("📡 Using Alchemy API with AVAXWallet class")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_AVALANCHE_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_AVALANCHE_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using demo key for testing.")
        print()
    
    # Run tests
    test_avalanche_wallet()
    test_wallet_creation()
    test_avalanche_features()

if __name__ == "__main__":
    main() 