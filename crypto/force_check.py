#!/usr/bin/env python3
"""
Force the polling system to check for new transactions.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

from util import check_pending
from shared.logger import setup_logging

logger = setup_logging()

async def force_transaction_check():
    """Force the polling system to check for new transactions"""
    
    logger.info("[FORCE] Forcing transaction check for BTC...")
    
    try:
        # Force check pending transactions for BTC
        await check_pending("BTC")
        logger.info("[FORCE] Transaction check completed!")
        
    except Exception as e:
        logger.error(f"[FORCE] Error during transaction check: {e}")
        import traceback
        logger.error(f"[FORCE] Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("[FORCE] Starting forced transaction check...")
    asyncio.run(force_transaction_check())
    logger.info("[FORCE] Forced transaction check completed!") 