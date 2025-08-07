#!/usr/bin/env python3
"""
Bitcart SDK-based worker for real-time transaction monitoring.
Based on https://sdk.bitcart.ai/en/latest/
"""

import asyncio
import sys
import os
from typing import Dict, List
from decimal import Decimal

# Add the current directory to Python path
sys.path.append('/app')

from bitcart import BTC, LTC, BCH, ETH, BNB, MATIC, TRX, XMR
from shared.logger import setup_logging
from db.wallet import CryptoAddress, Transaction, TransactionType, TransactionStatus
from db.connection import get_session
from sqlalchemy.orm import Session

logger = setup_logging()

class BitcartWorker:
    """Worker using Bitcart SDK for real-time transaction monitoring"""
    
    def __init__(self):
        self.coins = {}
        self.session = None
        self.setup_database()
    
    def setup_database(self):
        """Setup database connection"""
        try:
            self.session = get_session()
            logger.info("[WORKER] Database connection established")
        except Exception as e:
            logger.error(f"[WORKER] Database connection failed: {e}")
    
    async def load_addresses(self) -> Dict[str, List[str]]:
        """Load all crypto addresses from database"""
        try:
            addresses = {}
            crypto_addresses = self.session.query(CryptoAddress).filter_by(is_active=True).all()
            
            for addr in crypto_addresses:
                currency = addr.currency_code.upper()
                if currency not in addresses:
                    addresses[currency] = []
                addresses[currency].append(addr.address)
            
            logger.info(f"[WORKER] Loaded addresses: {addresses}")
            return addresses
        except Exception as e:
            logger.error(f"[WORKER] Error loading addresses: {e}")
            return {}
    
    def get_coin_instance(self, currency: str):
        """Get Bitcart coin instance based on currency"""
        currency_map = {
            'BTC': BTC,
            'LTC': LTC,
            'BCH': BCH,
            'ETH': ETH,
            'BNB': BNB,
            'MATIC': MATIC,
            'TRX': TRX,
            'XMR': XMR
        }
        
        coin_class = currency_map.get(currency.upper())
        if not coin_class:
            logger.warning(f"[WORKER] Unsupported currency: {currency}")
            return None
        
        return coin_class
    
    async def setup_coin_monitoring(self, currency: str, addresses: List[str]):
        """Setup monitoring for a specific coin"""
        try:
            coin_class = self.get_coin_instance(currency)
            if not coin_class:
                return
            
            # Create coin instance with first address as xpub
            # Note: In a real implementation, you'd need to derive xpub from addresses
            # For now, we'll use the first address as a placeholder
            if addresses:
                xpub = addresses[0]  # This should be an actual xpub in production
                
                coin = coin_class(xpub=xpub)
                
                # Register event handlers
                @coin.on("new_transaction")
                async def handle_new_transaction(event, tx):
                    await self.process_new_transaction(currency, tx)
                
                @coin.on("new_block")
                async def handle_new_block(event, height):
                    await self.process_new_block(currency, height)
                
                self.coins[currency] = coin
                logger.info(f"[WORKER] Setup monitoring for {currency} with {len(addresses)} addresses")
                
        except Exception as e:
            logger.error(f"[WORKER] Error setting up {currency} monitoring: {e}")
    
    async def process_new_transaction(self, currency: str, tx_hash: str):
        """Process new transaction event"""
        try:
            logger.info(f"[WORKER] New transaction detected: {currency} - {tx_hash}")
            
            # Get coin instance
            coin = self.coins.get(currency)
            if not coin:
                logger.warning(f"[WORKER] No coin instance found for {currency}")
                return
            
            # Get transaction details
            try:
                tx_data = await coin.get_tx(tx_hash)
                logger.info(f"[WORKER] Transaction data: {tx_data}")
                
                # Process transaction
                await self.save_transaction_to_db(currency, tx_hash, tx_data)
                
            except Exception as e:
                if "verbose transactions are currently unsupported" in str(e):
                    logger.info(f"[WORKER] Skipping verbose transaction {tx_hash} for {currency}")
                    # Use alternative method for BTC
                    await self.process_transaction_alternative(currency, tx_hash)
                else:
                    logger.error(f"[WORKER] Error getting transaction {tx_hash}: {e}")
                    
        except Exception as e:
            logger.error(f"[WORKER] Error processing new transaction: {e}")
    
    async def process_transaction_alternative(self, currency: str, tx_hash: str):
        """Process transaction using alternative method for BTC"""
        try:
            logger.info(f"[WORKER] Processing transaction {tx_hash} using alternative method")
            
            # Create minimal transaction data
            tx_data = {
                'txid': tx_hash,
                'confirmations': 1,
                'amount': 0,  # Will be updated when we get real data
                'to_address': '',
                'from_address': ''
            }
            
            await self.save_transaction_to_db(currency, tx_hash, tx_data)
            
        except Exception as e:
            logger.error(f"[WORKER] Error in alternative transaction processing: {e}")
    
    async def save_transaction_to_db(self, currency: str, tx_hash: str, tx_data: dict):
        """Save transaction to database"""
        try:
            # Check if transaction already exists
            existing_tx = self.session.query(Transaction).filter_by(blockchain_txid=tx_hash).first()
            if existing_tx:
                logger.info(f"[WORKER] Transaction {tx_hash} already exists in database")
                return
            
            # Get address for this transaction
            address = self.get_address_for_transaction(currency, tx_hash)
            if not address:
                logger.warning(f"[WORKER] No address found for transaction {tx_hash}")
                return
            
            # Create new transaction
            transaction = Transaction(
                account_id=address.account.id,
                amount=tx_data.get('amount', 0),
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                address=address.address,
                blockchain_txid=tx_hash,
                confirmations=tx_data.get('confirmations', 1),
                required_confirmations=6,
                description=f"Deposit to {address.address}",
                metadata_json={
                    'currency': currency,
                    'from_address': tx_data.get('from_address', ''),
                    'to_address': tx_data.get('to_address', ''),
                    'tx_data': tx_data
                }
            )
            
            self.session.add(transaction)
            self.session.commit()
            
            logger.info(f"[WORKER] Successfully saved transaction {tx_hash} to database")
            
        except Exception as e:
            logger.error(f"[WORKER] Error saving transaction to database: {e}")
            self.session.rollback()
    
    def get_address_for_transaction(self, currency: str, tx_hash: str):
        """Get the address associated with this transaction"""
        try:
            # This is a simplified version - in production you'd need to
            # match the transaction to the correct address
            address = self.session.query(CryptoAddress).filter_by(
                currency_code=currency.upper(),
                is_active=True
            ).first()
            
            return address
        except Exception as e:
            logger.error(f"[WORKER] Error getting address for transaction: {e}")
            return None
    
    async def process_new_block(self, currency: str, height: int):
        """Process new block event"""
        try:
            logger.info(f"[WORKER] New block detected: {currency} - {height}")
            
            # Update confirmations for pending transactions
            await self.update_transaction_confirmations(currency)
            
        except Exception as e:
            logger.error(f"[WORKER] Error processing new block: {e}")
    
    async def update_transaction_confirmations(self, currency: str):
        """Update confirmations for pending transactions"""
        try:
            pending_txs = self.session.query(Transaction).filter(
                Transaction.status == TransactionStatus.AWAITING_CONFIRMATION,
                Transaction.metadata_json.contains({'currency': currency})
            ).all()
            
            for tx in pending_txs:
                # Update confirmations based on current block height
                # This is a simplified version
                if tx.confirmations >= tx.required_confirmations:
                    tx.status = TransactionStatus.COMPLETED
                    logger.info(f"[WORKER] Transaction {tx.blockchain_txid} completed")
            
            self.session.commit()
            
        except Exception as e:
            logger.error(f"[WORKER] Error updating confirmations: {e}")
            self.session.rollback()
    
    async def start_monitoring(self):
        """Start monitoring all cryptocurrencies"""
        try:
            logger.info("[WORKER] Starting Bitcart SDK-based monitoring...")
            
            # Load addresses from database
            addresses_by_currency = await self.load_addresses()
            
            if not addresses_by_currency:
                logger.warning("[WORKER] No addresses found in database")
                return
            
            # Setup monitoring for each currency
            for currency, addresses in addresses_by_currency.items():
                await self.setup_coin_monitoring(currency, addresses)
            
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
        finally:
            if self.session:
                self.session.close()

async def main():
    """Main function to start the worker"""
    worker = BitcartWorker()
    await worker.start_monitoring()

if __name__ == "__main__":
    logger.info("[WORKER] Starting Bitcart SDK worker...")
    asyncio.run(main()) 