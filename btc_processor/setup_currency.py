#!/usr/bin/env python3
"""
Setup BTC currency in the database.
"""

import sys
from decouple import config

# Add the current directory to Python path
sys.path.append('/app')

from db.models import Currency, CurrencyType
from db.connection import session
from shared.logger import setup_logging

logger = setup_logging()

def setup_btc_currency():
    """Setup BTC currency in the database"""
    
    try:
        if not session:
            logger.error("No database session available")
            return False
        
        # Check if BTC currency already exists
        btc_currency = session.query(Currency).filter_by(code='BTC').first()
        if btc_currency:
            logger.info(f"BTC currency already exists: {btc_currency.name}")
            return True
        
        # Create BTC currency
        btc_currency = Currency(
            code='BTC',
            name='Bitcoin',
            type=CurrencyType.CRYPTO,
            symbol='₿',
            decimals=8,
            is_active=True
        )
        
        session.add(btc_currency)
        session.commit()
        
        logger.info("✅ Successfully created BTC currency in database")
        return True
        
    except Exception as e:
        logger.error(f"Error setting up BTC currency: {e}")
        if session:
            session.rollback()
        return False

if __name__ == "__main__":
    logger.info("🚀 Setting up BTC currency...")
    
    if setup_btc_currency():
        logger.info("✅ BTC currency setup completed successfully!")
    else:
        logger.error("❌ BTC currency setup failed!") 