#!/usr/bin/env python3
"""
Tron Address Generation Script
Generates Tron addresses for users using HD wallet derivation
"""

import os
import sys
import logging
from decouple import config
from sqlalchemy.orm import Session
from db.connection import get_session
from db.wallet import Account, AccountType, CryptoAddress
from db import User
from shared.crypto.HD import TRX
from shared.logger import setup_logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_logging():
    """Setup logging for the script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def create_tron_addresses_for_user(user_id: int, session: Session, logger: logging.Logger):
    """Create Tron addresses for a specific user"""
    try:
        # Check if user exists
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Check if TRX account exists
        trx_account = session.query(Account).filter_by(
            user_id=user_id,
            currency="TRX",
            account_type=AccountType.CRYPTO
        ).first()
        
        if not trx_account:
            logger.error(f"No TRX account found for user {user_id}")
            return False
        
        # Check if address already exists
        existing_address = session.query(CryptoAddress).filter_by(
            account_id=trx_account.id,
            currency_code="TRX"
        ).first()
        
        if existing_address:
            logger.info(f"Tron address already exists for user {user_id}: {existing_address.address}")
            return True
        
        # Get mnemonic from config
        mnemonic = config('TRX_MNEMONIC', default=None)
        
        if not mnemonic:
            logger.error("No TRX_MNEMONIC configured")
            return False
        
        # Initialize TRX wallet
        trx_wallet = TRX()
        wallet = trx_wallet.from_mnemonic(mnemonic=mnemonic)
        
        # Generate new address using account ID as index
        index = trx_account.id - 1
        address, priv_key, pub_key = wallet.new_address(index=index)
        
        # Create crypto address record
        crypto_address = CryptoAddress(
            account_id=trx_account.id,
            address=address,
            label="Tron Address",
            is_active=True,
            currency_code="TRX",
            address_type="hd_wallet",
            private_key=priv_key,
            public_key=pub_key
        )
        
        session.add(crypto_address)
        session.commit()
        
        logger.info(f"Created Tron address for user {user_id}: {address}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating Tron address for user {user_id}: {e}")
        session.rollback()
        return False

def create_tron_addresses_for_all_users(session: Session, logger: logging.Logger):
    """Create Tron addresses for all users who don't have them"""
    try:
        # Get all users with TRX accounts but no addresses
        users_without_addresses = session.query(User).join(Account).outerjoin(CryptoAddress).filter(
            Account.currency == "TRX",
            Account.account_type == AccountType.CRYPTO,
            CryptoAddress.id.is_(None)
        ).distinct().all()
        
        logger.info(f"Found {len(users_without_addresses)} users without Tron addresses")
        
        success_count = 0
        for user in users_without_addresses:
            if create_tron_addresses_for_user(user.id, session, logger):
                success_count += 1
        
        logger.info(f"Successfully created Tron addresses for {success_count} users")
        return success_count
        
    except Exception as e:
        logger.error(f"Error creating Tron addresses: {e}")
        return 0

def main():
    """Main function to run the Tron address generation"""
    logger = setup_logging()
    logger.info("Starting Tron address generation...")
    
    session = get_session()
    
    try:
        # Check if TRX_MNEMONIC is configured
        mnemonic = config('TRX_MNEMONIC', default=None)
        if not mnemonic:
            logger.error("TRX_MNEMONIC environment variable is not configured")
            logger.error("Please set TRX_MNEMONIC with your Tron mnemonic phrase")
            return 1
        
        # Check command line arguments
        if len(sys.argv) > 1:
            try:
                user_id = int(sys.argv[1])
                logger.info(f"Creating Tron address for specific user {user_id}")
                success = create_tron_addresses_for_user(user_id, session, logger)
                if success:
                    logger.info("Tron address creation completed successfully")
                    return 0
                else:
                    logger.error("Tron address creation failed")
                    return 1
            except ValueError:
                logger.error("Invalid user ID provided. Please provide a valid integer.")
                return 1
        else:
            # Create addresses for all users
            logger.info("Creating Tron addresses for all users...")
            success_count = create_tron_addresses_for_all_users(session, logger)
            if success_count > 0:
                logger.info(f"Successfully created {success_count} Tron addresses")
                return 0
            else:
                logger.warning("No Tron addresses were created")
                return 0
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    exit(main()) 