#!/usr/bin/env python3
"""
World Chain Address Generation Script
Generates World Chain addresses for users using HD wallet derivation
"""

import os
import sys
import logging
from decouple import config
from sqlalchemy.orm import Session
from db.connection import get_session
from db.wallet import Account, AccountType, CryptoAddress
from db import User
from shared.crypto.HD import WORLD
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

def create_world_addresses_for_user(user_id: int, session: Session, logger: logging.Logger):
    """Create World Chain addresses for a specific user"""
    try:
        # Check if user exists
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            logger.error(f"User {user_id} not found")
            return False
        
        # Check if World Chain account exists
        world_account = session.query(Account).filter_by(
            user_id=user_id,
            currency="WORLD",
            account_type=AccountType.CRYPTO
        ).first()
        
        if not world_account:
            logger.error(f"No World Chain account found for user {user_id}")
            return False
        
        # Check if address already exists
        existing_address = session.query(CryptoAddress).filter_by(
            account_id=world_account.id,
            currency_code="WORLD"
        ).first()
        
        if existing_address:
            logger.info(f"World Chain address already exists for user {user_id}: {existing_address.address}")
            return True
        
        # Get mnemonic from config
        mnemonic = config('WORLD_MNEMONIC', default=None)
        
        if not mnemonic:
            logger.error("No WORLD_MNEMONIC configured")
            return False
        
        # Initialize World Chain wallet
        world_wallet = WORLD()
        wallet = world_wallet.from_mnemonic(mnemonic=mnemonic)
        
        # Generate new address using account ID as index
        index = world_account.id - 1
        address, priv_key, pub_key = wallet.new_address(index=index)
        
        # Create crypto address record
        crypto_address = CryptoAddress(
            account_id=world_account.id,
            address=address,
            label="World Chain Address",
            is_active=True,
            currency_code="WORLD",
            address_type="hd_wallet",
            private_key=priv_key,
            public_key=pub_key
        )
        
        session.add(crypto_address)
        session.commit()
        
        logger.info(f"Created World Chain address for user {user_id}: {address}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating World Chain address for user {user_id}: {e}")
        session.rollback()
        return False

def create_world_addresses_for_all_users(session: Session, logger: logging.Logger):
    """Create World Chain addresses for all users who don't have them"""
    try:
        # Get all users with World Chain accounts but no addresses
        users_without_addresses = session.query(User).join(Account).outerjoin(CryptoAddress).filter(
            Account.currency == "WORLD",
            Account.account_type == AccountType.CRYPTO,
            CryptoAddress.id.is_(None)
        ).distinct().all()
        
        logger.info(f"Found {len(users_without_addresses)} users without World Chain addresses")
        
        success_count = 0
        for user in users_without_addresses:
            if create_world_addresses_for_user(user.id, session, logger):
                success_count += 1
        
        logger.info(f"Successfully created World Chain addresses for {success_count} users")
        return success_count
        
    except Exception as e:
        logger.error(f"Error creating World Chain addresses: {e}")
        return 0

def main():
    """Main function to run the World Chain address generation"""
    logger = setup_logging()
    logger.info("Starting World Chain address generation...")
    
    session = get_session()
    
    try:
        # Check if WORLD_MNEMONIC is configured
        mnemonic = config('WORLD_MNEMONIC', default=None)
        if not mnemonic:
            logger.error("WORLD_MNEMONIC environment variable is not configured")
            logger.error("Please set WORLD_MNEMONIC with your World Chain mnemonic phrase")
            return 1
        
        # Check command line arguments
        if len(sys.argv) > 1:
            try:
                user_id = int(sys.argv[1])
                logger.info(f"Creating World Chain address for specific user {user_id}")
                success = create_world_addresses_for_user(user_id, session, logger)
                if success:
                    logger.info("World Chain address creation completed successfully")
                    return 0
                else:
                    logger.error("World Chain address creation failed")
                    return 1
            except ValueError:
                logger.error("Invalid user ID provided. Please provide a valid integer.")
                return 1
        else:
            # Create addresses for all users
            logger.info("Creating World Chain addresses for all users...")
            success_count = create_world_addresses_for_all_users(session, logger)
            if success_count > 0:
                logger.info(f"Successfully created {success_count} World Chain addresses")
                return 0
            else:
                logger.warning("No World Chain addresses were created")
                return 0
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    exit(main()) 