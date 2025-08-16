#!/usr/bin/env python3
"""
Test script to verify database models can be imported without SQLAlchemy errors
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_model_imports():
    """Test that all models can be imported without errors"""
    try:
        print("Testing database model imports...")
        
        # Test importing the wallet models
        from db.wallet import (
            Trade, TradeType, TradeStatus, PaymentMethod, PaymentProvider,
            Transaction, TransactionType, TransactionStatus, Account,
            Voucher, VoucherStatus
        )
        print("+ Wallet models imported successfully")
        
        # Test importing the base models
        from db.models import User
        print("+ Base models imported successfully")
        
        # Test creating model instances (without saving to DB)
        trade = Trade(
            trade_type=TradeType.BUY,
            status=TradeStatus.PENDING,
            user_id=1,
            account_id=1,
            crypto_currency="BTC",
            crypto_amount=0.001,
            fiat_currency="UGX",
            fiat_amount=100000,
            exchange_rate=100000000,
            fee_amount=1000,
            fee_currency="UGX",
            payment_method=PaymentMethod.MOBILE_MONEY,
            payment_provider=PaymentProvider.RELWORX,
            description="Test trade"
        )
        print("+ Trade model instance created successfully")
        
        transaction = Transaction(
            account_id=1,
            amount=100000,
            type=TransactionType.BUY_CRYPTO,
            status=TransactionStatus.PENDING,
            description="Test transaction",
            trade_id=1
        )
        print("+ Transaction model instance created successfully")
        
        print("\nSUCCESS: All model imports and instantiations successful!")
        print("SQLAlchemy relationship conflicts have been resolved.")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Model import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_model_imports()
    sys.exit(0 if success else 1)
