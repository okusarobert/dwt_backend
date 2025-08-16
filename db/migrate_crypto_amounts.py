#!/usr/bin/env python3
"""
Data Migration Script for Crypto Amounts

This script converts existing crypto amounts from standard units to smallest units
(wei, satoshis, etc.) to support the new precision system.
"""

import os
import sys
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db.crypto_precision import CryptoPrecisionManager
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment"""
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'dwt_backend')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASS', 'password')

    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

def migrate_crypto_accounts():
    """Migrate existing crypto accounts to use smallest units"""
    
    # Create database connection
    db_url = get_database_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        logger.info("🚀 Starting crypto amount migration...")
        
        # Get all crypto accounts
        result = session.execute(text("""
            SELECT id, currency, balance, locked_amount, account_type
            FROM accounts 
            WHERE account_type = 'CRYPTO'
            AND (crypto_balance_smallest_unit IS NULL OR crypto_locked_amount_smallest_unit IS NULL)
        """))
        
        accounts = result.fetchall()
        logger.info(f"📊 Found {len(accounts)} crypto accounts to migrate")
        
        migrated_count = 0
        error_count = 0
        
        for account in accounts:
            try:
                account_id = account.id
                currency = account.currency
                balance = account.balance
                locked_amount = account.locked_amount
                
                logger.info(f"🔄 Migrating account {account_id} ({currency})")
                
                # Convert balance to smallest units
                if balance and balance > 0:
                    balance_smallest_unit = CryptoPrecisionManager.to_smallest_unit(balance, currency)
                    logger.info(f"   Balance: {balance} {currency} → {balance_smallest_unit:,} {CryptoPrecisionManager.get_smallest_unit_name(currency)}")
                else:
                    balance_smallest_unit = 0
                
                # Convert locked amount to smallest units
                if locked_amount and locked_amount > 0:
                    locked_amount_smallest_unit = CryptoPrecisionManager.to_smallest_unit(locked_amount, currency)
                    logger.info(f"   Locked: {locked_amount} {currency} → {locked_amount_smallest_unit:,} {CryptoPrecisionManager.get_smallest_unit_name(currency)}")
                else:
                    locked_amount_smallest_unit = 0
                
                # Update the account
                session.execute(text("""
                    UPDATE accounts 
                    SET crypto_balance_smallest_unit = :balance_smallest,
                        crypto_locked_amount_smallest_unit = :locked_smallest
                    WHERE id = :account_id
                """), {
                    'balance_smallest': balance_smallest_unit,
                    'locked_smallest': locked_amount_smallest_unit,
                    'account_id': account_id
                })
                
                migrated_count += 1
                logger.info(f"   ✅ Account {account_id} migrated successfully")
                
            except Exception as e:
                error_count += 1
                logger.error(f"   ❌ Error migrating account {account.id}: {e}")
                continue
        
        # Commit all changes
        session.commit()
        
        logger.info(f"✅ Migration completed!")
        logger.info(f"   Successfully migrated: {migrated_count} accounts")
        logger.info(f"   Errors: {error_count} accounts")
        
        return migrated_count, error_count
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def verify_migration():
    """Verify that the migration was successful"""
    
    db_url = get_database_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        logger.info("🔍 Verifying migration...")
        
        # Check for accounts that still need migration
        result = session.execute(text("""
            SELECT COUNT(*) as count
            FROM accounts 
            WHERE account_type = 'CRYPTO'
            AND (crypto_balance_smallest_unit IS NULL OR crypto_locked_amount_smallest_unit IS NULL)
        """))
        
        unmigrated_count = result.fetchone().count
        
        if unmigrated_count == 0:
            logger.info("✅ All crypto accounts have been migrated!")
        else:
            logger.warning(f"⚠️ {unmigrated_count} accounts still need migration")
        
        # Show sample of migrated accounts
        result = session.execute(text("""
            SELECT id, currency, balance, locked_amount, 
                   crypto_balance_smallest_unit, crypto_locked_amount_smallest_unit
            FROM accounts 
            WHERE account_type = 'CRYPTO'
            AND crypto_balance_smallest_unit IS NOT NULL
            LIMIT 5
        """))
        
        sample_accounts = result.fetchall()
        
        logger.info("📋 Sample of migrated accounts:")
        for account in sample_accounts:
            currency = account.currency
            smallest_unit_name = CryptoPrecisionManager.get_smallest_unit_name(currency)
            
            logger.info(f"   Account {account.id} ({currency}):")
            logger.info(f"     Balance: {account.balance} {currency} → {account.crypto_balance_smallest_unit:,} {smallest_unit_name}")
            logger.info(f"     Locked: {account.locked_amount} {currency} → {account.crypto_locked_amount_smallest_unit:,} {smallest_unit_name}")
        
        return unmigrated_count == 0
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False
    finally:
        session.close()

def rollback_migration():
    """Rollback the migration by setting smallest unit amounts to NULL"""
    
    db_url = get_database_url()
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        logger.info("🔄 Rolling back migration...")
        
        # Reset all crypto accounts
        result = session.execute(text("""
            UPDATE accounts 
            SET crypto_balance_smallest_unit = NULL,
                crypto_locked_amount_smallest_unit = NULL
            WHERE account_type = 'CRYPTO'
        """))
        
        session.commit()
        
        logger.info("✅ Rollback completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def main():
    """Main migration function"""
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "migrate"
    
    if command == "migrate":
        logger.info("🚀 Starting crypto amount migration...")
        migrated_count, error_count = migrate_crypto_accounts()
        
        if error_count == 0:
            logger.info("✅ Migration completed successfully!")
        else:
            logger.warning(f"⚠️ Migration completed with {error_count} errors")
    
    elif command == "verify":
        logger.info("🔍 Verifying migration...")
        success = verify_migration()
        
        if success:
            logger.info("✅ Verification passed!")
        else:
            logger.error("❌ Verification failed!")
            sys.exit(1)
    
    elif command == "rollback":
        logger.info("🔄 Rolling back migration...")
        rollback_migration()
        logger.info("✅ Rollback completed!")
    
    else:
        logger.error(f"❌ Unknown command: {command}")
        logger.info("Available commands: migrate, verify, rollback")
        sys.exit(1)

if __name__ == "__main__":
    main() 