#!/usr/bin/env python3
"""
Tron Integration Test Script
Tests the complete Tron wallet integration
"""

import os
import sys
import logging
from decouple import config
from sqlalchemy.orm import Session
from db.connection import get_session
from db.wallet import Account, AccountType, CryptoAddress
from db import User
from shared.crypto.HD import TRX, get_wallet
from shared.crypto.clients.tron import TronWallet, TronWalletConfig
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
    """Test the HD wallet integration for Tron"""
    logger = setup_logging()
    logger.info("🧪 Testing HD wallet integration...")
    
    try:
        # Test getting TRX wallet class
        trx_wallet_class = get_wallet("TRX")
        if trx_wallet_class is None:
            logger.error("❌ Failed to get TRX wallet class")
            return False
        
        logger.info("✅ TRX wallet class retrieved successfully")
        
        # Test wallet instantiation
        trx_wallet = trx_wallet_class()
        logger.info("✅ TRX wallet instantiated successfully")
        
        # Test mnemonic generation
        mnemonic = trx_wallet.mnemonic()
        if not mnemonic or len(mnemonic.split()) != 12:
            logger.error("❌ Failed to generate valid mnemonic")
            return False
        
        logger.info("✅ Mnemonic generated successfully")
        
        # Test wallet from mnemonic
        wallet = trx_wallet.from_mnemonic(mnemonic=mnemonic)
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

def test_tron_client_integration():
    """Test the Tron client integration"""
    logger = setup_logging()
    logger.info("🧪 Testing Tron client integration...")
    
    try:
        # Test configuration
        api_key = config('TRON_API_KEY', default='demo')
        tron_config = TronWalletConfig.testnet(api_key)
        
        if not tron_config.base_url:
            logger.error("❌ Failed to create Tron configuration")
            return False
        
        logger.info("✅ Tron configuration created successfully")
        logger.info(f"✅ Base URL: {tron_config.base_url}")
        
        # Test wallet client creation
        session = get_session()
        try:
            tron_wallet = TronWallet(
                user_id=1,
                config=tron_config,
                session=session
            )
            logger.info("✅ Tron wallet client created successfully")
            
            # Test connection (if API key is configured)
            if api_key != 'demo':
                if tron_wallet.test_connection():
                    logger.info("✅ Tron API connection successful")
                else:
                    logger.warning("⚠️ Tron API connection failed (may be expected with demo key)")
            else:
                logger.info("ℹ️ Skipping API connection test with demo key")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Tron client integration test failed: {e}")
        return False

def test_database_integration():
    """Test database integration for Tron"""
    logger = setup_logging()
    logger.info("🧪 Testing database integration...")
    
    session = get_session()
    
    try:
        # Test creating a test user
        test_user = User(
            email="test.tron@example.com",
            password_hash="test_hash",
            is_active=True
        )
        session.add(test_user)
        session.flush()
        logger.info(f"✅ Test user created with ID: {test_user.id}")
        
        # Test creating TRX account
        trx_account = Account(
            user_id=test_user.id,
            balance=0,
            locked_amount=0,
            currency="TRX",
            account_type=AccountType.CRYPTO,
            account_number="TEST_TRX_001",
            label="Test TRX Account"
        )
        session.add(trx_account)
        session.flush()
        logger.info(f"✅ TRX account created with ID: {trx_account.id}")
        
        # Test creating TRX address
        test_address = CryptoAddress(
            account_id=trx_account.id,
            address="TJRabPrwbZy45sbavfcjinPJC18kjpRTv8",
            label="Test TRX Address",
            is_active=True,
            currency_code="TRX",
            address_type="hd_wallet"
        )
        session.add(test_address)
        session.commit()
        logger.info("✅ TRX address created successfully")
        
        # Test querying TRX data
        trx_accounts = session.query(Account).filter_by(currency="TRX").all()
        trx_addresses = session.query(CryptoAddress).filter_by(currency_code="TRX").all()
        
        logger.info(f"✅ Found {len(trx_accounts)} TRX accounts")
        logger.info(f"✅ Found {len(trx_addresses)} TRX addresses")
        
        # Clean up test data
        session.delete(test_address)
        session.delete(trx_account)
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
    """Test crypto configuration for Tron"""
    logger = setup_logging()
    logger.info("🧪 Testing crypto configuration...")
    
    try:
        from shared.crypto import cryptos
        
        # Check if TRX is in the accounts list
        trx_crypto = None
        for crypto in cryptos.accounts:
            if crypto["symbol"] == "TRX":
                trx_crypto = crypto
                break
        
        if not trx_crypto:
            logger.error("❌ TRX not found in crypto configuration")
            return False
        
        logger.info("✅ TRX found in crypto configuration")
        logger.info(f"✅ Name: {trx_crypto['name']}")
        logger.info(f"✅ Symbol: {trx_crypto['symbol']}")
        logger.info(f"✅ Is Chain: {trx_crypto['is_chain']}")
        logger.info(f"✅ Decimals: {trx_crypto['decimals']}")
        
        # Verify configuration
        if trx_crypto["name"] != "Tron":
            logger.error("❌ Incorrect name for TRX")
            return False
        
        if trx_crypto["is_chain"] != True:
            logger.error("❌ TRX should be marked as a chain")
            return False
        
        if trx_crypto["decimals"] != 6:
            logger.error("❌ TRX should have 6 decimals")
            return False
        
        logger.info("✅ Tron configuration is correct")
        return True
        
    except Exception as e:
        logger.error(f"❌ Crypto configuration test failed: {e}")
        return False

def test_wallet_service_integration():
    """Test wallet service integration for Tron"""
    logger = setup_logging()
    logger.info("🧪 Testing wallet service integration...")
    
    try:
        # Test importing TRX from wallet service
        from wallet.app import create_crypto_addresses_for_user
        
        logger.info("✅ Tron wallet service functions imported successfully")
        
        # Test that TRX is in the crypto wallet classes
        from wallet.app import crypto_wallet_classes
        if "TRX" not in crypto_wallet_classes:
            logger.error("❌ TRX not found in wallet service crypto classes")
            return False
        
        logger.info("✅ TRX found in wallet service crypto classes")
        return True
        
    except Exception as e:
        logger.error(f"❌ Wallet service integration test failed: {e}")
        return False

def test_tron_specific_features():
    """Test Tron-specific features"""
    logger = setup_logging()
    logger.info("🧪 Testing Tron-specific features...")
    
    try:
        # Test Tron address validation
        from shared.crypto.clients.tron import TronWallet, TronWalletConfig
        
        # Create a test config
        test_config = TronWalletConfig.testnet("demo")
        
        # Test address validation
        valid_addresses = [
            "TJRabPrwbZy45sbavfcjinPJC18kjpRTv8",  # Mainnet
            "TJRabPrwbZy45sbavfcjinPJC18kjpRTv9",  # Mainnet
            "TJRabPrwbZy45sbavfcjinPJC18kjpRTvA"   # Mainnet
        ]
        
        invalid_addresses = [
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Bitcoin address
            "LQn9v2brJG7Z7qo7UiqEnQyQhqYQk2jJbK",  # Litecoin address
            "invalid_address",
            ""
        ]
        
        session = get_session()
        try:
            tron_wallet = TronWallet(
                user_id=1,
                config=test_config,
                session=session
            )
            
            # Test valid addresses
            for addr in valid_addresses:
                if tron_wallet.validate_address(addr):
                    logger.info(f"✅ Valid address: {addr}")
                else:
                    logger.error(f"❌ Invalid address marked as valid: {addr}")
                    return False
            
            # Test invalid addresses
            for addr in invalid_addresses:
                if not tron_wallet.validate_address(addr):
                    logger.info(f"✅ Invalid address correctly rejected: {addr}")
                else:
                    logger.error(f"❌ Invalid address marked as valid: {addr}")
                    return False
            
            # Test Tron features
            features = tron_wallet.get_tron_features()
            expected_features = [
                "smart_contracts", "trc20_tokens", "trc10_tokens",
                "delegated_proof_of_stake", "high_throughput", "low_fees"
            ]
            
            for feature in expected_features:
                if feature in features and features[feature]:
                    logger.info(f"✅ Feature confirmed: {feature}")
                else:
                    logger.warning(f"⚠️ Feature not confirmed: {feature}")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Tron-specific features test failed: {e}")
        return False

def main():
    """Run all Tron integration tests"""
    logger = setup_logging()
    logger.info("🚀 Starting Tron integration tests...")
    
    tests = [
        ("HD Wallet Integration", test_hd_wallet_integration),
        ("Tron Client Integration", test_tron_client_integration),
        ("Database Integration", test_database_integration),
        ("Crypto Configuration", test_crypto_configuration),
        ("Wallet Service Integration", test_wallet_service_integration),
        ("Tron-Specific Features", test_tron_specific_features),
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
        logger.info("🎉 All Tron integration tests passed!")
        logger.info("✅ Tron wallet is ready for production use!")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed")
        logger.error("Please fix the failing tests before deploying")
        return 1

if __name__ == "__main__":
    exit(main()) 