#!/usr/bin/env python3

"""
Test script to verify the refactored HD wallet implementations work with hdwallet==3.6.1
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.crypto.HD import BTC, ETH, TRX, XRP, LTC, BCH, GRS, BNB, MATIC, WORLD, OPTIMISM

def test_wallet_class(wallet_class, wallet_name, testnet=True):
    """Test a wallet class implementation"""
    print(f"\n=== Testing {wallet_name} Wallet ===")
    
    try:
        # Initialize wallet
        wallet = wallet_class(testnet=testnet)
        print(f"✅ {wallet_name} wallet initialized successfully")
        
        # Test mnemonic generation
        hd_base = wallet.__class__.__bases__[0]() if wallet.__class__.__bases__ else wallet
        mnemonic = hd_base.mnemonic()
        word_count = len(mnemonic.split())
        print(f"✅ Generated mnemonic: {str(mnemonic)[:50]}... ({word_count} words)")
        
        # Test from_mnemonic
        wallet.from_mnemonic(mnemonic)
        print(f"✅ Loaded wallet from mnemonic")
        
        # Test address generation
        address, priv_key, pub_key = wallet.new_address(index=0)
        print(f"✅ Generated address: {address}")
        print(f"✅ Private key length: {len(priv_key)}")
        print(f"✅ Public key length: {len(pub_key)}")
        
        return True
        
    except Exception as e:
        print(f"❌ {wallet_name} wallet test failed: {str(e)}")
        return False

def main():
    """Run tests for all wallet implementations"""
    print("Testing HD Wallet Refactor with hdwallet==3.6.1")
    print("=" * 50)
    
    test_cases = [
        (BTC, "Bitcoin", True),
        (ETH, "Ethereum", False),  # ETH typically uses mainnet
        (TRX, "Tron", False),
        (XRP, "Ripple", True),
        (LTC, "Litecoin", True),
        (BCH, "Bitcoin Cash", False),
        (GRS, "GroestlCoin", False),
        (BNB, "Binance Smart Chain", False),
        (MATIC, "Polygon", False),
        (WORLD, "World Chain", False),
        (OPTIMISM, "Optimism", False),
    ]
    
    results = []
    for wallet_class, name, testnet in test_cases:
        success = test_wallet_class(wallet_class, name, testnet)
        results.append((name, success))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name:20} {status}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All HD wallet implementations are working correctly!")
    else:
        print("⚠️  Some wallet implementations need attention")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
