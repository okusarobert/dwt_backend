#!/usr/bin/env python3
"""
Test script to verify multi-network deposit functionality after ETH client import fix
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from wallet.multi_network_deposits import MultiNetworkDepositManager
from db.connection import get_session
from shared.logger import setup_logging

logger = setup_logging()

def test_eth_client_import():
    """Test that ETH client can be imported correctly"""
    try:
        from shared.crypto.clients.eth import ETHWallet, EthereumConfig
        logger.info("✅ ETH client import successful")
        return True
    except ImportError as e:
        logger.error(f"❌ ETH client import failed: {e}")
        return False

def test_multi_network_manager():
    """Test MultiNetworkDepositManager initialization"""
    try:
        manager = MultiNetworkDepositManager()
        logger.info("✅ MultiNetworkDepositManager initialization successful")
        return True
    except Exception as e:
        logger.error(f"❌ MultiNetworkDepositManager initialization failed: {e}")
        return False

def test_get_deposit_networks():
    """Test getting deposit networks for ETH"""
    try:
        manager = MultiNetworkDepositManager()
        result = manager.get_deposit_networks("ETH", include_testnets=True)
        
        if result.get("success"):
            logger.info("✅ Get deposit networks successful")
            logger.info(f"Available networks: {[net['type'] for net in result.get('networks', [])]}")
            return True
        else:
            logger.error(f"❌ Get deposit networks failed: {result.get('error')}")
            return False
    except Exception as e:
        logger.error(f"❌ Get deposit networks failed with exception: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Testing multi-network deposit functionality after ETH client fix")
    
    tests = [
        ("ETH Client Import", test_eth_client_import),
        ("MultiNetworkDepositManager", test_multi_network_manager),
        ("Get Deposit Networks", test_get_deposit_networks),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        if test_func():
            passed += 1
        else:
            logger.error(f"Test {test_name} failed")
    
    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Multi-network deposit fix is working correctly.")
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
