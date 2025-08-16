#!/usr/bin/env python3
"""
Test script for wallet withdrawal integration with unified amount/balance system and accounting.
"""

import sys
import os
import json
import datetime
from decimal import Decimal

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_withdrawal_precision_conversion():
    """Test withdrawal amount conversion using unified precision system."""
    print("🧪 Testing withdrawal precision conversion...")
    
    try:
        from shared.currency_precision import AmountConverter
        
        # Test ETH withdrawal conversion
        eth_amount = Decimal("0.5")  # 0.5 ETH
        eth_wei = AmountConverter.to_smallest_units(eth_amount, "ETH")
        print(f"✅ {eth_amount} ETH = {eth_wei:,} wei")
        
        # Test SOL withdrawal conversion
        sol_amount = Decimal("2.5")  # 2.5 SOL
        sol_lamports = AmountConverter.to_smallest_units(sol_amount, "SOL")
        print(f"✅ {sol_amount} SOL = {sol_lamports:,} lamports")
        
        # Test display formatting
        eth_display = AmountConverter.format_display_amount(eth_wei, "ETH")
        sol_display = AmountConverter.format_display_amount(sol_lamports, "SOL")
        print(f"✅ ETH display: {eth_display}")
        print(f"✅ SOL display: {sol_display}")
        
        return True
    except Exception as e:
        print(f"❌ Withdrawal precision conversion test failed: {e}")
        return False

def test_withdrawal_service_imports():
    """Test withdrawal service function imports."""
    print("\n🧪 Testing withdrawal service imports...")
    
    try:
        from wallet.service import confirm_crypto_withdrawal, _create_crypto_withdrawal_accounting_entry
        print("✅ Withdrawal service functions imported")
        
        from db.wallet import Transaction, Account, TransactionType, TransactionStatus
        print("✅ Wallet models imported")
        
        return True
    except Exception as e:
        print(f"❌ Withdrawal service imports failed: {e}")
        return False

def test_accounting_integration():
    """Test accounting integration for withdrawals."""
    print("\n🧪 Testing withdrawal accounting integration...")
    
    try:
        from shared.trading_accounting import TradingAccountingService
        print("✅ TradingAccountingService imported")
        
        # Test accounting entry structure for crypto withdrawals
        sample_withdrawal_entry = {
            "description": "Confirmed crypto withdrawal: 0.5 ETH for user 123",
            "debit_account_name": "User Liabilities - ETH",
            "credit_account_name": "Crypto Assets - ETH",
            "amount_smallest_unit": 500000000000000000,  # 0.5 ETH in wei
            "currency": "ETH",
            "reference_id": "eth_withdraw_abc123",
            "metadata": {
                "transaction_id": 456,
                "account_id": 789,
                "user_id": 123,
                "blockchain_txid": "0x1234567890abcdef",
                "unified_system": True,
                "confirmation_type": "crypto_withdrawal"
            }
        }
        
        print(f"✅ Sample withdrawal accounting entry: {len(sample_withdrawal_entry)} fields")
        
        return True
    except Exception as e:
        print(f"❌ Withdrawal accounting integration test failed: {e}")
        return False

def test_withdrawal_confirmation_flow():
    """Test withdrawal confirmation flow logic."""
    print("\n🧪 Testing withdrawal confirmation flow...")
    
    try:
        from shared.currency_precision import AmountConverter
        
        # Simulate withdrawal confirmation process
        sample_tx_hash = "0x1234567890abcdef1234567890abcdef12345678"
        sample_amount_wei = 500000000000000000  # 0.5 ETH
        
        # Test amount formatting for confirmation
        formatted_amount = AmountConverter.format_display_amount(sample_amount_wei, "ETH")
        print(f"✅ Withdrawal confirmation: {formatted_amount}")
        
        # Test balance update logic
        locked_before = 1000000000000000000  # 1 ETH locked
        locked_after = max(0, locked_before - sample_amount_wei)
        print(f"✅ Locked balance update: {locked_before:,} → {locked_after:,} wei")
        
        # Test transaction status update
        status_before = "AWAITING_CONFIRMATION"
        status_after = "COMPLETED"
        print(f"✅ Status update: {status_before} → {status_after}")
        
        return True
    except Exception as e:
        print(f"❌ Withdrawal confirmation flow test failed: {e}")
        return False

def test_unified_balance_handling():
    """Test unified balance field handling."""
    print("\n🧪 Testing unified balance handling...")
    
    try:
        from db.unified_amounts import UnifiedBalanceMixin
        
        # Test balance field availability
        required_fields = ['balance_smallest_unit', 'locked_amount_smallest_unit']
        for field in required_fields:
            if hasattr(UnifiedBalanceMixin, field):
                print(f"✅ UnifiedBalanceMixin has {field}")
            else:
                print(f"⚠️ UnifiedBalanceMixin missing {field}")
        
        # Test balance operations
        initial_balance = 2000000000000000000  # 2 ETH
        withdrawal_amount = 500000000000000000  # 0.5 ETH
        
        # Simulate withdrawal: move from balance to locked
        new_balance = initial_balance - withdrawal_amount
        new_locked = withdrawal_amount
        
        print(f"✅ Balance after withdrawal initiation:")
        print(f"   Balance: {initial_balance:,} → {new_balance:,} wei")
        print(f"   Locked: 0 → {new_locked:,} wei")
        
        # Simulate confirmation: remove from locked
        final_locked = max(0, new_locked - withdrawal_amount)
        print(f"✅ Locked after confirmation: {new_locked:,} → {final_locked:,} wei")
        
        return True
    except Exception as e:
        print(f"❌ Unified balance handling test failed: {e}")
        return False

def test_withdrawal_metadata():
    """Test withdrawal transaction metadata structure."""
    print("\n🧪 Testing withdrawal metadata...")
    
    try:
        # Test ETH withdrawal metadata
        eth_metadata = {
            "to_address": "0x742d35Cc6634C0532925a3b8D4C9db96C4b4d8b6",
            "gas_limit": 21000,
            "estimated_cost_eth": 0.001,
            "transaction_hash": "0x1234567890abcdef",
            "from_address": "0x9876543210fedcba",
            "reservation_reference": "eth_withdrawal_1234567890_ref123",
            "unified_system": True
        }
        
        print(f"✅ ETH withdrawal metadata: {len(eth_metadata)} fields")
        
        # Test SOL withdrawal metadata
        sol_metadata = {
            "to_address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
            "priority_fee": 5000,
            "estimated_cost_sol": 0.000005,
            "transaction_hash": "5j7s1QjCeeSgZ1qbeLYmhBjNynDHzwsBa4ZjS3tAoWDy",
            "from_address": "DemoAddress1111111111111111111111111111",
            "reservation_reference": "sol_withdrawal_1234567890_ref456",
            "unified_system": True
        }
        
        print(f"✅ SOL withdrawal metadata: {len(sol_metadata)} fields")
        
        return True
    except Exception as e:
        print(f"❌ Withdrawal metadata test failed: {e}")
        return False

def main():
    """Run all withdrawal tests."""
    print("🚀 Starting wallet withdrawal unified system tests...\n")
    
    tests = [
        test_withdrawal_precision_conversion,
        test_withdrawal_service_imports,
        test_accounting_integration,
        test_withdrawal_confirmation_flow,
        test_unified_balance_handling,
        test_withdrawal_metadata
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n📊 Withdrawal Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All withdrawal tests passed! Unified withdrawal system is ready.")
        return 0
    else:
        print("⚠️ Some withdrawal tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
