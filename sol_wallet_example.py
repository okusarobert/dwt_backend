#!/usr/bin/env python3
"""
Solana Wallet Usage Example
Shows how to use the SOLWallet class in a real application
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

def create_user_wallet(user_id: int, session, network: str = "devnet"):
    """
    Create a new Solana wallet for a user
    
    Args:
        user_id: User ID
        session: Database session
        network: Network to use (mainnet, devnet)
    
    Returns:
        SOLWallet instance
    """
    # Get API key from environment
    api_key = config('ALCHEMY_SOLANA_API_KEY')
    if not api_key:
        raise ValueError("ALCHEMY_SOLANA_API_KEY environment variable is required")
    
    # Create configuration based on network
    if network == "mainnet":
        sol_config = SolanaConfig.mainnet(api_key)
    elif network == "devnet":
        sol_config = SolanaConfig.testnet(api_key)
    else:
        raise ValueError(f"Unsupported network: {network}")
    
    # Create wallet instance
    sol_wallet = SOLWallet(
        user_id=user_id,
        config=sol_config,
        session=session,
        logger=logger
    )
    
    # Create wallet in database
    sol_wallet.create_wallet()
    
    return sol_wallet

def get_user_balance(sol_wallet: SOLWallet, address: str):
    """
    Get balance for a user's address
    
    Args:
        sol_wallet: SOLWallet instance
        address: Solana address
    
    Returns:
        Balance information
    """
    balance = sol_wallet.get_balance(address)
    if balance:
        logger.info(f"Balance for {address}: {balance['sol_balance']:.9f} SOL")
        return balance
    else:
        logger.error(f"Failed to get balance for {address}")
        return None

def monitor_transactions(sol_wallet: SOLWallet, address: str):
    """
    Monitor transactions for an address
    
    Args:
        sol_wallet: SOLWallet instance
        address: Solana address to monitor
    """
    # Get transaction count
    tx_count = sol_wallet.get_transaction_count(address)
    if tx_count is not None:
        logger.info(f"Transaction count for {address}: {tx_count}")
    
    # Get account info
    account_info = sol_wallet.get_account_info(address)
    if account_info:
        logger.info(f"Account info for {address}:")
        logger.info(f"  - Owner: {account_info['owner']}")
        logger.info(f"  - Executable: {account_info['executable']}")
        logger.info(f"  - Rent Epoch: {account_info['rent_epoch']}")
        if account_info['sol_balance']:
            logger.info(f"  - Balance: {account_info['sol_balance']:.9f} SOL")

def get_network_status(sol_wallet: SOLWallet):
    """
    Get current network status
    
    Args:
        sol_wallet: SOLWallet instance
    
    Returns:
        Network status information
    """
    # Test connection
    if not sol_wallet.test_connection():
        logger.error("❌ Cannot connect to Solana API")
        return None
    
    # Get blockchain info
    blockchain_info = sol_wallet.get_blockchain_info()
    logger.info("📊 Blockchain Information:")
    logger.info(f"  - Network: {blockchain_info.get('network')}")
    logger.info(f"  - Latest slot: {blockchain_info.get('latest_slot')}")
    logger.info(f"  - Connection status: {blockchain_info.get('connection_status')}")
    
    # Get supply info
    supply = sol_wallet.get_supply()
    if supply:
        logger.info(f"  - Total supply: {supply.get('total')}")
        logger.info(f"  - Circulating: {supply.get('circulating')}")
    
    # Get recent blocks
    recent_blocks = sol_wallet.get_recent_blocks(3)
    logger.info(f"  - Recent blocks: {len(recent_blocks)} retrieved")
    
    return blockchain_info

def validate_and_monitor_address(sol_wallet: SOLWallet, address: str):
    """
    Validate an address and get its information
    
    Args:
        sol_wallet: SOLWallet instance
        address: Solana address to validate and monitor
    """
    # Validate address format
    if not sol_wallet.validate_address(address):
        logger.error(f"❌ Invalid Solana address: {address}")
        return False
    
    logger.info(f"✅ Valid Solana address: {address}")
    
    # Get balance
    balance = get_user_balance(sol_wallet, address)
    
    # Monitor transactions
    monitor_transactions(sol_wallet, address)
    
    return True

def get_token_balances(sol_wallet: SOLWallet, wallet_address: str):
    """
    Get SPL token balances for a wallet
    
    Args:
        sol_wallet: SOLWallet instance
        wallet_address: Wallet address to check
    """
    # Get all token accounts
    token_accounts = sol_wallet.get_token_accounts(wallet_address)
    if token_accounts:
        logger.info(f"🪙 Token Balances for {wallet_address}:")
        for account in token_accounts:
            if account.get('amount') and account['amount'] > 0:
                logger.info(f"  - {account.get('mint')}: {account.get('amount')}")
    else:
        logger.info("No token accounts found")

def get_solana_specific_info(sol_wallet: SOLWallet):
    """
    Get Solana-specific information
    
    Args:
        sol_wallet: SOLWallet instance
    """
    sol_info = sol_wallet.get_solana_specific_info()
    
    logger.info("🔧 Solana-Specific Information:")
    logger.info(f"  - Network: {sol_info.get('network')}")
    logger.info(f"  - Latest slot: {sol_info.get('latest_slot')}")
    logger.info(f"  - Consensus: {sol_info.get('consensus')}")
    logger.info(f"  - Block Time: {sol_info.get('block_time')}")
    logger.info(f"  - Finality: {sol_info.get('finality')}")
    logger.info(f"  - Native Token: {sol_info.get('native_token')}")
    
    return sol_info

def get_solana_features(sol_wallet: SOLWallet):
    """
    Get Solana-specific features
    
    Args:
        sol_wallet: SOLWallet instance
    """
    features = sol_wallet.get_solana_features()
    
    logger.info("🔧 Solana Features:")
    for feature, value in features.items():
        logger.info(f"  - {feature}: {value}")
    
    return features

def get_comprehensive_account_info(sol_wallet: SOLWallet, address: str):
    """
    Get comprehensive account information
    
    Args:
        sol_wallet: SOLWallet instance
        address: Solana address
    """
    comprehensive_info = sol_wallet.get_account_info_comprehensive(address)
    
    if comprehensive_info:
        logger.info(f"📊 Comprehensive Account Info for {address}:")
        
        if comprehensive_info.get('balance'):
            balance = comprehensive_info['balance']
            logger.info(f"  - SOL Balance: {balance['sol_balance']:.9f} SOL")
            logger.info(f"  - Lamports: {balance['lamports']}")
        
        if comprehensive_info.get('account_info'):
            account_info = comprehensive_info['account_info']
            logger.info(f"  - Owner: {account_info['owner']}")
            logger.info(f"  - Executable: {account_info['executable']}")
        
        if comprehensive_info.get('token_accounts'):
            token_count = len(comprehensive_info['token_accounts'])
            logger.info(f"  - Token Accounts: {token_count}")
        
        logger.info(f"  - Transaction Count: {comprehensive_info.get('transaction_count')}")
    
    return comprehensive_info

def get_spl_token_info(sol_wallet: SOLWallet, token_mint: str):
    """
    Get SPL token information
    
    Args:
        sol_wallet: SOLWallet instance
        token_mint: Token mint address
    """
    token_info = sol_wallet.get_spl_token_info(token_mint)
    
    if token_info:
        logger.info(f"🪙 SPL Token Info for {token_mint}:")
        logger.info(f"  - Mint: {token_info['mint']}")
        logger.info(f"  - Decimals: {token_info['decimals']}")
        logger.info(f"  - Supply: {token_info['supply']}")
        logger.info(f"  - Is Initialized: {token_info['is_initialized']}")
        logger.info(f"  - Mint Authority: {token_info.get('mint_authority')}")
        logger.info(f"  - Freeze Authority: {token_info.get('freeze_authority')}")
    
    return token_info

def main():
    """Main example function"""
    print("🔧 Solana Wallet Usage Example")
    print("📡 Demonstrating SOLWallet class usage")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_SOLANA_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_SOLANA_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Set ALCHEMY_SOLANA_API_KEY environment variable to run this example.")
        return
    
    # Check if Solana SDK is available
    try:
        from solana.rpc.api import Client
        print("✅ Solana SDK is available")
    except ImportError:
        print("⚠️  Solana SDK not available. Install with: pip install solana solders")
        print("💡 Some features may not work without the SDK.")
        print()
    
    # Create mock session (in real app, this would be a database session)
    class MockSession:
        def add(self, obj):
            logger.info(f"Mock: Added {type(obj).__name__} to database")
        
        def flush(self):
            logger.info("Mock: Flushed database session")
    
    mock_session = MockSession()
    
    try:
        # Example 1: Create a new wallet for a user
        logger.info("\n🔧 Example 1: Creating a new wallet")
        user_id = 12345
        sol_wallet = create_user_wallet(user_id, mock_session, "devnet")
        logger.info(f"✅ Created wallet for user {user_id}")
        
        # Example 2: Get network status
        logger.info("\n🌐 Example 2: Getting network status")
        network_status = get_network_status(sol_wallet)
        
        # Example 3: Validate and monitor an address
        logger.info("\n👤 Example 3: Validating and monitoring address")
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"  # Solana Foundation
        validate_and_monitor_address(sol_wallet, test_address)
        
        # Example 4: Get comprehensive account information
        logger.info("\n📊 Example 4: Getting comprehensive account information")
        comprehensive_info = get_comprehensive_account_info(sol_wallet, test_address)
        
        # Example 5: Get token balances
        logger.info("\n🪙 Example 5: Getting token balances")
        get_token_balances(sol_wallet, test_address)
        
        # Example 6: Get Solana-specific information
        logger.info("\n🔧 Example 6: Getting Solana-specific information")
        get_solana_specific_info(sol_wallet)
        
        # Example 7: Get Solana features
        logger.info("\n🔧 Example 7: Getting Solana features")
        get_solana_features(sol_wallet)
        
        # Example 8: Get SPL token information
        logger.info("\n🪙 Example 8: Getting SPL token information")
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC on Solana
        get_spl_token_info(sol_wallet, usdc_mint)
        
        logger.info("\n" + "="*50)
        logger.info("✅ All examples completed successfully!")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"❌ Error in example: {e}")
        logger.error("Make sure ALCHEMY_SOLANA_API_KEY is set correctly")

if __name__ == "__main__":
    main() 