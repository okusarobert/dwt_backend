#!/usr/bin/env python3
"""
Check the current Bitcoin testnet block height.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

from shared.crypto.util import get_coin
from shared.logger import setup_logging

logger = setup_logging()

async def check_block_height():
    """Check the current Bitcoin testnet block height"""
    
    try:
        # Get the BTC coin instance
        btc_coin = get_coin("BTC")
        
        logger.info("Checking current Bitcoin testnet block height...")
        
        # Get the current block height
        # This might not work with the current setup, but let's try
        try:
            # Try to get info from the daemon
            info = await btc_coin.server.getinfo()
            logger.info(f"Daemon info: {info}")
        except Exception as e:
            logger.error(f"Error getting daemon info: {e}")
        
        # Try to get the latest block
        try:
            # Get the latest block hash
            latest_block = await btc_coin.server.getblockcount()
            logger.info(f"Current block height: {latest_block}")
            
            # Get the latest block hash
            latest_block_hash = await btc_coin.server.getblockhash(latest_block)
            logger.info(f"Latest block hash: {latest_block_hash}")
            
        except Exception as e:
            logger.error(f"Error getting block height: {e}")
        
    except Exception as e:
        logger.error(f"Error checking block height: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    import asyncio
    logger.info("🚀 Checking Bitcoin testnet block height...")
    asyncio.run(check_block_height())
    logger.info("✅ Block height check completed!") 