#!/usr/bin/env python3
"""
Test script for complete webhook registration flow using sol.py logic
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from shared.crypto.clients.sol import SOLWallet, SolanaConfig
from shared.logger import setup_logging
from db.connection import session
from decouple import config

def test_webhook_registration():
    """Test the complete webhook registration flow"""
    
    logger = setup_logging()
    
    # Create a test SOL wallet
    sol_config = SolanaConfig.mainnet(config('ALCHEMY_API_KEY', default='test_key'))
    wallet = SOLWallet(user_id=1, sol_config=sol_config, session=session, logger=logger)
    
    # Test address
    test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    
    print(f"🔧 Testing webhook registration for address: {test_address}")
    
    # Test registering the address with webhook
    success = wallet.register_address_with_webhook(test_address)
    
    if success:
        print(f"✅ Successfully registered address {test_address} with webhook")
    else:
        print(f"❌ Failed to register address {test_address} with webhook")
    
    return success

def test_webhook_unregistration():
    """Test the webhook unregistration flow"""
    
    logger = setup_logging()
    
    # Create a test SOL wallet
    sol_config = SolanaConfig.mainnet(config('ALCHEMY_API_KEY', default='test_key'))
    wallet = SOLWallet(user_id=1, sol_config=sol_config, session=session, logger=logger)
    
    # Test address
    test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    
    print(f"🔧 Testing webhook unregistration for address: {test_address}")
    
    # Test unregistering the address from webhook
    success = wallet.unregister_address_from_webhook(test_address)
    
    if success:
        print(f"✅ Successfully unregistered address {test_address} from webhook")
    else:
        print(f"❌ Failed to unregister address {test_address} from webhook")
    
    return success

def test_register_all_addresses():
    """Test registering all addresses with webhook"""
    
    logger = setup_logging()
    
    # Create a test SOL wallet
    sol_config = SolanaConfig.mainnet(config('ALCHEMY_API_KEY', default='test_key'))
    wallet = SOLWallet(user_id=1, sol_config=sol_config, session=session, logger=logger)
    
    print(f"🔧 Testing registration of all addresses with webhook")
    
    # Test registering all addresses
    result = wallet.register_all_addresses_with_webhook()
    
    print(f"Result: {result}")
    
    if result.get('registered_count', 0) > 0:
        print(f"✅ Successfully registered {result['registered_count']} addresses")
    else:
        print(f"❌ Failed to register addresses: {result.get('error', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "unregister":
            test_webhook_unregistration()
        elif sys.argv[1] == "all":
            test_register_all_addresses()
        else:
            test_webhook_registration()
    else:
        test_webhook_registration()
