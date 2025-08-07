#!/usr/bin/env python3
"""
Ethereum Wallet Usage Example
Shows how to use the ETHWallet class in a real application
"""

import os
import logging
from decouple import config
from shared.crypto.clients.eth import ETHWallet, EthereumConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_user_wallet(user_id: int, session, network: str = "sepolia"):
    """
    Create a new Ethereum wallet for a user
    
    Args:
        user_id: User ID
        session: Database session
        network: Network to use (mainnet, sepolia, holesky)
    
    Returns:
        ETHWallet instance
    """
    # Get API key from environment
    api_key = config('ALCHEMY_API_KEY')
    if not api_key:
        raise ValueError("ALCHEMY_API_KEY environment variable is required")
    
    # Create configuration based on network
    if network == "mainnet":
        eth_config = EthereumConfig.mainnet(api_key)
    elif network == "sepolia":
        eth_config = EthereumConfig.testnet(api_key)
    elif network == "holesky":
        eth_config = EthereumConfig.holesky(api_key)
    else:
        raise ValueError(f"Unsupported network: {network}")
    
    # Create wallet instance
    eth_wallet = ETHWallet(
        user_id=user_id,
        config=eth_config,
        session=session,
        logger=logger
    )
    
    # Create wallet in database
    eth_wallet.create_wallet()
    
    return eth_wallet

def get_user_balance(eth_wallet: ETHWallet, address: str):
    """
    Get balance for a user's address
    
    Args:
        eth_wallet: ETHWallet instance
        address: Ethereum address
    
    Returns:
        Balance information
    """
    balance = eth_wallet.get_balance(address)
    if balance:
        logger.info(f"Balance for {address}: {balance['balance_eth']:.6f} ETH")
        return balance
    else:
        logger.error(f"Failed to get balance for {address}")
        return None

def monitor_transactions(eth_wallet: ETHWallet, address: str):
    """
    Monitor transactions for an address
    
    Args:
        eth_wallet: ETHWallet instance
        address: Ethereum address to monitor
    """
    # Get transaction count (nonce)
    tx_count = eth_wallet.get_transaction_count(address)
    if tx_count is not None:
        logger.info(f"Transaction count for {address}: {tx_count}")
    
    # Get account info
    account_info = eth_wallet.get_account_info(address)
    if account_info:
        logger.info(f"Account info for {address}:")
        logger.info(f"  - Transaction count: {account_info['transaction_count']}")
        logger.info(f"  - Is contract: {account_info['is_contract']}")
        if account_info['balance']:
            logger.info(f"  - Balance: {account_info['balance']['balance_eth']:.6f} ETH")

def estimate_transaction_gas(eth_wallet: ETHWallet, from_address: str, to_address: str, value_eth: float = 0.001):
    """
    Estimate gas for a transaction
    
    Args:
        eth_wallet: ETHWallet instance
        from_address: Sender address
        to_address: Recipient address
        value_eth: Amount in ETH
    
    Returns:
        Gas estimate
    """
    # Convert ETH to wei (hex format)
    value_wei = int(value_eth * (10 ** 18))
    value_hex = hex(value_wei)
    
    gas_estimate = eth_wallet.estimate_gas(
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

def get_network_status(eth_wallet: ETHWallet):
    """
    Get current network status
    
    Args:
        eth_wallet: ETHWallet instance
    
    Returns:
        Network status information
    """
    # Test connection
    if not eth_wallet.test_connection():
        logger.error("❌ Cannot connect to Alchemy API")
        return None
    
    # Get blockchain info
    blockchain_info = eth_wallet.get_blockchain_info()
    logger.info("📊 Blockchain Information:")
    logger.info(f"  - Network: {blockchain_info.get('network')}")
    logger.info(f"  - Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"  - Connection status: {blockchain_info.get('connection_status')}")
    
    # Get gas price
    gas_price = eth_wallet.get_gas_price()
    if gas_price:
        logger.info(f"  - Gas price: {gas_price['gas_price_gwei']:.2f} gwei")
    
    # Get recent blocks
    recent_blocks = eth_wallet.get_recent_blocks(3)
    logger.info(f"  - Recent blocks: {len(recent_blocks)} retrieved")
    
    return blockchain_info

def validate_and_monitor_address(eth_wallet: ETHWallet, address: str):
    """
    Validate an address and get its information
    
    Args:
        eth_wallet: ETHWallet instance
        address: Ethereum address to validate and monitor
    """
    # Validate address format
    if not eth_wallet.validate_address(address):
        logger.error(f"❌ Invalid Ethereum address: {address}")
        return False
    
    logger.info(f"✅ Valid Ethereum address: {address}")
    
    # Get balance
    balance = get_user_balance(eth_wallet, address)
    
    # Monitor transactions
    monitor_transactions(eth_wallet, address)
    
    return True

def main():
    """Main example function"""
    print("🔧 Ethereum Wallet Usage Example")
    print("📡 Demonstrating ETHWallet class usage")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Set ALCHEMY_API_KEY environment variable to run this example.")
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
        eth_wallet = create_user_wallet(user_id, mock_session, "sepolia")
        logger.info(f"✅ Created wallet for user {user_id}")
        
        # Example 2: Get network status
        logger.info("\n🌐 Example 2: Getting network status")
        network_status = get_network_status(eth_wallet)
        
        # Example 3: Validate and monitor an address
        logger.info("\n👤 Example 3: Validating and monitoring address")
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"  # Vitalik's address
        validate_and_monitor_address(eth_wallet, test_address)
        
        # Example 4: Estimate gas for a transaction
        logger.info("\n⛽ Example 4: Estimating gas for transaction")
        from_addr = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        to_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        estimate_transaction_gas(eth_wallet, from_addr, to_addr, 0.001)
        
        logger.info("\n" + "="*50)
        logger.info("✅ All examples completed successfully!")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"❌ Error in example: {e}")
        logger.error("Make sure ALCHEMY_API_KEY is set correctly")

if __name__ == "__main__":
    main() 