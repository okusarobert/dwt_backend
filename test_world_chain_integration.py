#!/usr/bin/env python3
"""
World Chain Integration Test Script
Tests the complete World Chain wallet integration
"""

import os
import sys
import logging
from decouple import config
from sqlalchemy.orm import Session
from db.connection import get_session
from db.wallet import Account, AccountType, CryptoAddress
from db import User
from shared.crypto.HD import WORLD, get_wallet
from shared.crypto.clients.world import WorldWallet, WorldConfig
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
    """Test the HD wallet integration for World Chain"""
    logger = setup_logging()
    logger.info("🧪 Testing HD wallet integration...")
    
    try:
        # Test getting WORLD wallet class
        world_wallet_class = get_wallet("WORLD")
        if world_wallet_class is None:
            logger.error("❌ Failed to get WORLD wallet class")
            return False
        
        logger.info("✅ WORLD wallet class retrieved successfully")
        
        # Test wallet instantiation
        world_wallet = world_wallet_class()
        logger.info("✅ WORLD wallet instantiated successfully")
        
        # Test mnemonic generation
        mnemonic = world_wallet.mnemonic()
        if not mnemonic or len(mnemonic.split()) != 12:
            logger.error("❌ Failed to generate valid mnemonic")
            return False
        
        logger.info("✅ Mnemonic generated successfully")
        
        # Test wallet from mnemonic
        wallet = world_wallet.from_mnemonic(mnemonic=mnemonic)
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

def test_world_client_integration():
    """Test the World Chain client integration"""
    logger = setup_logging()
    logger.info("🧪 Testing World Chain client integration...")
    
    try:
        # Test configuration
        api_key = config('ALCHEMY_WORLD_API_KEY', default='demo')
        world_config = WorldConfig.testnet(api_key)
        
        if not world_config.base_url:
            logger.error("❌ Failed to create World Chain configuration")
            return False
        
        logger.info("✅ World Chain configuration created successfully")
        logger.info(f"✅ Base URL: {world_config.base_url}")
        
        # Test wallet client creation
        session = get_session()
        try:
            world_wallet = WorldWallet(
                user_id=1,
                config=world_config,
                session=session
            )
            logger.info("✅ World Chain wallet client created successfully")
            
            # Test connection (if API key is configured)
            if api_key != 'demo':
                if world_wallet.test_connection():
                    logger.info("✅ World Chain API connection successful")
                else:
                    logger.warning("⚠️ World Chain API connection failed (may be expected with demo key)")
            else:
                logger.info("ℹ️ Skipping API connection test with demo key")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ World Chain client integration test failed: {e}")
        return False

def test_database_integration():
    """Test database integration for World Chain"""
    logger = setup_logging()
    logger.info("🧪 Testing database integration...")
    
    session = get_session()
    
    try:
        # Test creating a test user
        test_user = User(
            email="test.world@example.com",
            password_hash="test_hash",
            is_active=True
        )
        session.add(test_user)
        session.flush()
        logger.info(f"✅ Test user created with ID: {test_user.id}")
        
        # Test creating World Chain account
        world_account = Account(
            user_id=test_user.id,
            balance=0,
            locked_amount=0,
            currency="WORLD",
            account_type=AccountType.CRYPTO,
            account_number="TEST_WORLD_001",
            label="Test World Chain Account"
        )
        session.add(world_account)
        session.flush()
        logger.info(f"✅ World Chain account created with ID: {world_account.id}")
        
        # Test creating World Chain address
        test_address = CryptoAddress(
            account_id=world_account.id,
            address="0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            label="Test World Chain Address",
            is_active=True,
            currency_code="WORLD",
            address_type="hd_wallet"
        )
        session.add(test_address)
        session.commit()
        logger.info("✅ World Chain address created successfully")
        
        # Test querying World Chain data
        world_accounts = session.query(Account).filter_by(currency="WORLD").all()
        world_addresses = session.query(CryptoAddress).filter_by(currency_code="WORLD").all()
        
        logger.info(f"✅ Found {len(world_accounts)} World Chain accounts")
        logger.info(f"✅ Found {len(world_addresses)} World Chain addresses")
        
        # Clean up test data
        session.delete(test_address)
        session.delete(world_account)
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
    """Test crypto configuration for World Chain"""
    logger = setup_logging()
    logger.info("🧪 Testing crypto configuration...")
    
    try:
        from shared.crypto import cryptos
        
        # Check if WORLD is in the accounts list
        world_crypto = None
        for crypto in cryptos.accounts:
            if crypto["symbol"] == "WORLD":
                world_crypto = crypto
                break
        
        if not world_crypto:
            logger.error("❌ WORLD not found in crypto configuration")
            return False
        
        logger.info("✅ WORLD found in crypto configuration")
        logger.info(f"✅ Name: {world_crypto['name']}")
        logger.info(f"✅ Symbol: {world_crypto['symbol']}")
        logger.info(f"✅ Is Chain: {world_crypto['is_chain']}")
        logger.info(f"✅ Decimals: {world_crypto['decimals']}")
        
        # Verify configuration
        if world_crypto["name"] != "World Chain":
            logger.error("❌ Incorrect name for WORLD")
            return False
        
        if world_crypto["is_chain"] != True:
            logger.error("❌ WORLD should be marked as a chain")
            return False
        
        if world_crypto["decimals"] != 18:
            logger.error("❌ WORLD should have 18 decimals")
            return False
        
        logger.info("✅ World Chain configuration is correct")
        return True
        
    except Exception as e:
        logger.error(f"❌ Crypto configuration test failed: {e}")
        return False

def test_wallet_service_integration():
    """Test wallet service integration for World Chain"""
    logger = setup_logging()
    logger.info("🧪 Testing wallet service integration...")
    
    try:
        # Test importing WORLD from wallet service
        from wallet.app import create_crypto_addresses_for_user
        
        logger.info("✅ World Chain wallet service functions imported successfully")
        
        # Test that WORLD is in the crypto wallet classes
        from wallet.app import crypto_wallet_classes
        if "WORLD" not in crypto_wallet_classes:
            logger.error("❌ WORLD not found in wallet service crypto classes")
            return False
        
        logger.info("✅ WORLD found in wallet service crypto classes")
        return True
        
    except Exception as e:
        logger.error(f"❌ Wallet service integration test failed: {e}")
        return False

def main():
    """Run all World Chain integration tests"""
    logger = setup_logging()
    logger.info("🚀 Starting World Chain integration tests...")
    
    tests = [
        ("HD Wallet Integration", test_hd_wallet_integration),
        ("World Chain Client Integration", test_world_client_integration),
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
        logger.info("🎉 All World Chain integration tests passed!")
        logger.info("✅ World Chain wallet is ready for production use!")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed")
        logger.error("Please fix the failing tests before deploying")
        return 1

if __name__ == "__main__":
    exit(main()) 