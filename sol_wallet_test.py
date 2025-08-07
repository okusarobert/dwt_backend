#!/usr/bin/env python3
"""
Solana Wallet Test Script
Tests the new SOLWallet class functionality
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

def test_solana_wallet():
    """Test the Solana wallet functionality"""
    logger.info("🚀 Starting Solana wallet tests...")
    
    # Initialize Solana configuration
    api_key = config('ALCHEMY_SOLANA_API_KEY', default='demo')
    sol_config = SolanaConfig.testnet(api_key)
    
    logger.info(f"📡 Using network: {sol_config.network}")
    logger.info(f"🔗 Base URL: {sol_config.base_url}")
    
    # Create a mock session (in real usage, this would be a database session)
    class MockSession:
        def add(self, obj):
            logger.info(f"Mock: Added {type(obj).__name__}")
        
        def flush(self):
            logger.info("Mock: Flushed session")
    
    mock_session = MockSession()
    
    # Initialize SOL wallet
    user_id = 12345
    sol_wallet = SOLWallet(
        user_id=user_id,
        config=sol_config,
        session=mock_session,
        logger=logger
    )
    
    logger.info(f"✅ SOL wallet initialized for user {user_id}")
    
    # Test connection
    logger.info("\n🔍 Testing Solana API connection...")
    if sol_wallet.test_connection():
        logger.info("✅ Connection test successful!")
    else:
        logger.error("❌ Connection test failed!")
        return
    
    # Test blockchain info
    logger.info("\n📊 Getting blockchain information...")
    blockchain_info = sol_wallet.get_blockchain_info()
    logger.info(f"Network: {blockchain_info.get('network')}")
    logger.info(f"Latest slot: {blockchain_info.get('latest_slot')}")
    logger.info(f"Connection status: {blockchain_info.get('connection_status')}")
    
    # Test getting latest slot
    logger.info("\n📋 Getting latest slot...")
    latest_slot = sol_wallet.get_latest_slot()
    if latest_slot:
        logger.info(f"Latest slot: {latest_slot:,}")
    
    # Test getting recent blocks
    logger.info("\n📋 Getting recent blocks...")
    recent_blocks = sol_wallet.get_recent_blocks(3)
    logger.info(f"Retrieved {len(recent_blocks)} recent blocks")
    
    # Test address validation
    logger.info("\n🔍 Testing address validation...")
    test_addresses = [
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",  # Valid Solana address
        "11111111111111111111111111111111",  # Valid (System Program)
        "invalid_address",  # Invalid
        "123",  # Invalid
    ]
    
    for addr in test_addresses:
        is_valid = sol_wallet.validate_address(addr)
        logger.info(f"Address {addr}: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    # Test getting balance for a known address
    logger.info("\n💰 Getting balance for a test address...")
    test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"  # Solana Foundation
    balance = sol_wallet.get_balance(test_address)
    if balance:
        logger.info(f"Balance: {balance['sol_balance']:.9f} SOL ({balance['lamports']} lamports)")
    
    # Test account info
    logger.info("\n👤 Getting account information...")
    account_info = sol_wallet.get_account_info(test_address)
    if account_info:
        logger.info(f"Address: {account_info['address']}")
        logger.info(f"Owner: {account_info['owner']}")
        logger.info(f"Executable: {account_info['executable']}")
        logger.info(f"Rent Epoch: {account_info['rent_epoch']}")
    
    # Test network info
    logger.info("\n🌐 Getting network information...")
    network_info = sol_wallet.get_network_info()
    logger.info(f"Network: {network_info.get('network')}")
    logger.info(f"Latest slot: {network_info.get('latest_slot')}")
    
    # Test Solana-specific info
    logger.info("\n🔧 Getting Solana-specific information...")
    sol_info = sol_wallet.get_solana_specific_info()
    logger.info(f"Network: {sol_info.get('network')}")
    logger.info(f"Latest slot: {sol_info.get('latest_slot')}")
    logger.info(f"Consensus: {sol_info.get('consensus')}")
    logger.info(f"Block Time: {sol_info.get('block_time')}")
    logger.info(f"Finality: {sol_info.get('finality')}")
    logger.info(f"Native Token: {sol_info.get('native_token')}")
    
    # Test supply information
    logger.info("\n💰 Getting supply information...")
    supply = sol_wallet.get_supply()
    if supply:
        logger.info(f"Total supply: {supply.get('total')}")
        logger.info(f"Circulating: {supply.get('circulating')}")
        logger.info(f"Non-circulating: {supply.get('non_circulating')}")
    
    # Test version information
    logger.info("\n📋 Getting version information...")
    version = sol_wallet.get_version()
    if version:
        logger.info(f"Solana version: {version}")
    
    # Test token accounts
    logger.info("\n🪙 Testing token accounts...")
    token_accounts = sol_wallet.get_token_accounts(test_address)
    if token_accounts:
        logger.info(f"Found {len(token_accounts)} token accounts")
        for i, account in enumerate(token_accounts[:3]):  # Show first 3
            logger.info(f"  Token {i+1}: {account.get('mint')} - {account.get('amount')}")
    else:
        logger.info("No token accounts found")
    
    # Test comprehensive account info
    logger.info("\n📊 Getting comprehensive account information...")
    comprehensive_info = sol_wallet.get_account_info_comprehensive(test_address)
    if comprehensive_info:
        logger.info(f"Address: {comprehensive_info['address']}")
        if comprehensive_info.get('balance'):
            logger.info(f"Balance: {comprehensive_info['balance']['sol_balance']:.9f} SOL")
        if comprehensive_info.get('token_accounts'):
            logger.info(f"Token accounts: {len(comprehensive_info['token_accounts'])}")
        logger.info(f"Transaction count: {comprehensive_info.get('transaction_count')}")
    
    # Test Solana features
    logger.info("\n🔧 Getting Solana features...")
    features = sol_wallet.get_solana_features()
    logger.info("Solana Features:")
    for feature, value in features.items():
        logger.info(f"  - {feature}: {value}")
    
    logger.info("\n" + "="*50)
    logger.info("✅ All Solana wallet tests completed!")
    logger.info("="*50)

def test_wallet_creation():
    """Test wallet creation functionality (mock)"""
    logger.info("\n🔧 Testing wallet creation functionality...")
    
    # This would normally require a database session
    # For testing, we'll just show the structure
    logger.info("📝 Wallet creation would:")
    logger.info("  1. Create Account record in database")
    logger.info("  2. Generate unique account number")
    logger.info("  3. Create SOL address using Solana Keypair")
    logger.info("  4. Encrypt private key")
    logger.info("  5. Store CryptoAddress record")
    logger.info("  6. Set up webhooks (if needed)")
    
    logger.info("✅ Wallet creation test completed!")

def test_solana_features():
    """Test Solana-specific features"""
    logger.info("\n🔧 Testing Solana-specific features...")
    
    # Initialize Solana wallet
    api_key = config('ALCHEMY_SOLANA_API_KEY', default='demo')
    sol_config = SolanaConfig.testnet(api_key)
    
    class MockSession:
        def add(self, obj):
            pass
        def flush(self):
            pass
    
    mock_session = MockSession()
    
    sol_wallet = SOLWallet(
        user_id=12345,
        config=sol_config,
        session=mock_session,
        logger=logger
    )
    
    # Test Solana specific features
    logger.info("📊 Solana Features:")
    logger.info("  - High performance (65,000+ TPS)")
    logger.info("  - Fast finality (~400ms)")
    logger.info("  - Low fees")
    logger.info("  - SPL tokens")
    logger.info("  - Programs (smart contracts)")
    logger.info("  - Cross-program invocation")
    logger.info("  - Parallel processing")
    
    # Get Solana specific info
    sol_info = sol_wallet.get_solana_specific_info()
    logger.info(f"  - Block Time: {sol_info.get('block_time')}")
    logger.info(f"  - Finality: {sol_info.get('finality')}")
    
    # Get features
    features = sol_wallet.get_solana_features()
    logger.info(f"  - High Throughput: {features.get('high_throughput')}")
    logger.info(f"  - Fast Finality: {features.get('fast_finality')}")
    
    logger.info("✅ Solana features test completed!")

def test_spl_tokens():
    """Test SPL token functionality"""
    logger.info("\n🪙 Testing SPL token functionality...")
    
    # Initialize Solana wallet
    api_key = config('ALCHEMY_SOLANA_API_KEY', default='demo')
    sol_config = SolanaConfig.testnet(api_key)
    
    class MockSession:
        def add(self, obj):
            pass
        def flush(self):
            pass
    
    mock_session = MockSession()
    
    sol_wallet = SOLWallet(
        user_id=12345,
        config=sol_config,
        session=mock_session,
        logger=logger
    )
    
    # Test SPL token info
    logger.info("📊 SPL Token Features:")
    logger.info("  - SPL Token Standard")
    logger.info("  - Token accounts")
    logger.info("  - Mint authorities")
    logger.info("  - Freeze authorities")
    logger.info("  - Token balances")
    
    # Test getting token info for USDC
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC on Solana
    token_info = sol_wallet.get_spl_token_info(usdc_mint)
    if token_info:
        logger.info(f"  - USDC Mint: {token_info.get('mint')}")
        logger.info(f"  - Decimals: {token_info.get('decimals')}")
        logger.info(f"  - Supply: {token_info.get('supply')}")
        logger.info(f"  - Is Initialized: {token_info.get('is_initialized')}")
    
    logger.info("✅ SPL token test completed!")

def main():
    """Main function"""
    print("🔧 Solana Wallet Test Script")
    print("📡 Using Alchemy API with SOLWallet class")
    print("=" * 50)
    
    # Check if API key is set
    api_key = os.getenv('ALCHEMY_SOLANA_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_SOLANA_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Using demo key for testing.")
        print()
    
    # Check if Solana SDK is available
    try:
        from solana.rpc.api import Client
        print("✅ Solana SDK is available")
    except ImportError:
        print("⚠️  Solana SDK not available. Install with: pip install solana solders")
        print("💡 Some features may not work without the SDK.")
        print()
    
    # Run tests
    test_solana_wallet()
    test_wallet_creation()
    test_solana_features()
    test_spl_tokens()

if __name__ == "__main__":
    main() 