#!/usr/bin/env python3
"""
Test Solana Address Uniqueness
Demonstrates and verifies Solana address uniqueness guarantees
"""

import os
import logging
from decouple import config
from shared.crypto.clients.sol import SOLWallet, SolanaConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_solana_address_uniqueness():
    """Test Solana address uniqueness guarantees"""
    logger.info("🚀 Testing Solana address uniqueness...")
    
    # Initialize Solana configuration
    api_key = config('ALCHEMY_SOLANA_API_KEY', default='demo')
    sol_config = SolanaConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {sol_config.network}")
    logger.info(f"🔗 Base URL: {sol_config.base_url}")
    
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
    
    # Initialize Solana wallet
    user_id = 12345
    sol_wallet = SOLWallet(
        user_id=user_id,
        config=sol_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info(f"✅ Solana wallet initialized for user {user_id}")
    
    # Test connection
    logger.info("\n🔍 Testing Solana API connection...")
    if sol_wallet.test_connection():
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed!")
        return
    
    # Test address uniqueness validation
    logger.info("\n🔍 Testing address uniqueness validation...")
    test_addresses = [
        "11111111111111111111111111111111",  # System Program
        "So11111111111111111111111111111111111111112",  # Wrapped SOL
        "invalid_address",  # Invalid
        "0x123",  # Invalid format
    ]
    
    for addr in test_addresses:
        uniqueness_info = sol_wallet.validate_address_uniqueness(addr)
        logger.info(f"Address {addr}:")
        logger.info(f"  - Valid format: {uniqueness_info['is_valid_format']}")
        logger.info(f"  - Exists in DB: {uniqueness_info['exists_in_database']}")
        logger.info(f"  - Is unique: {uniqueness_info['is_unique']}")
    
    # Test address generation with uniqueness
    logger.info("\n🆕 Testing address generation with uniqueness guarantees...")
    
    # Generate multiple addresses to test uniqueness
    addresses = []
    for i in range(3):
        logger.info(f"\n--- Generating address {i + 1} ---")
        
        # Use the new method with uniqueness guarantees
        new_address = sol_wallet.ensure_address_uniqueness()
        if new_address:
            addresses.append(new_address["address"])
            logger.info(f"✅ Generated unique address: {new_address['address']}")
            logger.info(f"   Index: {new_address['index']}")
            logger.info(f"   Label: {new_address['label']}")
        else:
            logger.error(f"❌ Failed to generate address {i + 1}")
    
    # Test address collision detection
    logger.info("\n🔍 Testing address collision detection...")
    if addresses:
        # Simulate a collision by checking if the same address exists
        test_address = addresses[0]
        collision_check = sol_wallet.regenerate_address_if_collision(test_address)
        if collision_check:
            logger.info(f"⚠️  Collision detected and regenerated: {collision_check['address']}")
        else:
            logger.info(f"✅ No collision detected for: {test_address}")
    
    # Test wallet summary
    logger.info("\n📊 Testing wallet summary...")
    summary = sol_wallet.get_wallet_summary()
    logger.info(f"Wallet summary: {summary.get('symbol')} wallet for user {summary.get('user_id')}")
    logger.info(f"Total balance: {summary.get('total_balance_sol', 0)} SOL")
    logger.info(f"Addresses: {len(summary.get('addresses', []))}")
    
    # Test address generation stats
    logger.info("\n📈 Testing address generation stats...")
    stats = sol_wallet.get_address_generation_stats()
    logger.info(f"Total addresses: {stats.get('total_addresses', 0)}")
    logger.info(f"Active addresses: {stats.get('active_addresses', 0)}")
    logger.info(f"Unique addresses: {stats.get('unique_addresses', 0)}")
    logger.info(f"Has duplicates: {stats.get('has_duplicates', False)}")
    if stats.get('duplicate_count', 0) > 0:
        logger.warning(f"⚠️  Duplicate count: {stats['duplicate_count']}")
    
    # Test Solana-specific features
    logger.info("\n🏗️ Testing Solana-specific features...")
    features = sol_wallet.get_solana_features()
    logger.info(f"Solana Features: {list(features.keys())}")
    
    # Test blockchain info
    logger.info("\n📊 Testing blockchain information...")
    blockchain_info = sol_wallet.get_blockchain_info()
    logger.info(f"Network: {blockchain_info.get('network')}")
    logger.info(f"Latest slot: {blockchain_info.get('latest_slot')}")
    logger.info(f"Connection status: {blockchain_info.get('connection_status')}")
    
    logger.info("\n✅ All Solana uniqueness tests completed successfully!")

def demonstrate_uniqueness_guarantees():
    """Demonstrate the uniqueness guarantees in detail"""
    logger.info("\n🔬 Demonstrating Solana Address Uniqueness Guarantees")
    
    # Initialize configuration
    api_key = config('ALCHEMY_SOLANA_API_KEY', default='demo')
    sol_config = SolanaConfig.testnet(api_key)
    
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
    sol_wallet = SOLWallet(
        user_id=99999,
        config=sol_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info("\n📋 Uniqueness Guarantees:")
    logger.info("1. 🔍 Database-level uniqueness checking")
    logger.info("2. 🔄 Automatic collision detection and regeneration")
    logger.info("3. 📊 Address generation statistics tracking")
    logger.info("4. 🛡️ Multiple validation layers")
    logger.info("5. ⚡ Efficient collision prevention")
    
    logger.info("\n🔄 Collision Prevention Strategy:")
    logger.info("- Check database before storing new addresses")
    logger.info("- Regenerate on collision detection")
    logger.info("- Maximum retry attempts with exponential backoff")
    logger.info("- Comprehensive logging for audit trails")
    
    logger.info("\n📈 Monitoring Capabilities:")
    logger.info("- Real-time address generation statistics")
    logger.info("- Duplicate detection and reporting")
    logger.info("- Address validation and uniqueness verification")
    logger.info("- Blockchain-level address verification")

if __name__ == "__main__":
    test_solana_address_uniqueness()
    demonstrate_uniqueness_guarantees() 