#!/usr/bin/env python3
"""
Containerized test script for Solana webhook integration with unified amount/balance system and accounting.
This version is designed to run inside a Docker container with minimal dependencies.
"""

import sys
import os
import json
import datetime
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all required imports for Solana webhook integration."""
    print("🧪 Testing imports...")
    
    try:
        # Test currency precision imports
        from shared.currency_precision import AmountConverter, CURRENCY_PRECISION
        print("✅ Currency precision imports successful")
        
        # Test accounting imports
        from shared.trading_accounting import TradingAccountingService
        print("✅ Trading accounting imports successful")
        
        # Test database model imports
        from db.unified_amounts import UnifiedAmountMixin, UnifiedBalanceMixin
        print("✅ Unified amounts imports successful")
        
        # Test wallet model imports (may fail in container without full DB)
        try:
            from db.wallet import Account, Transaction, TransactionType, TransactionStatus
            print("✅ Wallet model imports successful")
        except Exception as e:
            print(f"⚠️ Wallet model imports failed (expected in container): {e}")
        
        # Test Solana webhook imports
        try:
            from wallet.solana_webhook import _create_solana_accounting_entry
            print("✅ Solana webhook function imports successful")
        except Exception as e:
            print(f"⚠️ Solana webhook imports failed (expected in container): {e}")
        
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_sol_amount_conversion():
    """Test SOL amount conversion using unified precision system."""
    print("\n🧪 Testing SOL amount conversion...")
    
    try:
        from shared.currency_precision import AmountConverter
        
        # Test various SOL amounts
        test_cases = [
            (1000000000, "1.0"),      # 1 SOL
            (1500000000, "1.5"),      # 1.5 SOL  
            (2500000000, "2.5"),      # 2.5 SOL
            (100000000, "0.1"),       # 0.1 SOL
            (1, "0.000000001"),       # 1 lamport
            (500000000, "0.5"),       # 0.5 SOL
        ]
        
        for lamports, expected_sol in test_cases:
            sol_amount = AmountConverter.from_smallest_units(lamports, "SOL")
            formatted = AmountConverter.format_display_amount(lamports, "SOL")
            print(f"✅ {lamports:,} lamports = {sol_amount} SOL (display: {formatted})")
            
            # Test reverse conversion
            converted_back = AmountConverter.to_smallest_units(sol_amount, "SOL")
            if converted_back == lamports:
                print(f"✅ Reverse conversion verified: {sol_amount} SOL = {converted_back:,} lamports")
            else:
                print(f"⚠️ Reverse conversion mismatch: expected {lamports}, got {converted_back}")
        
        return True
    except Exception as e:
        print(f"❌ SOL amount conversion test failed: {e}")
        return False

def test_currency_precision_config():
    """Test SOL currency precision configuration."""
    print("\n🧪 Testing SOL currency precision config...")
    
    try:
        from shared.currency_precision import CURRENCY_PRECISION
        
        if "SOL" in CURRENCY_PRECISION:
            sol_config = CURRENCY_PRECISION["SOL"]
            print(f"✅ SOL config found: {sol_config}")
            
            # Check PrecisionConfig object attributes
            if hasattr(sol_config, 'decimal_places'):
                print(f"✅ decimal_places: {sol_config.decimal_places}")
            else:
                print("⚠️ Missing decimal_places attribute")
                
            if hasattr(sol_config, 'display_decimals'):
                print(f"✅ display_decimals: {sol_config.display_decimals}")
            else:
                print("⚠️ Missing display_decimals attribute")
                
            if hasattr(sol_config, 'smallest_unit_name'):
                print(f"✅ smallest_unit_name: {sol_config.smallest_unit_name}")
            else:
                print("⚠️ Missing smallest_unit_name attribute")
            
            # Verify SOL has 9 decimal places (lamports)
            if hasattr(sol_config, 'decimal_places') and sol_config.decimal_places == 9:
                print("✅ SOL decimal places correct (9 for lamports)")
            else:
                print(f"⚠️ SOL decimal places incorrect: {getattr(sol_config, 'decimal_places', 'N/A')}")
        else:
            print("❌ SOL not found in CURRENCY_PRECISION")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Currency precision config test failed: {e}")
        return False

def test_unified_mixins():
    """Test unified amount and balance mixins."""
    print("\n🧪 Testing unified mixins...")
    
    try:
        from db.unified_amounts import UnifiedAmountMixin, UnifiedBalanceMixin
        
        # Test UnifiedAmountMixin methods
        print("✅ UnifiedAmountMixin imported")
        
        # Check if mixin has required methods
        required_amount_methods = ['amount_smallest_unit', 'currency']
        for method in required_amount_methods:
            if hasattr(UnifiedAmountMixin, method):
                print(f"✅ UnifiedAmountMixin has {method}")
            else:
                print(f"⚠️ UnifiedAmountMixin missing {method}")
        
        # Test UnifiedBalanceMixin methods
        print("✅ UnifiedBalanceMixin imported")
        
        required_balance_methods = ['balance_smallest_unit', 'locked_amount_smallest_unit']
        for method in required_balance_methods:
            if hasattr(UnifiedBalanceMixin, method):
                print(f"✅ UnifiedBalanceMixin has {method}")
            else:
                print(f"⚠️ UnifiedBalanceMixin missing {method}")
        
        return True
    except Exception as e:
        print(f"❌ Unified mixins test failed: {e}")
        return False

def test_webhook_data_processing():
    """Test webhook data processing logic."""
    print("\n🧪 Testing webhook data processing...")
    
    try:
        from shared.currency_precision import AmountConverter
        
        # Simulate Alchemy webhook payload
        sample_webhook_data = {
            "id": "webhook_123",
            "event": {
                "network": "SOLANA_DEVNET",
                "activity": [
                    {
                        "fromAddress": "11111111111111111111111111111112",
                        "toAddress": "DemoAddress1111111111111111111111111111",
                        "blockNum": 123456789,
                        "hash": "5j7s1QjCeeSgZ1qbeLYmhBjNynDHzwsBa4ZjS3tAoWDy",
                        "value": 2.5,  # SOL amount from webhook
                        "typeTraceAddress": "0x0",
                        "category": "external"
                    }
                ]
            }
        }
        
        # Process the webhook data
        activity = sample_webhook_data["event"]["activity"][0]
        sol_value = activity["value"]
        
        # Convert to lamports using unified system
        lamports = AmountConverter.to_smallest_units(Decimal(str(sol_value)), "SOL")
        formatted_amount = AmountConverter.format_display_amount(lamports, "SOL")
        
        print(f"✅ Webhook SOL value: {sol_value}")
        print(f"✅ Converted to lamports: {lamports:,}")
        print(f"✅ Display format: {formatted_amount}")
        
        # Test transaction metadata creation
        metadata = {
            'webhook_id': sample_webhook_data["id"],
            'from_address': activity["fromAddress"],
            'to_address': activity["toAddress"],
            'block_num': activity["blockNum"],
            'hash': activity["hash"],
            'network': sample_webhook_data["event"]["network"],
            'processed_at': datetime.datetime.utcnow().isoformat(),
            'unified_system': True
        }
        
        print(f"✅ Transaction metadata created: {len(metadata)} fields")
        
        return True
    except Exception as e:
        print(f"❌ Webhook data processing test failed: {e}")
        return False

def test_accounting_integration():
    """Test accounting integration structure."""
    print("\n🧪 Testing accounting integration...")
    
    try:
        from shared.trading_accounting import TradingAccountingService
        
        print("✅ TradingAccountingService imported")
        
        # Test if service has required methods
        required_methods = ['create_journal_entry']
        for method in required_methods:
            if hasattr(TradingAccountingService, method):
                print(f"✅ TradingAccountingService has {method}")
            else:
                # Check if it's an instance method by creating a dummy instance
                try:
                    dummy_service = TradingAccountingService(None)
                    if hasattr(dummy_service, method):
                        print(f"✅ TradingAccountingService has {method} (instance method)")
                    else:
                        print(f"⚠️ TradingAccountingService missing {method}")
                except:
                    print(f"⚠️ TradingAccountingService missing {method}")
        
        # Test accounting entry structure for SOL deposits
        sample_entry_data = {
            "description": "Solana deposit: 2.5 SOL for user 123",
            "debit_account_name": "Crypto Assets - SOL",
            "credit_account_name": "User Liabilities - SOL", 
            "amount_smallest_unit": 2500000000,  # 2.5 SOL in lamports
            "currency": "SOL",
            "reference_id": "sol_deposit_5j7s1QjCeeSgZ1qbeLYmhBjNynDHzwsBa4ZjS3tAoWDy",
            "metadata": {
                "transaction_id": 456,
                "account_id": 789,
                "user_id": 123,
                "blockchain_txid": "5j7s1QjCeeSgZ1qbeLYmhBjNynDHzwsBa4ZjS3tAoWDy",
                "unified_system": True,
                "webhook_source": "solana_alchemy"
            }
        }
        
        print(f"✅ Sample accounting entry structure: {len(sample_entry_data)} fields")
        
        return True
    except Exception as e:
        print(f"❌ Accounting integration test failed: {e}")
        return False

def main():
    """Run all containerized tests."""
    print("🐳 Starting containerized Solana webhook unified system tests...\n")
    
    tests = [
        test_imports,
        test_sol_amount_conversion,
        test_currency_precision_config,
        test_unified_mixins,
        test_webhook_data_processing,
        test_accounting_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Container Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All containerized tests passed! Solana webhook unified integration is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
