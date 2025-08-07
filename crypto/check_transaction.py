#!/usr/bin/env python3
"""
Check the details of a specific transaction to see what address it was sent to.
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

from shared.crypto.util import get_coin
from shared.logger import setup_logging

logger = setup_logging()

async def check_transaction_details():
    """Check the details of the specific transaction"""
    
    tx_hash = "44a6c220ce4beabef0e9684fce51832a18db976b0849ce43b19dbff4e58f45c2"
    
    try:
        # Get the BTC coin instance
        btc_coin = get_coin("BTC")
        
        logger.info(f"[CHECK] Checking transaction: {tx_hash}")
        
        # Try to get transaction details
        try:
            tx_data = await btc_coin.get_tx(tx_hash)
            logger.info(f"[CHECK] Transaction data: {tx_data}")
            
            # Extract addresses from transaction
            if 'vout' in tx_data:
                logger.info(f"[CHECK] Transaction outputs:")
                for i, output in enumerate(tx_data.get('vout', [])):
                    if 'scriptPubKey' in output and 'addresses' in output['scriptPubKey']:
                        addresses = output['scriptPubKey']['addresses']
                        value = output.get('value', 0)
                        logger.info(f"[CHECK] Output {i}: {addresses} - {value} BTC")
            
            if 'vin' in tx_data:
                logger.info(f"[CHECK] Transaction inputs:")
                for i, input_tx in enumerate(tx_data.get('vin', [])):
                    if 'prevout' in input_tx and 'scriptPubKey' in input_tx['prevout']:
                        addresses = input_tx['prevout']['scriptPubKey'].get('addresses', [])
                        value = input_tx['prevout'].get('value', 0)
                        logger.info(f"[CHECK] Input {i}: {addresses} - {value} BTC")
                        
        except Exception as e:
            logger.error(f"[CHECK] Error getting transaction details: {e}")
            
            # Try alternative method - get address history
            logger.info(f"[CHECK] Trying alternative method...")
            
            # Check if the transaction is in the address history
            monitored_address = "mwVbGCPf4MNfhKXftq3627DXtqqTcUQ5u3"
            logger.info(f"[CHECK] Checking if transaction is in address history for: {monitored_address}")
            
            try:
                address_history = await btc_coin.server.getaddresshistory(monitored_address)
                logger.info(f"[CHECK] Address history: {address_history}")
                
                # Check if our transaction is in the history
                tx_found = False
                for tx_info in address_history:
                    if tx_info.get('tx_hash') == tx_hash:
                        tx_found = True
                        logger.info(f"[CHECK] ✅ Transaction found in address history!")
                        logger.info(f"[CHECK] Transaction info: {tx_info}")
                        break
                
                if not tx_found:
                    logger.warning(f"[CHECK] ❌ Transaction NOT found in address history")
                    logger.warning(f"[CHECK] This means the transaction was not sent to the monitored address")
                    
            except Exception as e2:
                logger.error(f"[CHECK] Error getting address history: {e2}")
        
    except Exception as e:
        logger.error(f"[CHECK] Error: {e}")
        import traceback
        logger.error(f"[CHECK] Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("[CHECK] Starting transaction check...")
    asyncio.run(check_transaction_details())
    logger.info("[CHECK] Transaction check completed!") 