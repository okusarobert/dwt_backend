#!/usr/bin/env python3
"""
Test script to simulate a new transaction event and verify the event handling works.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

from util import new_payment_handler
from shared.crypto.util import get_coin
from shared.logger import setup_logging

logger = setup_logging()

async def test_transaction_event():
    """Test the new transaction event handler"""
    
    # Simulate a transaction hash (this should be a real transaction hash)
    test_tx_hash = "04dab864345e8bd78cbf217e86f44944b55772ef53f973989819d0f289140cac"
    
    # Create a mock instance object
    class MockInstance:
        def __init__(self):
            self.coin_name = "BTC"
    
    mock_instance = MockInstance()
    
    logger.info(f"[TEST] Testing new transaction event with hash: {test_tx_hash}")
    
    try:
        # Call the new_payment_handler directly
        await new_payment_handler(mock_instance, "new_transaction", test_tx_hash)
        logger.info("[TEST] Transaction event test completed successfully")
        
    except Exception as e:
        logger.error(f"[TEST] Error testing transaction event: {e}")
        import traceback
        logger.error(f"[TEST] Traceback: {traceback.format_exc()}")

async def test_with_real_transaction():
    """Test with a real transaction from the blockchain"""
    
    try:
        # Get the BTC coin instance
        from shared.crypto.util import get_coin
        btc_coin = get_coin("BTC")
        
        # Get a recent transaction
        recent_tx_hash = "04dab864345e8bd78cbf217e86f44944b55772ef53f973989819d0f289140cac"
        
        logger.info(f"[TEST] Testing with real transaction: {recent_tx_hash}")
        
        # Get the transaction data
        tx_data = await btc_coin.get_tx(recent_tx_hash)
        logger.info(f"[TEST] Transaction data: {tx_data}")
        
        # Test the transaction data processing
        from util import get_coin_txn_data
        processed_data = get_coin_txn_data("BTC", tx_data)
        logger.info(f"[TEST] Processed transaction data: {processed_data}")
        
    except Exception as e:
        logger.error(f"[TEST] Error testing with real transaction: {e}")
        import traceback
        logger.error(f"[TEST] Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("[TEST] Starting transaction event tests...")
    
    # Run the tests
    asyncio.run(test_transaction_event())
    asyncio.run(test_with_real_transaction())
    
    logger.info("[TEST] All tests completed!") 