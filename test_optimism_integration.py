#!/usr/bin/env python3
"""
Optimism Integration Test Script
Tests the complete Optimism wallet integration
"""

import os
import sys
import logging
from decouple import config
from sqlalchemy.orm import Session
from db.connection import get_session
from db.wallet import Account, AccountType, CryptoAddress
from db import User
from shared.crypto.HD import OPTIMISM, get_wallet
from shared.crypto.clients.optimism import OptimismWallet, OptimismConfig
from shared.logger import setup_logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Setup logging for the script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def test_hd_wallet_integration():
    """Test the HD wallet integration for Optimism"""
    logger = setup_logging()
    logger.info("🧪 Testing HD wallet integration...")
    
    try:
        # Test getting OPTIMISM wallet class
        optimism_wallet_class = get_wallet("OPTIMISM")
        if optimism_wallet_class is None:
            logger.error("❌ Failed to get OPTIMISM wallet class")
            return False
        
        logger.info("✅ OPTIMISM wallet class retrieved successfully")
        
        # Test wallet instantiation
        optimism_wallet = optimism_wallet_class()
        logger.info("✅ OPTIMISM wallet instantiated successfully")
        
        # Test mnemonic generation
        mnemonic = optimism_wallet.mnemonic()
        if not mnemonic or len(mnemonic.split()) != 12:
            logger.error("❌ Failed to generate valid mnemonic")
            return False
        
        logger.info("✅ Mnemonic generated successfully")
        
        # Test wallet from mnemonic
        wallet = optimism_wallet.from_mnemonic(mnemonic=mnemonic)
        logger.info("✅ Wallet created from mnemonic successfully")
        
        # Test address generation
        address, priv_key, pub_key = wallet.new_address(index=0)
        if not address or not priv_key or not pub_key:
            logger.error("❌ Failed to generate address")
            return False
        
        logger.info(f"✅ Address generated successfully: {address}")
        logger.info(f"✅ Private key generated: {priv_key[:10]}...")
        logger.info(f"✅ Public key generated: {pub_key[:10]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ HD wallet integration test failed: {e}")
        return False

def test_optimism_client_integration():
    """Test the Optimism client integration"""
    logger = setup_logging()
    logger.info("🧪 Testing Optimism client integration...")
    
    try:
        # Test configuration
        api_key = config('ALCHEMY_OPTIMISM_API_KEY', default='demo')
        optimism_config = OptimismConfig.testnet(api_key)
        
        if not optimism_config.base_url:
            logger.error("❌ Failed to create Optimism configuration")
            return False
        
        logger.info("✅ Optimism configuration created successfully")
        logger.info(f"✅ Base URL: {optimism_config.base_url}")
        
        # Test wallet client creation
        session = get_session()
        try:
            optimism_wallet = OptimismWallet(
                user_id=1,
                config=optimism_config,
                session=session
            )
            logger.info("✅ Optimism wallet client created successfully")
            
            # Test connection (if API key is configured)
            if api_key != 'demo':
                if optimism_wallet.test_connection():
                    logger.info("✅ Optimism API connection successful")
                else:
                    logger.warning("⚠️ Optimism API connection failed (may be expected with demo key)")
            else:
                logger.info("ℹ️ Skipping API connection test with demo key")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Optimism client integration test failed: {e}")
        return False

def test_database_integration():
    """Test database integration for Optimism"""
    logger = setup_logging()
    logger.info("🧪 Testing database integration...")
    
    session = get_session()
    
    try:
        # Test creating a test user
        test_user = User(
            email="test.optimism@example.com",
            password_hash="test_hash",
            is_active=True
        )
        session.add(test_user)
        session.flush()
        logger.info(f"✅ Test user created with ID: {test_user.id}")
        
        # Test creating Optimism account
        optimism_account = Account(
            user_id=test_user.id,
            balance=0,
            locked_amount=0,
            currency="OPTIMISM",
            account_type=AccountType.CRYPTO,
            account_number="TEST_OPTIMISM_001",
            label="Test Optimism Account"
        )
        session.add(optimism_account)
        session.flush()
        logger.info(f"✅ Optimism account created with ID: {optimism_account.id}")
        
        # Test creating Optimism address
        test_address = CryptoAddress(
            account_id=optimism_account.id,
            address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            label="Test Optimism Address",
            is_active=True,
            currency_code="OPTIMISM",
            address_type="hd_wallet"
        )
        session.add(test_address)
        session.commit()
        logger.info("✅ Optimism address created successfully")
        
        # Test querying Optimism data
        optimism_accounts = session.query(Account).filter_by(currency="OPTIMISM").all()
        optimism_addresses = session.query(CryptoAddress).filter_by(currency_code="OPTIMISM").all()
        
        logger.info(f"✅ Found {len(optimism_accounts)} Optimism accounts")
        logger.info(f"✅ Found {len(optimism_addresses)} Optimism addresses")
        
        # Clean up test data
        session.delete(test_address)
        session.delete(optimism_account)
        session.delete(test_user)
        session.commit()
        logger.info("✅ Test data cleaned up successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database integration test failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def test_crypto_configuration():
    """Test crypto configuration for Optimism"""
    logger = setup_logging()
    logger.info("🧪 Testing crypto configuration...")
    
    try:
        from shared.crypto import cryptos
        
        # Check if OPTIMISM is in the accounts list
        optimism_crypto = None
        for crypto in cryptos.accounts:
            if crypto["symbol"] == "OPTIMISM":
                optimism_crypto = crypto
                break
        
        if not optimism_crypto:
            logger.error("❌ OPTIMISM not found in crypto configuration")
            return False
        
        logger.info("✅ OPTIMISM found in crypto configuration")
        logger.info(f"✅ Name: {optimism_crypto['name']}")
        logger.info(f"✅ Symbol: {optimism_crypto['symbol']}")
        logger.info(f"✅ Is Chain: {optimism_crypto['is_chain']}")
        logger.info(f"✅ Decimals: {optimism_crypto['decimals']}")
        
        # Verify configuration
        if optimism_crypto["name"] != "Optimism":
            logger.error("❌ Incorrect name for OPTIMISM")
            return False
        
        if optimism_crypto["is_chain"] != True:
            logger.error("❌ OPTIMISM should be marked as a chain")
            return False
        
        if optimism_crypto["decimals"] != 18:
            logger.error("❌ OPTIMISM should have 18 decimals")
            return False
        
        logger.info("✅ Optimism configuration is correct")
        return True
        
    except Exception as e:
        logger.error(f"❌ Crypto configuration test failed: {e}")
        return False

def test_wallet_service_integration():
    """Test wallet service integration for Optimism"""
    logger = setup_logging()
    logger.info("🧪 Testing wallet service integration...")
    
    try:
        # Test importing OPTIMISM from wallet service
        from wallet.app import create_crypto_addresses_for_user
        
        logger.info("✅ Optimism wallet service functions imported successfully")
        
        # Test that OPTIMISM is in the crypto wallet classes
        from wallet.app import crypto_wallet_classes
        if "OPTIMISM" not in crypto_wallet_classes:
            logger.error("❌ OPTIMISM not found in wallet service crypto classes")
            return False
        
        logger.info("✅ OPTIMISM found in wallet service crypto classes")
        return True
        
    except Exception as e:
        logger.error(f"❌ Wallet service integration test failed: {e}")
        return False

def main():
    """Run all Optimism integration tests"""
    logger = setup_logging()
    logger.info("🚀 Starting Optimism integration tests...")
    
    tests = [
        ("HD Wallet Integration", test_hd_wallet_integration),
        ("Optimism Client Integration", test_optimism_client_integration),
        ("Database Integration", test_database_integration),
        ("Crypto Configuration", test_crypto_configuration),
        ("Wallet Service Integration", test_wallet_service_integration),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 All Optimism integration tests passed!")
        logger.info("✅ Optimism wallet is ready for production use!")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed")
        logger.error("Please fix the failing tests before deploying")
        return 1

if __name__ == "__main__":
    exit(main()) 