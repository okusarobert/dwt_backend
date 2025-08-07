#!/usr/bin/env python3
"""
Bitcart SDK Worker for real-time transaction monitoring.
Based on https://sdk.bitcart.ai/en/latest/
"""

import asyncio
import sys
import os
from typing import Dict, List, Optional
from decimal import Decimal

# Add the current directory to Python path
sys.path.append('/app')

from bitcart import BTC
from shared.logger import setup_logging
from shared.crypto.util import get_coin, coin_info
from util import process_deposit_txn, get_all_crypto_addresses
from db.wallet import CryptoAddress

logger = setup_logging()

class BitcartSDKWorker:
    """Bitcart SDK worker for real-time transaction monitoring"""
    
    def __init__(self):
        self.coins = {}
        self.addresses = {}
        self.setup_addresses()
    
    def setup_addresses(self):
        """Setup addresses for monitoring from database"""
        try:
            # Get all addresses from database
            all_addresses = get_all_crypto_addresses()
            logger.info(f"[WORKER] Found addresses: {all_addresses}")
            
            # For now, focus on BTC
            if 'BTC' in all_addresses and all_addresses['BTC']:
                self.addresses['BTC'] = all_addresses['BTC']
                logger.info(f"[WORKER] Setup BTC addresses: {self.addresses['BTC']}")
            else:
                logger.warning("[WORKER] No BTC addresses found in database")
                # Use a default address for testing
                self.addresses['BTC'] = ['msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T']
                logger.info(f"[WORKER] Using default BTC address: {self.addresses['BTC']}")
                
        except Exception as e:
            logger.error(f"[WORKER] Error setting up addresses: {e}")
            # Use a default address for testing
            self.addresses['BTC'] = ['msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T']
            logger.info(f"[WORKER] Using default BTC address due to error: {self.addresses['BTC']}")
    
    async def setup_btc_monitoring(self):
        """Setup BTC monitoring using Bitcart SDK"""
        try:
            if 'BTC' not in self.addresses or not self.addresses['BTC']:
                logger.error("[WORKER] No BTC addresses configured")
                return
            
            # Get the first BTC address for monitoring
            btc_address = self.addresses['BTC'][0]
            logger.info(f"[WORKER] Setting up BTC monitoring for address: {btc_address}")
            
            # Get authentication credentials
            btc_credentials = coin_info("BTC")
            if not btc_credentials:
                logger.error("[WORKER] Could not get BTC credentials")
                return
            
            # Create BTC instance
            # Note: For production, you'd use an xpub instead of individual addresses
            btc = BTC(xpub=btc_address)
            
            # Set the daemon URL and authentication
            btc.server.url = btc_credentials["credentials"]["rpc_url"]
            # Use the same credentials as the existing system
            btc.server.auth = (
                btc_credentials["credentials"]["rpc_user"], 
                btc_credentials["credentials"]["rpc_pass"]
            )
            
            logger.info(f"[WORKER] BTC daemon URL: {btc.server.url}")
            logger.info(f"[WORKER] BTC auth user: {btc_credentials['credentials']['rpc_user']}")
            
            # Register event handlers
            @btc.on("new_transaction")
            async def handle_new_transaction(event, tx):
                await self.process_new_transaction("BTC", tx)
            
            @btc.on("new_block")
            async def handle_new_block(event, height):
                await self.process_new_block("BTC", height)
            
            self.coins['BTC'] = btc
            logger.info(f"[WORKER] ✅ BTC monitoring setup complete")
            
        except Exception as e:
            logger.error(f"[WORKER] Error setting up BTC monitoring: {e}")
            import traceback
            logger.error(f"[WORKER] Traceback: {traceback.format_exc()}")
    
    async def process_new_transaction(self, currency: str, tx_hash: str):
        """Process new transaction event"""
        try:
            logger.info(f"[WORKER] 🎉 NEW TRANSACTION EVENT: {currency} - {tx_hash}")
            
            # Get coin instance
            coin = self.coins.get(currency)
            if not coin:
                logger.warning(f"[WORKER] No coin instance found for {currency}")
                return
            
            # Get transaction details
            try:
                tx_data = await coin.get_tx(tx_hash)
                logger.info(f"[WORKER] Transaction data received for {tx_hash}")
                
                # Process transaction using our existing logic
                await self.process_transaction_with_existing_logic(currency, tx_hash, tx_data)
                
            except Exception as e:
                error_msg = str(e)
                if "verbose transactions are currently unsupported" in error_msg:
                    logger.info(f"[WORKER] Skipping verbose transaction {tx_hash} for {currency}")
                    # Use alternative method for BTC
                    await self.process_transaction_alternative(currency, tx_hash)
                else:
                    logger.error(f"[WORKER] Error getting transaction {tx_hash}: {e}")
                    
        except Exception as e:
            logger.error(f"[WORKER] Error processing new transaction: {e}")
            import traceback
            logger.error(f"[WORKER] Traceback: {traceback.format_exc()}")
    
    async def process_transaction_with_existing_logic(self, currency: str, tx_hash: str, tx_data: dict):
        """Process transaction using our existing logic"""
        try:
            logger.info(f"[WORKER] Processing transaction with existing logic: {tx_hash}")
            
            # Get the address for this currency
            address = self.addresses.get(currency, [None])[0]
            if not address:
                logger.warning(f"[WORKER] No address found for {currency}")
                return
            
            # Use our existing process_deposit_txn function
            process_deposit_txn(tx_hash, tx_data, address, None)
            logger.info(f"[WORKER] ✅ Successfully processed transaction {tx_hash}")
            
        except Exception as e:
            logger.error(f"[WORKER] Error in existing logic processing: {e}")
            import traceback
            logger.error(f"[WORKER] Traceback: {traceback.format_exc()}")
    
    async def process_transaction_alternative(self, currency: str, tx_hash: str):
        """Process transaction using alternative method for BTC"""
        try:
            logger.info(f"[WORKER] Processing transaction {tx_hash} using alternative method")
            
            # Create minimal transaction data
            address = self.addresses.get(currency, [None])[0]
            tx_data = {
                'txid': tx_hash,
                'confirmations': 1,
                'vout': [{'value': 0, 'scriptPubKey': {'addresses': [address]}}],
                'vin': []
            }
            
            await self.process_transaction_with_existing_logic(currency, tx_hash, tx_data)
            
        except Exception as e:
            logger.error(f"[WORKER] Error in alternative transaction processing: {e}")
    
    async def process_new_block(self, currency: str, height: int):
        """Process new block event"""
        try:
            logger.info(f"[WORKER] 🎉 NEW BLOCK EVENT: {currency} - {height}")
            
            # You can add block-specific logic here
            # For example, update confirmations for pending transactions
            
        except Exception as e:
            logger.error(f"[WORKER] Error processing new block: {e}")
    
    async def start_monitoring(self):
        """Start monitoring all cryptocurrencies"""
        try:
            logger.info("[WORKER] 🚀 Starting Bitcart SDK monitoring...")
            
            # Setup BTC monitoring
            await self.setup_btc_monitoring()
            
            if not self.coins:
                logger.warning("[WORKER] No coins configured for monitoring")
                return
            
            # Start polling for all coins
            logger.info("[WORKER] Starting polling for all coins...")
            
            polling_tasks = []
            for currency, coin in self.coins.items():
                task = asyncio.create_task(coin.poll_updates())
                polling_tasks.append(task)
                logger.info(f"[WORKER] Started polling for {currency}")
            
            # Wait for all polling tasks
            await asyncio.gather(*polling_tasks)
            
        except Exception as e:
            logger.error(f"[WORKER] Error in monitoring: {e}")
            import traceback
            logger.error(f"[WORKER] Traceback: {traceback.format_exc()}")

async def main():
    """Main function to start the worker"""
    worker = BitcartSDKWorker()
    await worker.start_monitoring()

if __name__ == "__main__":
    logger.info("[WORKER] Starting Bitcart SDK worker...")
    asyncio.run(main()) 