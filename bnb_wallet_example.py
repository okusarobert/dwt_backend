#!/usr/bin/env python3
"""
BNB Wallet Usage Example
Shows how to use the BNBWallet class in a real application
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

def create_user_wallet(user_id: int, session, network: str = "testnet"):
    """
    Create a new BNB wallet for a user
    
    Args:
        user_id: User ID
        session: Database session
        network: Network to use (mainnet, testnet)
    
    Returns:
        BNBWallet instance
    """
    # Get API key from environment
    api_key = config('ALCHEMY_BNB_API_KEY')
    if not api_key:
        raise ValueError("ALCHEMY_BNB_API_KEY environment variable is required")
    
    # Create configuration based on network
    if network == "mainnet":
        bnb_config = BNBConfig.mainnet(api_key)
    elif network == "testnet":
        bnb_config = BNBConfig.testnet(api_key)
    else:
        raise ValueError(f"Unsupported network: {network}")
    
    # Create wallet instance
    bnb_wallet = BNBWallet(
        user_id=user_id,
        config=bnb_config,
        session=session,
        logger=logger
    )
    
    # Create wallet in database
    bnb_wallet.create_wallet()
    
    return bnb_wallet

def get_user_balance(bnb_wallet: BNBWallet, address: str):
    """
    Get balance for a user's address
    
    Args:
        bnb_wallet: BNBWallet instance
        address: BNB address
    
    Returns:
        Balance information
    """
    balance = bnb_wallet.get_balance(address)
    if balance:
        logger.info(f"Balance for {address}: {balance['balance_bnb']:.6f} BNB")
        return balance
    else:
        logger.error(f"Failed to get balance for {address}")
        return None

def monitor_transactions(bnb_wallet: BNBWallet, address: str):
    """
    Monitor transactions for an address
    
    Args:
        bnb_wallet: BNBWallet instance
        address: BNB address to monitor
    """
    # Get transaction count (nonce)
    tx_count = bnb_wallet.get_transaction_count(address)
    if tx_count is not None:
        logger.info(f"Transaction count for {address}: {tx_count}")
    
    # Get account info
    account_info = bnb_wallet.get_account_info(address)
    if account_info:
        logger.info(f"Account info for {address}:")
        logger.info(f"  - Transaction count: {account_info['transaction_count']}")
        logger.info(f"  - Is contract: {account_info['is_contract']}")
        if account_info['balance']:
            logger.info(f"  - Balance: {account_info['balance']['balance_bnb']:.6f} BNB")

def estimate_transaction_gas(bnb_wallet: BNBWallet, from_address: str, to_address: str, value_bnb: float = 0.001):
    """
    Estimate gas for a transaction
    
    Args:
        bnb_wallet: BNBWallet instance
        from_address: Sender address
        to_address: Recipient address
        value_bnb: Amount in BNB
    
    Returns:
        Gas estimate
    """
    # Convert BNB to wei (hex format)
    value_wei = int(value_bnb * (10 ** 18))
    value_hex = hex(value_wei)
    
    gas_estimate = bnb_wallet.estimate_gas(
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

def get_network_status(bnb_wallet: BNBWallet):
    """
    Get current network status
    
    Args:
        bnb_wallet: BNBWallet instance
    
    Returns:
        Network status information
    """
    # Test connection
    if not bnb_wallet.test_connection():
        logger.error("❌ Cannot connect to BNB API")
        return None
    
    # Get blockchain info
    blockchain_info = bnb_wallet.get_blockchain_info()
    logger.info("📊 Blockchain Information:")
    logger.info(f"  - Network: {blockchain_info.get('network')}")
    logger.info(f"  - Latest block: {blockchain_info.get('latest_block')}")
    logger.info(f"  - Connection status: {blockchain_info.get('connection_status')}")
    
    # Get gas price
    gas_price = bnb_wallet.get_gas_price()
    if gas_price:
        logger.info(f"  - Gas price: {gas_price['gas_price_gwei']:.2f} Gwei")
    
    # Get recent blocks
    recent_blocks = bnb_wallet.get_recent_blocks(3)
    logger.info(f"  - Recent blocks: {len(recent_blocks)} retrieved")
    
    return blockchain_info

def validate_and_monitor_address(bnb_wallet: BNBWallet, address: str):
    """
    Validate an address and get its information
    
    Args:
        bnb_wallet: BNBWallet instance
        address: BNB address to validate and monitor
    """
    # Validate address format
    if not bnb_wallet.validate_address(address):
        logger.error(f"❌ Invalid BNB address: {address}")
        return False
    
    logger.info(f"✅ Valid BNB address: {address}")
    
    # Get balance
    balance = get_user_balance(bnb_wallet, address)
    
    # Monitor transactions
    monitor_transactions(bnb_wallet, address)
    
    return True

def get_token_balances(bnb_wallet: BNBWallet, wallet_address: str):
    """
    Get BEP-20 token balances for a wallet
    
    Args:
        bnb_wallet: BNBWallet instance
        wallet_address: Wallet address to check
    """
    # Common BEP-20 tokens on BNB Smart Chain
    tokens = {
        "CAKE": "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",  # PancakeSwap
        "BUSD": "0xe9e7cea3dedca5984780bafc599bd69add087d56",  # Binance USD
        "USDT": "0x55d398326f99059ff775485246999027b3197955",  # Tether USD
        "WBNB": "0xbb4cdb9cbd36b01bd1cbaef2af88c6bb9c4d9a3b",  # Wrapped BNB
        "ADA": "0x3ee2200efb3400fabb9aacf31297cbdd1d435d47",  # Cardano
    }
    
    logger.info("🪙 Token Balances:")
    for token_name, token_address in tokens.items():
        token_balance = bnb_wallet.get_token_balance(token_address, wallet_address)
        if token_balance and token_balance['balance'] > 0:
            logger.info(f"  - {token_name}: {token_balance['balance']}")

def get_bnb_specific_info(bnb_wallet: BNBWallet):
    """
    Get BNB-specific information
    
    Args:
        bnb_wallet: BNBWallet instance
    """
    bnb_info = bnb_wallet.get_bnb_specific_info()
    
    logger.info("🔧 BNB-Specific Information:")
    logger.info(f"  - Network: {bnb_info.get('network')}")
    logger.info(f"  - Chain ID: {bnb_info.get('chain_id')}")
    logger.info(f"  - Consensus: {bnb_info.get('consensus')}")
    logger.info(f"  - Block Time: {bnb_info.get('block_time')}")
    logger.info(f"  - Finality: {bnb_info.get('finality')}")
    logger.info(f"  - Native Token: {bnb_info.get('native_token')}")
    
    return bnb_info

def get_bnb_features(bnb_wallet: BNBWallet):
    """
    Get BNB-specific features
    
    Args:
        bnb_wallet: BNBWallet instance
    """
    features = bnb_wallet.get_bnb_features()
    
    logger.info("🔧 BNB Features:")
    for feature, value in features.items():
        logger.info(f"  - {feature}: {value}")
    
    return features

def get_comprehensive_account_info(bnb_wallet: BNBWallet, address: str):
    """
    Get comprehensive account information
    
    Args:
        bnb_wallet: BNBWallet instance
        address: BNB address
    """
    comprehensive_info = bnb_wallet.get_account_info(address)
    
    if comprehensive_info:
        logger.info(f"📊 Comprehensive Account Info for {address}:")
        
        if comprehensive_info.get('balance'):
            balance = comprehensive_info['balance']
            logger.info(f"  - BNB Balance: {balance['balance_bnb']:.6f} BNB")
            logger.info(f"  - Wei: {balance['balance_wei']}")
        
        logger.info(f"  - Transaction Count: {comprehensive_info.get('transaction_count')}")
        logger.info(f"  - Is Contract: {comprehensive_info.get('is_contract')}")
    
    return comprehensive_info

def get_bep20_token_info(bnb_wallet: BNBWallet, token_address: str):
    """
    Get BEP-20 token information
    
    Args:
        bnb_wallet: BNBWallet instance
        token_address: Token contract address
    """
    token_info = bnb_wallet.get_bep20_token_info(token_address)
    
    if token_info:
        logger.info(f"🪙 BEP-20 Token Info for {token_address}:")
        logger.info(f"  - Name: {token_info.get('name')}")
        logger.info(f"  - Symbol: {token_info.get('symbol')}")
        logger.info(f"  - Decimals: {token_info.get('decimals')}")
        logger.info(f"  - Address: {token_info.get('address')}")
    
    return token_info

def main():
    """Main example function"""
    print("🔧 BNB Wallet Usage Example")
    print("📡 Demonstrating BNBWallet class usage")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALCHEMY_BNB_API_KEY')
    if not api_key:
        print("⚠️  No ALCHEMY_BNB_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.alchemy.com/")
        print("💡 Set ALCHEMY_BNB_API_KEY environment variable to run this example.")
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
        bnb_wallet = create_user_wallet(user_id, mock_session, "testnet")
        logger.info(f"✅ Created wallet for user {user_id}")
        
        # Example 2: Get network status
        logger.info("\n🌐 Example 2: Getting network status")
        network_status = get_network_status(bnb_wallet)
        
        # Example 3: Validate and monitor an address
        logger.info("\n👤 Example 3: Validating and monitoring address")
        test_address = "0x28C6c06298d514Db089934071355E5743bf21d60"  # Binance Hot Wallet
        validate_and_monitor_address(bnb_wallet, test_address)
        
        # Example 4: Estimate gas for a transaction
        logger.info("\n⛽ Example 4: Estimating gas for transaction")
        from_addr = "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6"
        to_addr = "0x28C6c06298d514Db089934071355E5743bf21d60"
        estimate_transaction_gas(bnb_wallet, from_addr, to_addr, 0.001)
        
        # Example 5: Get token balances
        logger.info("\n🪙 Example 5: Getting token balances")
        get_token_balances(bnb_wallet, test_address)
        
        # Example 6: Get BNB-specific information
        logger.info("\n🔧 Example 6: Getting BNB-specific information")
        get_bnb_specific_info(bnb_wallet)
        
        # Example 7: Get BNB features
        logger.info("\n🔧 Example 7: Getting BNB features")
        get_bnb_features(bnb_wallet)
        
        # Example 8: Get comprehensive account information
        logger.info("\n📊 Example 8: Getting comprehensive account information")
        comprehensive_info = get_comprehensive_account_info(bnb_wallet, test_address)
        
        # Example 9: Get BEP-20 token information
        logger.info("\n🪙 Example 9: Getting BEP-20 token information")
        cake_token = "0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82"  # CAKE on BNB
        get_bep20_token_info(bnb_wallet, cake_token)
        
        logger.info("\n" + "="*50)
        logger.info("✅ All examples completed successfully!")
        logger.info("="*50)
        
    except Exception as e:
        logger.error(f"❌ Error in example: {e}")
        logger.error("Make sure ALCHEMY_BNB_API_KEY is set correctly")

if __name__ == "__main__":
    main() 