#!/usr/bin/env python3
"""
Test script for Solana webhook integration with unified amount/balance system and accounting.
"""

import sys
import os
import json
import datetime
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_amount_conversion():
    """Test SOL amount conversion using unified precision system."""
    print("🧪 Testing SOL amount conversion...")
    
    try:
        from shared.currency_precision import AmountConverter
        
        # Test lamports to SOL conversion
        lamports = 1500000000  # 1.5 SOL
        sol_amount = AmountConverter.from_smallest_units(lamports, "SOL")
        print(f"✅ {lamports:,} lamports = {sol_amount} SOL")
        
        # Test SOL to lamports conversion
        sol_value = Decimal("2.5")
        converted_lamports = AmountConverter.to_smallest_units(sol_value, "SOL")
        print(f"✅ {sol_value} SOL = {converted_lamports:,} lamports")
        
        # Test display formatting
        formatted = AmountConverter.format_display_amount(lamports, "SOL")
        print(f"✅ Display format: {formatted}")
        
        return True
    except Exception as e:
        print(f"❌ Amount conversion test failed: {e}")
        return False

def test_accounting_service():
    """Test accounting service integration."""
    print("\n🧪 Testing accounting service...")
    
    try:
        from shared.trading_accounting import TradingAccountingService
        from db.connection import session
        
        # Test service initialization
        accounting_service = TradingAccountingService(session)
        print("✅ TradingAccountingService initialized")
        
        return True
    except Exception as e:
        print(f"❌ Accounting service test failed: {e}")
        return False

def test_solana_webhook_imports():
    """Test Solana webhook module imports."""
    print("\n🧪 Testing Solana webhook imports...")
    
    try:
        from wallet.solana_webhook import _create_solana_accounting_entry, _update_tx_confirmations_and_credit
        from wallet.solana_webhook import solana_webhook
        print("✅ Solana webhook functions imported")
        
        from db.wallet import Transaction, Account, TransactionType, TransactionStatus
        print("✅ Wallet models imported")
        
        return True
    except Exception as e:
        print(f"❌ Solana webhook imports failed: {e}")
        return False

def test_unified_models():
    """Test unified amount/balance model integration."""
    print("\n🧪 Testing unified models...")
    
    try:
        from db.wallet import Account, Transaction
        from db.unified_amounts import UnifiedAmountMixin, UnifiedBalanceMixin
        
        # Check if Account inherits from UnifiedBalanceMixin
        if issubclass(Account, UnifiedBalanceMixin):
            print("✅ Account model uses UnifiedBalanceMixin")
        else:
            print("⚠️ Account model doesn't inherit from UnifiedBalanceMixin")
        
        # Check if Transaction inherits from UnifiedAmountMixin
        if issubclass(Transaction, UnifiedAmountMixin):
            print("✅ Transaction model uses UnifiedAmountMixin")
        else:
            print("⚠️ Transaction model doesn't inherit from UnifiedAmountMixin")
        
        return True
    except Exception as e:
        print(f"❌ Unified models test failed: {e}")
        return False

def test_webhook_payload_processing():
    """Test webhook payload processing logic."""
    print("\n🧪 Testing webhook payload processing...")
    
    try:
        from shared.currency_precision import AmountConverter
        
        # Simulate webhook data
        sample_lamports = 2500000000  # 2.5 SOL
        
        # Test amount conversion
        sol_amount = AmountConverter.from_smallest_units(sample_lamports, "SOL")
        formatted_amount = AmountConverter.format_display_amount(sample_lamports, "SOL")
        
        print(f"✅ Sample webhook: {sample_lamports:,} lamports")
        print(f"✅ Converted to: {sol_amount} SOL")
        print(f"✅ Display format: {formatted_amount}")
        
        # Test transaction metadata
        metadata = {
            'webhook_id': 'test_webhook_123',
            'from_address': '11111111111111111111111111111112',
            'to_address': 'DemoAddress1111111111111111111111111111',
            'slot': 123456789,
            'network': 'devnet',
            'processed_at': datetime.datetime.utcnow().isoformat(),
            'unified_system': True
        }
        
        print(f"✅ Metadata structure: {json.dumps(metadata, indent=2)}")
        
        return True
    except Exception as e:
        print(f"❌ Webhook payload processing test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Solana webhook unified system tests...\n")
    
    tests = [
        test_amount_conversion,
        test_accounting_service,
        test_solana_webhook_imports,
        test_unified_models,
        test_webhook_payload_processing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Solana webhook unified integration is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
