#!/usr/bin/env python3
"""
BNB Wallet Test Script
Tests the new BNBWallet class functionality
"""

import os
import logging
from decouple import config
from shared.crypto.clients.bnb import BNBWallet, BNBConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_bnb_wallet():
    """Test the BNB wallet functionality"""
    logger.info("🚀 Starting BNB wallet tests...")
    
    # Initialize BNB configuration
    api_key = config('ALCHEMY_BNB_API_KEY', default='demo')
    bnb_config = BNBConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {bnb_config.network}")
    logger.info(f"🔗 Base URL: {bnb_config.base_url}")
    
    # Create a mock session (in real usage, this would be a database session)
    class MockSession:
        def add(self, obj):
            logger.info(f"Mock: Added {type(obj).__name__}")
        
        def flush(self):
            logger.info("Mock: Flushed session")
    
    mock_session = MockSession()
    
    # Initialize BNB wallet
    user_id = 12345
    bnb_wallet = BNBWallet(
        user_id=user_id,
        config=bnb_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info(f"✅ BNB wallet initialized for user {user_id}")
    
    # Test connection
    logger.info("\n🔍 Testing BNB API connection...")
    if bnb_wallet.test_connection():
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed!")
        return
    
    # Test blockchain info
    logger.info("\n📊 Getting blockchain information...")
    blockchain_info = bnb_wallet.get_blockchain_info()
    logger.info(f"Network: {blockchain_info.get('network')}")
    logger.info(f"Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"Connection status: {blockchain_info.get('connection_status')}")
    
    # Test gas price
    logger.info("\n⛽ Getting current gas price...")
    gas_price = bnb_wallet.get_gas_price()
    if gas_price:
        logger.info(f"Gas price: {gas_price['gas_price_gwei']:.2f} Gwei")
    
    # Test getting recent blocks
    logger.info("\n📋 Getting recent blocks...")
    recent_blocks = bnb_wallet.get_recent_blocks(3)
    logger.info(f"Retrieved {len(recent_blocks)} recent blocks")
    
    # Test address validation
    logger.info("\n🔍 Testing address validation...")
    test_addresses = [
        "0x28C6c06298d514Db089934071355E5743bf21d60",  # Valid BNB address
        "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549",  # Valid BNB address
        "invalid_address",  # Invalid
        "0x123",  # Invalid
    ]
    
    for addr in test_addresses:
        is_valid = bnb_wallet.validate_address(addr)
        logger.info(f"Address {addr}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test getting balance for a known address
    logger.info("\n💰 Getting balance for a test address...")
    test_address = "0x28C6c06298d514Db089934071355E5743bf21d60"  # Binance Hot Wallet
    balance = bnb_wallet.get_balance(test_address)
    if balance:
        logger.info(f"Balance: {balance['balance_bnb']:.6f} BNB ({balance['balance_wei']} wei)")
    
    # Test account info
    logger.info("\n👤 Getting account information...")
    account_info = bnb_wallet.get_account_info(test_address)
    if account_info:
        logger.info(f"Address: {account_info['address']}")
        logger.info(f"Transaction count: {account_info['transaction_count']}")
        logger.info(f"Is contract: {account_info['is_contract']}")
    
    # Test network info
    logger.info("\n🌐 Getting network information...")
    network_info = bnb_wallet.get_network_info()
    logger.info(f"Network: {network_info.get('network')}")
    logger.info(f"Latest block: {network_info.get('latest_block')}")
    
    # Test BNB-specific info
    logger.info("\n🔧 Getting BNB-specific information...")
    bnb_info = bnb_wallet.get_bnb_specific_info()
    logger.info(f"Network: {bnb_info.get('network')}")
    logger.info(f"Chain ID: {bnb_info.get('chain_id')}")
    logger.info(f"Consensus: {bnb_info.get('consensus')}")
    logger.info(f"Block Time: {bnb_info.get('block_time')}")
    logger.info(f"Finality: {bnb_info.get('finality')}")
    logger.info(f"Native Token: {bnb_info.get('native_token')}")
    
    # Test BEP-20 token info
    logger.info("\n🪙 Testing BEP-20 token information...")
    # Test with CAKE token on BNB Smart Chain
    cake_token = "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"  # CAKE token
    token_info = bnb_wallet.get_bep20_token_info(cake_token)
    if token_info:
        logger.info(f"Token Name: {token_info.get('name')}")
        logger.info(f"Token Symbol: {token_info.get('symbol')}")
        logger.info(f"Token Decimals: {token_info.get('decimals')}")
    
    # Test token balance
    logger.info("\n🪙 Testing token balance...")
    token_balance = bnb_wallet.get_token_balance(cake_token, test_address)
    if token_balance:
        logger.info(f"Token balance: {token_balance['balance']}")
        logger.info(f"Token address: {token_balance['token_address']}")
    else:
        logger.info("No token balance found or token not supported")
    
    # Test BNB features
    logger.info("\n🔧 Getting BNB features...")
    features = bnb_wallet.get_bnb_features()
    logger.info("BNB Features:")
    for feature, value in features.items():
        logger.info(f"  - {feature}: {value}")
    
    logger.info("\n" + "="*50)
    logger.info("✅ All BNB wallet tests completed!")
    logger.info("="*50)

def test_wallet_creation():
    """Test wallet creation functionality (mock)"""
    logger.info("\n🔧 Testing wallet creation functionality...")
    
    # This would normally require a database session
    # For testing, we'll just show the structure
    logger.info("📝 Wallet creation would:")
    logger.info("  1. Create Account record in database")
    logger.info("  2. Generate unique account number")
    logger.info("  3. Create BNB address using ETH HD wallet (BNB uses Ethereum addresses)")
    logger.info("  4. Encrypt private key")
    logger.info("  5. Store CryptoAddress record")
    logger.info("  6. Set up webhooks (if needed)")
    
    logger.info("✅ Wallet creation test completed!")

def test_bnb_features():
    """Test BNB-specific features"""
    logger.info("\n🔧 Testing BNB-specific features...")
    
    # Initialize BNB wallet
    api_key = config('ALCHEMY_BNB_API_KEY', default='demo')
    bnb_config = BNBConfig.testnet(api_key)
    
    class MockSession:
        def add(self, obj):
            pass
        def flush(self):
            pass
    
    mock_session = MockSession()
    
    bnb_wallet = BNBWallet(
        user_id=12345,
        config=bnb_config,
        session=mock_session,
        logger=logger
    )
    
    # Test BNB specific features
    logger.info("📊 BNB Smart Chain Features:")
    logger.info("  - High performance")
    logger.info("  - Fast finality (~3 seconds)")
    logger.info("  - Low gas fees")
    logger.info("  - BEP-20 tokens")
    logger.info("  - Smart contracts")
    logger.info("  - Cross-chain bridges")
    logger.info("  - Binance ecosystem integration")
    
    # Get BNB specific info
    bnb_info = bnb_wallet.get_bnb_specific_info()
    logger.info(f"  - Chain ID: {bnb_info.get('chain_id')}")
    logger.info(f"  - Consensus: {bnb_info.get('consensus')}")
    
    # Get features
    features = bnb_wallet.get_bnb_features()
    logger.info(f"  - Fast Finality: {features.get('fast_finality')}")
    logger.info(f"  - BEP-20 Tokens: {features.get('bep20_tokens')}")
    
    logger.info("✅ BNB features test completed!")

def test_bep20_tokens():
    """Test BEP-20 token functionality"""
    logger.info("\n🪙 Testing BEP-20 token functionality...")
    
    # Initialize BNB wallet
    api_key = config('ALCHEMY_BNB_API_KEY', default='demo')
    bnb_config = BNBConfig.testnet(api_key)
    
    class MockSession:
        def add(self, obj):
            pass
        def flush(self):
            pass
    
    mock_session = MockSession()
    
    bnb_wallet = BNBWallet(
        user_id=12345,
        config=bnb_config,
        session=mock_session,
        logger=logger
    )
    
    # Test BEP-20 token info
    logger.info("📊 BEP-20 Token Features:")
    logger.info("  - BEP-20 Token Standard")
    logger.info("  - Token balances")
    logger.info("  - Token information (name, symbol, decimals)")
    logger.info("  - Smart contract interaction")
    logger.info("  - Low transaction fees")
    
    # Test getting token info for CAKE
    cake_token = "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"  # CAKE on BNB
    token_info = bnb_wallet.get_bep20_token_info(cake_token)
    if token_info:
        logger.info(f"  - Token Name: {token_info.get('name')}")
        logger.info(f"  - Token Symbol: {token_info.get('symbol')}")
        logger.info(f"  - Token Decimals: {token_info.get('decimals')}")
    
    logger.info("✅ BEP-20 token test completed!")

def main():
    """Main function"""
    print("🔧 BNB Wallet Test Script")
    print("📡 Using Alchemy API with BNBWallet class")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_BNB_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_BNB_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using demo key for testing.")
        print()
    
    # Run tests
    test_bnb_wallet()
    test_wallet_creation()
    test_bnb_features()
    test_bep20_tokens()

if __name__ == "__main__":
    main() 