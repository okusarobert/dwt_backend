#!/usr/bin/env python3
"""
Test WebSocket connection to BTC daemon.
"""

import sys
import os
import asyncio

# Add the current directory to Python path
sys.path.append('/app')

from bitcart import APIManager, COINS
from shared.crypto.util import coin_info
from shared.logger import setup_logging

logger = setup_logging()

async def test_websocket_connection():
    """Test WebSocket connection to BTC daemon"""
    
    try:
        logger.info("🔍 Testing WebSocket connection...")
        
        # Create APIManager
        logger.info("Creating APIManager...")
        manager = APIManager({"BTC": []})
        
        # Get BTC credentials
        logger.info("Getting BTC credentials...")
        btc_credentials = coin_info("BTC")
        logger.info(f"BTC credentials: {btc_credentials}")
        
        # Create BTC coin instance
        logger.info("Creating BTC coin instance...")
        from bitcart import BTC
        btc_coin = BTC(**btc_credentials["credentials"])
        logger.info(f"BTC coin instance: {btc_coin}")
        
        # Add to manager
        logger.info("Adding BTC coin to manager...")
        manager.wallets["BTC"][""] = btc_coin
        logger.info(f"Manager wallets: {manager.wallets}")
        
        # Test basic connection
        logger.info("Testing basic connection...")
        try:
            info = await btc_coin.server.getinfo()
            logger.info(f"✅ Basic connection successful: {info}")
        except Exception as e:
            logger.error(f"❌ Basic connection failed: {e}")
            return
        
        # Test WebSocket connection
        logger.info("Testing WebSocket connection...")
        try:
            logger.info("Starting WebSocket connection...")
            await manager.start_websocket(force_connect=True)
            logger.info("✅ WebSocket connection started successfully!")
            
            # Wait a bit to see if we get any events
            logger.info("Waiting for events...")
            await asyncio.sleep(10)
            logger.info("WebSocket test completed!")
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

async def test_simple_connection():
    """Test simple connection to BTC daemon"""
    
    try:
        logger.info("🔍 Testing simple connection...")
        
        # Get BTC credentials
        btc_credentials = coin_info("BTC")
        
        # Create BTC coin instance
        from bitcart import BTC
        btc_coin = BTC(**btc_credentials["credentials"])
        
        # Test connection
        logger.info("Testing connection to BTC daemon...")
        info = await btc_coin.server.getinfo()
        logger.info(f"✅ Connection successful: {info}")
        
        # Test if we can get updates
        logger.info("Testing get_updates...")
        try:
            updates = await btc_coin.server.get_updates()
            logger.info(f"✅ Updates: {updates}")
        except Exception as e:
            logger.error(f"❌ Get updates failed: {e}")
        
    except Exception as e:
        logger.error(f"❌ Simple connection test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("🚀 Starting WebSocket connection tests...")
    
    # Test simple connection first
    asyncio.run(test_simple_connection())
    
    # Test WebSocket connection
    asyncio.run(test_websocket_connection())
    
    logger.info("✅ All tests completed!") 