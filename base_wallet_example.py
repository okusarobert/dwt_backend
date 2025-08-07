#!/usr/bin/env python3
"""
Base Wallet Usage Example
Shows how to use the BaseWallet class in a real application
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

def create_user_wallet(user_id: int, session, network: str = "sepolia"):
    """
    Create a new Base wallet for a user
    
    Args:
        user_id: User ID
        session: Database session
        network: Network to use (mainnet, sepolia)
    
    Returns:
        BaseWallet instance
    """
    # Get API key from environment
    api_key = config('ALCHEMY_BASE_API_KEY')
    if not api_key:
        raise ValueError("ALCHEMY_BASE_API_KEY environment variable is required")
    
    # Create configuration based on network
    if network == "mainnet":
        base_config = BaseConfig.mainnet(api_key)
    elif network == "sepolia":
        base_config = BaseConfig.testnet(api_key)
    else:
        raise ValueError(f"Unsupported network: {network}")
    
    # Create wallet instance
    base_wallet = BaseWallet(
        user_id=user_id,
        config=base_config,
        session=session,
        logger=logger
    )
    
    # Create wallet in database
    base_wallet.create_wallet()
    
    return base_wallet

def get_user_balance(base_wallet: BaseWallet, address: str):
    """
    Get balance for a user's address
    
    Args:
        base_wallet: BaseWallet instance
        address: Base address
    
    Returns:
        Balance information
    """
    balance = base_wallet.get_balance(address)
    if balance:
        logger.info(f"Balance for {address}: {balance['balance_base']:.6f} BASE")
        return balance
    else:
        logger.error(f"Failed to get balance for {address}")
        return None

def monitor_transactions(base_wallet: BaseWallet, address: str):
    """
    Monitor transactions for an address
    
    Args:
        base_wallet: BaseWallet instance
        address: Base address to monitor
    """
    # Get transaction count (nonce)
    tx_count = base_wallet.get_transaction_count(address)
    if tx_count is not None:
        logger.info(f"Transaction count for {address}: {tx_count}")
    
    # Get account info
    account_info = base_wallet.get_account_info(address)
    if account_info:
        logger.info(f"Account info for {address}:")
        logger.info(f"  - Transaction count: {account_info['transaction_count']}")
        logger.info(f"  - Is contract: {account_info['is_contract']}")
        if account_info['balance']:
            logger.info(f"  - Balance: {account_info['balance']['balance_base']:.6f} BASE")

def estimate_transaction_gas(base_wallet: BaseWallet, from_address: str, to_address: str, value_base: float = 0.001):
    """
    Estimate gas for a transaction
    
    Args:
        base_wallet: BaseWallet instance
        from_address: Sender address
        to_address: Recipient address
        value_base: Amount in BASE
    
    Returns:
        Gas estimate
    """
    # Convert BASE to wei (hex format)
    value_wei = int(value_base * (10 ** 18))
    value_hex = hex(value_wei)
    
    gas_estimate = base_wallet.estimate_gas(
        from_address=from_address,
        to_address=to_address,
        value=value_hex
    )
    
    if gas_estimate:
        logger.info(f"Gas estimate: {gas_estimate['gas_estimate']} gas units")
        return gas_estimate
    else:
        logger.error("Failed to estimate gas")
        return None

def get_network_status(base_wallet: BaseWallet):
    """
    Get current network status
    
    Args:
        base_wallet: BaseWallet instance
    
    Returns:
        Network status information
    """
    # Test connection
    if not base_wallet.test_connection():
        logger.error("❌ Cannot connect to Base API")
        return None
    
    # Get blockchain info
    blockchain_info = base_wallet.get_blockchain_info()
    logger.info("📊 Blockchain Information:")
    logger.info(f"  - Network: {blockchain_info.get('network')}")
    logger.info(f"  - Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"  - Connection status: {blockchain_info.get('connection_status')}")
    
    # Get gas price
    gas_price = base_wallet.get_gas_price()
    if gas_price:
        logger.info(f"  - Gas price: {gas_price['gas_price_gwei']:.2f} gwei")
    
    # Get recent blocks
    recent_blocks = base_wallet.get_recent_blocks(3)
    logger.info(f"  - Recent blocks: {len(recent_blocks)} retrieved")
    
    return blockchain_info

def validate_and_monitor_address(base_wallet: BaseWallet, address: str):
    """
    Validate an address and get its information
    
    Args:
        base_wallet: BaseWallet instance
        address: Base address to validate and monitor
    """
    # Validate address format
    if not base_wallet.validate_address(address):
        logger.error(f"❌ Invalid Base address: {address}")
        return False
    
    logger.info(f"✅ Valid Base address: {address}")
    
    # Get balance
    balance = get_user_balance(base_wallet, address)
    
    # Monitor transactions
    monitor_transactions(base_wallet, address)
    
    return True

def get_token_balance_example(base_wallet: BaseWallet, wallet_address: str):
    """
    Example of getting token balance on Base
    
    Args:
        base_wallet: BaseWallet instance
        wallet_address: Wallet address to check
    """
    # Common tokens on Base
    tokens = {
        "USDC": "0x036CbD53842c5426634e7929541eC2318f3dCF7c",  # USDC on Base Sepolia
        "USDT": "0x7169D38820dfd117C3FA1f22a697dBA58d90BA06",  # USDT on Base Sepolia
        "WETH": "0x4200000000000000000000000000000000000006",  # WETH on Base Sepolia
    }
    
    logger.info("🪙 Token Balances:")
    for token_name, token_address in tokens.items():
        token_balance = base_wallet.get_token_balance(token_address, wallet_address)
        if token_balance and token_balance['balance'] > 0:
            logger.info(f"  - {token_name}: {token_balance['balance']}")
        else:
            logger.info(f"  - {token_name}: 0")

def get_l2_specific_info(base_wallet: BaseWallet):
    """
    Get L2-specific information for Base
    
    Args:
        base_wallet: BaseWallet instance
    """
    l2_info = base_wallet.get_base_specific_info()
    
    logger.info("🔧 L2-Specific Information:")
    logger.info(f"  - Network: {l2_info.get('network')}")
    logger.info(f"  - Chain ID: {l2_info.get('chain_id')}")
    logger.info(f"  - Is L2: {l2_info.get('is_l2')}")
    logger.info(f"  - L1 Chain: {l2_info.get('l1_chain')}")
    logger.info(f"  - L2 Block Number: {l2_info.get('l2_block_number')}")
    
    return l2_info

def main():
    """Main example function"""
    print("🔧 Base Wallet Usage Example")
    print("📡 Demonstrating BaseWallet class usage")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_BASE_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_BASE_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Set ALCHEMY_BASE_API_KEY environment variable to run this example.")
        return
    
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
        base_wallet = create_user_wallet(user_id, mock_session, "sepolia")
        logger.info(f"✅ Created wallet for user {user_id}")
        
        # Example 2: Get network status
        logger.info("\n🌐 Example 2: Getting network status")
        network_status = get_network_status(base_wallet)
        
        # Example 3: Validate and monitor an address
        logger.info("\n👤 Example 3: Validating and monitoring address")
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        validate_and_monitor_address(base_wallet, test_address)
        
        # Example 4: Estimate gas for a transaction
        logger.info("\n⛽ Example 4: Estimating gas for transaction")
        from_addr = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        to_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        estimate_transaction_gas(base_wallet, from_addr, to_addr, 0.001)
        
        # Example 5: Get token balances
        logger.info("\n🪙 Example 5: Getting token balances")
        get_token_balance_example(base_wallet, test_address)
        
        # Example 6: Get L2-specific information
        logger.info("\n🔧 Example 6: Getting L2-specific information")
        get_l2_specific_info(base_wallet)
        
        logger.info("\n" + "="*50)
        logger.info("✅ All examples completed successfully!")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"❌ Error in example: {e}")
        logger.error("Make sure ALCHEMY_BASE_API_KEY is set correctly")

if __name__ == "__main__":
    main() 