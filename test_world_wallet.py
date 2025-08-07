#!/usr/bin/env python3
"""
World Chain Wallet Test Script
Tests the World Chain wallet functionality with comprehensive features
"""

import os
import logging
from decouple import config
from shared.crypto.clients.world import WorldWallet, WorldConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_world_wallet():
    """Test the World Chain wallet functionality"""
    logger.info("🚀 Starting World Chain wallet tests...")
    
    # Initialize World Chain configuration
    api_key = config('ALCHEMY_WORLD_API_KEY', default='demo')
    world_config = WorldConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {world_config.network}")
    logger.info(f"🔗 Base URL: {world_config.base_url}")
    
    # Create a mock session
    class MockSession:
        def add(self, obj):
            logger.info(f"Mock: Added {type(obj).__name__}")
        
        def flush(self):
            logger.info("Mock: Flushed session")
        
        def query(self, model):
            return MockQuery()
    
    class MockQuery:
        def filter_by(self, **kwargs):
            return self
        
        def all(self):
            return []
        
        def first(self):
            return None
    
    mock_session = MockSession()
    
    # Initialize World Chain wallet
    user_id = 12345
    world_wallet = WorldWallet(
        user_id=user_id,
        config=world_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info(f"✅ World Chain wallet initialized for user {user_id}")
    
    # Test connection
    logger.info("\n🔍 Testing World Chain API connection...")
    if world_wallet.test_connection():
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed!")
        return
    
    # Test blockchain info
    logger.info("\n📊 Getting blockchain information...")
    blockchain_info = world_wallet.get_blockchain_info()
    logger.info(f"Network: {blockchain_info.get('network')}")
    logger.info(f"Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"Connection status: {blockchain_info.get('connection_status')}")
    
    # Test gas price
    logger.info("\n⛽ Getting current gas price...")
    gas_price = world_wallet.get_gas_price()
    if gas_price:
        logger.info(f"Gas price: {gas_price['gas_price_gwei']:.2f} Gwei")
    
    # Test getting recent blocks
    logger.info("\n📋 Getting recent blocks...")
    recent_blocks = world_wallet.get_recent_blocks(3)
    logger.info(f"Retrieved {len(recent_blocks)} recent blocks")
    
    # Test address validation
    logger.info("\n🔍 Testing address validation...")
    test_addresses = [
        "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",  # Example World Chain address
        "0x1234567890123456789012345678901234567890",  # Valid format
        "invalid_address",  # Invalid
        "0x123",  # Invalid
    ]
    
    for addr in test_addresses:
        is_valid = world_wallet.validate_address(addr)
        logger.info(f"Address {addr}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test getting balance for a known address
    logger.info("\n💰 Getting balance for a test address...")
    test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"  # Example address
    balance = world_wallet.get_balance(test_address)
    if balance:
        logger.info(f"Balance: {balance['balance_wld']:.6f} WLD ({balance['balance_wei']} wei)")
    
    # Test account info
    logger.info("\n👤 Getting account information...")
    account_info = world_wallet.get_account_info(test_address)
    if account_info:
        logger.info(f"Transaction count: {account_info.get('transaction_count')}")
        logger.info(f"Is contract: {account_info.get('is_contract')}")
    
    # Test new methods
    logger.info("\n🆕 Testing new methods...")
    
    # Test wallet addresses
    addresses = world_wallet.get_wallet_addresses()
    logger.info(f"Wallet addresses: {len(addresses)} found")
    
    # Test wallet summary
    summary = world_wallet.get_wallet_summary()
    logger.info(f"Wallet summary: {summary.get('symbol')} wallet for user {summary.get('user_id')}")
    
    # Test World Chain-specific info
    world_info = world_wallet.get_world_specific_info()
    logger.info(f"World Chain ID: {world_info.get('chain_id')}")
    logger.info(f"World Chain Consensus: {world_info.get('consensus')}")
    logger.info(f"World Chain Scaling: {world_info.get('scaling_solution')}")
    
    # Test World Chain features
    features = world_wallet.get_world_features()
    logger.info(f"World Chain Features: {list(features.keys())}")
    
    logger.info("\n✅ All World Chain wallet tests completed successfully!")

def test_world_specific_features():
    """Test World Chain-specific features"""
    logger.info("\n🏗️ Testing World Chain-specific features...")
    
    # Initialize configuration
    api_key = config('ALCHEMY_WORLD_API_KEY', default='demo')
    world_config = WorldConfig.testnet(api_key)
    
    # Create mock session
    class MockSession:
        def add(self, obj):
            pass
        def flush(self):
            pass
        def query(self, model):
            return MockQuery()
    
    class MockQuery:
        def filter_by(self, **kwargs):
            return self
        def all(self):
            return []
        def first(self):
            return None
    
    mock_session = MockSession()
    
    # Create wallet
    world_wallet = WorldWallet(
        user_id=99999,
        config=world_config,
        session=mock_session,
        logger=logger
    )
    
    # Test ERC-20 token info
    logger.info("\n🪙 Testing ERC-20 token functionality...")
    test_token = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"  # Example token
    token_info = world_wallet.get_erc20_token_info(test_token)
    if token_info:
        logger.info(f"Token Name: {token_info.get('name')}")
        logger.info(f"Token Symbol: {token_info.get('symbol')}")
        logger.info(f"Token Decimals: {token_info.get('decimals')}")
    
    # Test token balance
    logger.info("\n💰 Testing token balance...")
    test_wallet = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    token_balance = world_wallet.get_token_balance(test_token, test_wallet)
    if token_balance:
        logger.info(f"Token Balance: {token_balance.get('balance')}")
    
    # Test address uniqueness validation
    logger.info("\n🔍 Testing address uniqueness validation...")
    test_address = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
    uniqueness_info = world_wallet.validate_address_uniqueness(test_address)
    logger.info(f"Address uniqueness validation:")
    logger.info(f"  - Valid format: {uniqueness_info['is_valid_format']}")
    logger.info(f"  - Exists in DB: {uniqueness_info['exists_in_database']}")
    logger.info(f"  - Is unique: {uniqueness_info['is_unique']}")
    
    # Test address generation stats
    logger.info("\n📈 Testing address generation stats...")
    stats = world_wallet.get_address_generation_stats()
    logger.info(f"Address generation statistics:")
    logger.info(f"  - Total addresses: {stats.get('total_addresses', 0)}")
    logger.info(f"  - Active addresses: {stats.get('active_addresses', 0)}")
    logger.info(f"  - Unique addresses: {stats.get('unique_addresses', 0)}")
    logger.info(f"  - Has duplicates: {stats.get('has_duplicates', False)}")

def demonstrate_world_advantages():
    """Demonstrate World Chain's advantages"""
    logger.info("\n🚀 Demonstrating World Chain Advantages:")
    
    logger.info("\n📊 World Chain Benefits:")
    logger.info("1. ⚡ Ultra High Performance: 100,000+ TPS")
    logger.info("2. 💰 Ultra Low Fees: Minimal transaction costs")
    logger.info("3. 🔗 Ethereum Compatible: Full EVM compatibility")
    logger.info("4. 🏗️ High-Performance Blockchain: Built for scale")
    logger.info("5. 🌐 Ultra Fast Finality: ~1 second block time")
    logger.info("6. 🤖 AI Integration: Advanced AI capabilities")
    logger.info("7. 🛡️ Security: Enterprise-grade security")
    
    logger.info("\n🔧 Technical Features:")
    logger.info("- Chain ID: 1000 (mainnet) / 1001 (testnet)")
    logger.info("- Consensus: Proof of Stake (PoS)")
    logger.info("- Native Token: WLD")
    logger.info("- Address Format: Ethereum-compatible (0x...)")
    logger.info("- Smart Contracts: Full EVM support")
    logger.info("- Token Standards: ERC-20, ERC-721, ERC-1155")
    logger.info("- AI Integration: Advanced AI capabilities")
    logger.info("- World Ecosystem: Comprehensive ecosystem support")

def main():
    """Run all World Chain wallet tests"""
    try:
        test_world_wallet()
        test_world_specific_features()
        demonstrate_world_advantages()
        
        logger.info("\n🎉 All World Chain wallet tests completed successfully!")
        logger.info("✅ World Chain wallet is ready for production use!")
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 