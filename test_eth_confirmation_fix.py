#!/usr/bin/env python3
"""
Test script to manually trigger ETH confirmation check for stuck transaction
"""
import os
import sys
sys.path.append('/Users/ojr.roberto/dev/python/dwt_backend')

from eth_monitor.app import EthereumMonitor
from db.connection import get_session
from db.wallet import Transaction, TransactionStatus
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_confirmation_fix():
    """Test the confirmation fix for stuck transaction"""
    try:
        # Initialize ETH monitor
        api_key = os.getenv('ALCHEMY_API_KEY')
        if not api_key:
            logger.error("ALCHEMY_API_KEY not set")
            return
            
        monitor = EthereumMonitor(api_key=api_key, network='mainnet')
        
        # Get the stuck transaction
        session = get_session()
        stuck_tx = session.query(Transaction).filter_by(id=32).first()
        
        if not stuck_tx:
            logger.error("Transaction ID 32 not found")
            return
            
        logger.info(f"Found stuck transaction: {stuck_tx.blockchain_txid}")
        logger.info(f"Current status: {stuck_tx.status}")
        logger.info(f"Current confirmations: {stuck_tx.confirmations}")
        logger.info(f"Block number in metadata: {stuck_tx.metadata_json.get('block_number', 'None') if stuck_tx.metadata_json else 'None'}")
        
        # Get current block number
        current_block = monitor._get_current_block_number()
        logger.info(f"Current block number: {current_block}")
        
        # Test the confirmation check
        logger.info("Testing confirmation check...")
        monitor._check_transaction_confirmations_for_block_sync(stuck_tx.blockchain_txid, current_block)
        
        # Check the transaction status after the fix
        session.refresh(stuck_tx)
        logger.info(f"After fix - Status: {stuck_tx.status}")
        logger.info(f"After fix - Confirmations: {stuck_tx.confirmations}")
        logger.info(f"After fix - Block number: {stuck_tx.metadata_json.get('block_number', 'None') if stuck_tx.metadata_json else 'None'}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Error testing confirmation fix: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_confirmation_fix()
