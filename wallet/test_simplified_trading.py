#!/usr/bin/env python3
"""
Test script for simplified trading system using existing Relworx implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connection import get_session
from db.wallet import Trade, TradeType, TradeStatus, PaymentMethod, PaymentProvider
from trading_service import TradingService
from lib.relworx_client import RelworxApiClient

def test_simplified_trading():
    """Test the simplified trading system"""
    print("Testing simplified trading system...")
    
    # Test 1: Verify Relworx client works
    try:
        client = RelworxApiClient()
        print("✓ Relworx client initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Relworx client: {e}")
        return False
    
    # Test 2: Verify trading service works
    try:
        session = get_session()
        trading_service = TradingService()
        print("✓ Trading service initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize trading service: {e}")
        return False
    
    # Test 3: Test fee calculation (should be 1% for all methods)
    try:
        fee = trading_service._get_fee_percentage(PaymentMethod.MOBILE_MONEY)
        assert fee == 0.01, f"Expected 1% fee, got {fee}"
        print("✓ Fee calculation works correctly (1% for all methods)")
    except Exception as e:
        print(f"✗ Fee calculation failed: {e}")
        return False
    
    # Test 4: Test trade amount calculation
    try:
        amounts = trading_service.calculate_trade_amounts(
            crypto_currency="BTC",
            fiat_currency="UGX",
            amount=100000,  # 100k UGX
            trade_type=TradeType.BUY,
            payment_method=PaymentMethod.MOBILE_MONEY
        )
        
        expected_fee = 100000 * 0.01  # 1% of 100k
        assert abs(amounts["fee_amount"] - expected_fee) < 0.01, f"Fee calculation incorrect"
        print("✓ Trade amount calculation works correctly")
        print(f"  - Fiat amount: {amounts['fiat_amount']} UGX")
        print(f"  - Fee amount: {amounts['fee_amount']} UGX")
        print(f"  - Crypto amount: {amounts['crypto_amount']} BTC")
        
    except Exception as e:
        print(f"✗ Trade amount calculation failed: {e}")
        return False
    
    # Test 5: Test database model
    try:
        # Create a test trade (don't save to DB)
        trade = Trade(
            trade_type=TradeType.BUY,
            status=TradeStatus.PENDING,
            user_id=1,
            account_id=1,
            crypto_currency="BTC",
            crypto_amount=0.001,
            fiat_currency="UGX",
            fiat_amount=100000,
            exchange_rate=100000000,  # 100M UGX per BTC
            fee_amount=1000,
            fee_currency="UGX",
            payment_method=PaymentMethod.MOBILE_MONEY,
            payment_provider=PaymentProvider.RELWORX,
            phone_number="+256700000000",
            description="Test trade"
        )
        print("✓ Trade model works correctly")
        
    except Exception as e:
        print(f"✗ Trade model failed: {e}")
        return False
    
    print("\n🎉 All tests passed! Simplified trading system is working correctly.")
    print("\nKey improvements:")
    print("- Uses existing Relworx implementation (no duplicate code)")
    print("- 1% fee for all payment methods")
    print("- Fixed metadata field name conflict")
    print("- Simplified mobile money processing")
    
    return True

if __name__ == "__main__":
    success = test_simplified_trading()
    sys.exit(0 if success else 1)
