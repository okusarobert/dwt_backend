#!/usr/bin/env python3
"""
Test script for the simplified crypto price service
"""

import sys
import os

# Add the websocket directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crypto_price_service_simple import CryptoPriceServiceSimple

class MockSocketIO:
    """Mock SocketIO for testing"""
    def emit(self, event, data, namespace=None):
        print(f"Mock SocketIO: Emitting {event} with {len(data)} items")
        for item in data[:3]:  # Show first 3 items
            print(f"  {item['symbol']}: ${item['price']:.2f} ({item['changePercent24h']:+.2f}%)")

def test_simple_service():
    """Test the simplified crypto price service"""
    print("🧪 Testing Simplified Crypto Price Service...")
    
    try:
        # Create mock SocketIO
        mock_socketio = MockSocketIO()
        
        # Initialize service
        service = CryptoPriceServiceSimple(mock_socketio)
        print(f"✅ Service initialized with {len(service.price_cache)} cryptocurrencies")
        
        # Test cached prices
        print("\n📊 Testing cached prices...")
        cached_prices = service.get_cached_prices()
        print(f"✅ Retrieved {len(cached_prices)} cached prices")
        
        # Show sample data
        print("\n📈 Sample Price Data:")
        for price in cached_prices[:3]:
            print(f"  {price['symbol']} ({price['name']}):")
            print(f"    Price: ${price['price']:,.2f}")
            print(f"    24h Change: {price['changePercent24h']:+.2f}%")
            print(f"    Volume: ${price['volume24h']:,.0f}")
            print(f"    Market Cap: ${price['marketCap']:,.0f}")
            print()
        
        # Test price updates
        print("🔄 Testing price updates...")
        service.update_prices()
        updated_prices = service.get_cached_prices()
        print(f"✅ Updated {len(updated_prices)} prices")
        
        # Test broadcasting
        print("\n📡 Testing broadcast functionality...")
        service.broadcast_prices(updated_prices)
        
        print("\n🎉 All tests passed! The simplified crypto price service is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error testing service: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Simplified Crypto Price Service Tests...")
    print("=" * 60)
    
    try:
        success = test_simple_service()
        if success:
            print("\n✅ Simplified Crypto Price Service is ready!")
            sys.exit(0)
        else:
            print("\n❌ Service has issues that need fixing.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
