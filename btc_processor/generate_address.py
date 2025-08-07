#!/usr/bin/env python3
"""
Generate a new Bitcoin testnet address for testing.
This script is part of the btc_processor service.
"""

import sys
import os
import random
from decouple import config

# Add the current directory to Python path
sys.path.append('/app')

from shared.crypto.HD import BTC
from shared.logger import setup_logging
from db.connection import session
from db.wallet import CryptoAddress, Account, AccountType
from db.models import Currency

logger = setup_logging()

def generate_new_btc_address():
    """Generate a new Bitcoin testnet address"""
    
    try:
        # Get the mnemonic from environment
        mnemonic = config('BTC_MNEMONIC', default=None)
        if not mnemonic:
            logger.error("No BTC_MNEMONIC configured in environment")
            return None
        
        logger.info("Creating BTC wallet from mnemonic...")
        
        # Create BTC wallet
        wallet = BTC()
        wallet = wallet.from_mnemonic(mnemonic=mnemonic)
        
        # Generate a new address with a random index
        index = random.randint(1000, 9999)  # Random index for testing
        
        logger.info(f"Generating new BTC address with index: {index}")
        
        address_gen, priv_key, pub_key = wallet.new_address(index=index)
        
        logger.info(f"✅ Generated new BTC testnet address: {address_gen}")
        logger.info(f"Private key: {priv_key}")
        logger.info(f"Public key: {pub_key}")
        
        return {
            'address': address_gen,
            'private_key': priv_key,
            'public_key': pub_key,
            'index': index
        }
        
    except Exception as e:
        logger.error(f"Error generating BTC address: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def save_address_to_database(address_data):
    """Save the generated address to the database"""
    try:
        if not session:
            logger.error("No database session available")
            return False
        
        # Get BTC currency
        btc_currency = session.query(Currency).filter_by(code='BTC').first()
        if not btc_currency:
            logger.error("BTC currency not found in database")
            return False
        
        # Get or create a default account for BTC
        account = session.query(Account).filter_by(currency='BTC').first()
        if not account:
            logger.info("Creating new BTC account...")
            account = Account(
                balance=0,
                currency='BTC',
                account_type=AccountType.CRYPTO,
                user_id=1,  # Default user ID
                account_number='BTC001',
                label='BTC Testnet Account'
            )
            session.add(account)
            session.flush()  # Get the ID
        
        # Check if address already exists
        existing_address = session.query(CryptoAddress).filter_by(address=address_data['address']).first()
        if existing_address:
            logger.warning(f"Address {address_data['address']} already exists in database")
            return True
        
        # Create new crypto address
        crypto_address = CryptoAddress(
            account_id=account.id,
            address=address_data['address'],
            currency_code='BTC',
            is_active=True,
            label=f"BTC Address {address_data['index']}"
        )
        
        session.add(crypto_address)
        session.commit()
        
        logger.info(f"✅ Successfully saved address {address_data['address']} to database")
        return True
        
    except Exception as e:
        logger.error(f"Error saving address to database: {e}")
        if session:
            session.rollback()
        return False

def generate_and_save_address():
    """Generate a new address and save it to the database"""
    
    logger.info("🚀 Starting BTC address generation...")
    
    # Generate new address
    address_data = generate_new_btc_address()
    
    if not address_data:
        logger.error("Failed to generate BTC address")
        return None
    
    # Save to database
    if save_address_to_database(address_data):
        logger.info("✅ Address generated and saved successfully!")
        
        print("\n" + "="*60)
        print("🎉 NEW BITCOIN TESTNET ADDRESS GENERATED!")
        print("="*60)
        print(f"Address: {address_data['address']}")
        print(f"Index: {address_data['index']}")
        print(f"Private Key: {address_data['private_key']}")
        print(f"Public Key: {address_data['public_key']}")
        print("="*60)
        print("✅ Address has been saved to the database")
        print("✅ The btc_processor service will now monitor this address")
        print("="*60)
        
        return address_data
    else:
        logger.error("Failed to save address to database")
        return None

if __name__ == "__main__":
    result = generate_and_save_address()
    
    if result:
        logger.info("Address generation completed successfully!")
    else:
        logger.error("Address generation failed!") 