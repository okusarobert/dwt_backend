#!/usr/bin/env python3
"""
Avalanche Wallet Usage Example
Shows how to use the AVAXWallet class in a real application
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

def create_user_wallet(user_id: int, session, network: str = "testnet"):
    """
    Create a new Avalanche wallet for a user
    
    Args:
        user_id: User ID
        session: Database session
        network: Network to use (mainnet, testnet)
    
    Returns:
        AVAXWallet instance
    """
    # Get API key from environment
    api_key = config('ALCHEMY_AVALANCHE_API_KEY')
    if not api_key:
        raise ValueError("ALCHEMY_AVALANCHE_API_KEY environment variable is required")
    
    # Create configuration based on network
    if network == "mainnet":
        avax_config = AvalancheConfig.mainnet(api_key)
    elif network == "testnet":
        avax_config = AvalancheConfig.testnet(api_key)
    else:
        raise ValueError(f"Unsupported network: {network}")
    
    # Create wallet instance
    avax_wallet = AVAXWallet(
        user_id=user_id,
        config=avax_config,
        session=session,
        logger=logger
    )
    
    # Create wallet in database
    avax_wallet.create_wallet()
    
    return avax_wallet

def get_user_balance(avax_wallet: AVAXWallet, address: str):
    """
    Get balance for a user's address
    
    Args:
        avax_wallet: AVAXWallet instance
        address: Avalanche address
    
    Returns:
        Balance information
    """
    balance = avax_wallet.get_balance(address)
    if balance:
        logger.info(f"Balance for {address}: {balance['balance_avax']:.6f} AVAX")
        return balance
    else:
        logger.error(f"Failed to get balance for {address}")
        return None

def monitor_transactions(avax_wallet: AVAXWallet, address: str):
    """
    Monitor transactions for an address
    
    Args:
        avax_wallet: AVAXWallet instance
        address: Avalanche address to monitor
    """
    # Get transaction count (nonce)
    tx_count = avax_wallet.get_transaction_count(address)
    if tx_count is not None:
        logger.info(f"Transaction count for {address}: {tx_count}")
    
    # Get account info
    account_info = avax_wallet.get_account_info(address)
    if account_info:
        logger.info(f"Account info for {address}:")
        logger.info(f"  - Transaction count: {account_info['transaction_count']}")
        logger.info(f"  - Is contract: {account_info['is_contract']}")
        if account_info['balance']:
            logger.info(f"  - Balance: {account_info['balance']['balance_avax']:.6f} AVAX")

def estimate_transaction_gas(avax_wallet: AVAXWallet, from_address: str, to_address: str, value_avax: float = 0.001):
    """
    Estimate gas for a transaction
    
    Args:
        avax_wallet: AVAXWallet instance
        from_address: Sender address
        to_address: Recipient address
        value_avax: Amount in AVAX
    
    Returns:
        Gas estimate
    """
    # Convert AVAX to wei (hex format)
    value_wei = int(value_avax * (10 ** 18))
    value_hex = hex(value_wei)
    
    gas_estimate = avax_wallet.estimate_gas(
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

def get_network_status(avax_wallet: AVAXWallet):
    """
    Get current network status
    
    Args:
        avax_wallet: AVAXWallet instance
    
    Returns:
        Network status information
    """
    # Test connection
    if not avax_wallet.test_connection():
        logger.error("❌ Cannot connect to Avalanche API")
        return None
    
    # Get blockchain info
    blockchain_info = avax_wallet.get_blockchain_info()
    logger.info("📊 Blockchain Information:")
    logger.info(f"  - Network: {blockchain_info.get('network')}")
    logger.info(f"  - Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"  - Connection status: {blockchain_info.get('connection_status')}")
    
    # Get gas price
    gas_price = avax_wallet.get_gas_price()
    if gas_price:
        logger.info(f"  - Gas price: {gas_price['gas_price_navax']:.2f} nAVAX")
    
    # Get recent blocks
    recent_blocks = avax_wallet.get_recent_blocks(3)
    logger.info(f"  - Recent blocks: {len(recent_blocks)} retrieved")
    
    return blockchain_info

def validate_and_monitor_address(avax_wallet: AVAXWallet, address: str):
    """
    Validate an address and get its information
    
    Args:
        avax_wallet: AVAXWallet instance
        address: Avalanche address to validate and monitor
    """
    # Validate address format
    if not avax_wallet.validate_address(address):
        logger.error(f"❌ Invalid Avalanche address: {address}")
        return False
    
    logger.info(f"✅ Valid Avalanche address: {address}")
    
    # Get balance
    balance = get_user_balance(avax_wallet, address)
    
    # Monitor transactions
    monitor_transactions(avax_wallet, address)
    
    return True

def get_token_balance_example(avax_wallet: AVAXWallet, wallet_address: str):
    """
    Example of getting token balance on Avalanche
    
    Args:
        avax_wallet: AVAXWallet instance
        wallet_address: Wallet address to check
    """
    # Common tokens on Avalanche
    tokens = {
        "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",  # USDC on Avalanche Mainnet
        "USDT": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",  # USDT on Avalanche Mainnet
        "WETH": "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",  # WETH on Avalanche Mainnet
    }
    
    logger.info("🪙 Token Balances:")
    for token_name, token_address in tokens.items():
        token_balance = avax_wallet.get_token_balance(token_address, wallet_address)
        if token_balance and token_balance['balance'] > 0:
            logger.info(f"  - {token_name}: {token_balance['balance']}")
        else:
            logger.info(f"  - {token_name}: 0")

def get_avalanche_specific_info(avax_wallet: AVAXWallet):
    """
    Get Avalanche-specific information
    
    Args:
        avax_wallet: AVAXWallet instance
    """
    avax_info = avax_wallet.get_avalanche_specific_info()
    
    logger.info("🔧 Avalanche-Specific Information:")
    logger.info(f"  - Network: {avax_info.get('network')}")
    logger.info(f"  - Chain ID: {avax_info.get('chain_id')}")
    logger.info(f"  - Consensus: {avax_info.get('consensus')}")
    logger.info(f"  - Subnet: {avax_info.get('subnet')}")
    logger.info(f"  - Native Token: {avax_info.get('native_token')}")
    
    return avax_info

def get_subnet_information(avax_wallet: AVAXWallet):
    """
    Get subnet information for Avalanche
    
    Args:
        avax_wallet: AVAXWallet instance
    """
    subnet_info = avax_wallet.get_subnet_info()
    
    logger.info("🔧 Subnet Information:")
    logger.info(f"  - Subnet: {subnet_info.get('subnet')}")
    logger.info(f"  - Description: {subnet_info.get('description')}")
    logger.info(f"  - Consensus: {subnet_info.get('consensus')}")
    logger.info(f"  - Block Time: {subnet_info.get('block_time')}")
    logger.info(f"  - Finality: {subnet_info.get('finality')}")
    logger.info(f"  - Gas Limit: {subnet_info.get('gas_limit')}")
    logger.info(f"  - Compatibility: {subnet_info.get('compatibility')}")
    
    return subnet_info

def main():
    """Main example function"""
    print("🔧 Avalanche Wallet Usage Example")
    print("📡 Demonstrating AVAXWallet class usage")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_AVALANCHE_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_AVALANCHE_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Set ALCHEMY_AVALANCHE_API_KEY environment variable to run this example.")
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
        avax_wallet = create_user_wallet(user_id, mock_session, "testnet")
        logger.info(f"✅ Created wallet for user {user_id}")
        
        # Example 2: Get network status
        logger.info("\n🌐 Example 2: Getting network status")
        network_status = get_network_status(avax_wallet)
        
        # Example 3: Validate and monitor an address
        logger.info("\n👤 Example 3: Validating and monitoring address")
        test_address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        validate_and_monitor_address(avax_wallet, test_address)
        
        # Example 4: Estimate gas for a transaction
        logger.info("\n⛽ Example 4: Estimating gas for transaction")
        from_addr = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        to_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
        estimate_transaction_gas(avax_wallet, from_addr, to_addr, 0.001)
        
        # Example 5: Get token balances
        logger.info("\n🪙 Example 5: Getting token balances")
        get_token_balance_example(avax_wallet, test_address)
        
        # Example 6: Get Avalanche-specific information
        logger.info("\n🔧 Example 6: Getting Avalanche-specific information")
        get_avalanche_specific_info(avax_wallet)
        
        # Example 7: Get subnet information
        logger.info("\n🔧 Example 7: Getting subnet information")
        get_subnet_information(avax_wallet)
        
        logger.info("\n" + "="*50)
        logger.info("✅ All examples completed successfully!")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"❌ Error in example: {e}")
        logger.error("Make sure ALCHEMY_AVALANCHE_API_KEY is set correctly")

if __name__ == "__main__":
    main() 