#!/usr/bin/env python3
"""
Test script for the real crypto price service
Tests live API calls to CoinGecko
"""

import asyncio
import sys
import logging
from crypto_price_service import CryptoPriceService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockSocketIO:
    """Mock SocketIO for testing"""
    def emit(self, event, data, namespace='/'):
        logger.info("Mock emit: {} -> {} items".format(event, len(data)))
        for item in data[:3]:  # Show first 3 items
            logger.info("  {}: ${:.2f} ({:+.2f}%)".format(
                item['symbol'], item['price'], item['changePercent24h']
            ))

async def test_real_crypto_service():
    """Test the real crypto price service"""
    try:
        logger.info("Testing real crypto price service...")
        
        # Create mock SocketIO
        mock_socketio = MockSocketIO()
        
        # Initialize service
        service = CryptoPriceService(mock_socketio)
        logger.info("Service initialized successfully")
        
        # Test price fetching
        logger.info("Fetching live prices from CoinGecko...")
        prices = await service.fetch_crypto_prices()
        
        if prices:
            logger.info(f"✅ Successfully fetched {len(prices)} cryptocurrency prices!")
            logger.info("Sample prices:")
            for price in prices[:5]:  # Show first 5
                logger.info(f"  {price['symbol']} ({price['name']}): ${price['price']:,.2f}")
                logger.info(f"    24h Change: {price['changePercent24h']:+.2f}% (${price['change24h']:+.2f})")
                logger.info(f"    Volume: ${price['volume24h']:,.0f} | Market Cap: ${price['marketCap']:,.0f}")
                logger.info(f"    Updated: {price['lastUpdated']}")
                logger.info("")
        else:
            logger.error("❌ No prices fetched!")
            return False
        
        # Test broadcasting
        logger.info("Testing price broadcasting...")
        await service.broadcast_prices(prices)
        logger.info("✅ Broadcasting test completed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_real_crypto_service())
        if success:
            logger.info("🎉 All tests passed!")
            sys.exit(0)
        else:
            logger.error("💥 Tests failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
