#!/usr/bin/env python3
"""
Test BNB Wallet Fixes
Verifies that the BNB wallet configuration fixes are working correctly
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

def test_bnb_wallet_fixes():
    """Test the BNB wallet with the configuration fixes"""
    logger.info("🚀 Testing BNB wallet fixes...")
    
    # Initialize BNB configuration
    api_key = config('ALCHEMY_BNB_API_KEY', default='demo')
    bnb_config = BNBConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {bnb_config.network}")
    logger.info(f"🔗 Base URL: {bnb_config.base_url}")
    
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
    
    # Test new methods
    logger.info("\n🆕 Testing new methods...")
    
    # Test wallet addresses
    addresses = bnb_wallet.get_wallet_addresses()
    logger.info(f"Wallet addresses: {len(addresses)} found")
    
    # Test wallet summary
    summary = bnb_wallet.get_wallet_summary()
    logger.info(f"Wallet summary: {summary.get('symbol')} wallet for user {summary.get('user_id')}")
    
    # Test BNB-specific info
    bnb_info = bnb_wallet.get_bnb_specific_info()
    logger.info(f"BNB Chain ID: {bnb_info.get('chain_id')}")
    logger.info(f"BNB Consensus: {bnb_info.get('consensus')}")
    
    # Test BNB features
    features = bnb_wallet.get_bnb_features()
    logger.info(f"BNB Features: {list(features.keys())}")
    
    logger.info("\n✅ All BNB wallet tests completed successfully!")

if __name__ == "__main__":
    test_bnb_wallet_fixes() 