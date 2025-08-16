#!/usr/bin/env python3
"""
Updated Ethereum Transaction Monitor Service with Unified Amount/Balance System
Integrates with double-entry accounting system for automatic journal entries
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
from db.unified_amounts import UnifiedAmountMixin, UnifiedBalanceMixin
from shared.crypto.clients.eth import ETHWallet, EthereumConfig
from shared.currency_precision import AmountConverter
from shared.trading_accounting import TradingAccountingService
from db.accounting import JournalEntry, LedgerTransaction, AccountingAccount
from kafka_consumer import start_ethereum_address_consumer, stop_ethereum_address_consumer
import traceback

logger = setup_logging()


@dataclass
class TransactionEvent:
    """Represents a new transaction event with unified amount handling"""
    tx_hash: str
    from_address: str
    to_address: str
    value_smallest_unit: int  # Store in wei (smallest units)
    currency: str = "ETH"
    block_number: int = 0
    gas_price: int = 0
    gas_used: int = 0
    timestamp: int = 0
    confirmations: int = 0
    status: str = "pending"
    
    @property
    def value_display(self) -> Decimal:
        """Get display value using unified converter"""
        return AmountConverter.from_smallest_units(self.value_smallest_unit, self.currency)
    
    def format_amount(self) -> str:
        """Format amount for display"""
        return AmountConverter.format_display_amount(self.value_smallest_unit, self.currency)


class UnifiedEthereumMonitor:
    """Updated Ethereum monitor with unified precision and accounting integration"""
    
    def __init__(self, api_key: str, network: str = "mainnet"):
        self.api_key = api_key
        self.network = network
        self.ws_url = self._get_websocket_url()
        self.ws = None
        self.is_connected = False
        self.is_running = False
        self.monitored_addresses: Set[str] = set()
        self.eth_config = EthereumConfig.mainnet(api_key) if network == "mainnet" else EthereumConfig.testnet(api_key)
        
        # Initialize accounting service for automatic journal entries
        self.accounting_service = None
        
        # ETH transfer polling configuration
        self.eth_polling_enabled = True
        self.eth_polling_interval = 300  # 5 minutes
        self.eth_polling_block_range = 200
        
        # Performance tuning
        self.max_scan_time_per_block = 5
        self.max_total_scan_time = 30
        self.max_initial_scan_time = 120
        self.block_scan_delay = 0.01
        
        # Load ERC20 token configuration
        self._load_erc20_config()
        
        logger.info(f"🔧 Initialized Unified Ethereum Monitor for {network}")
        logger.info(f"📡 WebSocket URL: {self.ws_url}")
        logger.info(f"💰 Using unified amount/balance system with automatic accounting")
    
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
    
    def _load_erc20_config(self):
        """Load ERC20 token configuration"""
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
            
            logger.info(f"📋 Loaded {len(self.erc20_tokens)} ERC20 tokens")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"⚠️ Failed to parse ERC20 config: {e}")
            self.erc20_tokens = {}
    
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
                result = params.get("result")
                
                if result:
                    if isinstance(result, dict) and "number" in result:
                        # Block event
                        self._handle_new_block(result)
                    else:
                        # Transaction event
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
        self._subscribe_to_blocks()
        
        if not self.monitored_addresses:
            logger.warning("⚠️ No addresses to monitor")
            return
        
        for address in self.monitored_addresses:
            self._subscribe_to_address(address)
    
    def _subscribe_to_address(self, address: str):
        """Subscribe to a specific address"""
        # Subscribe to pending transactions TO this address
        to_subscription = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": [
                "alchemy_pendingTransactions",
                {"toAddress": address}
            ]
        }
        
        # Subscribe to pending transactions FROM this address
        from_subscription = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "eth_subscribe",
            "params": [
                "alchemy_pendingTransactions",
                {"fromAddress": address}
            ]
        }
        
        if self.ws and self.is_connected:
            self.ws.send(json.dumps(to_subscription))
            self.ws.send(json.dumps(from_subscription))
            logger.info(f"📡 Subscribed to address: {address}")
    
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
        """Handle new transaction with unified amount system"""
        try:
            tx_hash = tx_data.get("hash")
            from_address = tx_data.get("from", "").lower()
            to_address = tx_data.get("to", "").lower()
            value_wei = int(tx_data.get("value", "0"), 16)
            block_number = int(tx_data.get("blockNumber", "0"), 16)
            gas_price = int(tx_data.get("gasPrice", "0"), 16)
            gas_used = int(tx_data.get("gas", "0"), 16)
            timestamp = int(tx_data.get("timestamp", "0"), 16)
            input_data = tx_data.get("input", "")
            
            # Check if this is an ERC20 transfer
            is_erc20 = input_data and input_data != "0x" and value_wei == 0
            
            if is_erc20:
                logger.info(f"🔍 Processing ERC20 transfer {tx_hash}")
                self._handle_erc20_transaction(tx_data)
                return
            
            # Only process native ETH transfers
            if input_data and input_data != "0x":
                logger.info(f"⏭️ Skipping contract call {tx_hash}")
                return
            
            # Check if involves monitored addresses
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            
            if (from_address in monitored_addresses_lower or 
                to_address in monitored_addresses_lower):
                
                event = TransactionEvent(
                    tx_hash=tx_hash,
                    from_address=from_address,
                    to_address=to_address,
                    value_smallest_unit=value_wei,  # Store in wei
                    currency="ETH",
                    block_number=block_number,
                    gas_price=gas_price,
                    gas_used=gas_used,
                    timestamp=timestamp
                )
                
                logger.info(f"💰 New ETH transaction: {tx_hash}")
                logger.info(f"   From: {from_address}")
                logger.info(f"   To: {to_address}")
                logger.info(f"   Amount: {event.format_amount()}")
                
                # Process in separate thread
                thread = threading.Thread(target=self._process_transaction_unified, args=(event,))
                thread.daemon = True
                thread.start()
            
        except Exception as e:
            logger.error(f"❌ Error handling new transaction: {e}")
    
    def _handle_new_block(self, block_data: Dict):
        """Handle new block for confirmation tracking"""
        try:
            block_number = int(block_data.get("number", "0"), 16)
            logger.info(f"🔄 New block: {block_number}")
            
            # Process confirmations
            self._process_block_confirmations_unified(block_number)
            
            # Scan for ERC20 transfers
            try:
                lookback = int(os.getenv('ETH_LOG_LOOKBACK_BLOCKS', '200'))
                from_block = max(0, block_number - lookback)
                self._scan_erc20_transfers_unified(from_block, block_number)
            except Exception as scan_err:
                logger.error(f"Error scanning ERC20 logs: {scan_err}")
            
        except Exception as e:
            logger.error(f"❌ Error handling new block: {e}")
    
    def _process_transaction_unified(self, event: TransactionEvent):
        """Process transaction with unified amount system and accounting integration"""
        try:
            # Initialize accounting service for this session
            self.accounting_service = TradingAccountingService(session)
            
            # Determine transaction direction
            monitored_addresses_lower = {addr.lower() for addr in self.monitored_addresses}
            is_incoming = event.to_address.lower() in monitored_addresses_lower
            is_outgoing = event.from_address.lower() in monitored_addresses_lower
            
            logger.info(f"   Processing transaction {event.tx_hash}")
            logger.info(f"   Amount: {event.format_amount()}")
            logger.info(f"   Is incoming: {is_incoming}")
            logger.info(f"   Is outgoing: {is_outgoing}")
            
            # Handle internal transfers
            if is_incoming and is_outgoing:
                logger.info(f"🔄 Internal transfer: {event.tx_hash}")
                
                # Process sender (withdrawal)
                sender_address = self._get_crypto_address(event.from_address.lower())
                if sender_address:
                    self._create_unified_transaction(event, sender_address, is_withdrawal=True)
                
                # Process recipient (deposit)
                recipient_address = self._get_crypto_address(event.to_address.lower())
                if recipient_address:
                    self._create_unified_transaction(event, recipient_address, is_withdrawal=False)
                
                return
            
            # Handle external transactions
            if is_incoming:
                logger.info(f"📥 Incoming transaction: {event.tx_hash}")
                crypto_address = self._get_crypto_address(event.to_address.lower())
                if crypto_address:
                    self._create_unified_transaction(event, crypto_address, is_withdrawal=False)
                    
            elif is_outgoing:
                logger.info(f"📤 Outgoing transaction: {event.tx_hash}")
                crypto_address = self._get_crypto_address(event.from_address.lower())
                if crypto_address:
                    self._create_unified_transaction(event, crypto_address, is_withdrawal=True)
            
            logger.info(f"✅ Transaction {event.tx_hash} processed with unified system")
            
        except Exception as e:
            logger.error(f"❌ Error processing transaction {event.tx_hash}: {e}")
        finally:
            try:
                session.remove()
            except Exception:
                pass
    
    def _get_crypto_address(self, address: str) -> Optional[CryptoAddress]:
        """Get crypto address record (case-insensitive)"""
        try:
            return session.query(CryptoAddress).filter(
                CryptoAddress.address.ilike(address),
                CryptoAddress.is_active == True
            ).first()
        except Exception as e:
            logger.error(f"❌ Error getting crypto address: {e}")
            return None
    
    def _create_unified_transaction(self, event: TransactionEvent, crypto_address: CryptoAddress, is_withdrawal: bool = False):
        """Create transaction with unified amount system and accounting integration"""
        try:
            # Determine transaction type
            if is_withdrawal:
                tx_type = TransactionType.WITHDRAWAL
                address_field = event.from_address.lower()
            else:
                tx_type = TransactionType.DEPOSIT
                address_field = event.to_address.lower()
            
            # Check for existing transaction
            existing_tx = session.query(Transaction).filter_by(
                blockchain_txid=event.tx_hash,
                address=address_field,
                type=tx_type
            ).first()
            
            if existing_tx:
                logger.info(f"⏭️ Transaction {event.tx_hash} already exists")
                return
            
            logger.info(f"Creating unified transaction:")
            logger.info(f"   Type: {tx_type}")
            logger.info(f"   Address: {address_field}")
            logger.info(f"   Amount: {event.format_amount()}")
            
            # Create transaction with unified amount fields
            transaction = Transaction(
                account_id=crypto_address.account_id,
                reference_id=event.tx_hash,
                amount=float(event.value_display),  # Backward compatibility
                amount_smallest_unit=event.value_smallest_unit,  # Unified field
                currency="ETH",  # Add currency field
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
                    "value_wei": str(event.value_smallest_unit),
                    "amount_eth": str(event.value_display),
                    "unified_system": True
                }
            )
            
            session.add(transaction)
            
            # Update account balance using unified system
            self._update_unified_account_balance(crypto_address.account_id, event, is_withdrawal)
            
            # Create accounting journal entry
            self._create_accounting_entry(transaction, event, crypto_address, is_withdrawal)
            
            session.commit()
            
            logger.info(f"💾 Created unified transaction and accounting entries")
            logger.info(f"   Amount: {event.format_amount()}")
            logger.info(f"   Account: {crypto_address.account_id}")
            
        except Exception as e:
            logger.error(f"❌ Error creating unified transaction: {e}")
            session.rollback()
    
    def _update_unified_account_balance(self, account_id: int, event: TransactionEvent, is_withdrawal: bool):
        """Update account balance using unified amount system"""
        try:
            account = session.query(Account).filter_by(id=account_id).first()
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            # Update balance in smallest units
            current_balance = account.balance_smallest_unit or 0
            
            if is_withdrawal:
                # Lock amount for withdrawal (will be unlocked on confirmation)
                current_locked = account.locked_amount_smallest_unit or 0
                account.locked_amount_smallest_unit = current_locked + event.value_smallest_unit
                logger.info(f"🔒 Locked {event.format_amount()} for withdrawal")
            else:
                # For deposits, lock amount until confirmed
                current_locked = account.locked_amount_smallest_unit or 0
                account.locked_amount_smallest_unit = current_locked + event.value_smallest_unit
                logger.info(f"🔒 Locked {event.format_amount()} pending confirmation")
            
        except Exception as e:
            logger.error(f"❌ Error updating unified account balance: {e}")
            raise
    
    def _create_accounting_entry(self, transaction: Transaction, event: TransactionEvent, crypto_address: CryptoAddress, is_withdrawal: bool):
        """Create accounting journal entry for the transaction"""
        try:
            if not self.accounting_service:
                self.accounting_service = TradingAccountingService(session)
            
            # Get or create crypto asset account
            crypto_account_name = f"Crypto Assets - ETH"
            crypto_account = self.accounting_service.get_account_by_name(crypto_account_name)
            
            if not crypto_account:
                logger.warning(f"⚠️ Crypto asset account not found: {crypto_account_name}")
                return
            
            # Create journal entry description
            direction = "withdrawal" if is_withdrawal else "deposit"
            description = f"ETH {direction} - {event.format_amount()} (TX: {event.tx_hash[:8]}...)"
            
            # Create journal entry
            journal_entry = JournalEntry(description=description)
            session.add(journal_entry)
            session.flush()  # Get ID
            
            # Create ledger transactions based on direction
            if is_withdrawal:
                # Debit: Pending settlements (liability), Credit: Crypto assets
                pending_account = self.accounting_service.get_account_by_name("Pending Trade Settlements")
                if pending_account:
                    # Debit pending settlements
                    debit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=pending_account.id,
                        debit_smallest_unit=event.value_smallest_unit,
                        credit_smallest_unit=0
                    )
                    session.add(debit_tx)
                    
                    # Credit crypto assets
                    credit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=crypto_account.id,
                        debit_smallest_unit=0,
                        credit_smallest_unit=event.value_smallest_unit
                    )
                    session.add(credit_tx)
            else:
                # Deposit: Debit crypto assets, Credit pending settlements
                pending_account = self.accounting_service.get_account_by_name("Pending Trade Settlements")
                if pending_account:
                    # Debit crypto assets
                    debit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=crypto_account.id,
                        debit_smallest_unit=event.value_smallest_unit,
                        credit_smallest_unit=0
                    )
                    session.add(debit_tx)
                    
                    # Credit pending settlements
                    credit_tx = LedgerTransaction(
                        journal_entry_id=journal_entry.id,
                        account_id=pending_account.id,
                        debit_smallest_unit=0,
                        credit_smallest_unit=event.value_smallest_unit
                    )
                    session.add(credit_tx)
            
            # Link transaction to journal entry
            transaction.journal_entry_id = journal_entry.id
            
            logger.info(f"📊 Created accounting entry: {description}")
            
        except Exception as e:
            logger.error(f"❌ Error creating accounting entry: {e}")
            raise
    
    def _process_block_confirmations_unified(self, block_number: int):
        """Process confirmations with unified system"""
        try:
            # Get pending transactions
            pending_txs = session.query(Transaction).filter(
                Transaction.status == TransactionStatus.AWAITING_CONFIRMATION,
                Transaction.blockchain_txid.isnot(None)
            ).all()
            
            for tx in pending_txs:
                if tx.metadata_json and "block_number" in tx.metadata_json:
                    tx_block = tx.metadata_json["block_number"]
                    confirmations = block_number - tx_block
                    
                    if confirmations >= 0:
                        tx.confirmations = confirmations
                        
                        # Check if confirmed
                        if confirmations >= tx.required_confirmations:
                            self._confirm_unified_transaction(tx)
            
            session.commit()
            
        except Exception as e:
            logger.error(f"❌ Error processing confirmations: {e}")
            session.rollback()
    
    def _confirm_unified_transaction(self, transaction: Transaction):
        """Confirm transaction and update balances using unified system"""
        try:
            transaction.status = TransactionStatus.CONFIRMED
            
            # Update account balance
            account = session.query(Account).filter_by(id=transaction.account_id).first()
            if account:
                # Unlock the amount
                locked_amount = account.locked_amount_smallest_unit or 0
                tx_amount = transaction.amount_smallest_unit or 0
                account.locked_amount_smallest_unit = max(0, locked_amount - tx_amount)
                
                # For deposits, credit the balance
                if transaction.type == TransactionType.DEPOSIT:
                    current_balance = account.balance_smallest_unit or 0
                    account.balance_smallest_unit = current_balance + tx_amount
                    
                    # Convert for logging
                    amount_display = AmountConverter.from_smallest_units(tx_amount, "ETH")
                    logger.info(f"💰 Confirmed deposit: +{amount_display} ETH")
                
                elif transaction.type == TransactionType.WITHDRAWAL:
                    # For withdrawals, debit the balance
                    current_balance = account.balance_smallest_unit or 0
                    account.balance_smallest_unit = max(0, current_balance - tx_amount)
                    
                    amount_display = AmountConverter.from_smallest_units(tx_amount, "ETH")
                    logger.info(f"💸 Confirmed withdrawal: -{amount_display} ETH")
            
            logger.info(f"✅ Transaction confirmed: {transaction.blockchain_txid}")
            
        except Exception as e:
            logger.error(f"❌ Error confirming transaction: {e}")
            raise
    
    def _handle_erc20_transaction(self, tx_data: Dict):
        """Handle ERC20 transactions with unified system"""
        # Placeholder for ERC20 handling - can be expanded later
        logger.info(f"🔍 ERC20 transaction detected - unified handling not yet implemented")
    
    def _scan_erc20_transfers_unified(self, from_block: int, to_block: int):
        """Scan for ERC20 transfers with unified system"""
        # Placeholder for ERC20 scanning - can be expanded later
        pass
    
    def add_address(self, address: str):
        """Add address to monitoring"""
        self.monitored_addresses.add(address.lower())
        if self.is_connected:
            self._subscribe_to_address(address.lower())
    
    def remove_address(self, address: str):
        """Remove address from monitoring"""
        self.monitored_addresses.discard(address.lower())
    
    def start(self):
        """Start the monitor"""
        self.is_running = True
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        
        logger.info("🚀 Starting Unified Ethereum Monitor...")
        self.ws.run_forever()
    
    def stop(self):
        """Stop the monitor"""
        self.is_running = False
        if self.ws:
            self.ws.close()
        logger.info("🛑 Unified Ethereum Monitor stopped")


# Main execution
if __name__ == "__main__":
    # Load configuration
    api_key = config("ALCHEMY_API_KEY")
    network = config("ETHEREUM_NETWORK", default="mainnet")
    
    # Initialize monitor
    monitor = UnifiedEthereumMonitor(api_key, network)
    
    # Add test addresses (replace with your actual addresses)
    test_addresses = [
        "0x742d35Cc6634C0532925a3b8D5c9C8e3DE4c4b5B",  # Example address
    ]
    
    for addr in test_addresses:
        monitor.add_address(addr)
    
    try:
        monitor.start()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
        monitor.stop()
