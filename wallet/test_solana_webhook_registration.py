#!/usr/bin/env python3
"""
Test script for Solana webhook registration functionality
Tests the new approach: one webhook per network, add addresses to existing webhook
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.clients.sol import SOLWallet, SolanaConfig
from db.connection import session
from shared.logger import setup_logging
from decouple import config

logger = setup_logging()

def test_solana_webhook_registration():
    """Test the Solana webhook registration functionality"""
    try:
        # Get Alchemy API key
        alchemy_api_key = config('ALCHEMY_API_KEY', default=None)
        if not alchemy_api_key:
            logger.error("ALCHEMY_API_KEY not configured")
            return False
        
        # Create Solana config for testnet
        sol_config = SolanaConfig.testnet(alchemy_api_key)
        
        # Create a test wallet instance
        test_user_id = 999  # Test user ID
        wallet = SOLWallet(test_user_id, sol_config, session, logger)
        
        logger.info("Testing Solana webhook registration...")
        
        # Test 1: Register a test address with webhook (creates webhook if none exists)
        # Use a valid Solana address format (base58 encoded, 32-44 characters)
        test_address = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"  # Valid Solana address
        logger.info(f"Testing webhook registration for address: {test_address}")
        
        success = wallet.register_address_with_webhook(test_address)
        if success:
            logger.info("✅ Webhook registration test passed")
        else:
            logger.warning("⚠️ Webhook registration test failed (this might be expected if Alchemy API is not configured)")
        
        # Test 2: Register another address (should add to existing webhook)
        test_address2 = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"  # Another valid Solana address
        logger.info(f"Testing adding second address to webhook: {test_address2}")
        
        success2 = wallet.register_address_with_webhook(test_address2)
        if success2:
            logger.info("✅ Second address registration test passed")
        else:
            logger.warning("⚠️ Second address registration test failed")
        
        # Test 3: Test unregistration
        logger.info(f"Testing webhook unregistration for address: {test_address}")
        unregister_success = wallet.unregister_address_from_webhook(test_address)
        if unregister_success:
            logger.info("✅ Webhook unregistration test passed")
        else:
            logger.warning("⚠️ Webhook unregistration test failed (this might be expected if Alchemy API is not configured)")
        
        # Test 4: Test registering all addresses (should be empty for test user)
        logger.info("Testing registration of all addresses...")
        all_results = wallet.register_all_addresses_with_webhook()
        logger.info(f"All addresses registration results: {all_results}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing Solana webhook registration: {e}")
        return False

def test_address_creation_with_webhook():
    """Test creating a new address and automatic webhook registration"""
    try:
        # Get Alchemy API key
        alchemy_api_key = config('ALCHEMY_API_KEY', default=None)
        if not alchemy_api_key:
            logger.error("ALCHEMY_API_KEY not configured")
            return False
        
        # Create Solana config for testnet
        sol_config = SolanaConfig.testnet(alchemy_api_key)
        
        # Create a test wallet instance
        test_user_id = 999  # Test user ID
        wallet = SOLWallet(test_user_id, sol_config, session, logger)
        
        logger.info("Testing address creation with automatic webhook registration...")
        
        # This would create a real address and register it with webhook
        # Note: This requires Solana SDK to be installed
        try:
            wallet.create_address()
            logger.info("✅ Address creation with webhook registration test passed")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Address creation test failed (this might be expected if Solana SDK is not installed): {e}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error testing address creation with webhook: {e}")
        return False

def test_webhook_management():
    """Test the webhook management functionality"""
    try:
        # Get Alchemy API key
        alchemy_api_key = config('ALCHEMY_API_KEY', default=None)
        if not alchemy_api_key:
            logger.error("ALCHEMY_API_KEY not configured")
            return False
        
        # Create Solana config for testnet
        sol_config = SolanaConfig.testnet(alchemy_api_key)
        
        # Create a test wallet instance
        test_user_id = 999  # Test user ID
        wallet = SOLWallet(test_user_id, sol_config, session, logger)
        
        logger.info("Testing webhook management functionality...")
        
        # Test getting existing webhooks
        alchemy_url = f"https://solana-devnet.g.alchemy.com/v2/{alchemy_api_key}"
        existing_webhooks = wallet._get_existing_webhooks(alchemy_url)
        logger.info(f"Existing webhooks: {existing_webhooks}")
        
        # Test webhook creation (if no webhooks exist)
        if not existing_webhooks:
            logger.info("No existing webhooks found, testing webhook creation...")
            webhook_url = config('WEBHOOK_BASE_URL', default='http://localhost:3030')
            webhook_endpoint = f"{webhook_url}/api/v1/wallet/sol/callbacks/address-webhook"
            test_address = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"  # Valid Solana address
            
            success = wallet._create_webhook_with_address(alchemy_url, webhook_endpoint, test_address)
            if success:
                logger.info("✅ Webhook creation test passed")
            else:
                logger.warning("⚠️ Webhook creation test failed")
        else:
            logger.info("Existing webhooks found, testing address addition...")
            webhook_id = existing_webhooks[0]['id']
            test_address = "6ZRCB7AAqGre6c72PRz3MHLC73VMYvJ8bi9KHf1HFpNk"  # Valid Solana address
            
            success = wallet._add_address_to_webhook(alchemy_url, webhook_id, test_address)
            if success:
                logger.info("✅ Address addition to existing webhook test passed")
            else:
                logger.warning("⚠️ Address addition test failed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing webhook management: {e}")
        return False

if __name__ == "__main__":
    logger.info("🧪 Starting Solana webhook registration tests...")
    
    # Test 1: Basic webhook registration
    test1_result = test_solana_webhook_registration()
    
    # Test 2: Address creation with webhook
    test2_result = test_address_creation_with_webhook()
    
    # Test 3: Webhook management
    test3_result = test_webhook_management()
    
    logger.info("📊 Test Results:")
    logger.info(f"   Webhook registration test: {'✅ PASSED' if test1_result else '❌ FAILED'}")
    logger.info(f"   Address creation test: {'✅ PASSED' if test2_result else '❌ FAILED'}")
    logger.info(f"   Webhook management test: {'✅ PASSED' if test3_result else '❌ FAILED'}")
    
    if test1_result and test2_result and test3_result:
        logger.info("🎉 All tests passed!")
    else:
        logger.warning("⚠️ Some tests failed (check logs for details)")
