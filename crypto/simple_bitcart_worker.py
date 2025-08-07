#!/usr/bin/env python3
"""
Simplified Bitcart SDK worker for real-time transaction monitoring.
Based on https://sdk.bitcart.ai/en/latest/
"""

import asyncio
import sys
import os
from typing import Dict, List

# Add the current directory to Python path
sys.path.append('/app')

from bitcart import BTC
from shared.logger import setup_logging
from shared.crypto.util import get_coin
from util import process_deposit_txn
from db.wallet import CryptoAddress

logger = setup_logging()

class SimpleBitcartWorker:
    """Simplified worker using Bitcart SDK for real-time transaction monitoring"""
    
    def __init__(self):
        self.coins = {}
        self.addresses = {}
        self.setup_addresses()
    
    def setup_addresses(self):
        """Setup addresses for monitoring"""
        try:
            # For now, let's use our existing BTC address
            self.addresses['BTC'] = ['mwVbGCPf4MNfhKXftq3627DXtqqTcUQ5u3']
            logger.info(f"[WORKER] Setup addresses: {self.addresses}")
        except Exception as e:
            logger.error(f"[WORKER] Error setting up addresses: {e}")
    
    async def setup_btc_monitoring(self):
        """Setup BTC monitoring using Bitcart SDK"""
        try:
            # Create BTC instance with our address
            # Note: In production, you'd use an xpub instead of individual addresses
            btc_address = self.addresses['BTC'][0]
            
            # Get authentication credentials using the same method as the main system
            from shared.crypto.util import coin_info
            btc_credentials = coin_info("BTC")
            
            if not btc_credentials:
                logger.error("[WORKER] Could not get BTC credentials")
                return
            
            # Create BTC instance with authentication
            btc = BTC(xpub=btc_address)
            
            # Set the daemon URL and authentication using the same credentials
            btc.server.url = btc_credentials["credentials"]["rpc_url"]
            btc.server.auth = (
                btc_credentials["credentials"]["rpc_user"], 
                btc_credentials["credentials"]["rpc_pass"]
            )
            
            logger.info(f"[WORKER] Using BTC credentials: {btc_credentials['credentials']['rpc_url']}")
            logger.info(f"[WORKER] BTC user: {btc_credentials['credentials']['rpc_user']}")
            logger.info(f"[WORKER] BTC pass: {btc_credentials['credentials']['rpc_pass']}")
            
            # Register event handlers
            @btc.on("new_transaction")
            async def handle_new_transaction(event, tx):
                await self.process_new_transaction("BTC", tx)
            
            @btc.on("new_block")
            async def handle_new_block(event, height):
                await self.process_new_block("BTC", height)
            
            self.coins['BTC'] = btc
            logger.info(f"[WORKER] Setup BTC monitoring with address: {btc_address}")
            
        except Exception as e:
            logger.error(f"[WORKER] Error setting up BTC monitoring: {e}")
    
    async def process_new_transaction(self, currency: str, tx_hash: str):
        """Process new transaction event"""
        try:
            logger.info(f"[WORKER] 🎉 NEW TRANSACTION EVENT FIRED: {currency} - {tx_hash}")
            
            # Get coin instance
            coin = self.coins.get(currency)
            if not coin:
                logger.warning(f"[WORKER] No coin instance found for {currency}")
                return
            
            # Get transaction details
            try:
                tx_data = await coin.get_tx(tx_hash)
                logger.info(f"[WORKER] Transaction data: {tx_data}")
                
                # Process transaction using our existing logic
                await self.process_transaction_with_existing_logic(currency, tx_hash, tx_data)
                
            except Exception as e:
                if "verbose transactions are currently unsupported" in str(e):
                    logger.info(f"[WORKER] Skipping verbose transaction {tx_hash} for {currency}")
                    # Use alternative method for BTC
                    await self.process_transaction_alternative(currency, tx_hash)
                else:
                    logger.error(f"[WORKER] Error getting transaction {tx_hash}: {e}")
                    
        except Exception as e:
            logger.error(f"[WORKER] Error processing new transaction: {e}")
    
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
            logger.info(f"[WORKER] Successfully processed transaction {tx_hash}")
            
        except Exception as e:
            logger.error(f"[WORKER] Error in existing logic processing: {e}")
    
    async def process_transaction_alternative(self, currency: str, tx_hash: str):
        """Process transaction using alternative method for BTC"""
        try:
            logger.info(f"[WORKER] Processing transaction {tx_hash} using alternative method")
            
            # Create minimal transaction data
            tx_data = {
                'txid': tx_hash,
                'confirmations': 1,
                'vout': [{'value': 0, 'scriptPubKey': {'addresses': [self.addresses['BTC'][0]]}}],
                'vin': []
            }
            
            await self.process_transaction_with_existing_logic(currency, tx_hash, tx_data)
            
        except Exception as e:
            logger.error(f"[WORKER] Error in alternative transaction processing: {e}")
    
    async def process_new_block(self, currency: str, height: int):
        """Process new block event"""
        try:
            logger.info(f"[WORKER] 🎉 NEW BLOCK EVENT FIRED: {currency} - {height}")
            
            # You can add block-specific logic here
            # For example, update confirmations for pending transactions
            
        except Exception as e:
            logger.error(f"[WORKER] Error processing new block: {e}")
    
    async def start_monitoring(self):
        """Start monitoring all cryptocurrencies"""
        try:
            logger.info("[WORKER] Starting simplified Bitcart SDK monitoring...")
            
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

async def main():
    """Main function to start the worker"""
    worker = SimpleBitcartWorker()
    await worker.start_monitoring()

if __name__ == "__main__":
    logger.info("[WORKER] Starting simplified Bitcart SDK worker...")
    asyncio.run(main()) 