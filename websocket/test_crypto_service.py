#!/usr/bin/env python3
"""
Test script for the crypto price service
"""

import asyncio
import sys
import os

# Add the parent directory to the path so we can import the crypto service
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from websocket.crypto_price_service import CryptoPriceService

class MockSocketIO:
    """Mock SocketIO for testing"""
    def emit(self, event, data, namespace=None):
        print(f"Mock SocketIO: Emitting {event} with {len(data)} items")
        for item in data[:3]:  # Show first 3 items
            print(f"  {item['symbol']}: ${item['price']:.2f} ({item['changePercent24h']:+.2f}%)")

async def test_crypto_service():
    """Test the crypto price service"""
    print("🧪 Testing Crypto Price Service...")
    
    # Create mock SocketIO
    mock_socketio = MockSocketIO()
    
    # Initialize service
    service = CryptoPriceService(mock_socketio)
    
    print("\n📊 Fetching crypto prices...")
    try:
        prices = await service.fetch_crypto_prices()
        print(f"✅ Successfully fetched {len(prices)} crypto prices")
        
        # Show some sample data
        print("\n📈 Sample Price Data:")
        for price in prices[:3]:
            print(f"  {price['symbol']} ({price['name']}):")
            print(f"    Price: ${price['price']:,.2f}")
            print(f"    24h Change: {price['changePercent24h']:+.2f}%")
            print(f"    Volume: ${price['volume24h']:,.0f}")
            print(f"    Market Cap: ${price['marketCap']:,.0f}")
            print()
        
        # Test caching
        print("💾 Testing cache functionality...")
        cached_prices = service.get_cached_prices()
        print(f"✅ Cached {len(cached_prices)} prices")
        
        # Test broadcasting
        print("\n📡 Testing broadcast functionality...")
        await service.broadcast_prices(prices)
        
        print("\n🎉 All tests passed! The crypto price service is working correctly.")
        
    except Exception as e:
        print(f"❌ Error testing crypto service: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting Crypto Price Service Tests...")
    print("=" * 50)
    
    try:
        success = asyncio.run(test_crypto_service())
        if success:
            print("\n✅ Crypto Price Service is ready for production!")
            sys.exit(0)
        else:
            print("\n❌ Crypto Price Service has issues that need fixing.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
