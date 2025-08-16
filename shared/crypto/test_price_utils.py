#!/usr/bin/env python3
"""
Test script for the crypto price utilities.

This script demonstrates how to use the AlchemyPriceAPI class and convenience functions
to fetch crypto prices.
"""

import os
import sys
from price_utils import AlchemyPriceAPI, get_crypto_price, get_crypto_prices

def test_basic_functionality():
    """Test basic API functionality."""
    print("=== Testing Basic Functionality ===")
    
    # Initialize API client
    api_key = os.getenv('ALCHEMY_API_KEY', 'demo')
    api = AlchemyPriceAPI(api_key)
    
    print(f"Using API key: {api_key[:10]}..." if len(api_key) > 10 else f"Using API key: {api_key}")
    
    # Test single symbol
    print("\n1. Testing single symbol (ETH):")
    eth_data = api.get_price_by_symbol("ETH")
    if eth_data:
        print(f"   ETH data: {eth_data}")
        usd_price = api.get_usd_price("ETH")
        print(f"   ETH USD price: ${usd_price}")
    else:
        print("   Failed to get ETH data")
    
    # Test multiple symbols
    print("\n2. Testing multiple symbols:")
    symbols = ["BTC", "ETH", "SOL", "USDT"]
    prices = api.get_prices_by_symbols(symbols)
    print(f"   Raw response: {prices}")
    
    # Test USD price extraction
    print("\n3. Testing USD price extraction:")
    usd_prices = api.get_multiple_usd_prices(symbols)
    for symbol, price in usd_prices.items():
        status = f"${price}" if price else "Not available"
        print(f"   {symbol}: {status}")

def test_convenience_functions():
    """Test convenience functions."""
    print("\n=== Testing Convenience Functions ===")
    
    # Test single price
    print("\n1. Quick single price (BTC):")
    btc_price = get_crypto_price("BTC")
    print(f"   BTC: ${btc_price}" if btc_price else "   BTC: Not available")
    
    # Test multiple prices
    print("\n2. Quick multiple prices:")
    quick_prices = get_crypto_prices(["ETH", "SOL", "ADA"])
    for symbol, price in quick_prices.items():
        status = f"${price}" if price else "Not available"
        print(f"   {symbol}: {status}")

def test_error_handling():
    """Test error handling."""
    print("\n=== Testing Error Handling ===")
    
    # Test with invalid API key
    print("\n1. Testing with invalid API key:")
    try:
        invalid_api = AlchemyPriceAPI("invalid_key")
        result = invalid_api.get_price_by_symbol("ETH")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   Expected error: {e}")
    
    # Test with empty symbols
    print("\n2. Testing with empty symbols:")
    api = AlchemyPriceAPI()
    result = api.get_prices_by_symbols([])
    print(f"   Empty symbols result: {result}")
    
    # Test with invalid symbols
    print("\n3. Testing with invalid symbols:")
    result = api.get_prices_by_symbols(["INVALID_SYMBOL_12345"])
    print(f"   Invalid symbol result: {result}")

def main():
    """Main test function."""
    print("🚀 Crypto Price Utilities Test")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        test_convenience_functions()
        test_error_handling()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
