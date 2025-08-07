#!/usr/bin/env python3
"""
Bitcart SDK Service for real-time Bitcoin transaction monitoring.
This service uses the standard Bitcart SDK to connect to the Bitcoin daemon.
"""

import asyncio
import os
import sys
from typing import Dict, List, Optional
from decimal import Decimal

# Add the parent directory to Python path for imports
sys.path.append('/app')

from bitcart import BTC
from shared.logger import setup_logging
from db.wallet import CryptoAddress, Transaction, TransactionType, TransactionStatus
from db.connection import session

logger = setup_logging()

class BitcartSDKService:
    """Bitcart SDK Service for real-time Bitcoin monitoring"""
    
    def __init__(self):
        self.btc = None
        self.addresses = []
        self.session = None
        self.setup_database()
        self.load_addresses()
    
    def setup_database(self):
        """Setup database connection"""
        try:
            self.session = session
            logger.info("[SERVICE] Database connection established")
        except Exception as e:
            logger.error(f"[SERVICE] Database connection failed: {e}")
    
    def load_addresses(self):
        """Load Bitcoin addresses from database"""
        try:
            if not self.session:
                logger.error("[SERVICE] No database session available")
                return
            
            # Get all BTC addresses from database
            addresses = self.session.query(CryptoAddress).filter_by(currency_code='BTC').all()
            self.addresses = [addr.address for addr in addresses]
            logger.info(f"[SERVICE] Loaded {len(self.addresses)} BTC addresses: {self.addresses}")
            
        except Exception as e:
            logger.error(f"[SERVICE] Error loading addresses: {e}")
            # Use default address for testing
            self.addresses = ['msxtM27m4i3iz1jb955uKCRtvggvnF1Z1T']
            logger.info(f"[SERVICE] Using default address: {self.addresses}")
    
    async def setup_btc_connection(self):
        """Setup BTC connection using Bitcart SDK"""
        try:
            # Get environment variables for BTC daemon
            btc_host = os.getenv('BTC_HOST', 'btc')
            btc_port = os.getenv('BTC_PORT', '5000')
            btc_user = os.getenv('BTC_USER', 'okusa')
            btc_pass = os.getenv('BTC_PASS', 'uQa4nq5kkDsjILyiDgxJc4bCVrLnt8NQRWsuHCB27jg')
            
            # Create BTC instance
            self.btc = BTC(xpub=self.addresses[0] if self.addresses else 'default')
            
            # Set daemon URL and authentication
            self.btc.server.url = f"http://{btc_host}:{btc_port}"
            self.btc.server.auth = (btc_user, btc_pass)
            
            logger.info(f"[SERVICE] BTC daemon URL: {self.btc.server.url}")
            logger.info(f"[SERVICE] BTC auth user: {btc_user}")
            
            # Test connection
            try:
                # Use a simple method to test connection
                info = await self.btc.server.getinfo()
                logger.info(f"[SERVICE] ✅ BTC connection successful: {info}")
            except Exception as e:
                logger.error(f"[SERVICE] ❌ BTC connection failed: {e}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[SERVICE] Error setting up BTC connection: {e}")
            return False
    
    async def setup_event_handlers(self):
        """Setup event handlers for real-time updates"""
        try:
            @self.btc.on("new_transaction")
            async def handle_new_transaction(event, tx_hash):
                await self.process_new_transaction(tx_hash)
            
            @self.btc.on("new_block")
            async def handle_new_block(event, height):
                await self.process_new_block(height)
            
            logger.info("[SERVICE] ✅ Event handlers registered")
            
        except Exception as e:
            logger.error(f"[SERVICE] Error setting up event handlers: {e}")
    
    async def process_new_transaction(self, tx_hash: str):
        """Process new transaction event"""
        try:
            logger.info(f"[SERVICE] 🎉 NEW TRANSACTION EVENT: {tx_hash}")
            
            # Get transaction details
            try:
                tx_data = await self.btc.server.get_transaction(tx_hash)
                logger.info(f"[SERVICE] Transaction data received for {tx_hash}")
                
                # Process transaction
                await self.save_transaction_to_db(tx_hash, tx_data)
                
            except Exception as e:
                error_msg = str(e)
                if "verbose transactions are currently unsupported" in error_msg:
                    logger.info(f"[SERVICE] Skipping verbose transaction {tx_hash}")
                    # Create minimal transaction data
                    await self.save_minimal_transaction(tx_hash)
                else:
                    logger.error(f"[SERVICE] Error getting transaction {tx_hash}: {e}")
                    
        except Exception as e:
            logger.error(f"[SERVICE] Error processing new transaction: {e}")
    
    async def process_new_block(self, height: int):
        """Process new block event"""
        try:
            logger.info(f"[SERVICE] 🎉 NEW BLOCK EVENT: {height}")
            
            # Update confirmations for pending transactions
            await self.update_transaction_confirmations(height)
            
        except Exception as e:
            logger.error(f"[SERVICE] Error processing new block: {e}")
    
    async def save_transaction_to_db(self, tx_hash: str, tx_data: dict):
        """Save transaction to database"""
        try:
            if not self.session:
                logger.error("[SERVICE] No database session available")
                return
            
            # Check if transaction already exists
            existing = self.session.query(Transaction).filter_by(blockchain_txid=tx_hash).first()
            if existing:
                logger.info(f"[SERVICE] Transaction {tx_hash} already exists in database")
                return
            
            # Extract transaction details
            amount = tx_data.get('amount', 0)
            confirmations = tx_data.get('confirmations', 0)
            to_address = tx_data.get('to_address', '')
            from_address = tx_data.get('from_address', '')
            
            # Find the address model
            address_model = self.session.query(CryptoAddress).filter_by(address=to_address).first()
            if not address_model:
                logger.warning(f"[SERVICE] No address model found for {to_address}")
                return
            
            # Create new transaction
            transaction = Transaction(
                account_id=address_model.account.id,
                amount=amount,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                address=to_address,
                blockchain_txid=tx_hash,
                confirmations=confirmations,
                required_confirmations=6,
                description=f"Deposit to {to_address}",
                metadata_json={
                    "from_address": from_address,
                    "to_address": to_address,
                    "source": "bitcart_sdk"
                }
            )
            
            self.session.add(transaction)
            self.session.commit()
            logger.info(f"[SERVICE] ✅ Successfully saved transaction {tx_hash}")
            
        except Exception as e:
            logger.error(f"[SERVICE] Error saving transaction to DB: {e}")
            if self.session:
                self.session.rollback()
    
    async def save_minimal_transaction(self, tx_hash: str):
        """Save minimal transaction data when full data is not available"""
        try:
            if not self.session:
                logger.error("[SERVICE] No database session available")
                return
            
            # Check if transaction already exists
            existing = self.session.query(Transaction).filter_by(blockchain_txid=tx_hash).first()
            if existing:
                logger.info(f"[SERVICE] Transaction {tx_hash} already exists in database")
                return
            
            # Use first address as default
            address = self.addresses[0] if self.addresses else 'unknown'
            address_model = self.session.query(CryptoAddress).filter_by(address=address).first()
            if not address_model:
                logger.warning(f"[SERVICE] No address model found for {address}")
                return
            
            # Create minimal transaction
            transaction = Transaction(
                account_id=address_model.account.id,
                amount=0,  # Will be updated when full data is available
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                address=address,
                blockchain_txid=tx_hash,
                confirmations=1,
                required_confirmations=6,
                description=f"Deposit to {address} (minimal data)",
                metadata_json={
                    "from_address": "unknown",
                    "to_address": address,
                    "source": "bitcart_sdk_minimal"
                }
            )
            
            self.session.add(transaction)
            self.session.commit()
            logger.info(f"[SERVICE] ✅ Successfully saved minimal transaction {tx_hash}")
            
        except Exception as e:
            logger.error(f"[SERVICE] Error saving minimal transaction to DB: {e}")
            if self.session:
                self.session.rollback()
    
    async def update_transaction_confirmations(self, current_height: int):
        """Update confirmations for pending transactions"""
        try:
            if not self.session:
                logger.error("[SERVICE] No database session available")
                return
            
            # Get pending transactions
            pending_txns = self.session.query(Transaction).filter_by(
                status=TransactionStatus.AWAITING_CONFIRMATION
            ).all()
            
            for txn in pending_txns:
                # Update confirmations (simplified logic)
                if txn.confirmations < 6:
                    txn.confirmations += 1
                    if txn.confirmations >= txn.required_confirmations:
                        txn.status = TransactionStatus.CONFIRMED
                        logger.info(f"[SERVICE] Transaction {txn.blockchain_txid} confirmed")
            
            self.session.commit()
            logger.info(f"[SERVICE] Updated confirmations for {len(pending_txns)} transactions")
            
        except Exception as e:
            logger.error(f"[SERVICE] Error updating transaction confirmations: {e}")
            if self.session:
                self.session.rollback()
    
    async def start_monitoring(self):
        """Start monitoring Bitcoin transactions"""
        try:
            logger.info("[SERVICE] 🚀 Starting Bitcart SDK monitoring...")
            
            # Setup BTC connection
            if not await self.setup_btc_connection():
                logger.error("[SERVICE] Failed to setup BTC connection")
                return
            
            # Setup event handlers
            await self.setup_event_handlers()
            
            # Start polling for updates
            logger.info("[SERVICE] Starting polling for updates...")
            
            while True:
                try:
                    # Poll for updates
                    await self.btc.poll_updates()
                    await asyncio.sleep(1)  # Small delay between polls
                    
                except Exception as e:
                    logger.error(f"[SERVICE] Error during polling: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
            
        except Exception as e:
            logger.error(f"[SERVICE] Error in monitoring: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown the service"""
        try:
            logger.info("[SERVICE] Shutting down Bitcart SDK service...")
            if self.session:
                self.session.close()
            logger.info("[SERVICE] Service shutdown complete")
        except Exception as e:
            logger.error(f"[SERVICE] Error during shutdown: {e}")

async def main():
    """Main function to start the service"""
    service = BitcartSDKService()
    
    try:
        await service.start_monitoring()
    except KeyboardInterrupt:
        logger.info("[SERVICE] Received interrupt signal")
        await service.shutdown()
    except Exception as e:
        logger.error(f"[SERVICE] Unexpected error: {e}")
        await service.shutdown()

if __name__ == "__main__":
    logger.info("[SERVICE] Starting Bitcart SDK service...")
    asyncio.run(main()) 