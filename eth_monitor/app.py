#!/usr/bin/env python3
"""
Ethereum Transaction Monitor Service
Monitors Ethereum addresses for new transactions using Alchemy WebSocket API
"""

import os
import sys
import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from decimal import Decimal

import websocket
import requests
from sqlalchemy.orm import Session
from decouple import config
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from shared.logger import setup_logging
from db.connection import session
from db.wallet import CryptoAddress, Transaction, Account, PaymentProvider, TransactionType, TransactionStatus, Reservation, ReservationType
from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from shared.currency_precision import AmountConverter
from shared.trading_accounting import TradingAccountingService
from db.accounting import JournalEntry, LedgerTransaction, AccountingAccount
from kafka_consumer import start_ethereum_address_consumer, stop_ethereum_address_consumer
import traceback

logger = setup_logging()


@dataclass
class TransactionEvent:
    """Represents a new transaction event"""
    tx_hash: str
    from_address: str
    to_address: str
    value: Decimal
    block_number: int
    gas_price: int
    gas_used: int
    timestamp: int
    confirmations: int = 0
    status: str = "pending"


class AlchemyWebSocketClient:
    """Alchemy WebSocket client for real-time transaction monitoring"""
    
    def __init__(self, api_key: str, network: str = "mainnet"):
        self.api_key = api_key
        self.network = network
        self.ws_url = self._get_websocket_url()
        self.ws = None
        self.is_connected = False
        self.is_running = False
        self.monitored_addresses: Set[str] = set()
        self.eth_config = EthereumConfig.mainnet(api_key) if network == "mainnet" else EthereumConfig.testnet(api_key)
        
        # ETH transfer polling configuration
        self.eth_polling_enabled = True
        self.eth_polling_interval = 300  # 5 minutes in seconds
        self.eth_polling_block_range = 200  # Number of blocks to scan in each cycle
        
        # Performance tuning for non-blocking operation
        self.max_scan_time_per_block = 5  # Maximum 5 seconds per block (reduced for responsiveness)
        self.max_total_scan_time = 30  # Maximum 30 seconds for 200 blocks (reduced for responsiveness)
        self.max_initial_scan_time = 120  # Maximum 2 minutes for initial scan (reduced for responsiveness)
        self.block_scan_delay = 0.01  # Delay between block scans (reduced for responsiveness)
        
        # Load ERC20 token configuration from environment variable
        contracts_env = os.getenv('ETH_ERC20_CONTRACTS', '{}')
        try:
            contracts_config = json.loads(contracts_env)
            self.erc20_tokens = {}
            
            for symbol, token_info in contracts_config.items():
                contract_address = token_info.get('address', '').lower()
                if contract_address:
                    self.erc20_tokens[contract_address] = {
                        "symbol": symbol,
                        "name": f"{symbol} Token",
                        "decimals": token_info.get('decimals', 18),
                        "smallest_unit": "units"
                    }
            
            logger.info(f"📋 Loaded {len(self.erc20_tokens)} ERC20 tokens from environment: {list(self.erc20_tokens.keys())}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"⚠️ Failed to parse ETH_ERC20_CONTRACTS environment variable: {e}")
            logger.warning("⚠️ Using default ERC20 token configuration")
            # Fallback to default configuration
            self.erc20_tokens = {
                # USDC on Ethereum mainnet
                "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": {
                    "symbol": "USDC",
                    "name": "USD Coin",
                    "decimals": 6,
                    "smallest_unit": "units"
                },
                # USDT on Ethereum mainnet
                "0xdac17f958d2ee523a2206206994597c13d831ec7": {
                    "symbol": "USDT",
                    "name": "Tether USD",
                    "decimals": 6,
                    "smallest_unit": "units"
                }
            }
        
        logger.info(f"🔧 Initialized Alchemy WebSocket client for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
        logger.info(f"🔄 ETH transfer polling: {'enabled' if self.eth_polling_enabled else 'disabled'}")
        logger.info(f"⏱️  Polling interval: {self.eth_polling_interval} seconds")
        logger.info(f"📦 Block range per cycle: {self.eth_polling_block_range} blocks")
        logger.info(f"⚡ Performance tuning: max {self.max_scan_time_per_block}s/block, {self.max_total_scan_time}s total, {self.block_scan_delay}s delay")
    
    def _get_websocket_url(self) -> str:
        """Get WebSocket URL based on network"""
        if self.network == "mainnet":
            return f"wss://eth-mainnet.g.alchemy.com/v2/{self.api_key}"
        elif self.network == "sepolia":
            return f"wss://eth-sepolia.g.alchemy.com/v2/{self.api_key}"
        elif self.network == "holesky":
            return f"wss://eth-holesky.g.alchemy.com/v2/{self.api_key}"
        else:
            raise ValueError(f"Unsupported network: {self.network}")
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Handle subscription confirmation
            if "id" in data and "result" in data:
                subscription_id = data["result"]
                logger.info(f"✅ Subscription confirmed: {subscription_id}")
                return
            
            # Handle new transaction notifications
            if "method" in data and data["method"] == "eth_subscription":
                params = data.get("params", {})
                subscription = params.get("subscription")
                result = params.get("result")
                
                if result:
                    # Check if this is a block event or transaction event
                    if isinstance(result, dict) and "number" in result:
                        # This is a block event
                        self._handle_new_block(result)
                    else:
                        # This is a transaction event
                        logger.info(f"New transaction event: {result}")
                        self._handle_new_transaction(result)
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse WebSocket message: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling WebSocket message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.error(f"❌ WebSocket error: {error}")
        self.is_connected = False
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info(f"🔌 WebSocket connection closed: {close_status_code} - {close_msg}")
        self.is_connected = False
    
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.info("🔌 WebSocket connection established!")
        self.is_connected = True
        self._subscribe_to_addresses()
    
    def _subscribe_to_addresses(self):
        """Subscribe to monitored addresses and blocks"""
        # Subscribe to blocks for confirmation tracking
        self._subscribe_to_blocks()
        
        if not self.monitored_addresses:
            logger.warning("⚠️ No addresses to monitor")
            return
        
        for address in self.monitored_addresses:
            self._subscribe_to_address(address)
    
    def _subscribe_to_address(self, address: str):
        """Subscribe to a specific address for both incoming and outgoing transactions"""
        # Subscribe to pending transactions TO this address
        to_subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": [
                "alchemy_pendingTransactions",
                {
                    "toAddress": address
                }
            ]
        }
        
        # Subscribe to pending transactions FROM this address
        from_subscription = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "eth_subscribe",
            "params": [
                "alchemy_pendingTransactions",
                {
                    "fromAddress": address
                }
            ]
        }
        
        if self.ws and self.is_connected:
            self.ws.send(json.dumps(to_subscription))
            self.ws.send(json.dumps(from_subscription))
            logger.info(f"📡 Subscribed to address (incoming & outgoing): {address}")
    
    def _subscribe_to_blocks(self):
        """Subscribe to new blocks"""
        block_subscription = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "eth_subscribe",
            "params": ["newHeads"]
        }
        
        if self.ws and self.is_connected:
            self.ws.send(json.dumps(block_subscription))
            logger.info(f"📡 Subscribed to new blocks")
    
    def _handle_new_transaction(self, tx_data: Dict):
        """Handle new transaction data"""
        try:
            # Extract transaction details
            # logger.info(f"💰 New transaction event: {tx_data}")
            # sys.exit(0)
            tx_hash = tx_data.get("hash")
            from_address = tx_data.get("from", "").lower()
            to_address = tx_data.get("to", "").lower()
            value = int(tx_data.get("value", "0"), 16)
            block_number = int(tx_data.get("blockNumber", "0"), 16)
            gas_price = int(tx_data.get("gasPrice", "0"), 16)
            gas_used = int(tx_data.get("gas", "0"), 16)
            timestamp = int(tx_data.get("timestamp", "0"), 16)
            input_data = tx_data.get("input", "")
            
            # Check if this is an ERC20 transfer (has input data and value is 0)
            is_erc20 = input_data and input_data != "0x" and value == 0

            if is_erc20:
                logger.info(f"🔍 Processing ERC20 transfer {tx_hash} via WebSocket")
            else:
                logger.info(f"🔍 Processing ETH transfer {tx_hash} via WebSocket")
            
            # Convert value from wei to ETH (only for native ETH transfers)
            value_eth = Decimal(value) / Decimal(10**18)
            
            # Check if this transaction involves our monitored addresses
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            
            if (from_address in monitored_addresses_lower or 
                to_address in monitored_addresses_lower):
                
                if is_erc20:
                    # Handle ERC20 transfers immediately via WebSocket
                    logger.info(f"🔍 Processing ERC20 transfer {tx_hash} via WebSocket")
                    self._handle_erc20_transaction(tx_data)
                    return
                
                # Only process native ETH transfers (no input data or value > 0)
                if input_data and input_data != "0x":
                    logger.info(f"⏭️ Skipping contract call {tx_hash} - not a native ETH transfer")
                    return
                
                event = TransactionEvent(
                    tx_hash=tx_hash,
                    from_address=from_address,
                    to_address=to_address,
                    value=value_eth,
                    block_number=block_number,
                    gas_price=gas_price,
                    gas_used=gas_used,
                    timestamp=timestamp
                )
                
                logger.info(f"💰 New ETH transaction detected: {tx_hash}")
                logger.info(f"   From: {from_address}")
                logger.info(f"   To: {to_address}")
                logger.info(f"   Value: {value_eth} ETH")
                
                # Process the transaction synchronously to avoid async issues
                # We'll run it in a thread to avoid blocking the WebSocket
                import threading
                thread = threading.Thread(target=self._process_transaction_sync, args=(event,))
                thread.daemon = True
                thread.start()
            
        except Exception as e:
            logger.error(f"❌ Error handling new transaction: {e}")
    
    def _handle_new_block(self, block_data: Dict):
        """Handle new block data for confirmation tracking only"""
        try:
            block_number = int(block_data.get("number", "0"), 16)
            logger.info(f"🔄 New block: {block_number}")
            
            # Process confirmations for all pending transactions
            self._process_block_confirmations_sync(block_number)

            # Detect ERC-20 deposits using Alchemy Transfers API (with lookback)
            try:
                # Look back a window to catch missed logs
                lookback = 0
                try:
                    lookback = int(os.getenv('ETH_LOG_LOOKBACK_BLOCKS', '200'))
                except Exception:
                    lookback = 200
                from_block = max(0, block_number - lookback)
                self._scan_erc20_transfers_via_transfers_api(from_block, block_number)
            except Exception as scan_err:
                logger.error(f"Error scanning ERC20 logs for block {block_number}: {scan_err}")
            
            # NOTE: Removed _check_block_for_transactions_sync to prevent duplicate processing
            # New transactions are detected via WebSocket pending events only
            
        except Exception as e:
            logger.error(f"❌ Error handling new block: {e}")
    
    async def _process_transaction(self, event: TransactionEvent):
        """Process a new transaction event"""
        try:
            # Check if transaction already exists
            if await self._is_transaction_processed(event.tx_hash):
                logger.info(f"⏭️ Transaction {event.tx_hash} already processed")
                return
            
            # Get the crypto address record
            crypto_address = self._get_crypto_address(event.to_address)
            if not crypto_address:
                logger.warning(f"⚠️ No crypto address found for: {event.to_address}")
                return
            
            # Create transaction record
            await self._create_transaction_record(event, crypto_address)
            
            # Update account balance
            await self._update_account_balance(crypto_address.account_id, event.value)
            
            # Send notification (you can integrate with your notification system)
            await self._send_notification(event, crypto_address)
            
            logger.info(f"✅ Transaction {event.tx_hash} processed successfully")
            
        except Exception as e:
            logger.error(f"❌ Error processing transaction {event.tx_hash}: {e}")
    
    async def _is_transaction_processed(self, tx_hash: str) -> bool:
        """Check if transaction has already been processed"""
        try:
            existing_tx = session.query(Transaction).filter_by(
                blockchain_txid=tx_hash
            ).first()
            return existing_tx is not None
        except Exception as e:
            logger.error(f"❌ Error checking transaction status: {e}")
            return False
    
    def _get_crypto_address(self, address: str) -> Optional[CryptoAddress]:
        """Get crypto address record from database (case-insensitive)"""
        try:
            # Use case-insensitive lookup
            return session.query(CryptoAddress).filter(
                CryptoAddress.address.ilike(address),
                CryptoAddress.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"❌ Error getting crypto address: {e}")
            return None
    
    async def _create_transaction_record(self, event: TransactionEvent, crypto_address: CryptoAddress):
        """Create a new transaction record"""
        try:
            # Determine transaction type
            tx_type = TransactionType.DEPOSIT if event.to_address.lower() in self.monitored_addresses else TransactionType.TRANSFER
            
            # Create transaction
            transaction = Transaction(
                account_id=crypto_address.account_id,
                reference_id=event.tx_hash,
                amount=float(event.value),
                type=tx_type,
                provider=PaymentProvider.CRYPTO,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                description=f"Ethereum transaction {event.tx_hash[:8]}...",
                blockchain_txid=event.tx_hash,
                confirmations=event.confirmations,
                required_confirmations=12,  # Ethereum typically needs 12 confirmations
                address=event.to_address,
                metadata_json={
                    "from_address": event.from_address,
                    "to_address": event.to_address,
                    "block_number": event.block_number,
                    "gas_price": event.gas_price,
                    "gas_used": event.gas_used,
                    "timestamp": event.timestamp,
                    "value_wei": str(int(event.value * 10**18))
                }
            )
            
            session.add(transaction)
            session.commit()
            
            logger.info(f"💾 Created transaction record for {event.tx_hash}")
            
        except Exception as e:
            logger.error(f"❌ Error creating transaction record: {e}")
            session.rollback()
    
    async def _update_account_balance(self, account_id: int, amount: Decimal):
        """Update account balance"""
        try:
            account = session.query(Account).filter_by(id=account_id).first()
            if account:
                account.balance += float(amount)
                session.commit()
                logger.info(f"💰 Updated balance for account {account_id}: +{amount} ETH")
        except Exception as e:
            logger.error(f"❌ Error updating account balance: {e}")
            session.rollback()
    
    async def _send_notification(self, event: TransactionEvent, crypto_address: CryptoAddress):
        """Send notification about new transaction"""
        try:
            # You can integrate with your notification system here
            # For example, send to Kafka, WebSocket, or email
            notification_data = {
                "type": "new_ethereum_transaction",
                "account_id": crypto_address.account_id,
                "address": crypto_address.address,
                "tx_hash": event.tx_hash,
                "amount": str(event.value),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📢 Notification sent for transaction {event.tx_hash}")
            
        except Exception as e:
            logger.error(f"❌ Error sending notification: {e}")
    
    def _process_transaction_sync(self, event: TransactionEvent):
        """Process transaction synchronously in a separate thread"""
        try:
            # Determine if this is an incoming or outgoing transaction
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            is_incoming = event.to_address.lower() in monitored_addresses_lower
            is_outgoing = event.from_address.lower() in monitored_addresses_lower
            
            logger.info(f"   Processing transaction {event.tx_hash}")
            logger.info(f"   From: {event.from_address}")
            logger.info(f"   To: {event.to_address}")
            logger.info(f"   Is incoming: {is_incoming}")
            logger.info(f"   Is outgoing: {is_outgoing}")
            
            # Handle internal transfers (both addresses are monitored)
            if is_incoming and is_outgoing:
                logger.info(f"🔄 Internal transfer detected: {event.tx_hash}")
                
                # Process as outgoing (WITHDRAWAL) for sender
                sender_crypto_address = self._get_crypto_address(event.from_address.lower())
                if sender_crypto_address:
                    self._create_transaction_record_sync(event, sender_crypto_address, is_withdrawal=True)
                    self._send_notification_sync(event, sender_crypto_address)
                else:
                    logger.warning(f"⚠️ No crypto address found for sender: {event.from_address}")
                
                # Process as incoming (DEPOSIT) for recipient
                recipient_crypto_address = self._get_crypto_address(event.to_address.lower())
                if recipient_crypto_address:
                    self._create_transaction_record_sync(event, recipient_crypto_address, is_withdrawal=False)
                    self._send_notification_sync(event, recipient_crypto_address)
                else:
                    logger.warning(f"⚠️ No crypto address found for recipient: {event.to_address}")
                
                return
            
            # Handle external transactions (only one address is monitored)
            if is_incoming:
                logger.info(f"📥 Incoming transaction {event.tx_hash} to {event.to_address}")
                # For incoming transactions: look up the to_address
                crypto_address = self._get_crypto_address(event.to_address.lower())
                if not crypto_address:
                    logger.warning(f"⚠️ No crypto address found for incoming transaction to: {event.to_address}")
                    return
                
                # Create transaction record and lock amount
                self._create_transaction_record_sync(event, crypto_address, is_withdrawal=False)
                    
            elif is_outgoing:
                logger.info(f"📤 Outgoing transaction {event.tx_hash} from {event.from_address}")
                # For outgoing transactions: look up the from_address
                crypto_address = self._get_crypto_address(event.from_address.lower())
                if not crypto_address:
                    logger.warning(f"⚠️ No crypto address found for outgoing transaction from: {event.from_address}")
                    return
                
                # Create transaction record and lock amount
                self._create_transaction_record_sync(event, crypto_address, is_withdrawal=True)
            else:
                logger.warning(f"⚠️ Transaction {event.tx_hash} doesn't involve monitored addresses")
                return
            
            # Send notification
            self._send_notification_sync(event, crypto_address)
            
            logger.info(f"✅ Transaction {event.tx_hash} processed successfully")
            logger.info(f"   Type: {'Incoming' if is_incoming else 'Outgoing'}")
            logger.info(f"   Amount locked: {event.value} ETH")
            logger.info(f"   Awaiting 15 confirmations via real-time block events...")
            
        except Exception as e:
            logger.error(f"❌ Error processing transaction {event.tx_hash}: {e}")
        finally:
            # Prevent long-lived sessions that can lock tables
            try:
                session.remove()
            except Exception:
                pass
    
    def _is_transaction_processed_sync(self, tx_hash: str, address: str = None, tx_type: TransactionType = TransactionType.DEPOSIT) -> bool:
        """Check if transaction has already been processed for a specific address (synchronous)"""
        try:
            if address:
                # Check if this specific address already has a transaction record for this hash
                existing_tx = session.query(Transaction).filter_by(
                    blockchain_txid=tx_hash,
                    address=address,
                    type=tx_type
                ).first()
                return existing_tx is not None
            # else:
            #     # Check if any transaction with this hash exists (for general duplicate detection)
            #     existing_tx = session.query(Transaction).filter_by(
            #         blockchain_txid=tx_hash
            #     ).first()
            #     return existing_tx is not None
        except Exception as e:
            logger.error(f"❌ Error checking transaction status: {e}")
            return False
    
    def _create_transaction_record_sync(self, event: TransactionEvent, crypto_address: CryptoAddress, is_withdrawal: bool = False):
        """Create a new transaction record and lock the amount (synchronous)"""
        try:
            # Determine transaction type based on is_withdrawal parameter or by checking addresses
            if is_withdrawal:
                tx_type = TransactionType.WITHDRAWAL
                address_field = event.from_address.lower()
            else:
                # Determine if this is an incoming or outgoing transaction
                monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
                is_incoming = event.to_address.lower() in monitored_addresses_lower
                is_outgoing = event.from_address.lower() in monitored_addresses_lower
                
                if is_incoming:
                    tx_type = TransactionType.DEPOSIT
                    address_field = event.to_address.lower()
                elif is_outgoing:
                    tx_type = TransactionType.WITHDRAWAL
                    address_field = event.from_address.lower()
                else:
                    tx_type = TransactionType.TRANSFER
                    address_field = event.to_address.lower()
            
            # Check for existing transaction first (with session refresh to avoid stale data)
            session.flush()  # Ensure any pending changes are flushed
            existing_tx = session.query(Transaction).filter_by(
                blockchain_txid=event.tx_hash,
                address=address_field,
                type=tx_type
            ).first()
            
            if existing_tx:
                logger.info(f"⏭️ Transaction {event.tx_hash} already exists for {address_field} ({tx_type})")
                return
            
            # Convert amount to smallest units (wei) using unified converter
            amount_wei = AmountConverter.to_smallest_units(event.value, "ETH")

            logger.info(f"Creating unified transaction record:")
            logger.info(f"   Type: {tx_type}")
            logger.info(f"   Address: {address_field}")
            logger.info(f"   Account: {crypto_address.account_id}")
            logger.info(f"   Amount: {AmountConverter.format_display_amount(amount_wei, 'ETH')}")
            
            # Create transaction record with unified amount system
            transaction = Transaction(
                account_id=crypto_address.account_id,
                reference_id=event.tx_hash,
                amount=float(event.value),  # Keep for backward compatibility
                amount_smallest_unit=amount_wei,  # Unified field
                type=tx_type,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                description=f"Ethereum transaction {event.tx_hash[:8]}...",
                blockchain_txid=event.tx_hash,
                confirmations=event.confirmations,
                required_confirmations=15,
                address=address_field,
                provider=PaymentProvider.CRYPTO,
                metadata_json={
                    "from_address": event.from_address,
                    "to_address": event.to_address,
                    "block_number": event.block_number,
                    "gas_price": event.gas_price,
                    "gas_used": event.gas_used,
                    "timestamp": event.timestamp,
                    "value_wei": str(amount_wei),
                    "amount_eth": str(event.value),
                    "currency": "ETH",  # Store currency in metadata
                    "unified_system": True
                }
            )
            
            session.add(transaction)
            
            # Create accounting journal entry
            try:
                accounting_service = TradingAccountingService(session)
                self._create_accounting_entry(transaction, event, crypto_address, accounting_service, tx_type == TransactionType.WITHDRAWAL)
            except Exception as e:
                logger.error(f"⚠️ Failed to create accounting entry: {e}")
            
            # Lock the amount by creating a reservation
            self._create_reservation_sync(crypto_address.account_id, amount_wei, event.tx_hash)
            
            try:
                session.commit()
                logger.info(f"💾 Created unified transaction record with accounting for {event.tx_hash}")
                logger.info(f"   Type: {tx_type}")
                logger.info(f"   Amount: {AmountConverter.format_display_amount(amount_wei, 'ETH')}")
                logger.info(f"   Account: {crypto_address.account_id}")
                
                # Notify via Kafka
                self._send_transaction_notification(transaction)
                
            except Exception as e:
                session.rollback()
                logger.error(f"❌ Failed to save unified transaction: {e}")
                
                # Check if this is a duplicate key error (unique constraint violation)
                error_str = str(e).lower()
                if any(phrase in error_str for phrase in [
                    "duplicate key", 
                    "unique constraint", 
                    "uq_transaction_blockchain_txid_address_type"
                ]):
                    logger.info(f"⏭️ Transaction {event.tx_hash} was already created by another process for {address_field} ({tx_type})")
                    return
                else:
                    # Re-raise if it's not a duplicate error
                    raise
            
        except Exception as e:
            logger.error(f"❌ Error creating transaction record: {e}")
            session.rollback()
    
    def _create_accounting_entry(self, transaction: Transaction, event, crypto_address: CryptoAddress, accounting_service: TradingAccountingService, is_withdrawal: bool):
        """Create accounting journal entry for the transaction"""
        try:
            # Get or create crypto asset account
            crypto_account_name = f"Crypto Assets - ETH"
            crypto_account = accounting_service.get_account_by_name(crypto_account_name)
            
            if not crypto_account:
                logger.warning(f"⚠️ Crypto asset account not found: {crypto_account_name}")
                return
            
            # Create journal entry description
            direction = "withdrawal" if is_withdrawal else "deposit"
            amount_display = AmountConverter.format_display_amount(transaction.amount_smallest_unit, "ETH")
            description = f"ETH {direction} - {amount_display} (TX: {event.tx_hash[:8]}...)"
            
            # Create journal entry
            journal_entry = JournalEntry(description=description)
            session.add(journal_entry)
            session.flush()  # Get ID
            
            # Create ledger transactions based on direction
            if is_withdrawal:
                # Debit: Pending settlements (liability), Credit: Crypto assets
                pending_account = accounting_service.get_account_by_name("Pending Trade Settlements")
                if pending_account:
                    # Debit pending settlements
                    debit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=pending_account.id,
                        debit_smallest_unit=transaction.amount_smallest_unit,
                        credit_smallest_unit=0
                    )
                    session.add(debit_tx)
                    
                    # Credit crypto assets
                    credit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=crypto_account.id,
                        debit_smallest_unit=0,
                        credit_smallest_unit=transaction.amount_smallest_unit
                    )
                    session.add(credit_tx)
            else:
                # Deposit: Debit crypto assets, Credit pending settlements
                pending_account = accounting_service.get_account_by_name("Pending Trade Settlements")
                if pending_account:
                    # Debit crypto assets
                    debit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=crypto_account.id,
                        debit_smallest_unit=transaction.amount_smallest_unit,
                        credit_smallest_unit=0
                    )
                    session.add(debit_tx)
                    
                    # Credit pending settlements
                    credit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=pending_account.id,
                        debit_smallest_unit=0,
                        credit_smallest_unit=transaction.amount_smallest_unit
                    )
                    session.add(credit_tx)
            
            # Link transaction to journal entry
            transaction.journal_entry_id = journal_entry.id
            
            logger.info(f"📊 Created accounting entry: {description}")
            
        except Exception as e:
            logger.error(f"❌ Error creating accounting entry: {e}")
            raise
    
    def _create_reservation_sync(self, account_id: int, amount_wei: int, tx_hash: str):
        """Create a reservation to lock the amount (synchronous)"""
        try:
            account = session.query(Account).filter_by(id=account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            # Update locked amount in smallest units
            current_locked = account.crypto_locked_amount_smallest_unit or 0
            new_locked = current_locked + amount_wei
            account.crypto_locked_amount_smallest_unit = new_locked
            
            # Create reservation record with a unique reference that doesn't depend on tx_hash
            import time
            reservation_reference = f"eth_monitor_{int(time.time() * 1000)}_{tx_hash[:8]}"
            
            reservation = Reservation(
                user_id=account.user_id,
                reference=reservation_reference,
                amount=float(CryptoPrecisionManager.from_smallest_unit(amount_wei, "ETH")),
                type=ReservationType.RESERVE,
                status="active"
            )
            
            session.add(reservation)
            
            logger.info(f"🔒 Created reservation for {amount_wei:,} wei (ref: {reservation_reference})")
            
        except Exception as e:
            logger.error(f"❌ Error creating reservation: {e}")
            raise
    
    def _update_account_balance_sync(self, account_id: int, amount: Decimal):
        """Update account balance (synchronous) - now handles credit after confirmations"""
        try:
            account = session.query(Account).filter_by(id=account_id).first()
            if not account:
                logger.warning(f"⚠️ Account {account_id} not found")
                return
            
            # Convert amount to smallest units
            amount_wei = CryptoPrecisionManager.to_smallest_unit(amount, "ETH")
            
            # Update balance in smallest units
            current_balance = account.crypto_balance_smallest_unit or 0
            new_balance = current_balance + amount_wei
            account.crypto_balance_smallest_unit = new_balance
            
            # Convert back to ETH for logging
            amount_eth = CryptoPrecisionManager.from_smallest_unit(amount_wei, "ETH")
            
            logger.info(f"💰 Credited account {account_id}: +{amount_eth} ETH ({amount_wei:,} wei)")
            
        except Exception as e:
            logger.error(f"❌ Error updating account balance: {e}")
            raise
    
    def _send_notification_sync(self, event: TransactionEvent, crypto_address: CryptoAddress):
        """Send notification (synchronous)"""
        try:
            # You can integrate with your notification system here
            # For now, just log the notification
            logger.info(f"📢 Notification: New transaction {event.tx_hash} for address {crypto_address.address}")
            logger.info(f"   Amount: {event.value} ETH")
            logger.info(f"   Account: {crypto_address.account_id}")
        except Exception as e:
            logger.error(f"❌ Error sending notification: {e}")
    
    def _process_confirmed_transaction_sync(self, tx_hash: str, tx_type: TransactionType = TransactionType.DEPOSIT):
        """Process a transaction that has reached 15 confirmations (synchronous)"""
        try:
            # Find the transaction
            transaction = session.query(Transaction).filter_by(blockchain_txid=tx_hash, type=tx_type).first()
            if not transaction:
                logger.warning(f"⚠️ Transaction {tx_hash} not found for confirmation processing")
                return
            
            # Check if already processed
            if transaction.status == TransactionStatus.COMPLETED:
                logger.info(f"⏭️ Transaction {tx_hash} already completed")
                return
            
            # Get the account
            account = session.query(Account).filter_by(id=transaction.account_id).first()
            if not account:
                logger.error(f"❌ Account {transaction.account_id} not found for transaction {tx_hash}")
                return
            
            # Convert amount to smallest units
            amount_wei = transaction.amount_smallest_unit
            
            # Handle different transaction types
            if transaction.type == TransactionType.DEPOSIT:
                # For incoming transactions: Credit the account and release reservation
                current_balance = account.crypto_balance_smallest_unit or 0
                new_balance = current_balance + amount_wei
                account.crypto_balance_smallest_unit = new_balance
                
                # Release the reservation (reduce locked amount)
                current_locked = account.crypto_locked_amount_smallest_unit or 0
                new_locked = current_locked - amount_wei
                if new_locked < 0:
                    new_locked = 0  # Prevent negative locked amounts
                account.crypto_locked_amount_smallest_unit = new_locked
                
                logger.info(f"✅ Incoming transaction {tx_hash} confirmed and credited")
                
            elif transaction.type == TransactionType.WITHDRAWAL:
                # For outgoing transactions: Just release the reservation (amount was already deducted)
                current_locked = account.crypto_locked_amount_smallest_unit or 0
                new_locked = current_locked - amount_wei
                if new_locked < 0:
                    new_locked = 0  # Prevent negative locked amounts
                account.crypto_locked_amount_smallest_unit = new_locked
                
                # Handle withdrawal-specific reservation if it exists
                reservation_ref = transaction.metadata_json.get("reservation_reference")
                if reservation_ref:
                    # Find and update the withdrawal reservation
                    withdrawal_reservation = session.query(Reservation).filter_by(
                        user_id=account.user_id,
                        reference=reservation_ref,
                        type=ReservationType.RESERVE
                    ).first()
                    
                    if withdrawal_reservation:
                        withdrawal_reservation.status = "completed"
                        logger.info(f"✅ Updated withdrawal reservation: {reservation_ref}")
                
                logger.info(f"✅ Outgoing transaction {tx_hash} confirmed and reservation released")
                
            else:
                # For other transaction types: Just release reservation
                current_locked = account.crypto_locked_amount_smallest_unit or 0
                new_locked = current_locked - amount_wei
                if new_locked < 0:
                    new_locked = 0
                account.crypto_locked_amount_smallest_unit = new_locked
                
                logger.info(f"✅ Transaction {tx_hash} confirmed and reservation released")
            
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            
            # Create release reservation record
            import time
            release_reference = f"eth_monitor_release_{int(time.time() * 1000)}_{tx_hash[:8]}"
            
            release_reservation = Reservation(
                user_id=account.user_id,
                reference=release_reference,
                amount=float(CryptoPrecisionManager.from_smallest_unit(amount_wei, "ETH")),
                type=ReservationType.RELEASE,
                status="completed"
            )
            
            session.add(release_reservation)
            session.commit()
            
            # Convert back to ETH for logging
            amount_eth = CryptoPrecisionManager.from_smallest_unit(amount_wei, "ETH")
            
            logger.info(f"   Amount: {amount_eth} ETH ({amount_wei:,} wei)")
            logger.info(f"   Account: {account.id}")
            logger.info(f"   New balance: {account.get_balance()} ETH")
            logger.info(f"   New locked: {account.get_locked_amount()} ETH")
            
        except Exception as e:
            logger.error(f"❌ Error processing confirmed transaction {tx_hash}: {e}")
            session.rollback()
    
    def _process_block_confirmations_sync(self, current_block: int):
        """Process confirmations for all pending transactions based on new block (synchronous)"""
        try:
            # Get all pending ETH and ERC20 token transactions
            from db.wallet import Account  # local import to avoid circulars at module load
            
            # Build list of currencies to include (ETH + configured ERC20 tokens)
            currencies_to_monitor = ["ETH"]
            if hasattr(self, 'erc20_tokens') and self.erc20_tokens:
                # Add ERC20 token symbols to the currencies list
                for token_info in self.erc20_tokens.values():
                    if 'symbol' in token_info:
                        currencies_to_monitor.append(token_info['symbol'])
            
            logger.info(f"🔍 Monitoring confirmations for ETH-based currencies: {currencies_to_monitor}")
            
            pending_transactions = (
                session.query(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .filter(
                    Transaction.status == TransactionStatus.AWAITING_CONFIRMATION,
                    Transaction.blockchain_txid.isnot(None),
                    Account.currency.in_(currencies_to_monitor),
                )
                .all()
            )
            
            logger.info(f"Pending ETH and ERC20 transactions: {len(pending_transactions)}")
            
            if not pending_transactions:
                return
            
            logger.info(f"🔍 Processing confirmations for {len(pending_transactions)} transactions at block {current_block}")
            
            # Track processing statistics
            eth_transactions = 0
            erc20_transactions = 0
            skipped_transactions = 0
            
            for transaction in pending_transactions:
                try:
                    # Get the account currency for this transaction
                    account = session.query(Account).filter_by(id=transaction.account_id).first()
                    if not account:
                        logger.warning(f"❌ Account not found for transaction {transaction.blockchain_txid}")
                        continue
                    
                    currency = account.currency
                    
                    # Check if this is an ETH-based transaction (ETH or ERC20 token)
                    is_eth_based = False
                    
                    if currency == "ETH":
                        # Native ETH transaction
                        is_eth_based = True
                        eth_transactions += 1
                    elif account.precision_config and account.precision_config.get('parent_currency','').upper() == 'ETH':
                        # Check if this is a configured ERC20 token (which are all ETH-based)
                        is_eth_based = True
                        erc20_transactions += 1
                    
                    if is_eth_based:
                        # Process ETH-based transaction confirmations
                        logger.debug(f"✅ Processing ETH-based transaction for currency: {currency}")
                        self._check_transaction_confirmations_for_block_sync(transaction, current_block)
                    else:
                        # Skip non-ETH-based transactions (e.g., BTC, LTC, etc.)
                        skipped_transactions += 1
                        logger.debug(f"⏭️ Skipping non-ETH transaction for currency: {currency}, precision config: {account.precision_config}")
                        
                except Exception as e:
                    logger.error(f"❌ Error checking transaction {transaction.blockchain_txid}: {e}")
            
            # Log processing summary
            logger.info(f"📊 Block {current_block} processing summary: ETH={eth_transactions}, ERC20={erc20_transactions}, Skipped={skipped_transactions}")
            
        except Exception as e:
            logger.error(f"❌ Error processing block confirmations: {e}")
        finally:
            try:
                session.remove()
            except Exception:
                pass

    def _scan_erc20_transfers_for_block(self, block_number: int):
        """Scan ERC-20 Transfer logs in this block for monitored addresses and record deposits."""
        try:
            # Use pre-loaded ERC20 token configuration from __init__
            contracts_map = {}
            for contract_addr, token_info in self.erc20_tokens.items():
                contracts_map[token_info['symbol']] = {
                    'address': contract_addr,
                    'decimals': token_info['decimals']
                }

            logger.info(f"Contract map: {contracts_map}")

            # Quick exit if no monitored addresses
            if not self.monitored_addresses:
                return

            logger.info(f"Monitored addresses: {self.monitored_addresses}")
            from shared.crypto.clients.eth import ETHWallet, EthereumConfig
            api_key = os.getenv('ALCHEMY_API_KEY')
            cfg = EthereumConfig.mainnet(api_key) if self.network == 'mainnet' else EthereumConfig.testnet(api_key)
            eth_client = ETHWallet(user_id=0, eth_config=cfg, session=session, logger=logger)

            # Topic0 for Transfer(address,address,uint256)
            topic0 = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
            to_blocks_hex = hex(block_number)
            from_blocks_hex = hex(block_number)

            # Scan per monitored address as topic2 (indexed to)
            for recv in list(self.monitored_addresses):
                # Pad address to topic
                topic2 = '0x' + ('0' * 24) + recv.lower().replace('0x','')
                logs = eth_client.get_logs(from_block=from_blocks_hex, to_block=to_blocks_hex, topics=[topic0, None, topic2]) or []
                if not logs:
                    logger.info(f"No logs found for {recv}")
                    continue
                logger.info(f"Logs: {logs}")
                for log in logs:
                    try:
                        contract = log.get('address')
                        data_hex = log.get('data','0x')
                        topics = log.get('topics',[])
                        if len(topics) < 3:
                            continue
                        from_topic = topics[1]
                        to_topic = topics[2]
                        # Decode value (uint256) from data
                        value_smallest = int(data_hex, 16) if data_hex else 0
                        from_addr = '0x' + from_topic[-40:]
                        to_addr = '0x' + to_topic[-40:]

                        # Resolve token meta
                        symbol = None
                        decimals = 18
                        # If allowlist provided, use it
                        for sym, meta in contracts_map.items():
                            if str(meta.get('address','')).lower() == str(contract).lower():
                                symbol = sym.upper()
                                decimals = int(meta.get('decimals', decimals))
                                break
                        if not symbol:
                            symbol = 'TOKEN'

                        # Find crypto address row for recipient
                        ca = session.query(CryptoAddress).filter(
                            CryptoAddress.address.ilike(to_addr),
                            CryptoAddress.is_active == True
                        ).first()
                        if not ca:
                            continue

                        acc = session.query(Account).filter_by(id=ca.account_id).first()
                        if not acc:
                            continue

                        token_accounts = session.query(Account).filter_by(user_id=acc.user_id, currency=symbol).all()
                        token_account = None
                        for t in token_accounts:
                            if t.precision_config and t.precision_config.get('parent_currency','').upper() == 'ETH':
                                token_account = t
                                break
                        if not token_account:
                            continue

                        
                        if not (token_account.currency and token_account.currency.upper() == symbol and (token_account.precision_config or {}).get('parent_currency','').upper() == 'ETH'):
                            logger.info(f"Skipping ERC20 {symbol} deposit to {to_addr} because it's not a token account")
                            continue

                        # Create deposit if not recorded
                        existing = session.query(Transaction).filter_by(
                            blockchain_txid=log.get('transactionHash'),
                            address=to_addr.lower(),
                            type=TransactionType.DEPOSIT,
                        ).first()
                        if existing:
                            continue

                        amount_standard = Decimal(value_smallest) / (Decimal(10) ** Decimal(decimals))
                        # Lock reservation
                        res = Reservation(
                            user_id=acc.user_id,
                            reference=f"eth_erc20_{block_number}_{log.get('transactionHash','')[:8]}",
                            amount=float(amount_standard),
                            type=ReservationType.RESERVE,
                            status='active',
                        )
                        session.add(res)

                        tx = Transaction(
                            account_id=token_account.id,
                            reference_id=log.get('transactionHash'),
                            amount=float(amount_standard),
                            amount_smallest_unit=int(value_smallest),
                            precision_config={
                                'currency': symbol,
                                'decimals': int(decimals),
                                'smallest_unit': 'units',
                                'parent_currency': 'ETH',
                            },
                            type=TransactionType.DEPOSIT,
                            status=TransactionStatus.AWAITING_CONFIRMATION,
                            description=f"ERC20 {symbol} transfer {log.get('transactionHash','')[:8]}...",
                            blockchain_txid=log.get('transactionHash'),
                            confirmations=0,
                            required_confirmations=15,
                            address=to_addr.lower(),
                            provider=PaymentProvider.CRYPTO,
                            metadata_json={
                                'from_address': from_addr,
                                'to_address': to_addr,
                                'contract': contract,
                                'log_index': log.get('logIndex'),
                                'block_number': block_number,
                                'value_smallest': str(value_smallest),
                                'symbol': symbol,
                                'decimals': int(decimals),
                            },
                        )
                        session.add(tx)
                        session.commit()
                        logger.info(f"💾 Recorded ERC20 {symbol} deposit to {to_addr}: {amount_standard} (smallest={value_smallest})")
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Error recording ERC20 log deposit: {e}")
        except Exception as e:
            logger.error(f"ERC20 scan error: {e}")

    def _scan_erc20_transfers_for_range(self, from_block_number: int, to_block_number: int):
        """Scan ERC-20 Transfer logs in a block range for monitored addresses and record deposits."""
        try:
            # Use pre-loaded ERC20 token configuration from __init__
            contracts_map = {}
            for contract_addr, token_info in self.erc20_tokens.items():
                contracts_map[token_info['symbol']] = {
                    'address': contract_addr,
                    'decimals': token_info['decimals']
                }

            if not self.monitored_addresses:
                return

            from shared.crypto.clients.eth import ETHWallet, EthereumConfig
            api_key = os.getenv('ALCHEMY_API_KEY')
            cfg = EthereumConfig.mainnet(api_key) if self.network == 'mainnet' else EthereumConfig.testnet(api_key)
            eth_client = ETHWallet(user_id=0, eth_config=cfg, session=session, logger=logger)

            topic0 = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
            to_hex = hex(int(to_block_number))
            from_hex = hex(int(from_block_number))

            for recv in list(self.monitored_addresses):
                topic2 = '0x' + ('0' * 24) + recv.lower().replace('0x','')
                logs = eth_client.get_logs(from_block=from_hex, to_block=to_hex, topics=[topic0, None, topic2]) or []
                if not logs:
                    continue
                for log in logs:
                    try:
                        contract = log.get('address')
                        data_hex = log.get('data','0x')
                        topics = log.get('topics',[])
                        if len(topics) < 3:
                            continue
                        from_topic = topics[1]
                        to_topic = topics[2]
                        value_smallest = int(data_hex, 16) if data_hex else 0
                        from_addr = '0x' + from_topic[-40:]
                        to_addr = '0x' + to_topic[-40:]

                        symbol = None
                        decimals = 18
                        for sym, meta in contracts_map.items():
                            if str(meta.get('address','')).lower() == str(contract).lower():
                                symbol = sym.upper()
                                decimals = int(meta.get('decimals', decimals))
                                break
                        if not symbol:
                            symbol = 'TOKEN'

                        ca = session.query(CryptoAddress).filter(
                            CryptoAddress.address.ilike(to_addr),
                            CryptoAddress.is_active == True
                        ).first()
                        if not ca:
                            continue

                        acc = session.query(Account).filter_by(id=ca.account_id).first()
                        if not acc:
                            continue
                        token_accounts = session.query(Account).filter_by(user_id=acc.user_id, currency=symbol).all()
                        token_account = None
                        for t in token_accounts:
                            if t.precision_config and t.precision_config.get('parent_currency','').upper() == 'ETH':
                                token_account = t
                                break
                        if not token_account:
                            continue

                        
                        if not (token_account.currency and token_account.currency.upper() == symbol and (token_account.precision_config or {}).get('parent_currency','').upper() == 'ETH'):
                            logger.info(f"Skipping ERC20 {symbol} deposit to {to_addr} because it's not a token account")
                            continue

                        existing = session.query(Transaction).filter_by(
                            blockchain_txid=log.get('transactionHash'),
                            address=to_addr.lower(),
                            type=TransactionType.DEPOSIT,
                        ).first()
                        if existing:
                            continue

                        amount_standard = Decimal(value_smallest) / (Decimal(10) ** Decimal(decimals))
                        res = Reservation(
                            user_id=acc.user_id,
                            reference=f"eth_erc20_{log.get('blockNumber')}_{log.get('transactionHash','')[:8]}",
                            amount=float(amount_standard),
                            type=ReservationType.RESERVE,
                            status='active',
                        )
                        session.add(res)

                        # Parse block number from log
                        try:
                            log_block = int(log.get('blockNumber'), 16) if isinstance(log.get('blockNumber'), str) else int(log.get('blockNumber') or 0)
                        except Exception:
                            log_block = int(to_block_number)

                        tx = Transaction(
                            account_id=token_account.id,
                            reference_id=log.get('transactionHash'),
                            amount=float(amount_standard),
                            amount_smallest_unit=int(value_smallest),
                            precision_config={
                                'currency': symbol,
                                'decimals': int(decimals),
                                'smallest_unit': 'units',
                                'parent_currency': 'ETH',
                            },
                            type=TransactionType.DEPOSIT,
                            status=TransactionStatus.AWAITING_CONFIRMATION,
                            description=f"ERC20 {symbol} transfer {log.get('transactionHash','')[:8]}...",
                            blockchain_txid=log.get('transactionHash'),
                            confirmations=0,
                            required_confirmations=15,
                            address=to_addr.lower(),
                            provider=PaymentProvider.CRYPTO,
                            metadata_json={
                                'from_address': from_addr,
                                'to_address': to_addr,
                                'contract': contract,
                                'log_index': log.get('logIndex'),
                                'block_number': log_block,
                                'value_smallest': str(value_smallest),
                                'symbol': symbol,
                                'decimals': int(decimals),
                            },
                        )
                        session.add(tx)
                        session.commit()
                        logger.info(f"💾 Recorded ERC20 {symbol} deposit to {to_addr}: {amount_standard} (smallest={value_smallest})")
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Error recording ERC20 log deposit (range): {e}")
        except Exception as e:
            logger.error(f"ERC20 range scan error: {e}")

    def _scan_erc20_transfers_via_transfers_api(self, from_block_number: int, to_block_number: int):
        """Scan ERC-20 transfers via Alchemy Transfers API and record deposits to monitored addresses."""
        try:
            # Use pre-loaded ERC20 token configuration from __init__
            contracts_map = {}
            for contract_addr, token_info in self.erc20_tokens.items():
                contracts_map[token_info['symbol']] = {
                    'address': contract_addr,
                    'decimals': token_info['decimals']
                }

            if not self.monitored_addresses:
                return

            api_key = os.getenv('ALCHEMY_API_KEY')
            cfg = EthereumConfig.mainnet(api_key) if self.network == 'mainnet' else EthereumConfig.testnet(api_key)
            eth_client = ETHWallet(user_id=0, eth_config=cfg, session=session, logger=logger)

            from_hex = hex(int(from_block_number))
            to_hex = hex(int(to_block_number))

            for recv in list(self.monitored_addresses):
                params = {
                    'fromBlock': from_hex,
                    'toBlock': to_hex,
                    'toAddress': recv,
                    'excludeZeroValue': True,
                    'category': ['erc20'],
                    'withMetadata': True,
                    'order': 'asc',
                    'maxCount': '0x3e8',
                }
                transfers = eth_client.get_asset_transfers(params) or []
                logger.info(f"Transfers: {transfers}")
                if not transfers:
                    continue
                for t in transfers:
                    try:
                        tx_hash = t.get('hash')
                        to_addr = (t.get('to') or '').lower()
                        from_addr = (t.get('from') or '').lower()
                        if not tx_hash or not to_addr:
                            continue

                        # Contract and metadata
                        raw = t.get('rawContract') or {}
                        contract = (raw.get('address') or '').lower()

                        logger.info(f"Contract address: {contract}")

                        # Resolve symbol/decimals: prefer allowlist, then use API fields
                        symbol = None
                        decimals = None
                        for sym, meta in contracts_map.items():
                            if str(meta.get('address','')).lower() == contract:
                                symbol = sym.upper()
                                try:
                                    decimals = int(meta.get('decimals'))
                                except Exception:
                                    decimals = None
                                break
                        if not symbol:
                            symbol = (t.get('asset') or 'TOKEN').upper()
                        if decimals is None:
                            try:
                                # Some payloads include decimal in rawContract
                                decimals = int(raw.get('decimal')) if raw.get('decimal') is not None else 18
                            except Exception:
                                decimals = 18

                        # Amounts
                        val = t.get('value')
                        try:
                            amount_standard = Decimal(str(val)) if val is not None else Decimal(0)
                        except Exception:
                            amount_standard = Decimal(0)
                        value_smallest = int((amount_standard * (Decimal(10) ** Decimal(decimals))).to_integral_value())

                        # Dedup check
                        existing = session.query(Transaction).filter_by(
                            blockchain_txid=tx_hash,
                            address=to_addr,
                            type=TransactionType.DEPOSIT,
                        ).first()
                        if existing:
                            continue

                        # Ensure recipient address belongs to an active crypto address
                        ca = session.query(CryptoAddress).filter(
                            CryptoAddress.address.ilike(to_addr),
                            CryptoAddress.is_active == True
                        ).first()
                        if not ca:
                            continue
                        logger.info(f"Crypto address: {ca}")

                        acc = session.query(Account).filter_by(id=ca.account_id).first()
                        token_accounts = session.query(Account).filter_by(user_id=acc.user_id, currency=symbol).all()
                        token_account = None
                        for t_acc in token_accounts:
                            if (t_acc.precision_config or {}).get('parent_currency','').upper() == 'ETH':
                                token_account = t_acc
                                break

                        if not token_account:
                            logger.info(f"No token account found for {symbol}")
                            continue
                        if not (token_account.currency and token_account.currency.upper() == symbol and (token_account.precision_config or {}).get('parent_currency','').upper() == 'ETH'):
                            logger.info(f"Account does not match")
                            continue


                        # Block number
                        try:
                            log_block = int(t.get('blockNum'), 16) if isinstance(t.get('blockNum'), str) else int(t.get('blockNum') or 0)
                        except Exception:
                            log_block = int(to_block_number)

                        logger.info(f"Making a reservation for {symbol} {amount_standard}")

                        # Create reservation and transaction
                        res = Reservation(
                            user_id=acc.user_id,
                            reference=f"eth_erc20_{log_block}_{tx_hash[:8]}",
                            amount=float(amount_standard),
                            type=ReservationType.RESERVE,
                            status='active',
                        )
                        session.add(res)

                        tx = Transaction(
                            account_id=token_account.id,
                            reference_id=tx_hash,
                            amount=float(amount_standard),
                            amount_smallest_unit=int(value_smallest),
                            precision_config={
                                'currency': symbol,
                                'decimals': int(decimals),
                                'smallest_unit': 'units',
                                'parent_currency': 'ETH',
                            },
                            type=TransactionType.DEPOSIT,
                            status=TransactionStatus.AWAITING_CONFIRMATION,
                            description=f"ERC20 {symbol} transfer {tx_hash[:8]}...",
                            blockchain_txid=tx_hash,
                            confirmations=0,
                            required_confirmations=15,
                            address=to_addr,
                            provider=PaymentProvider.CRYPTO,
                            metadata_json={
                                'from_address': from_addr,
                                'to_address': to_addr,
                                'contract': contract,
                                'block_number': log_block,
                                'value_smallest': str(value_smallest),
                                'symbol': symbol,
                                'decimals': int(decimals),
                            },
                        )
                        session.add(tx)
                        session.commit()
                        logger.info(f"Recorded ERC20 {symbol} deposit to {to_addr}: {amount_standard} (smallest={value_smallest})")
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Error recording ERC20 transfer (transfers API): {e}")
        except Exception as e:
            logger.error(f"ERC20 transfers API scan error: {e}")
        finally:
            try:
                session.remove()
            except Exception:
                pass
    
    def _scan_eth_transfers_for_block(self, block_number: int):
        """Scan a specific block for regular ETH transfers (non-ERC20)"""
        try:
            logger.info(f"🔍 Scanning block {block_number} for ETH transfers...")
            
            # Get the full block data including transactions
            full_block = self._get_block_with_transactions(block_number)
            if not full_block:
                logger.warning(f"⚠️ Could not fetch full block data for block {block_number}")
                return
            
            transactions = full_block.get("transactions", [])
            if not transactions:
                logger.info(f"ℹ️ No transactions found in block {block_number}")
                return
            
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            found_eth_transfers = 0
            
            for tx_data in transactions:
                # Skip contract creation transactions (no 'to' address)
                if not tx_data.get("to"):
                    continue
                
                # Skip transactions with input data (likely ERC20 or contract calls)
                if tx_data.get("input") and tx_data.get("input") != "0x":
                    continue
                
                # Check if this transaction involves our monitored addresses
                from_address = tx_data.get("from", "").lower() if tx_data.get("from") else ""
                to_address = tx_data.get("to", "").lower() if tx_data.get("to") else ""
                
                if (from_address in monitored_addresses_lower or 
                    to_address in monitored_addresses_lower):
                    
                    # Extract transaction details
                    tx_hash = tx_data.get("hash")
                    value = int(tx_data.get("value", "0"), 16)
                    gas_price = int(tx_data.get("gasPrice", "0"), 16)
                    gas_used = int(tx_data.get("gas", "0"), 16)
                    timestamp = int(full_block.get("timestamp", "0"), 16)
                    
                    # Convert value from wei to ETH
                    value_eth = Decimal(value) / Decimal(10**18)
                    
                    # Skip zero-value transactions
                    if value_eth == 0:
                        continue
                    
                    event = TransactionEvent(
                        tx_hash=tx_hash,
                        from_address=from_address,
                        to_address=to_address,
                        value=value_eth,
                        block_number=block_number,
                        gas_price=gas_price,
                        gas_used=gas_used,
                        timestamp=timestamp
                    )
                    
                    logger.info(f"💰 ETH transfer detected in block {block_number}: {tx_hash}")
                    logger.info(f"   From: {from_address}")
                    logger.info(f"   To: {to_address}")
                    logger.info(f"   Value: {value_eth} ETH")
                    
                    # Check if transaction already processed
                    if not self._is_transaction_processed_sync(tx_hash, from_address if from_address in monitored_addresses_lower else to_address):
                        # Process the transaction
                        self._process_transaction_sync(event)
                        found_eth_transfers += 1
                    else:
                        logger.info(f"⏭️ ETH transfer {tx_hash} already processed")
            
            if found_eth_transfers > 0:
                logger.info(f"✅ Found {found_eth_transfers} new ETH transfers in block {block_number}")
            else:
                logger.info(f"ℹ️ No new ETH transfers found in block {block_number}")
                    
        except Exception as e:
            logger.error(f"❌ Error scanning block {block_number} for ETH transfers: {e}")
        finally:
            try:
                session.remove()
            except Exception:
                pass



    def _scan_eth_transfers_for_range_with_stats(self, from_block_number: int, to_block_number: int) -> int:
        """Scan a range of blocks for regular ETH transfers and return count of transfers found"""
        total_transfers = 0
        max_scan_time = 30  # Maximum 30 seconds for scanning 200 blocks (reduced from 60s)
        start_time = time.time()
        
        try:
            logger.info(f"🔍 Scanning blocks {from_block_number} to {to_block_number} for ETH transfers...")
            
            for block_number in range(from_block_number, to_block_number + 1):
                # Check if we're taking too long (circuit breaker)
                if time.time() - start_time > max_scan_time:
                    logger.warning(f"⏰ Scanning taking too long ({max_scan_time}s), stopping early at block {block_number}")
                    break
                
                transfers_in_block = self._scan_eth_transfers_for_block_with_stats(block_number)
                total_transfers += transfers_in_block
                
                # Use configured delay for responsiveness
                time.sleep(self.block_scan_delay)
                
            scan_duration = time.time() - start_time
            logger.info(f"✅ ETH transfer range scan completed: {total_transfers} transfers found in {to_block_number - from_block_number + 1} blocks in {scan_duration:.2f}s")
            return total_transfers
                
        except Exception as e:
            logger.error(f"❌ Error scanning ETH transfers for range {from_block_number}-{to_block_number}: {e}")
            return total_transfers

    def _scan_eth_transfers_for_block_with_stats(self, block_number: int) -> int:
        """Scan a specific block for regular ETH transfers (non-ERC20) and return count of transfers found"""
        transfers_found = 0
        block_start_time = time.time()
        max_block_scan_time = 5  # Maximum 5 seconds per block (reduced from 10s)
        
        try:
            logger.debug(f"🔍 Scanning block {block_number} for ETH transfers...")
            
            # Get the full block data including transactions
            full_block = self._get_block_with_transactions(block_number)
            if not full_block:
                logger.warning(f"⚠️ Could not fetch full block data for block {block_number}")
                return transfers_found
            
            transactions = full_block.get("transactions", [])
            if not transactions:
                logger.info(f"ℹ️ No transactions found in block {block_number}")
                return transfers_found
            
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            
            for tx_data in transactions:
                # Check if we're taking too long on this block
                if time.time() - block_start_time > max_block_scan_time:
                    logger.warning(f"⏰ Block {block_number} scanning taking too long ({max_block_scan_time}s), stopping early")
                    break
                
                # Skip contract creation transactions (no 'to' address)
                if not tx_data.get("to"):
                    logger.debug(f"⏭️ Skipping contract creation tx {tx_data.get('hash', 'unknown')[:10]}...")
                    continue
                
                # Check if this is a simple ETH transfer
                # Many wallets include minimal input data even for ETH transfers
                # We'll check if the input data is minimal (0x or very short)
                input_data = tx_data.get("input", "0x")
                if input_data and len(input_data) > 10:  # Skip only transactions with substantial input data
                    logger.debug(f"⏭️ Skipping contract call tx {tx_data.get('hash', 'unknown')[:10]}... (input length: {len(input_data)})")
                    continue
                
                # Log all transactions being considered for ETH transfer detection
                tx_hash = tx_data.get("hash", "unknown")
                from_addr = tx_data.get("from", "unknown")
                to_addr = tx_data.get("to", "unknown")
                value_hex = tx_data.get("value", "0")
                logger.debug(f"🔍 Considering tx {tx_hash[:10]}... for ETH transfer detection")
                logger.debug(f"   From: {from_addr[:10]}... To: {to_addr[:10]}... Value: {value_hex}")
                
                # Check if this transaction involves our monitored addresses
                from_address = tx_data.get("from", "").lower() if tx_data.get("from") else ""
                to_address = tx_data.get("to", "").lower() if tx_data.get("to") else ""
                
                if (from_address in monitored_addresses_lower or 
                    to_address in monitored_addresses_lower):
                    
                    # Extract transaction details
                    tx_hash = tx_data.get("hash")
                    value = int(tx_data.get("value", "0"), 16)
                    gas_price = int(tx_data.get("gasPrice", "0"), 16)
                    gas_used = int(tx_data.get("gas", "0"), 16)
                    timestamp = int(full_block.get("timestamp", "0"), 16)
                    
                    # Convert value from wei to ETH
                    value_eth = Decimal(value) / Decimal(10**18)
                    
                    # Skip zero-value transactions
                    if value_eth == 0:
                        continue
                    
                    event = TransactionEvent(
                        tx_hash=tx_hash,
                        from_address=from_address,
                        to_address=to_address,
                        value=value_eth,
                        block_number=block_number,
                        gas_price=gas_price,
                        gas_used=gas_used,
                        timestamp=timestamp
                    )
                    
                    logger.info(f"💰 ETH transfer detected in block {block_number}: {tx_hash}")
                    logger.info(f"   From: {from_address}")
                    logger.info(f"   To: {to_address}")
                    logger.info(f"   Value: {value_eth} ETH")
                    
                    # Check if transaction already processed
                    if not self._is_transaction_processed_sync(tx_hash, from_address if from_address in monitored_addresses_lower else to_address):
                        # Process the transaction
                        self._process_transaction_sync(event)
                        transfers_found += 1
                    else:
                        logger.info(f"⏭️ ETH transfer {tx_hash} already processed")
            
            if transfers_found > 0:
                logger.info(f"✅ Found {transfers_found} new ETH transfers in block {block_number}")
            else:
                logger.info(f"ℹ️ No new ETH transfers found in block {block_number}")
            
            return transfers_found
                    
        except Exception as e:
            logger.error(f"❌ Error scanning block {block_number} for ETH transfers: {e}")
            return transfers_found
        finally:
            try:
                session.remove()
            except Exception:
                pass

    def _check_transaction_confirmations_for_block_sync(self, transaction: Transaction, current_block: int):
        """Check transaction confirmations against current block (synchronous)"""
        try:
            # Guard: process only ETH transactions here
            from db.wallet import Account  # local import to avoid circulars
            account = session.query(Account).filter_by(id=transaction.account_id).first()
            found = False
            if account.currency == "ETH":
                found = True
            elif account.precision_config and account.precision_config.get('parent_currency','').upper() == 'ETH':
                found = True

            if not found:
                logger.info(
                    f"Skipping non-ETH transaction {transaction.blockchain_txid} (currency={getattr(account, 'currency', None)})"
                )
                return
            
            logger.info(f" confirming transaction {transaction.blockchain_txid} with metadata {transaction.metadata_json}")
            
            # Calculate confirmations
            if transaction.metadata_json and 'block_number' in transaction.metadata_json:
                tx_block = int(transaction.metadata_json.get('block_number', 0))
                if tx_block == 0:
                    metadata = transaction.metadata_json or {}
                    metadata['block_number'] = current_block
                    transaction.metadata_json = metadata
                    # Mark the field as modified for SQLAlchemy
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(transaction, "metadata_json")
                    session.commit()
                else:
                    confirmations = current_block - tx_block
                    
                    # Update transaction confirmations
                    transaction.confirmations = confirmations
                    
                    # Check if ready for confirmation
                    if confirmations >= transaction.required_confirmations:
                        logger.info(f"🎯 Transaction {transaction.blockchain_txid} reached {confirmations} confirmations")
                        self._process_confirmed_transaction_sync(transaction.blockchain_txid, transaction.type)
                    elif confirmations > 0:
                        logger.info(f"⏳ Transaction {transaction.blockchain_txid} has {confirmations}/{transaction.required_confirmations} confirmations")
                    
                    session.commit()
            else:
                logger.info(f"No block number found for transaction {transaction.blockchain_txid}")
                metadata = transaction.metadata_json or {}
                metadata['block_number'] = current_block
                transaction.metadata_json = metadata
                # Mark the field as modified for SQLAlchemy
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(transaction, "metadata_json")
                logger.info(f"transaction.metadata_json: {transaction.metadata_json}")
                session.commit()
                
            
        except Exception as e:
            logger.error(f"❌ Error checking confirmations for {transaction.blockchain_txid}: {e}")
            logger.error(traceback.format_exc())
    
    def _check_transaction_confirmations_sync(self, tx_hash: str):
        """Check transaction confirmations and process if ready (synchronous) - legacy method for API calls"""
        try:
            # Get current block number from Alchemy
            current_block = self._get_current_block_number()
            if not current_block:
                logger.warning(f"⚠️ Could not get current block number for {tx_hash}")
                return
            
            # Get transaction details
            transaction = session.query(Transaction).filter_by(blockchain_txid=tx_hash).first()
            if not transaction:
                logger.warning(f"⚠️ Transaction {tx_hash} not found")
                return
            
            # Calculate confirmations
            if transaction.metadata_json and 'block_number' in transaction.metadata_json:
                tx_block = transaction.metadata_json['block_number']
                confirmations = current_block - tx_block
                
                # Update transaction confirmations
                transaction.confirmations = confirmations
                
                # Check if ready for confirmation
                if confirmations >= transaction.required_confirmations:
                    logger.info(f"🎯 Transaction {tx_hash} reached {confirmations} confirmations")
                    self._process_confirmed_transaction_sync(tx_hash, transaction.type)
                else:
                    logger.info(f"⏳ Transaction {tx_hash} has {confirmations}/{transaction.required_confirmations} confirmations")
                
                session.commit()
            
        except Exception as e:
            logger.error(f"❌ Error checking confirmations for {tx_hash}: {e}")
    
    def _get_current_block_number(self) -> Optional[int]:
        """Get current block number from Alchemy API"""
        try:
            # Use the correct network from constructor
            if self.network == "sepolia":
                url = f"https://eth-sepolia.g.alchemy.com/v2/{self.api_key}"
            elif self.network == "goerli":
                url = f"https://eth-goerli.g.alchemy.com/v2/{self.api_key}"
            else:
                url = f"https://eth-mainnet.g.alchemy.com/v2/{self.api_key}"
                
            # Alchemy API expects POST requests with JSON-RPC payload
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            
            response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
            
            logger.info(f"Block response: {response.json()}")
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return int(data['result'], 16)
                elif 'error' in data:
                    logger.error(f"❌ Alchemy API error: {data['error']}")
            
            return None
        except Exception as e:
            logger.error(f"❌ Error getting current block number: {e}")
            return None
    
    def _check_pending_transactions_sync(self):
        """Check all pending transactions for confirmations (synchronous)"""
        try:
            # Get all pending ETH transactions only
            from db.wallet import Account  # local import to avoid circulars at module load
            pending_transactions = (
                session.query(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .filter(
                    Transaction.status == TransactionStatus.AWAITING_CONFIRMATION,
                    Transaction.blockchain_txid.isnot(None),
                    Account.currency == "ETH",
                )
                .all()
            )
            
            if not pending_transactions:
                return
            
            logger.info(f"🔍 Checking {len(pending_transactions)} pending transactions for confirmations...")
            
            for transaction in pending_transactions:
                try:
                    self._check_transaction_confirmations_sync(transaction.blockchain_txid)
                except Exception as e:
                    logger.error(f"❌ Error checking transaction {transaction.blockchain_txid}: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error checking pending transactions: {e}")
        finally:
            try:
                session.remove()
            except Exception:
                pass
    
    def _check_block_for_transactions_sync(self, block_data: Dict):
        """Check a block for transactions involving our monitored addresses"""
        try:
            block_number = int(block_data.get("number", "0"), 16)
            logger.info(f"🔍 Checking block {block_number} for transactions...")
            
            # Get the full block data including transactions from Alchemy API
            full_block = self._get_block_with_transactions(block_number)
            if not full_block:
                logger.warning(f"⚠️ Could not fetch full block data for block {block_number}")
                return
            
            transactions = full_block.get("transactions", [])
            if not transactions:
                logger.info(f"ℹ️ No transactions found in block {block_number}")
                return
            
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            found_transactions = 0
            
            for tx_data in transactions:
                # Check if this transaction involves our monitored addresses
                from_address = tx_data.get("from", "").lower() if tx_data.get("from") else ""
                to_address = tx_data.get("to", "").lower() if tx_data.get("to") else ""
                
                if (from_address in monitored_addresses_lower or 
                    to_address in monitored_addresses_lower):
                    
                    # Extract transaction details
                    tx_hash = tx_data.get("hash")
                    value = int(tx_data.get("value", "0"), 16)
                    gas_price = int(tx_data.get("gasPrice", "0"), 16)
                    gas_used = int(tx_data.get("gas", "0"), 16)
                    timestamp = int(block_data.get("timestamp", "0"), 16)
                    
                    # Convert value from wei to ETH
                    value_eth = Decimal(value) / Decimal(10**18)
                    
                    event = TransactionEvent(
                        tx_hash=tx_hash,
                        from_address=from_address,
                        to_address=to_address,
                        value=value_eth,
                        block_number=block_number,
                        gas_price=gas_price,
                        gas_used=gas_used,
                        timestamp=timestamp
                    )
                    
                    logger.info(f"💰 Confirmed transaction detected in block {block_number}: {tx_hash}")
                    logger.info(f"   From: {from_address}")
                    logger.info(f"   To: {to_address}")
                    logger.info(f"   Value: {value_eth} ETH")
                    
                    # Process the transaction
                    self._process_transaction_sync(event)
                    found_transactions += 1
            
            if found_transactions > 0:
                logger.info(f"✅ Found {found_transactions} transactions in block {block_number}")
            else:
                logger.info(f"ℹ️ No relevant transactions found in block {block_number}")
                    
        except Exception as e:
            logger.error(f"❌ Error checking block for transactions: {e}")
        finally:
            try:
                session.remove()
            except Exception:
                pass
    
    def _get_block_with_transactions(self, block_number: int) -> Optional[Dict]:
        """Get full block data including transactions from Alchemy API with proper timeouts"""
        try:
            import requests
            import json
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            
            api_key = os.getenv('ALCHEMY_API_KEY')
            if not api_key:
                logger.error("❌ ALCHEMY_API_KEY not found")
                return None
            
            # Use the correct network from constructor
            if self.network == "sepolia":
                url = f"https://eth-sepolia.g.alchemy.com/v2/{api_key}"
            elif self.network == "goerli":
                url = f"https://eth-goerli.g.alchemy.com/v2/{api_key}"
            else:
                url = f"https://eth-mainnet.g.alchemy.com/v2/{api_key}"
            
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [hex(block_number), True],  # True to include full transaction objects
                "id": 1
            }
            
            # Create session with retry strategy and timeouts
            session = requests.Session()
            retry_strategy = Retry(
                total=1,  # Only retry once to avoid blocking
                backoff_factor=0.1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Use much shorter timeout to prevent blocking
            response = session.post(url, json=payload, timeout=(3, 8))  # (connect_timeout, read_timeout)
            result = response.json()
            
            if 'result' in result and result['result']:
                return result['result']
            else:
                logger.warning(f"⚠️ No block data returned for block {block_number}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"⏰ Timeout fetching block {block_number} data")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"🌐 Network error fetching block {block_number}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching block data: {e}")
            return None
    
    def start_confirmation_checker(self):
        """Start the confirmation checker thread (now using real-time block events)"""
        # Note: We no longer need periodic checking since we're using real-time block events
        # This method is kept for backward compatibility but doesn't start a thread
        logger.info("🔄 Confirmation checking now uses real-time block events")
    
    def stop_confirmation_checker(self):
        """Stop the confirmation checker thread (now using real-time block events)"""
        # Note: We no longer need to stop a thread since we're using real-time block events
        logger.info("🛑 Confirmation checking uses real-time block events")
    
    def add_address(self, address: str):
        """Add an address to monitor"""
        self.monitored_addresses.add(address)
        if self.is_connected:
            self._subscribe_to_address(address)
        logger.info(f"➕ Added address to monitor: {address}")
    
    def add_address_from_kafka(self, address: str, currency_code: str = "ETH", account_id: int = None, user_id: int = None):
        """Add an address to monitor from Kafka event"""
        if currency_code.upper() == "ETH":
            self.add_address(address)
            logger.info(f"📨 Added Ethereum address from Kafka: {address} (User: {user_id}, Account: {account_id})")
        else:
            logger.info(f"ℹ️ Skipping non-Ethereum address from Kafka: {address} (Currency: {currency_code})")
    
    def remove_address(self, address: str):
        """Remove an address from monitoring"""
        self.monitored_addresses.discard(address)
        logger.info(f"➖ Removed address from monitoring: {address}")
    
    def load_addresses_from_db(self):
        """Load all active Ethereum addresses from database"""
        try:
            logger.info("🔍 Loading Ethereum addresses from database...")
            logger.info(f"🔧 Database session: {session}")
            logger.info(f"🔧 CryptoAddress model: {CryptoAddress}")
            
            addresses = session.query(CryptoAddress).filter_by(
                currency_code="ETH",
                is_active=True
            ).all()
            
            logger.info(f"📋 Found {len(addresses)} active ETH addresses in database")
            
            for addr in addresses:
                logger.debug(f"➕ Adding address to monitoring: {addr.address}")
                self.add_address(addr.address)
            
            logger.info(f"✅ Successfully loaded {len(addresses)} Ethereum addresses from database")
            logger.info(f"🔍 Currently monitoring {len(self.monitored_addresses)} addresses")
            
        except Exception as e:
            logger.error(f"❌ Error loading addresses from database: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    def connect(self):
        """Connect to Alchemy WebSocket"""
        try:
            websocket.enableTrace(True)
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self.on_open,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close
            )
            
            self.is_running = True
            self.ws.run_forever()
            
        except Exception as e:
            logger.error(f"❌ Error connecting to WebSocket: {e}")
    
    def disconnect(self):
        """Disconnect from WebSocket"""
        self.is_running = False
        if self.ws:
            self.ws.close()
        logger.info("🔌 Disconnected from WebSocket")

    def start_eth_transfer_polling(self):
        """Start background ETH transfer polling service"""
        logger.info("🚀 Starting ETH transfer polling service...")
        
        if not self.eth_polling_enabled:
            logger.info("ℹ️ ETH transfer polling is disabled")
            return
        
        logger.info("✅ ETH transfer polling is enabled, proceeding with startup")
            
        # Set the service as running so the polling worker can start
        self.is_running = True
        logger.info(f"🔧 Set is_running flag to: {self.is_running}")
            
        # Initialize statistics and record start time
        self._last_eth_poll_time = None
        self._total_blocks_scanned = 0
        self._total_eth_transfers_found = 0
        self._eth_polling_errors = 0
        self._eth_polling_cycles = 0
        self._last_cycle_duration = 0
        self._last_cycle_blocks_scanned = 0
        self._last_cycle_transfers_found = 0
        self._cycle_durations = []  # Store last 10 cycle durations for averaging
        self._record_polling_start_time()
        
        logger.info("📊 Statistics initialized, performing initial catch-up scan...")
        
        # Perform initial catch-up scan when service starts
        self._perform_initial_catch_up_scan()
            
        def eth_polling_worker():
            """Background worker for polling ETH transfers"""
            logger.info("🔄 Starting ETH transfer polling service")
            
            while self.is_running:
                try:
                    cycle_start_time = time.time()
                    
                    # Get current block number
                    current_block = self._get_current_block_number()
                    if not current_block:
                        logger.warning("⚠️ Could not get current block number, skipping polling cycle")
                        time.sleep(30)  # Wait 30 seconds before retry
                        continue
                    
                    # Poll for ETH transfers in recent blocks using configured range
                    from_block = max(1, current_block - self.eth_polling_block_range)
                    to_block = current_block
                    
                    logger.info(f"🔍 Polling ETH transfers in blocks {from_block} to {to_block}")
                    
                    # Track polling time
                    poll_start_time = time.time()
                    self._last_eth_poll_time = poll_start_time
                    
                    # Scan for ETH transfers
                    transfers_found = self._scan_eth_transfers_for_range_with_stats(from_block, to_block)
                    
                    # Update statistics and cycle count
                    poll_duration = time.time() - poll_start_time
                    cycle_duration = time.time() - cycle_start_time
                    blocks_scanned = to_block - from_block + 1
                    
                    self._total_blocks_scanned += blocks_scanned
                    self._total_eth_transfers_found += transfers_found
                    self._last_cycle_duration = cycle_duration
                    self._last_cycle_blocks_scanned = blocks_scanned
                    self._last_cycle_transfers_found = transfers_found
                    self._update_cycle_duration_average(cycle_duration)
                    self._update_polling_cycle_count()
                    
                    # Log performance metrics
                    logger.info(f"✅ ETH transfer polling cycle {self._eth_polling_cycles} completed in {cycle_duration:.2f}s")
                    logger.info(f"   - Scan duration: {poll_duration:.2f}s")
                    logger.info(f"   - Blocks scanned: {blocks_scanned}")
                    logger.info(f"   - ETH transfers found: {transfers_found}")
                    logger.info(f"   - Total blocks scanned: {self._total_blocks_scanned}")
                    logger.info(f"   - Total ETH transfers found: {self._total_eth_transfers_found}")
                    logger.info(f"   - Total cycles completed: {self._eth_polling_cycles}")
                    logger.info(f"   - Average cycle duration: {getattr(self, '_average_cycle_duration', 0):.2f}s")
                    
                    # Performance warnings
                    if cycle_duration > 120:  # More than 2 minutes
                        logger.warning(f"⚠️ Slow ETH polling cycle: {cycle_duration:.2f}s (threshold: 120s)")
                    if transfers_found == 0 and blocks_scanned > 50:
                        logger.info(f"ℹ️ No ETH transfers found in {blocks_scanned} blocks (this is normal)")
                    
                    # Wait for configured interval before next polling cycle
                    time.sleep(self.eth_polling_interval)
                    
                except Exception as e:
                    self._eth_polling_errors += 1
                    logger.error(f"❌ Error in ETH transfer polling worker: {e}")
                    logger.error(f"   - Total errors: {self._eth_polling_errors}")
                    logger.error(f"   - Error rate: {(self._eth_polling_errors / max(1, self._eth_polling_cycles)) * 100:.1f}%")
                    time.sleep(60)  # Wait 1 minute before retry
            
            logger.info("🛑 ETH transfer polling service stopped")
        
        # Start polling in a separate thread
        import threading
        self.eth_polling_thread = threading.Thread(target=eth_polling_worker)
        self.eth_polling_thread.daemon = True
        self.eth_polling_thread.start()
        logger.info("✅ ETH transfer polling service started")

    def _perform_initial_catch_up_scan(self):
        """Perform initial catch-up scan for ETH transfers when service starts"""
        try:
            logger.info("🔄 Starting initial ETH transfer catch-up scan...")
            
            # Get current block number
            current_block = self._get_current_block_number()
            if not current_block:
                logger.info("Failure just")
                logger.warning("⚠️ Could not get current block number for initial scan")
                return
            
            # Calculate the range to scan for initial catch-up
            # Use a larger range for initial scan to catch up on missed transactions
            initial_scan_range = min(1000, self.eth_polling_block_range * 10)  # Scan more blocks initially
            from_block = max(1, current_block - initial_scan_range)
            to_block = current_block
            
            logger.info(f"🔍 Initial catch-up scan: scanning blocks {from_block} to {to_block} ({initial_scan_range} blocks)")
            
            # Perform the initial scan with timeout protection
            start_time = time.time()
            max_initial_scan_time = 300  # Maximum 5 minutes for initial scan
            
            # Run initial scan in a separate thread with timeout
            import threading
            import queue
            
            result_queue = queue.Queue()
            
            def run_initial_scan():
                try:
                    transfers_found = self._scan_eth_transfers_for_range_with_stats(from_block, to_block)
                    result_queue.put(("success", transfers_found))
                except Exception as e:
                    result_queue.put(("error", str(e)))
            
            scan_thread = threading.Thread(target=run_initial_scan)
            scan_thread.daemon = True
            scan_thread.start()
            
            # Wait for completion or timeout
            scan_thread.join(timeout=max_initial_scan_time)
            
            if scan_thread.is_alive():
                logger.warning(f"⏰ Initial scan taking too long ({max_initial_scan_time}s), stopping early")
                transfers_found = 0
            else:
                try:
                    result_type, result_data = result_queue.get_nowait()
                    if result_type == "success":
                        transfers_found = result_data
                    else:
                        logger.error(f"❌ Initial scan failed: {result_data}")
                        transfers_found = 0
                except queue.Empty:
                    transfers_found = 0
            
            scan_duration = time.time() - start_time
            
            logger.info(f"✅ Initial catch-up scan completed in {scan_duration:.2f}s")
            logger.info(f"   - Blocks scanned: {initial_scan_range}")
            logger.info(f"   - ETH transfers found: {transfers_found}")
            logger.info(f"   - Scan rate: {initial_scan_range / scan_duration:.1f} blocks/second")
            
            if transfers_found > 0:
                logger.info(f"💰 Found {transfers_found} missed ETH transfers during initial scan")
            else:
                logger.info("ℹ️ No missed ETH transfers found during initial scan")
                
        except Exception as e:
            logger.error(f"❌ Error during initial catch-up scan: {e}")
            # Don't fail the service startup, just log the error

    def _update_cycle_duration_average(self, cycle_duration: float):
        """Update the average cycle duration calculation"""
        if not hasattr(self, '_cycle_durations'):
            self._cycle_durations = []
        
        # Keep only last 10 cycle durations for rolling average
        self._cycle_durations.append(cycle_duration)
        if len(self._cycle_durations) > 10:
            self._cycle_durations.pop(0)
        
        # Calculate average
        self._average_cycle_duration = sum(self._cycle_durations) / len(self._cycle_durations)

    def stop_eth_transfer_polling(self):
        """Stop the ETH transfer polling service"""
        if hasattr(self, 'eth_polling_thread') and self.eth_polling_thread.is_alive():
            logger.info("🛑 Stopping ETH transfer polling service")
            self.is_running = False
            # Wait for the thread to finish (with timeout)
            self.eth_polling_thread.join(timeout=10)
            if self.eth_polling_thread.is_alive():
                logger.warning("⚠️ ETH transfer polling thread did not stop gracefully")
            else:
                logger.info("✅ ETH transfer polling service stopped")
        else:
            logger.info("ℹ️ ETH transfer polling service was not running")

    def get_eth_polling_status(self):
        """Get the current status of ETH transfer polling"""
        status = {
            "enabled": self.eth_polling_enabled,
            "interval_seconds": self.eth_polling_interval,
            "block_range": self.eth_polling_block_range,
            "is_running": hasattr(self, 'eth_polling_thread') and self.eth_polling_thread.is_alive() if hasattr(self, 'eth_polling_thread') else False,
            "last_poll_time": getattr(self, '_last_eth_poll_time', None),
            "total_blocks_scanned": getattr(self, '_total_blocks_scanned', 0),
            "total_eth_transfers_found": getattr(self, '_total_eth_transfers_found', 0)
        }
        return status

    def get_eth_polling_detailed_stats(self):
        """Get detailed statistics about ETH transfer polling"""
        stats = self.get_eth_polling_status()
        stats.update({
            "total_errors": getattr(self, '_eth_polling_errors', 0),
            "uptime_seconds": time.time() - getattr(self, '_eth_polling_start_time', time.time()) if hasattr(self, '_eth_polling_start_time') else 0,
            "average_blocks_per_cycle": self._total_blocks_scanned / max(1, getattr(self, '_eth_polling_cycles', 1)) if hasattr(self, '_eth_polling_cycles') else 0,
            "average_transfers_per_cycle": self._total_eth_transfers_found / max(1, getattr(self, '_eth_polling_cycles', 1)) if hasattr(self, '_eth_polling_cycles') else 0,
            "success_rate": max(0, 100 - (self._eth_polling_errors / max(1, getattr(self, '_eth_polling_cycles', 1)) * 100)) if hasattr(self, '_eth_polling_cycles') else 100
        })
        return stats

    def trigger_eth_transfer_polling_cycle(self):
        """Manually trigger a single ETH transfer polling cycle"""
        if not self.eth_polling_enabled:
            logger.warning("⚠️ ETH transfer polling is disabled")
            return False
            
        try:
            logger.info("🔄 Manually triggering ETH transfer polling cycle")
            
            # Get current block number
            current_block = self._get_current_block_number()
            if not current_block:
                logger.error("❌ Could not get current block number for manual polling")
                return False
            
            # Poll for ETH transfers in recent blocks using configured range
            from_block = max(1, current_block - self.eth_polling_block_range)
            to_block = current_block
            
            logger.info(f"🔍 Manual ETH transfer polling for blocks {from_block} to {to_block}")
            
            # Track polling time
            poll_start_time = time.time()
            
            # Scan for ETH transfers
            transfers_found = self._scan_eth_transfers_for_range_with_stats(from_block, to_block)
            
            # Update statistics and cycle count
            poll_duration = time.time() - poll_start_time
            self._total_blocks_scanned += (to_block - from_block + 1)
            self._total_eth_transfers_found += transfers_found
            self._update_polling_cycle_count()
            
            logger.info(f"✅ Manual ETH transfer polling cycle {self._eth_polling_cycles} completed in {poll_duration:.2f}s")
            logger.info(f"   - Blocks scanned: {to_block - from_block + 1}")
            logger.info(f"   - ETH transfers found: {transfers_found}")
            logger.info(f"   - Total blocks scanned: {self._total_blocks_scanned}")
            logger.info(f"   - Total ETH transfers found: {self._total_eth_transfers_found}")
            logger.info(f"   - Total cycles completed: {self._eth_polling_cycles}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during manual ETH transfer polling: {e}")
            return False

    def configure_eth_polling(self, enabled: bool = None, interval_seconds: int = None, block_range: int = None):
        """Configure ETH transfer polling parameters"""
        if enabled is not None:
            self.eth_polling_enabled = enabled
            logger.info(f"🔄 ETH transfer polling {'enabled' if enabled else 'disabled'}")
        
        if interval_seconds is not None:
            if interval_seconds < 60:  # Minimum 1 minute
                logger.warning("⚠️ Polling interval too short, setting to minimum 60 seconds")
                interval_seconds = 60
            self.eth_polling_interval = interval_seconds
            logger.info(f"⏱️  ETH transfer polling interval set to {interval_seconds} seconds")
        
        if block_range is not None:
            if block_range < 1 or block_range > 100:  # Reasonable limits
                logger.warning("⚠️ Block range out of bounds, setting to 10")
                block_range = 10
            self.eth_polling_block_range = block_range
            logger.info(f"📦 ETH transfer polling block range set to {block_range} blocks")

    def reset_eth_polling_stats(self):
        """Reset ETH transfer polling statistics"""
        logger.info("🔄 Resetting ETH transfer polling statistics")
        self._last_eth_polling_time = None
        self._total_blocks_scanned = 0
        self._total_eth_transfers_found = 0
        self._eth_polling_errors = 0
        self._eth_polling_cycles = 0
        logger.info("✅ ETH transfer polling statistics reset")

    def get_eth_polling_config(self):
        """Get the current ETH transfer polling configuration"""
        config = {
            "enabled": self.eth_polling_enabled,
            "interval_seconds": self.eth_polling_interval,
            "block_range": self.eth_polling_block_range,
            "min_interval_seconds": 60,
            "max_block_range": 100,
            "description": "ETH transfer polling configuration for regular ETH transfers (non-ERC20)"
        }
        return config

    def pause_eth_transfer_polling(self):
        """Pause ETH transfer polling temporarily"""
        if hasattr(self, 'eth_polling_thread') and self.eth_polling_thread.is_alive():
            logger.info("⏸️ Pausing ETH transfer polling service")
            self.eth_polling_enabled = False
            logger.info("✅ ETH transfer polling service paused")
        else:
            logger.warning("⚠️ ETH transfer polling service is not running")

    def resume_eth_transfer_polling(self):
        """Resume ETH transfer polling after being paused"""
        if not self.eth_polling_enabled:
            logger.info("▶️ Resuming ETH transfer polling service")
            self.eth_polling_enabled = True
            # Restart polling if thread is not alive
            if not hasattr(self, 'eth_polling_thread') or not self.eth_polling_thread.is_alive():
                self.start_eth_transfer_polling()
            logger.info("✅ ETH transfer polling service resumed")
        else:
            logger.info("ℹ️ ETH transfer polling service is already running")

    def get_eth_polling_health(self):
        """Get the health status of ETH transfer polling service"""
        health = {
            "status": "healthy" if self.eth_polling_enabled and hasattr(self, 'eth_polling_thread') and self.eth_polling_thread.is_alive() else "unhealthy",
            "enabled": self.eth_polling_enabled,
            "thread_alive": hasattr(self, 'eth_polling_thread') and self.eth_polling_thread.is_alive() if hasattr(self, 'eth_polling_thread') else False,
            "last_poll_time": getattr(self, '_last_eth_poll_time', None),
            "last_poll_age_seconds": time.time() - getattr(self, '_last_eth_poll_time', time.time()) if getattr(self, '_last_eth_poll_time', None) else None,
            "total_errors": getattr(self, '_eth_polling_errors', 0),
            "error_rate": (getattr(self, '_eth_polling_errors', 0) / max(1, getattr(self, '_eth_polling_cycles', 1)) * 100) if hasattr(self, '_eth_polling_cycles') else 0,
            "recommendations": []
        }
        
        # Add health recommendations
        if health["total_errors"] > 10:
            health["recommendations"].append("High error rate detected. Consider increasing polling interval or checking API limits.")
        
        if health["last_poll_age_seconds"] and health["last_poll_age_seconds"] > self.eth_polling_interval * 2:
            health["recommendations"].append("Last poll was too long ago. Service may be stuck.")
        
        if not health["thread_alive"] and self.eth_polling_enabled:
            health["recommendations"].append("Polling thread is not alive. Consider restarting the service.")
        
        return health

    def get_eth_polling_summary(self):
        """Get a comprehensive summary of ETH transfer polling capabilities and status"""
        summary = {
            "service": "ETH Transfer Polling Service",
            "description": "Background service that polls Ethereum blocks for regular ETH transfers (non-ERC20)",
            "capabilities": [
                "Automatic block scanning at configurable intervals",
                "Real-time ETH transfer detection",
                "Duplicate transaction prevention",
                "Configurable polling parameters",
                "Health monitoring and statistics",
                "Manual trigger capabilities",
                "Pause/resume functionality"
            ],
            "configuration": self.get_eth_polling_config(),
            "status": self.get_eth_polling_status(),
            "health": self.get_eth_polling_health(),
            "statistics": self.get_eth_polling_detailed_stats(),
            "methods": [
                "start_eth_transfer_polling() - Start the polling service",
                "stop_eth_transfer_polling() - Stop the polling service",
                "pause_eth_transfer_polling() - Pause polling temporarily",
                "resume_eth_transfer_polling() - Resume polling after pause",
                "trigger_eth_transfer_polling_cycle() - Manually trigger a single cycle",
                "configure_eth_polling() - Configure polling parameters",
                "get_eth_polling_status() - Get current status",
                "get_eth_polling_health() - Get health information",
                "get_eth_polling_stats() - Get detailed statistics",
                "reset_eth_polling_stats() - Reset statistics",

            ]
        }
        return summary

    def _update_polling_cycle_count(self):
        """Update the polling cycle counter"""
        if not hasattr(self, '_eth_polling_cycles'):
            self._eth_polling_cycles = 0
        self._eth_polling_cycles += 1

    def _record_polling_start_time(self):
        """Record the start time of ETH transfer polling service"""
        if not hasattr(self, '_eth_polling_start_time'):
            self._eth_polling_start_time = time.time()

    def get_eth_polling_performance_metrics(self):
        """Get real-time performance metrics for ETH transfer polling"""
        try:
            current_time = time.time()
            uptime = current_time - getattr(self, '_eth_polling_start_time', current_time)
            
            # Calculate performance metrics
            metrics = {
                "uptime_seconds": uptime,
                "uptime_formatted": self._format_duration(uptime),
                "cycles_per_hour": (getattr(self, '_eth_polling_cycles', 0) / max(1, uptime / 3600)),
                "blocks_per_second": (getattr(self, '_total_blocks_scanned', 0) / max(1, uptime)),
                "transfers_per_second": (getattr(self, '_total_eth_transfers_found', 0) / max(1, uptime)),
                "efficiency_score": self._calculate_efficiency_score(),
                "memory_usage_mb": self._get_memory_usage(),
                "last_cycle_performance": {
                    "duration": getattr(self, '_last_cycle_duration', 0),
                    "blocks_scanned": getattr(self, '_last_cycle_blocks_scanned', 0),
                    "transfers_found": getattr(self, '_last_cycle_transfers_found', 0)
                },
                "average_performance": {
                    "cycle_duration": getattr(self, '_average_cycle_duration', 0),
                    "blocks_per_cycle": (getattr(self, '_total_blocks_scanned', 0) / max(1, getattr(self, '_eth_polling_cycles', 1))),
                    "transfers_per_cycle": (getattr(self, '_total_eth_transfers_found', 0) / max(1, getattr(self, '_eth_polling_cycles', 1)))
                }
            }
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Error getting ETH polling performance metrics: {e}")
            return {"error": str(e)}
    
    def _calculate_efficiency_score(self) -> float:
        """Calculate an efficiency score based on performance metrics"""
        try:
            if not hasattr(self, '_eth_polling_cycles') or self._eth_polling_cycles == 0:
                return 0.0
            
            # Base score starts at 100
            score = 100.0
            
            # Deduct points for errors (max 30 points)
            error_rate = getattr(self, '_eth_polling_errors', 0) / self._eth_polling_cycles
            score -= min(30, error_rate * 100)
            
            # Deduct points for slow cycles (max 20 points)
            avg_cycle_time = getattr(self, '_average_cycle_duration', 0)
            if avg_cycle_time > 60:  # More than 1 minute per cycle
                score -= min(20, (avg_cycle_time - 60) / 10)
            
            # Deduct points for low transfer detection (max 20 points)
            blocks_scanned = getattr(self, '_total_blocks_scanned', 0)
            transfers_found = getattr(self, '_total_eth_transfers_found', 0)
            if blocks_scanned > 0:
                transfer_rate = transfers_found / blocks_scanned
                if transfer_rate < 0.01:  # Less than 1% of blocks have transfers
                    score -= min(20, (0.01 - transfer_rate) * 2000)
            
            # Deduct points for memory usage (max 10 points)
            memory_mb = self._get_memory_usage()
            if memory_mb > 100:  # More than 100MB
                score -= min(10, (memory_mb - 100) / 10)
            
            return max(0.0, score)
            
        except Exception as e:
            logger.error(f"❌ Error calculating efficiency score: {e}")
            return 0.0

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        try:
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                minutes = seconds / 60
                return f"{minutes:.1f}m"
            else:
                hours = seconds / 3600
                return f"{hours:.1f}h"
        except Exception:
            return "N/A"

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return round(memory_info.rss / 1024 / 1024, 2)  # Convert to MB
        except ImportError:
            # psutil not available, return estimate
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error getting memory usage: {e}")
            return 0.0
    
    def get_eth_polling_recommendations(self) -> dict:
        """Get actionable recommendations for improving ETH transfer polling performance"""
        try:
            recommendations = {
                "performance": [],
                "configuration": [],
                "monitoring": [],
                "maintenance": []
            }
            
            # Performance recommendations
            avg_cycle_duration = getattr(self, '_average_cycle_duration', 0)
            if avg_cycle_duration > 120:  # More than 2 minutes
                recommendations["performance"].append({
                    "priority": "high",
                    "issue": "Slow polling cycles detected",
                    "recommendation": "Consider reducing block range or optimizing block scanning logic",
                    "impact": "High - affects real-time transfer detection"
                })
            
            error_rate = getattr(self, '_eth_polling_errors', 0) / max(1, getattr(self, '_eth_polling_cycles', 1))
            if error_rate > 0.1:  # More than 10% errors
                recommendations["performance"].append({
                    "priority": "high",
                    "issue": "High error rate detected",
                    "recommendation": "Check network connectivity and API rate limits",
                    "impact": "High - affects service reliability"
                })
            
            # Configuration recommendations
            if self.eth_polling_block_range > 500:
                recommendations["configuration"].append({
                    "priority": "medium",
                    "issue": "Large block range may cause timeouts",
                    "recommendation": "Consider reducing block range to 200-300 blocks",
                    "impact": "Medium - may improve reliability"
                })
            
            if self.eth_polling_interval < 60:
                recommendations["configuration"].append({
                    "priority": "medium",
                    "issue": "Very frequent polling may hit rate limits",
                    "recommendation": "Consider increasing interval to at least 60 seconds",
                    "impact": "Medium - may improve stability"
                })
            
            # Monitoring recommendations
            if not hasattr(self, '_eth_polling_start_time') or getattr(self, '_eth_polling_start_time', 0) == 0:
                recommendations["monitoring"].append({
                    "priority": "low",
                    "issue": "Missing start time tracking",
                    "recommendation": "Ensure proper initialization of timing variables",
                    "impact": "Low - affects metrics accuracy"
                })
            
            # Maintenance recommendations
            uptime = time.time() - getattr(self, '_eth_polling_start_time', time.time())
            if uptime > 86400:  # More than 24 hours
                recommendations["maintenance"].append({
                    "priority": "low",
                    "issue": "Service has been running for over 24 hours",
                    "recommendation": "Consider scheduled restart to refresh connections",
                    "impact": "Low - may improve stability"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Error getting recommendations: {e}")
            return {"error": str(e)}

    def validate_eth_polling_config(self, enabled: bool = None, interval_seconds: int = None, block_range: int = None) -> dict:
        """Validate ETH transfer polling configuration parameters"""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Validate enabled flag
        if enabled is not None and not isinstance(enabled, bool):
            validation_results["valid"] = False
            validation_results["errors"].append("enabled must be a boolean value")
        
        # Validate interval
        if interval_seconds is not None:
            if not isinstance(interval_seconds, int) or interval_seconds < 60:
                validation_results["valid"] = False
                validation_results["errors"].append("interval_seconds must be an integer >= 60")
            elif interval_seconds < 300:
                validation_results["warnings"].append("interval_seconds < 300 may cause high API usage")
            elif interval_seconds > 3600:
                validation_results["warnings"].append("interval_seconds > 3600 may miss recent transactions")
        
        # Validate block range
        if block_range is not None:
            if not isinstance(block_range, int) or block_range < 10:
                validation_results["valid"] = False
                validation_results["errors"].append("block_range must be an integer >= 10")
            elif block_range > 1000:
                validation_results["warnings"].append("block_range > 1000 may cause long scan times")
            elif block_range < 50:
                validation_results["warnings"].append("block_range < 50 may miss transactions in high-activity periods")
        
        # Add recommendations
        if validation_results["valid"]:
            if interval_seconds is None or interval_seconds < 300:
                validation_results["recommendations"].append("Consider using interval_seconds >= 300 for production environments")
            if block_range is None or block_range < 100:
                validation_results["recommendations"].append("Consider using block_range >= 100 for better coverage")
        
        return validation_results

    def get_eth_polling_dashboard(self) -> dict:
        """Get a comprehensive dashboard view of ETH transfer polling system"""
        try:
            # Get all available data
            status = self.get_eth_polling_status()
            detailed_stats = self.get_eth_polling_detailed_stats()
            performance_metrics = self.get_eth_polling_performance_metrics()
            config = self.get_eth_polling_config()
            health = self.get_eth_polling_health()
            recommendations = self.get_eth_polling_recommendations()
            
            # Create dashboard
            dashboard = {
                "timestamp": time.time(),
                "timestamp_formatted": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "overview": {
                    "service_status": "🟢 Active" if status.get("is_running") else "🔴 Inactive",
                    "polling_enabled": status.get("enabled"),
                    "current_cycle": detailed_stats.get("total_cycles", 0),
                    "uptime": performance_metrics.get("uptime_formatted", "N/A"),
                    "efficiency_score": f"{performance_metrics.get('efficiency_score', 0):.1f}/100"
                },
                "performance": {
                    "current_metrics": performance_metrics,
                    "health_status": health,
                    "recommendations": recommendations
                },
                "statistics": {
                    "blocks_scanned": status.get("total_blocks_scanned", 0),
                    "transfers_found": status.get("total_eth_transfers_found", 0),
                    "errors_encountered": detailed_stats.get("total_errors", 0),
                    "success_rate": f"{detailed_stats.get('success_rate', 100):.1f}%"
                },
                "configuration": config,
                "real_time": {
                    "last_poll_time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(status.get("last_poll_time"))) if status.get("last_poll_time") else "Never",
                    "next_poll_in": self._calculate_next_poll_time(),
                    "current_block": self._get_current_block_number(),
                    "memory_usage": f"{performance_metrics.get('memory_usage_mb', 0):.1f} MB"
                },
                "alerts": self._get_eth_polling_alerts(),
                "quick_actions": {
                    "trigger_cycle": "POST /api/eth-polling/trigger",
                    "pause_service": "POST /api/eth-polling/pause",
                    "resume_service": "POST /api/eth-polling/resume",
                    "reset_stats": "POST /api/eth-polling/reset-stats",
                    "configure": "POST /api/eth-polling/configure"
                }
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"❌ Error getting ETH polling dashboard: {e}")
            return {"error": str(e)}
    
    def _calculate_next_poll_time(self) -> str:
        """Calculate when the next polling cycle will occur"""
        try:
            if not hasattr(self, '_last_eth_poll_time') or not self._last_eth_poll_time:
                return "Unknown"
            
            next_poll = self._last_eth_poll_time + self.eth_polling_interval
            time_until = next_poll - time.time()
            
            if time_until <= 0:
                return "Due now"
            elif time_until < 60:
                return f"{int(time_until)} seconds"
            elif time_until < 3600:
                return f"{int(time_until / 60)} minutes"
            else:
                return f"{int(time_until / 3600)} hours"
                
        except Exception as e:
            logger.error(f"❌ Error calculating next poll time: {e}")
            return "Error"
    
    def _get_eth_polling_alerts(self) -> list:
        """Get current alerts for the ETH polling system"""
        alerts = []
        
        try:
            # Check for high error rate
            if hasattr(self, '_eth_polling_errors') and hasattr(self, '_eth_polling_cycles'):
                if self._eth_polling_cycles > 0:
                    error_rate = (self._eth_polling_errors / self._eth_polling_cycles) * 100
                    if error_rate > 20:
                        alerts.append({
                            "level": "high",
                            "type": "error_rate",
                            "message": f"High error rate: {error_rate:.1f}%",
                            "recommendation": "Check network connectivity and API limits"
                        })
            
            # Check for slow cycles
            if hasattr(self, '_average_cycle_duration'):
                if self._average_cycle_duration > 120:
                    alerts.append({
                        "level": "medium",
                        "type": "performance",
                        "message": f"Slow polling cycles: {self._average_cycle_duration:.1f}s average",
                        "recommendation": "Consider reducing block range or increasing interval"
                    })
            
            # Check for memory usage
            memory_mb = self._get_memory_usage()
            if memory_mb > 200:
                alerts.append({
                    "level": "medium",
                    "type": "memory",
                    "message": f"High memory usage: {memory_mb:.1f} MB",
                    "recommendation": "Monitor for memory leaks"
                })
            
            # Check for no transfers found
            if hasattr(self, '_total_blocks_scanned') and hasattr(self, '_total_eth_transfers_found'):
                if self._total_blocks_scanned > 1000 and self._total_eth_transfers_found == 0:
                    alerts.append({
                        "level": "low",
                        "type": "detection",
                        "message": "No ETH transfers detected in many blocks",
                        "recommendation": "Verify monitored addresses and network activity"
                    })
            
        except Exception as e:
            logger.error(f"❌ Error getting ETH polling alerts: {e}")
            alerts.append({
                "level": "high",
                "type": "system",
                "message": f"Error generating alerts: {str(e)}",
                "recommendation": "Check system logs"
            })
        
        return alerts

    def export_eth_polling_report(self, format: str = "json") -> str:
        """Export comprehensive ETH transfer polling report"""
        try:
            # Gather all data
            dashboard = self.get_eth_polling_dashboard()
            performance = self.get_eth_polling_performance_metrics()
            health = self.get_eth_polling_health()
            config = self.get_eth_polling_config()
            
            report_data = {
                "report_type": "ETH Transfer Polling Report",
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                "generated_timestamp": time.time(),
                "summary": {
                    "status": dashboard.get("overview", {}).get("service_status", "Unknown"),
                    "efficiency_score": performance.get("efficiency_score", 0),
                    "total_cycles": dashboard.get("overview", {}).get("current_cycle", 0),
                    "uptime": performance.get("uptime_formatted", "N/A"),
                    "total_blocks_scanned": dashboard.get("statistics", {}).get("blocks_scanned", 0),
                    "total_transfers_found": dashboard.get("statistics", {}).get("transfers_found", 0),
                    "success_rate": dashboard.get("statistics", {}).get("success_rate", "0%")
                },
                "performance_analysis": {
                    "current_metrics": performance,
                    "health_status": health,
                    "alerts": dashboard.get("alerts", [])
                },
                "configuration": config,
                "recommendations": dashboard.get("performance", {}).get("recommendations", {}),
                "quick_actions": dashboard.get("quick_actions", {})
            }
            
            if format.lower() == "json":
                return json.dumps(report_data, indent=2, default=str)
            
            elif format.lower() == "csv":
                # Convert to CSV format
                csv_lines = []
                csv_lines.append("Metric,Value")
                csv_lines.append(f"Report Type,{report_data['report_type']}")
                csv_lines.append(f"Generated At,{report_data['generated_at']}")
                csv_lines.append(f"Status,{report_data['summary']['status']}")
                csv_lines.append(f"Efficiency Score,{report_data['summary']['efficiency_score']}")
                csv_lines.append(f"Total Cycles,{report_data['summary']['total_cycles']}")
                csv_lines.append(f"Uptime,{report_data['summary']['uptime']}")
                csv_lines.append(f"Total Blocks Scanned,{report_data['summary']['total_blocks_scanned']}")
                csv_lines.append(f"Total Transfers Found,{report_data['summary']['total_transfers_found']}")
                csv_lines.append(f"Success Rate,{report_data['summary']['success_rate']}")
                
                # Add performance metrics
                for key, value in performance.items():
                    if isinstance(value, (int, float)):
                        csv_lines.append(f"{key},{value}")
                    else:
                        csv_lines.append(f"{key},\"{value}\"")
                
                return "\n".join(csv_lines)
            
            elif format.lower() == "text":
                # Convert to human-readable text format
                lines = []
                lines.append("=" * 60)
                lines.append(f"ETH TRANSFER POLLING REPORT")
                lines.append("=" * 60)
                lines.append(f"Generated: {report_data['generated_at']}")
                lines.append(f"Status: {report_data['summary']['status']}")
                lines.append(f"Efficiency Score: {report_data['summary']['efficiency_score']}/100")
                lines.append("")
                
                lines.append("SUMMARY:")
                lines.append(f"  Total Cycles: {report_data['summary']['total_cycles']}")
                lines.append(f"  Uptime: {report_data['summary']['uptime']}")
                lines.append(f"  Blocks Scanned: {report_data['summary']['total_blocks_scanned']}")
                lines.append(f"  Transfers Found: {report_data['summary']['total_transfers_found']}")
                lines.append(f"  Success Rate: {report_data['summary']['success_rate']}")
                lines.append("")
                
                lines.append("PERFORMANCE METRICS:")
                for key, value in performance.items():
                    if isinstance(value, (int, float)):
                        lines.append(f"  {key}: {value}")
                    else:
                        lines.append(f"  {key}: {value}")
                lines.append("")
                
                if dashboard.get("alerts"):
                    lines.append("ALERTS:")
                    for alert in dashboard["alerts"]:
                        lines.append(f"  [{alert['level'].upper()}] {alert['message']}")
                        lines.append(f"    Recommendation: {alert['recommendation']}")
                    lines.append("")
                
                lines.append("QUICK ACTIONS:")
                for action, endpoint in dashboard.get("quick_actions", {}).items():
                    lines.append(f"  {action}: {endpoint}")
                
                lines.append("=" * 60)
                return "\n".join(lines)
            
            else:
                raise ValueError(f"Unsupported format: {format}. Supported formats: json, csv, text")
                
        except Exception as e:
            logger.error(f"❌ Error exporting ETH transfer polling report: {e}")
            return f"Error exporting report: {str(e)}"
    
    def get_eth_polling_analytics(self) -> dict:
        """Get advanced analytics for ETH transfer polling"""
        try:
            current_time = time.time()
            uptime = current_time - getattr(self, '_eth_polling_start_time', current_time)
            
            # Calculate trends
            analytics = {
                "trends": {
                    "cycles_per_hour": (getattr(self, '_eth_polling_cycles', 0) / max(1, uptime / 3600)),
                    "blocks_per_hour": (getattr(self, '_total_blocks_scanned', 0) / max(1, uptime / 3600)),
                    "transfers_per_hour": (getattr(self, '_total_eth_transfers_found', 0) / max(1, uptime / 3600)),
                    "errors_per_hour": (getattr(self, '_eth_polling_errors', 0) / max(1, uptime / 3600))
                },
                "efficiency_metrics": {
                    "overall_score": self._calculate_efficiency_score(),
                    "block_scanning_efficiency": self._calculate_block_scanning_efficiency(),
                    "transfer_detection_rate": self._calculate_transfer_detection_rate(),
                    "error_tolerance": self._calculate_error_tolerance()
                },
                "performance_benchmarks": {
                    "optimal_cycle_duration": 60,  # 1 minute
                    "optimal_block_range": 100,    # 100 blocks
                    "optimal_interval": 300,       # 5 minutes
                    "current_performance": {
                        "cycle_duration_vs_optimal": getattr(self, '_average_cycle_duration', 0) / 60,
                        "block_range_vs_optimal": self.eth_polling_block_range / 100,
                        "interval_vs_optimal": self.eth_polling_interval / 300
                    }
                },
                "resource_utilization": {
                    "memory_usage_mb": self._get_memory_usage(),
                    "cpu_usage_estimate": self._estimate_cpu_usage(),
                    "network_requests_per_hour": self._estimate_network_requests()
                }
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"❌ Error getting ETH polling analytics: {e}")
            return {"error": str(e)}
    
    def _calculate_block_scanning_efficiency(self) -> float:
        """Calculate efficiency of block scanning operations"""
        try:
            if not hasattr(self, '_eth_polling_cycles') or self._eth_polling_cycles == 0:
                return 0.0
            
            # Ideal: scan 200 blocks in under 60 seconds
            ideal_blocks_per_second = 200 / 60  # 3.33 blocks/second
            actual_blocks_per_second = getattr(self, '_total_blocks_scanned', 0) / max(1, getattr(self, '_eth_polling_start_time', 0))
            
            efficiency = min(100, (actual_blocks_per_second / ideal_blocks_per_second) * 100)
            return max(0, efficiency)
            
        except Exception as e:
            logger.error(f"❌ Error calculating block scanning efficiency: {e}")
            return 0.0
    
    def _calculate_transfer_detection_rate(self) -> float:
        """Calculate the rate of transfer detection vs expected"""
        try:
            # This is more of a monitoring metric than efficiency
            # Normal networks might have 0.1% of blocks with transfers
            expected_rate = 0.001  # 0.1%
            actual_rate = getattr(self, '_total_eth_transfers_found', 0) / max(1, getattr(self, '_total_blocks_scanned', 1))
            
            # Score based on how close we are to expected rate
            if actual_rate >= expected_rate:
                return 100.0  # At or above expected
            else:
                return (actual_rate / expected_rate) * 100
                
        except Exception as e:
            logger.error(f"❌ Error calculating transfer detection rate: {e}")
            return 0.0
    
    def _calculate_error_tolerance(self) -> float:
        """Calculate error tolerance score"""
        try:
            if not hasattr(self, '_eth_polling_cycles') or self._eth_polling_cycles == 0:
                return 100.0
            
            error_rate = getattr(self, '_eth_polling_errors', 0) / self._eth_polling_cycles
            
            # Perfect: 0% errors = 100 points
            # Acceptable: 5% errors = 80 points
            # Poor: 20% errors = 0 points
            if error_rate <= 0.05:
                return 100 - (error_rate * 400)  # 0-5% = 100-80 points
            else:
                return max(0, 80 - ((error_rate - 0.05) * 533))  # 5-20% = 80-0 points
                
        except Exception as e:
            logger.error(f"❌ Error calculating error tolerance: {e}")
            return 0.0
    
    def _estimate_cpu_usage(self) -> float:
        """Estimate CPU usage based on cycle duration and frequency"""
        try:
            if not hasattr(self, '_average_cycle_duration'):
                return 0.0
            
            # Rough estimate: if we spend 30s scanning every 5 minutes = 10% CPU
            cycle_duration = getattr(self, '_average_cycle_duration', 0)
            interval = self.eth_polling_interval
            
            if interval > 0:
                cpu_percentage = (cycle_duration / interval) * 100
                return min(100, cpu_percentage)
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ Error estimating CPU usage: {e}")
            return 0.0
    
    def _estimate_network_requests(self) -> int:
        """Estimate network requests per hour"""
        try:
            # Each polling cycle makes approximately:
            # - 1 request to get current block
            # - 1 request per block in range to get block data
            # - Additional requests for transaction details if transfers found
            
            blocks_per_cycle = self.eth_polling_block_range
            cycles_per_hour = 3600 / self.eth_polling_interval
            
            base_requests = cycles_per_hour * (1 + blocks_per_cycle)  # block + current block
            transfer_requests = getattr(self, '_total_eth_transfers_found', 0) * 0.1  # Estimate 10% need additional requests
            
            return int(base_requests + transfer_requests)
            
        except Exception as e:
            logger.error(f"❌ Error estimating network requests: {e}")
            return 0

    def _handle_polling_error(self, error: Exception, context: str = "unknown") -> bool:
        """Handle polling errors with retry logic and circuit breaker"""
        try:
            # Record error
            if not hasattr(self, '_eth_polling_errors'):
                self._eth_polling_errors = 0
            self._eth_polling_errors += 1
            
            # Log error with context
            logger.error(f"❌ ETH polling error in {context}: {error}")
            logger.error(f"   Error type: {type(error).__name__}")
            logger.error(f"   Error details: {str(error)}")
            
            # Check if we should trigger circuit breaker
            if self._check_circuit_breaker():
                logger.warning("🚨 Circuit breaker triggered - pausing polling temporarily")
                self.pause_eth_transfer_polling()
                return False
            
            # Attempt automatic retry for recoverable errors
            if self._is_recoverable_error(error):
                logger.info("🔄 Attempting automatic retry for recoverable error")
                self._retry_polling_cycle()
                return True
            
            # For non-recoverable errors, log and continue
            logger.warning(f"⚠️ Non-recoverable error in {context}, continuing with next cycle")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in error handler: {e}")
            return False

    def _is_recoverable_error(self, error: Exception) -> bool:
        """Determine if an error is recoverable"""
        recoverable_errors = [
            'ConnectionError', 'TimeoutError', 'requests.exceptions.RequestException',
            'websocket.WebSocketConnectionClosedException', 'json.JSONDecodeError'
        ]
        
        error_type = type(error).__name__
        return any(recoverable in error_type for recoverable in recoverable_errors)

    def _retry_polling_cycle(self):
        """Retry the current polling cycle with exponential backoff"""
        try:
            if not hasattr(self, '_retry_count'):
                self._retry_count = 0
            if not hasattr(self, '_last_retry_time'):
                self._last_retry_time = 0
            
            current_time = time.time()
            time_since_last_retry = current_time - self._last_retry_time
            
            # Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 60s
            backoff_delay = min(60, 2 ** self._retry_count)
            
            if time_since_last_retry >= backoff_delay:
                logger.info(f"🔄 Retrying polling cycle (attempt {self._retry_count + 1})")
                self._last_retry_time = current_time
                self._retry_count += 1
                
                # Trigger a new polling cycle
                self.trigger_eth_transfer_polling_cycle()
                
                # Reset retry count on success
                if self._retry_count > 0:
                    self._retry_count = 0
            else:
                logger.debug(f"⏳ Waiting for backoff delay ({backoff_delay - time_since_last_retry:.1f}s remaining)")
                
        except Exception as e:
            logger.error(f"❌ Error in retry logic: {e}")

    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be triggered"""
        try:
            if not hasattr(self, '_eth_polling_errors'):
                return False
            
            # Trigger circuit breaker if error rate > 50% in last 10 cycles
            recent_cycles = min(10, getattr(self, '_eth_polling_cycles', 1))
            error_rate = self._eth_polling_errors / max(1, recent_cycles)
            
            return error_rate > 0.5
            
        except Exception as e:
            logger.error(f"❌ Error checking circuit breaker: {e}")
            return False

    def _get_adaptive_polling_interval(self) -> int:
        """Get adaptive polling interval based on performance"""
        try:
            base_interval = self.eth_polling_interval
            
            # Adjust based on error rate
            if hasattr(self, '_eth_polling_errors') and hasattr(self, '_eth_polling_cycles'):
                error_rate = self._eth_polling_errors / max(1, self._eth_polling_cycles)
                if error_rate > 0.3:  # High error rate
                    base_interval = min(600, base_interval * 1.5)  # Increase interval
                elif error_rate < 0.1:  # Low error rate
                    base_interval = max(60, base_interval * 0.8)   # Decrease interval
            
            # Adjust based on performance
            avg_cycle_duration = getattr(self, '_average_cycle_duration', 0)
            if avg_cycle_duration > 120:  # Slow cycles
                base_interval = min(600, base_interval * 1.2)
            elif avg_cycle_duration < 30:  # Fast cycles
                base_interval = max(60, base_interval * 0.9)
            
            return int(base_interval)
            
        except Exception as e:
            logger.error(f"❌ Error calculating adaptive interval: {e}")
            return self.eth_polling_interval

    def _get_adaptive_block_range(self) -> int:
        """Get adaptive block range based on performance"""
        try:
            base_range = self.eth_polling_block_range
            
            # Adjust based on cycle duration
            avg_cycle_duration = getattr(self, '_average_cycle_duration', 0)
            if avg_cycle_duration > 120:  # Slow cycles
                base_range = max(50, base_range * 0.8)  # Reduce block range
            elif avg_cycle_duration < 30:  # Fast cycles
                base_range = min(500, base_range * 1.2)  # Increase block range
            
            # Adjust based on transfer detection rate
            if hasattr(self, '_total_blocks_scanned') and hasattr(self, '_total_eth_transfers_found'):
                blocks_scanned = self._total_blocks_scanned
                transfers_found = self._total_eth_transfers_found
                if blocks_scanned > 0:
                    transfer_rate = transfers_found / blocks_scanned
                    if transfer_rate < 0.01:  # Low transfer rate
                        base_range = min(500, base_range * 1.1)  # Increase range
                    elif transfer_rate > 0.1:  # High transfer rate
                        base_range = max(50, base_range * 0.9)   # Decrease range
            
            return int(base_range)
            
        except Exception as e:
            logger.error(f"❌ Error calculating adaptive block range: {e}")
            return self.eth_polling_block_range

    def auto_optimize_polling_config(self) -> dict:
        """Automatically optimize polling configuration based on performance metrics"""
        try:
            logger.info("🔧 Running automatic polling configuration optimization")
            
            # Get current performance metrics
            current_metrics = self.get_eth_polling_performance_metrics()
            efficiency_score = current_metrics.get('efficiency_score', 0)
            
            # Calculate optimal settings
            optimal_interval = self._get_adaptive_polling_interval()
            optimal_block_range = self._get_adaptive_block_range()
            
            # Apply optimizations if they differ significantly from current settings
            changes_made = []
            
            if abs(optimal_interval - self.eth_polling_interval) > 30:  # 30 second threshold
                old_interval = self.eth_polling_interval
                self.eth_polling_interval = optimal_interval
                changes_made.append(f"Polling interval: {old_interval}s → {optimal_interval}s")
            
            if abs(optimal_block_range - self.eth_polling_block_range) > 20:  # 20 block threshold
                old_range = self.eth_polling_block_range
                self.eth_polling_block_range = optimal_block_range
                changes_made.append(f"Block range: {old_range} → {optimal_block_range}")
            
            # Update configuration
            if changes_made:
                logger.info("✅ Applied automatic optimizations:")
                for change in changes_made:
                    logger.info(f"   - {change}")
                
                # Reset stats to measure new performance
                self.reset_eth_polling_stats()
            else:
                logger.info("✅ Configuration is already optimal")
            
            return {
                "optimization_applied": len(changes_made) > 0,
                "changes": changes_made,
                "new_interval": self.eth_polling_interval,
                "new_block_range": self.eth_polling_block_range,
                "efficiency_score": efficiency_score
            }
            
        except Exception as e:
            logger.error(f"❌ Error in auto-optimization: {e}")
            return {"error": str(e)}

    def get_enhanced_health_status(self) -> dict:
        """Get enhanced health status with circuit breaker and adaptive configuration info"""
        try:
            base_health = self.get_eth_polling_health()
            
            # Add circuit breaker status
            circuit_breaker_triggered = self._check_circuit_breaker()
            
            # Add adaptive configuration info
            adaptive_interval = self._get_adaptive_polling_interval()
            adaptive_block_range = self._get_adaptive_block_range()
            
            # Add retry information
            retry_count = getattr(self, '_retry_count', 0)
            last_retry_time = getattr(self, '_last_retry_time', 0)
            
            enhanced_status = {
                **base_health,
                "circuit_breaker": {
                    "triggered": circuit_breaker_triggered,
                    "error_rate": (getattr(self, '_eth_polling_errors', 0) / max(1, getattr(self, '_eth_polling_cycles', 1))),
                    "threshold": 0.5
                },
                "adaptive_configuration": {
                    "current_interval": self.eth_polling_interval,
                    "optimal_interval": adaptive_interval,
                    "current_block_range": self.eth_polling_block_range,
                    "optimal_block_range": adaptive_block_range,
                    "needs_optimization": (
                        abs(adaptive_interval - self.eth_polling_interval) > 30 or
                        abs(adaptive_block_range - self.eth_polling_block_range) > 20
                    )
                },
                "retry_mechanism": {
                    "retry_count": retry_count,
                    "last_retry": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_retry_time)) if last_retry_time > 0 else "Never",
                    "backoff_delay": min(60, 2 ** retry_count) if retry_count > 0 else 0
                },
                "recovery_status": {
                    "auto_retry_enabled": True,
                    "circuit_breaker_enabled": True,
                    "adaptive_config_enabled": True
                }
            }
            
            return enhanced_status
            
        except Exception as e:
            logger.error(f"❌ Error getting enhanced health status: {e}")
            return {"error": str(e)}

    def cli_interface(self):
        """Simple CLI interface for ETH transfer polling management"""
        print("\n" + "="*60)
        print("🔍 ETH TRANSFER POLLING CLI INTERFACE")
        print("="*60)
        
        while True:
            print("\nAvailable commands:")
            print("1. status     - Show current status")
            print("2. stats      - Show detailed statistics")
            print("3. health     - Show health status")
            print("4. dashboard  - Show comprehensive dashboard")
            print("5. analytics  - Show performance analytics")
            print("6. config     - Show current configuration")
            print("7. start      - Start polling service")
            print("8. stop       - Stop polling service")
            print("9. pause      - Pause polling service")
            print("10. resume    - Resume polling service")
            print("11. restart   - Restart polling service")
            print("12. trigger   - Trigger manual polling cycle")
            print("13. optimize  - Auto-optimize configuration")
            print("14. export    - Export report (json/csv/text)")
            print("15. reset     - Reset statistics")
            print("16. help      - Show this help")
            print("17. quit      - Exit CLI")
            print("18. circuit   - Show circuit breaker status")
            print("19. adaptive  - Show adaptive configuration")
            print("20. auto-opt  - Run auto-optimization")
            print("21. enhanced  - Show enhanced health status")
            
            try:
                command = input("\nEnter command (1-21): ").strip().lower()
                
                if command in ['1', 'status']:
                    status = self.get_eth_polling_status()
                    print(f"\n📊 STATUS: {status['status']}")
                    print(f"🔄 Current Cycle: {status['current_cycle']}")
                    print(f"⏰ Last Poll: {status['last_poll_time']}")
                    print(f"⏱️  Next Poll: {status['next_poll_time']}")
                
                elif command in ['2', 'stats']:
                    stats = self.get_eth_polling_detailed_stats()
                    print(f"\n📈 DETAILED STATISTICS:")
                    print(f"   Total Cycles: {stats['total_cycles']}")
                    print(f"   Blocks Scanned: {stats['blocks_scanned']}")
                    print(f"   Transfers Found: {stats['transfers_found']}")
                    print(f"   Total Errors: {stats['total_errors']}")
                    print(f"   Success Rate: {stats['success_rate']}")
                    print(f"   Average Cycle Duration: {stats['average_cycle_duration']:.1f}s")
                
                elif command in ['3', 'health']:
                    health = self.get_eth_polling_health()
                    print(f"\n🏥 HEALTH STATUS: {health['service_status'].upper()}")
                    print(f"   Overall Score: {health['overall_score']}/100")
                    for check_name, check_data in health['checks'].items():
                        status_icon = "✅" if check_data['status'] == 'healthy' else "⚠️" if check_data['status'] == 'warning' else "❌"
                        print(f"   {status_icon} {check_name}: {check_data['message']}")
                
                elif command in ['4', 'dashboard']:
                    dashboard = self.get_eth_polling_dashboard()
                    print(f"\n🎯 DASHBOARD OVERVIEW:")
                    print(f"   Service Status: {dashboard['overview']['service_status']}")
                    print(f"   Efficiency Score: {dashboard['overview']['efficiency_score']}/100")
                    print(f"   Current Cycle: {dashboard['overview']['current_cycle']}")
                    print(f"   Uptime: {dashboard['overview']['uptime']}")
                    
                    if dashboard.get('alerts'):
                        print(f"\n🚨 ALERTS:")
                        for alert in dashboard['alerts']:
                            level_icon = "🔴" if alert['level'] == 'critical' else "🟡" if alert['level'] == 'warning' else "🔵"
                            print(f"   {level_icon} [{alert['level'].upper()}] {alert['message']}")
                
                elif command in ['5', 'analytics']:
                    analytics = self.get_eth_polling_analytics()
                    print(f"\n📊 PERFORMANCE ANALYTICS:")
                    print(f"   Overall Efficiency: {analytics['efficiency_metrics']['overall_score']}/100")
                    print(f"   Block Scanning: {analytics['efficiency_metrics']['block_scanning_efficiency']:.1f}/100")
                    print(f"   Error Tolerance: {analytics['efficiency_metrics']['error_tolerance']:.1f}/100")
                    print(f"   Estimated CPU Usage: {analytics['resource_utilization']['cpu_usage_estimate']:.1f}%")
                    print(f"   Network Requests/Hour: {analytics['resource_utilization']['network_requests_per_hour']}")
                
                elif command in ['6', 'config']:
                    config = self.get_eth_polling_config()
                    print(f"\n⚙️  CONFIGURATION:")
                    print(f"   Enabled: {config['enabled']}")
                    print(f"   Interval: {config['interval_seconds']} seconds")
                    print(f"   Block Range: {config['block_range']} blocks")
                    print(f"   Next Poll: {config['next_poll_time']}")
                
                elif command in ['7', 'start']:
                    if self.eth_polling_enabled:
                        self.start_eth_transfer_polling()
                        print("✅ ETH transfer polling service started")
                    else:
                        print("❌ Service is disabled. Enable it first with configure command.")
                
                elif command in ['8', 'stop']:
                    self.stop_eth_transfer_polling()
                    print("🛑 ETH transfer polling service stopped")
                
                elif command in ['9', 'pause']:
                    self.pause_eth_transfer_polling()
                    print("⏸️  ETH transfer polling service paused")
                
                elif command in ['10', 'resume']:
                    self.resume_eth_transfer_polling()
                    print("▶️  ETH transfer polling service resumed")
                
                elif command in ['11', 'restart']:
                    self.stop_eth_transfer_polling()
                    time.sleep(2)
                    self.start_eth_transfer_polling()
                    print("🔄 ETH transfer polling service restarted")
                
                elif command in ['12', 'trigger']:
                    print("🔍 Triggering manual polling cycle...")
                    transfers_found = self.trigger_eth_transfer_polling_cycle()
                    print(f"✅ Manual cycle completed. Found {transfers_found} transfers.")
                
                elif command in ['13', 'optimize']:
                    print("🔧 Auto-optimizing configuration...")
                    # Get current performance
                    performance = self.get_eth_polling_performance_metrics()
                    health = self.get_eth_polling_health()
                    
                    if health.get('overall_score', 100) >= 80:
                        print("✅ Performance is already good. No optimization needed.")
                    else:
                        # Apply basic optimizations
                        current_config = self.get_eth_polling_config()
                        optimizations = []
                        
                        # Check cycle duration
                        avg_cycle_duration = performance.get('average_cycle_duration', 0)
                        if avg_cycle_duration > 120:
                            new_block_range = max(100, current_config['block_range'] // 2)
                            if new_block_range != current_config['block_range']:
                                self.eth_polling_block_range = new_block_range
                                optimizations.append(f"Reduced block range to {new_block_range}")
                        
                        # Check error rate
                        error_rate = performance.get('error_rate_percent', 0)
                        if error_rate > 10:
                            new_interval = min(600, current_config['interval_seconds'] * 1.5)
                            if new_interval != current_config['interval_seconds']:
                                self.eth_polling_interval = int(new_interval)
                                optimizations.append(f"Increased interval to {int(new_interval)}s")
                        
                        if optimizations:
                            print("🔧 Applied optimizations:")
                            for opt in optimizations:
                                print(f"   • {opt}")
                            print("🔄 Restarting service to apply changes...")
                            self.stop_eth_transfer_polling()
                            time.sleep(2)
                            self.start_eth_transfer_polling()
                        else:
                            print("ℹ️  No optimizations needed or possible.")
                
                elif command in ['14', 'export']:
                    format_choice = input("Enter format (json/csv/text): ").strip().lower()
                    if format_choice in ['json', 'csv', 'text']:
                        print(f"📤 Exporting report in {format_choice} format...")
                        report = self.export_eth_polling_report(format_choice)
                        if format_choice == 'json':
                            print(json.dumps(json.loads(report), indent=2))
                        else:
                            print(report)
                    else:
                        print("❌ Invalid format. Use json, csv, or text.")
                
                elif command in ['15', 'reset']:
                    confirm = input("Are you sure you want to reset all statistics? (yes/no): ").strip().lower()
                    if confirm == 'yes':
                        self.reset_eth_polling_stats()
                        print("✅ Statistics reset successfully")
                    else:
                        print("❌ Reset cancelled")
                
                elif command in ['16', 'help']:
                    continue  # Show help again
                
                elif command in ['17', 'quit']:
                    print("👋 Exiting CLI interface")
                    break
                
                elif command in ['18', 'circuit']:
                    circuit_status = self._check_circuit_breaker()
                    if circuit_status:
                        time_until_reset = 1800 - (time.time() - getattr(self, '_circuit_breaker_start_time', 0))
                        print(f"\n🔴 CIRCUIT BREAKER STATUS: ACTIVE")
                        print(f"   Time until reset: {max(0, int(time_until_reset))} seconds")
                        print(f"   Errors since trigger: {getattr(self, '_eth_polling_errors', 0)}")
                        print(f"   Service is temporarily paused for safety")
                    else:
                        print(f"\n🟢 CIRCUIT BREAKER STATUS: INACTIVE")
                        print(f"   Service is operating normally")
                        print(f"   Total errors: {getattr(self, '_eth_polling_errors', 0)}")
                
                elif command in ['19', 'adaptive']:
                    print(f"\n🔧 ADAPTIVE CONFIGURATION:")
                    print(f"   Current Interval: {self.eth_polling_interval}s")
                    print(f"   Current Block Range: {self.eth_polling_block_range}")
                    print(f"   Recommended Interval: {self._get_adaptive_polling_interval()}s")
                    print(f"   Recommended Block Range: {self._get_adaptive_block_range()}")
                    
                    needs_optimization = (
                        self._get_adaptive_polling_interval() != self.eth_polling_interval or
                        self._get_adaptive_block_range() != self.eth_polling_block_range
                    )
                    
                    if needs_optimization:
                        print(f"   ⚠️  Optimization recommended")
                        print(f"   Run 'auto-opt' command to apply changes")
                    else:
                        print(f"   ✅ Configuration is optimal")
                
                elif command in ['20', 'auto-opt']:
                    print("🔧 Running automatic optimization...")
                    result = self.auto_optimize_polling_config()
                    
                    if 'error' in result:
                        print(f"❌ Optimization failed: {result['error']}")
                    else:
                        print(f"✅ Optimization completed successfully!")
                        if result['optimizations_applied']:
                            print(f"   Applied optimizations:")
                            for opt in result['optimizations_applied']:
                                print(f"     • {opt}")
                        else:
                            print(f"   No optimizations were needed")
                
                elif command in ['21', 'enhanced']:
                    enhanced_health = self.get_enhanced_health_status()
                    if 'error' in enhanced_health:
                        print(f"❌ Error getting enhanced health: {enhanced_health['error']}")
                    else:
                        print(f"\n🏥 ENHANCED HEALTH STATUS:")
                        print(f"   Overall Score: {enhanced_health['overall_score']}/100")
                        print(f"   Service Status: {enhanced_health['service_status']}")
                        
                        # Circuit breaker info
                        cb = enhanced_health.get('circuit_breaker', {})
                        if cb.get('active'):
                            print(f"   🔴 Circuit Breaker: ACTIVE ({cb['time_until_reset']}s until reset)")
                        else:
                            print(f"   🟢 Circuit Breaker: INACTIVE")
                        
                        # Adaptive config info
                        ac = enhanced_health.get('adaptive_config', {})
                        if ac.get('needs_optimization'):
                            print(f"   ⚠️  Configuration needs optimization")
                            print(f"     Current: {ac['current_interval']}s, {ac['current_block_range']} blocks")
                            print(f"     Recommended: {ac['recommended_interval']}s, {ac['recommended_block_range']} blocks")
                        else:
                            print(f"   ✅ Configuration is optimal")
                
                else:
                    print("❌ Invalid command. Use 1-21 or type 'help' for assistance.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Exiting CLI interface")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                logger.error(f"CLI error: {e}")
        
        print("="*60)

    def _handle_erc20_transaction(self, tx_data: Dict):
        """Handle ERC20 transaction data from WebSocket"""
        try:
            tx_hash = tx_data.get("hash")
            from_address = tx_data.get("from", "").lower()
            to_address = tx_data.get("to", "").lower()
            input_data = tx_data.get("input", "")
            block_number = int(tx_data.get("blockNumber", "0"), 16)
            gas_price = int(tx_data.get("gasPrice", "0"), 16)
            gas_used = int(tx_data.get("gas", "0"), 16)
            timestamp = int(tx_data.get("timestamp", "0"), 16)
            
            # Check if this transaction involves our monitored addresses
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            
            # Parse ERC20 transfer data from input
            if input_data.startswith("0xa9059cbb"):  # ERC20 transfer method signature
                logger.info(f"🔍 ERC20 transfer method signature detected")
                # Extract recipient and amount from input data
                if len(input_data) >= 138:  # 0x + 4 bytes method + 32 bytes address + 32 bytes amount
                    recipient_hex = "0x" + input_data[34:74]  # Extract recipient address
                    amount_hex = "0x" + input_data[74:138]    # Extract amount
                    
                    try:
                        recipient = "0x" + recipient_hex[2:].zfill(40)  # Ensure proper address format
                        amount = int(amount_hex, 16)
                        
                        logger.info(f"📝 Decoded ERC20 transfer: {amount} tokens to {recipient}")
                        
                        # Check if this transaction involves our monitored addresses
                        # For ERC20: from_address = sender, recipient = actual recipient, to_address = contract
                        if (from_address in monitored_addresses_lower or 
                            recipient in monitored_addresses_lower):
                            
                            # Get token information from pre-loaded configuration
                            contract_address_lower = to_address.lower()
                            token_info = self.erc20_tokens.get(contract_address_lower, {
                                "symbol": "UNKNOWN",
                                "name": "Unknown Token",
                                "decimals": 18,
                                "smallest_unit": "units",
                                "contract_address": contract_address_lower
                            })
                            
                            if recipient in monitored_addresses_lower:
                                # Incoming ERC20 transfer to our monitored address
                                logger.info(f"💰 Incoming ERC20 transfer: {amount} {token_info['symbol']} to {recipient}")
                                
                                transaction_data = {
                                    "tx_hash": tx_hash,
                                    "from_address": from_address,
                                    "to_address": recipient,  # Use the actual recipient, not contract
                                    "amount": amount,
                                    "currency": token_info["symbol"],
                                    "block_number": block_number,
                                    "gas_price": gas_price,
                                    "gas_used": gas_used,
                                    "timestamp": timestamp,
                                    "transaction_type": "incoming",
                                    "network": self.network,
                                    "is_erc20": True,
                                    "contract_address": to_address,  # The contract address for the ERC20 token
                                    "token_info": token_info
                                }
                                
                                # Create ERC20 transaction record
                                self._create_erc20_transaction_record_sync(transaction_data)
                                
                            elif from_address in monitored_addresses_lower:
                                # Outgoing ERC20 transfer from our monitored address
                                logger.info(f"💸 Outgoing ERC20 transfer: {amount} {token_info['symbol']} tokens from {from_address}")
                                
                                transaction_data = {
                                    "tx_hash": tx_hash,
                                    "from_address": from_address,
                                    "to_address": recipient,  # Use the actual recipient, not contract
                                    "amount": amount,
                                    "currency": token_info["symbol"],
                                    "block_number": block_number,
                                    "gas_price": gas_price,
                                    "gas_used": gas_used,
                                    "timestamp": timestamp,
                                    "transaction_type": "outgoing",
                                    "network": self.network,
                                    "is_erc20": True,
                                    "contract_address": to_address,  # The contract address for the ERC20 token
                                    "token_info": token_info
                                }
                                
                                # Create ERC20 transaction record
                                self._create_erc20_transaction_record_sync(transaction_data)
                                
                    except (ValueError, IndexError) as e:
                        logger.error(f"❌ Error parsing ERC20 transfer data: {e}")
                        return
                else:
                    logger.warning(f"⚠️ Invalid ERC20 transfer input data length: {len(input_data)}")
                    return
            else:
                logger.debug(f"ℹ️ Non-transfer ERC20 transaction: {tx_hash}")
                
        except Exception as e:
            logger.error(f"❌ Error handling ERC20 transaction: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def _create_erc20_transaction_record_sync(self, transaction_data: Dict):
        """Create a new ERC20 transaction record (synchronous)"""
        try:
            # from db.models import Transaction, TransactionType, TransactionStatus, PaymentProvider, CryptoAddress, Account
            from db.connection import get_session
            
            session = get_session()
            
            tx_hash = transaction_data["tx_hash"]
            from_address = transaction_data["from_address"]
            to_address = transaction_data["to_address"]
            amount = transaction_data["amount"]
            currency = transaction_data["currency"]
            block_number = transaction_data["block_number"]
            gas_price = transaction_data["gas_price"]
            gas_used = transaction_data["gas_used"]
            timestamp = transaction_data["timestamp"]
            transaction_type = transaction_data["transaction_type"]
            network = transaction_data["network"]
            is_erc20 = transaction_data["is_erc20"]
            contract_address = transaction_data["contract_address"]
            
            # Determine which address to monitor and transaction type
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            
            if transaction_type == "incoming":
                # Incoming ERC20 transfer
                monitored_address = to_address.lower()
                tx_type = TransactionType.DEPOSIT
                address_field = to_address.lower()
            else:
                # Outgoing ERC20 transfer
                monitored_address = from_address.lower()
                tx_type = TransactionType.WITHDRAWAL
                address_field = from_address.lower()
            
            # Check if this address is monitored
            if monitored_address not in monitored_addresses_lower:
                logger.debug(f"⏭️ Address {monitored_address} not monitored, skipping ERC20 transaction")
                return
            
            # Get the crypto address record
            crypto_address = session.query(CryptoAddress).filter(
                CryptoAddress.address.ilike(monitored_address),
                CryptoAddress.is_active == True
            ).first()
            
            if not crypto_address:
                logger.warning(f"⚠️ No active crypto address found for: {monitored_address}")
                return
            
            # Check for existing transaction
            existing_tx = session.query(Transaction).filter_by(
                blockchain_txid=tx_hash,
                address=address_field,
                type=tx_type
            ).first()
            
            if existing_tx:
                logger.info(f"⏭️ ERC20 transaction {tx_hash} already exists for {address_field} ({tx_type})")
                return
            
            # Get the account
            account = session.query(Account).filter_by(id=crypto_address.account_id).first()
            token_accounts = session.query(Account).filter_by(user_id=account.user_id, currency=currency).all()
            if not account:
                return
            token_account = None
            for t in token_accounts:
                if t.precision_config and t.precision_config.get('parent_currency','').upper() == 'ETH':
                    token_account = t
                    break
            if not token_account:
                return

            
            if not (token_account.currency and token_account.currency.upper() == currency and (token_account.precision_config or {}).get('parent_currency','').upper() == 'ETH'):
                logger.info(f"Skipping ERC20 {currency} deposit to {to_address} because it's not a token account")
                return

            
            # Use pre-loaded token information from transaction_data
            token_info = transaction_data.get('token_info', {})
            decimals = token_info.get('decimals', 18)  # Default to 18 decimals
            smallest_unit = token_info.get('smallest_unit', 'units')
            
            # Convert amount to standard units
            amount_standard = Decimal(amount) / Decimal(10**decimals)
            
            logger.info(f"Creating ERC20 transaction record:")
            logger.info(f"   Type: {tx_type}")
            logger.info(f"   Currency: {currency}")
            logger.info(f"   Address: {address_field}")
            logger.info(f"   Account: {crypto_address.account_id}")
            logger.info(f"   Amount: {amount_standard} {currency}")
            
            # Create transaction record with ERC20 precision
            transaction = Transaction(
                account_id=crypto_address.account_id,
                reference_id=tx_hash,
                amount=float(amount_standard),  # Standard units
                amount_smallest_unit=int(amount),  # Raw token units
                precision_config={
                    "currency": currency,
                    "decimals": decimals,
                    "smallest_unit": smallest_unit,
                    "parent_currency": "ETH"  # ERC20 tokens are on Ethereum
                },
                type=tx_type,
                status=TransactionStatus.AWAITING_CONFIRMATION,
                address=address_field,
                blockchain_txid=tx_hash,
                payment_provider=PaymentProvider.ETHEREUM,
                metadata={
                    "is_erc20": True,
                    "contract_address": contract_address,
                    "token_info": transaction_data.get("token_info", {}),
                    "block_number": block_number,
                    "gas_price": gas_price,
                    "gas_used": gas_used,
                    "timestamp": timestamp,
                    "network": network
                }
            )
            
            # Add to session and commit
            session.add(transaction)
            session.commit()
            
            logger.info(f"✅ ERC20 transaction record created: {tx_hash}")
            logger.info(f"   Account: {crypto_address.account_id}")
            logger.info(f"   Amount: {amount_standard} {currency}")
            logger.info(f"   Type: {tx_type}")
            
            # Update account balance if this is a deposit
            if tx_type == TransactionType.DEPOSIT:
                try:
                    self._update_account_balance_sync(crypto_address.account_id, amount_standard)
                    logger.info(f"💰 Account balance updated for {currency} deposit")
                except Exception as e:
                    logger.error(f"❌ Error updating account balance: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error creating ERC20 transaction record: {e}")
            import traceback
            logger.error(traceback.format_exc())
            if 'session' in locals():
                session.rollback()
        finally:
            if 'session' in locals():
                session.close()

    def _get_erc20_token_info(self, contract_address: str) -> Optional[Dict]:
        """Get ERC20 token information by contract address"""
        contract_address_lower = contract_address.lower()
        
        # Check if we have this token in our mapping
        if contract_address_lower in self.erc20_tokens:
            return self.erc20_tokens[contract_address_lower]
        
        # If not found, try to query the contract for basic info
        # This is a fallback for tokens not in our environment configuration
        try:
            from shared.crypto.clients.eth import ETHWallet, EthereumConfig
            import os
            api_key = os.getenv('ALCHEMY_API_KEY')
            if api_key:
                cfg = EthereumConfig.mainnet(api_key) if self.network == 'mainnet' else EthereumConfig.testnet(api_key)
                eth_client = ETHWallet(user_id=0, eth_config=cfg, session=session, logger=logger)
                
                # Try to get token info from contract
                # Note: This is a simplified approach - in production you might want more robust contract calls
                return {
                    "symbol": "UNKNOWN",
                    "name": "Unknown Token",
                    "decimals": 18,  # Default to 18 decimals
                    "smallest_unit": "units",
                    "contract_address": contract_address_lower
                }
        except Exception as e:
            logger.debug(f"Could not query contract {contract_address_lower} for token info: {e}")
        
        # Final fallback
        return {
            "symbol": "UNKNOWN",
            "name": "Unknown Token",
            "decimals": 18,  # Default to 18 decimals
            "smallest_unit": "units",
            "contract_address": contract_address_lower
        }


class EthereumMonitorService:
    """Main service for monitoring Ethereum transactions"""
    
    def __init__(self):
        self.api_key = config('ALCHEMY_API_KEY', default=None)
        self.network = config('ETH_NETWORK', default='mainnet')
        self.client = None
        
        if not self.api_key:
            raise ValueError("ALCHEMY_API_KEY environment variable is required")
    
    async def start(self):
        """Start the Ethereum monitoring service"""
        logger.info("🚀 Starting Ethereum Transaction Monitor Service")
        
        try:
            # Initialize WebSocket client
            self.client = AlchemyWebSocketClient(self.api_key, self.network)
            
            # Load addresses from database
            self.client.load_addresses_from_db()
            
            # Start Kafka consumer for new address events
            start_ethereum_address_consumer(self.client.add_address_from_kafka)
            
            # Start confirmation checker
            self.client.start_confirmation_checker()
            
            # Start ETH transfer polling service
            self.client.start_eth_transfer_polling()
            
            # Start monitoring in a separate thread
            import threading
            monitor_thread = threading.Thread(target=self.client.connect)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            logger.info("✅ Ethereum monitoring service started successfully")
            logger.info("   - WebSocket monitoring active")
            logger.info("   - Kafka consumer active")
            logger.info("   - Real-time block confirmation tracking (15 confirmations)")
            logger.info("   - ETH transfer polling service active (5-minute intervals)")
            
            # Keep the service running
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
            await self.stop()
        except Exception as e:
            logger.error(f"❌ Error in Ethereum monitoring service: {e}")
            await self.stop()
    
    async def stop(self):
        """Stop the Ethereum monitoring service"""
        logger.info("🛑 Stopping Ethereum monitoring service")
        
        # Stop confirmation checker
        if self.client:
            self.client.stop_confirmation_checker()
        
        # Stop ETH transfer polling service
        if self.client:
            self.client.stop_eth_transfer_polling()
        
        # Stop Kafka consumer
        stop_ethereum_address_consumer()
        
        # Disconnect WebSocket client
        if self.client:
            self.client.disconnect()
        
        logger.info("✅ Ethereum monitoring service stopped")


async def main():
    """Main entry point"""
    service = EthereumMonitorService()
    await service.start()


if __name__ == "__main__":
    asyncio.run(main()) 