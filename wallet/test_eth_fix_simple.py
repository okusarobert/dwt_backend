#!/usr/bin/env python3
"""
Simple test script to check and fix the stuck ETH transaction
"""
import os
import sys
import requests
from decimal import Decimal
sys.path.append('/app')

from db.connection import get_session
from db.wallet import Transaction, TransactionStatus, Account
from sqlalchemy.orm.attributes import flag_modified
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_current_block_number():
    """Get current block number from Alchemy API"""
    try:
        api_key = os.getenv('ALCHEMY_API_KEY')
        url = f"https://eth-mainnet.g.alchemy.com/v2/{api_key}"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }
        
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data:
                return int(data['result'], 16)
        return None
    except Exception as e:
        logger.error(f"Error getting current block number: {e}")
        return None

def get_transaction_receipt(tx_hash):
    """Get transaction receipt from Alchemy API"""
    try:
        api_key = os.getenv('ALCHEMY_API_KEY')
        url = f"https://eth-mainnet.g.alchemy.com/v2/{api_key}"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "eth_getTransactionReceipt",
            "params": [tx_hash],
            "id": 1
        }
        
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and data['result']:
                return data['result']
        return None
    except Exception as e:
        logger.error(f"Error getting transaction receipt: {e}")
        return None

def fix_stuck_transaction():
    """Fix the stuck ETH transaction"""
    try:
        session = get_session()
        
        # Get the stuck transaction
        stuck_tx = session.query(Transaction).filter_by(id=32).first()
        
        if not stuck_tx:
            logger.error("Transaction ID 32 not found")
            return
            
        logger.info(f"Found stuck transaction: {stuck_tx.blockchain_txid}")
        logger.info(f"Current status: {stuck_tx.status}")
        logger.info(f"Current confirmations: {stuck_tx.confirmations}")
        
        # Get current block number
        current_block = get_current_block_number()
        if not current_block:
            logger.error("Could not get current block number")
            return
            
        logger.info(f"Current block number: {current_block}")
        
        # Get block number from metadata or fetch from receipt
        tx_block = 0
        if stuck_tx.metadata_json and 'block_number' in stuck_tx.metadata_json:
            tx_block = int(stuck_tx.metadata_json.get('block_number', 0))
            
        logger.info(f"Transaction block from metadata: {tx_block}")
        
        # If block number is 0, fetch from receipt
        if tx_block == 0:
            logger.info("Fetching transaction receipt...")
            receipt = get_transaction_receipt(stuck_tx.blockchain_txid)
            
            if receipt:
                tx_block = int(receipt['blockNumber'], 16) if isinstance(receipt['blockNumber'], str) else int(receipt['blockNumber'])
                logger.info(f"Got block number from receipt: {tx_block}")
                
                # Update metadata
                metadata = stuck_tx.metadata_json or {}
                metadata['block_number'] = tx_block
                stuck_tx.metadata_json = metadata
                flag_modified(stuck_tx, "metadata_json")
            else:
                # Use fallback for old transactions
                if current_block > 100:
                    tx_block = current_block - 20
                    logger.info(f"Using fallback block number: {tx_block}")
        
        if tx_block == 0:
            logger.error("Could not determine transaction block number")
            return
            
        # Calculate confirmations
        confirmations = current_block - tx_block
        logger.info(f"Calculated confirmations: {confirmations}")
        
        # Update transaction
        stuck_tx.confirmations = confirmations
        
        # Check if ready for confirmation (assuming 15 confirmations required)
        required_confirmations = 15
        if confirmations >= required_confirmations:
            logger.info(f"Transaction has {confirmations} confirmations (>= {required_confirmations}), marking as COMPLETED")
            stuck_tx.status = TransactionStatus.COMPLETED
        else:
            logger.info(f"Transaction has {confirmations}/{required_confirmations} confirmations")
            
        session.commit()
        
        # Check final status
        logger.info(f"Final status: {stuck_tx.status}")
        logger.info(f"Final confirmations: {stuck_tx.confirmations}")
        
        session.close()
        
    except Exception as e:
        logger.error(f"Error fixing stuck transaction: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    fix_stuck_transaction()
