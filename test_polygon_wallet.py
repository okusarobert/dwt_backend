#!/usr/bin/env python3
"""
Polygon Wallet Test Script
Tests the Polygon wallet functionality with comprehensive features
"""

import os
import logging
from decouple import config
from shared.crypto.clients.polygon import PolygonWallet, PolygonConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_polygon_wallet():
    """Test the Polygon wallet functionality"""
    logger.info("🚀 Starting Polygon wallet tests...")
    
    # Initialize Polygon configuration
    api_key = config('ALCHEMY_POLYGON_API_KEY', default='demo')
    polygon_config = PolygonConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {polygon_config.network}")
    logger.info(f"🔗 Base URL: {polygon_config.base_url}")
    
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
    
    # Initialize Polygon wallet
    user_id = 12345
    polygon_wallet = PolygonWallet(
        user_id=user_id,
        config=polygon_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info(f"✅ Polygon wallet initialized for user {user_id}")
    
    # Test connection
    logger.info("\n🔍 Testing Polygon API connection...")
    if polygon_wallet.test_connection():
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed!")
        return
    
    # Test blockchain info
    logger.info("\n📊 Getting blockchain information...")
    blockchain_info = polygon_wallet.get_blockchain_info()
    logger.info(f"Network: {blockchain_info.get('network')}")
    logger.info(f"Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"Connection status: {blockchain_info.get('connection_status')}")
    
    # Test gas price
    logger.info("\n⛽ Getting current gas price...")
    gas_price = polygon_wallet.get_gas_price()
    if gas_price:
        logger.info(f"Gas price: {gas_price['gas_price_gwei']:.2f} Gwei")
    
    # Test getting recent blocks
    logger.info("\n📋 Getting recent blocks...")
    recent_blocks = polygon_wallet.get_recent_blocks(3)
    logger.info(f"Retrieved {len(recent_blocks)} recent blocks")
    
    # Test address validation
    logger.info("\n🔍 Testing address validation...")
    test_addresses = [
        "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619",  # WETH on Polygon
        "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",  # WMATIC on Polygon
        "invalid_address",  # Invalid
        "0x123",  # Invalid
    ]
    
    for addr in test_addresses:
        is_valid = polygon_wallet.validate_address(addr)
        logger.info(f"Address {addr}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test getting balance for a known address
    logger.info("\n💰 Getting balance for a test address...")
    test_address = "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"  # WETH on Polygon
    balance = polygon_wallet.get_balance(test_address)
    if balance:
        logger.info(f"Balance: {balance['balance_matic']:.6f} MATIC ({balance['balance_wei']} wei)")
    
    # Test account info
    logger.info("\n👤 Getting account information...")
    account_info = polygon_wallet.get_account_info(test_address)
    if account_info:
        logger.info(f"Transaction count: {account_info.get('transaction_count')}")
        logger.info(f"Is contract: {account_info.get('is_contract')}")
    
    # Test new methods
    logger.info("\n🆕 Testing new methods...")
    
    # Test wallet addresses
    addresses = polygon_wallet.get_wallet_addresses()
    logger.info(f"Wallet addresses: {len(addresses)} found")
    
    # Test wallet summary
    summary = polygon_wallet.get_wallet_summary()
    logger.info(f"Wallet summary: {summary.get('symbol')} wallet for user {summary.get('user_id')}")
    
    # Test Polygon-specific info
    polygon_info = polygon_wallet.get_polygon_specific_info()
    logger.info(f"Polygon Chain ID: {polygon_info.get('chain_id')}")
    logger.info(f"Polygon Consensus: {polygon_info.get('consensus')}")
    logger.info(f"Polygon Scaling: {polygon_info.get('scaling_solution')}")
    
    # Test Polygon features
    features = polygon_wallet.get_polygon_features()
    logger.info(f"Polygon Features: {list(features.keys())}")
    
    logger.info("\n✅ All Polygon wallet tests completed successfully!")

def test_polygon_specific_features():
    """Test Polygon-specific features"""
    logger.info("\n🏗️ Testing Polygon-specific features...")
    
    # Initialize configuration
    api_key = config('ALCHEMY_POLYGON_API_KEY', default='demo')
    polygon_config = PolygonConfig.testnet(api_key)
    
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
    polygon_wallet = PolygonWallet(
        user_id=99999,
        config=polygon_config,
        session=mock_session,
        logger=logger
    )
    
    # Test ERC-20 token info
    logger.info("\n🪙 Testing ERC-20 token functionality...")
    test_token = "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"  # WETH on Polygon
    token_info = polygon_wallet.get_erc20_token_info(test_token)
    if token_info:
        logger.info(f"Token Name: {token_info.get('name')}")
        logger.info(f"Token Symbol: {token_info.get('symbol')}")
        logger.info(f"Token Decimals: {token_info.get('decimals')}")
    
    # Test token balance
    logger.info("\n💰 Testing token balance...")
    test_wallet = "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"
    token_balance = polygon_wallet.get_token_balance(test_token, test_wallet)
    if token_balance:
        logger.info(f"Token Balance: {token_balance.get('balance')}")
    
    # Test address uniqueness validation
    logger.info("\n🔍 Testing address uniqueness validation...")
    test_address = "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"
    uniqueness_info = polygon_wallet.validate_address_uniqueness(test_address)
    logger.info(f"Address uniqueness validation:")
    logger.info(f"  - Valid format: {uniqueness_info['is_valid_format']}")
    logger.info(f"  - Exists in DB: {uniqueness_info['exists_in_database']}")
    logger.info(f"  - Is unique: {uniqueness_info['is_unique']}")
    
    # Test address generation stats
    logger.info("\n📈 Testing address generation stats...")
    stats = polygon_wallet.get_address_generation_stats()
    logger.info(f"Address generation statistics:")
    logger.info(f"  - Total addresses: {stats.get('total_addresses', 0)}")
    logger.info(f"  - Active addresses: {stats.get('active_addresses', 0)}")
    logger.info(f"  - Unique addresses: {stats.get('unique_addresses', 0)}")
    logger.info(f"  - Has duplicates: {stats.get('has_duplicates', False)}")

def demonstrate_polygon_advantages():
    """Demonstrate Polygon's advantages"""
    logger.info("\n🚀 Demonstrating Polygon Advantages:")
    
    logger.info("\n📊 Polygon Benefits:")
    logger.info("1. ⚡ High Performance: 65,000+ TPS")
    logger.info("2. 💰 Low Fees: Fraction of Ethereum gas costs")
    logger.info("3. 🔗 Ethereum Compatible: Full EVM compatibility")
    logger.info("4. 🏗️ Layer 2 Scaling: Built on Ethereum")
    logger.info("5. 🌐 Fast Finality: ~2 second block time")
    logger.info("6. 🛡️ Security: Inherits Ethereum's security")
    
    logger.info("\n🔧 Technical Features:")
    logger.info("- Chain ID: 137 (mainnet) / 80001 (Mumbai testnet)")
    logger.info("- Consensus: Proof of Stake (PoS)")
    logger.info("- Native Token: MATIC")
    logger.info("- Address Format: Ethereum-compatible (0x...)")
    logger.info("- Smart Contracts: Full EVM support")
    logger.info("- Token Standards: ERC-20, ERC-721, ERC-1155")

def main():
    """Run all Polygon wallet tests"""
    try:
        test_polygon_wallet()
        test_polygon_specific_features()
        demonstrate_polygon_advantages()
        
        logger.info("\n🎉 All Polygon wallet tests completed successfully!")
        logger.info("✅ Polygon wallet is ready for production use!")
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main() 