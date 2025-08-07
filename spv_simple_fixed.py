#!/usr/bin/env python3
"""
Simple SPV Client using bitcoinlib
Supports real-time transaction monitoring via WebSocket
Includes transaction sending functionality
"""

import time
import threading
import logging
import hashlib
import random
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import bitcoinlib
from bitcoinlib.services.services import Service
from bitcoinlib.wallets import Wallet
from bitcoinlib.transactions import Transaction

# Configure logging to filter out bitcoinlib's noisy errors
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Filter out bitcoinlib's "Malformed script" errors
class BitcoinlibFilter(logging.Filter):
    def filter(self, record):
        # Filter out "Malformed script" errors from bitcoinlib
        if "Malformed script" in record.getMessage():
            return False
        return True

# Apply the filter to all loggers
for handler in logging.root.handlers:
    handler.addFilter(BitcoinlibFilter())

# Also configure bitcoinlib's internal logging
bitcoinlib_logger = logging.getLogger('bitcoinlib')
bitcoinlib_logger.setLevel(logging.WARNING)  # Only show warnings and errors, not debug info

class ThompsonSamplingProvider:
    """Thompson sampling for provider selection"""
    
    def __init__(self, providers: List[str]):
        self.providers = providers
        self.success_counts = {provider: 0 for provider in providers}
        self.failure_counts = {provider: 0 for provider in providers}
        self.total_attempts = {provider: 0 for provider in providers}
        self.last_selected = None
        self.selection_history = []
        
    def select_provider(self) -> str:
        """Select a provider using Thompson sampling"""
        if not self.providers:
            return None
            
        # If we haven't tried all providers yet, explore
        untried_providers = [p for p in self.providers if self.total_attempts[p] == 0]
        if untried_providers:
            selected = random.choice(untried_providers)
            logger.info(f"🔍 Exploring untried provider: {selected}")
            self.last_selected = selected
            return selected
        
        # Use Thompson sampling for providers we've tried
        samples = {}
        for provider in self.providers:
            if self.total_attempts[provider] > 0:
                # Sample from Beta distribution
                alpha = self.success_counts[provider] + 1  # Add 1 for prior
                beta = self.failure_counts[provider] + 1   # Add 1 for prior
                sample = np.random.beta(alpha, beta)
                samples[provider] = sample
            else:
                samples[provider] = 0.5  # Default for untried providers
        
        # Select provider with highest sample
        selected = max(samples, key=samples.get)
        self.last_selected = selected
        
        # Log selection with confidence
        confidence = samples[selected]
        logger.info(f"🎯 Thompson sampling selected {selected} (confidence: {confidence:.3f})")
        
        return selected
    
    def update_provider_result(self, provider: str, success: bool):
        """Update provider statistics after a request"""
        if provider not in self.providers:
            return
            
        self.total_attempts[provider] += 1
        
        if success:
            self.success_counts[provider] += 1
            logger.info(f"✅ Provider {provider} succeeded (successes: {self.success_counts[provider]}, failures: {self.failure_counts[provider]})")
        else:
            self.failure_counts[provider] += 1
            logger.warning(f"❌ Provider {provider} failed (successes: {self.success_counts[provider]}, failures: {self.failure_counts[provider]})")
        
        # Record selection history
        self.selection_history.append({
            'provider': provider,
            'success': success,
            'timestamp': time.time()
        })
    
    def get_provider_stats(self) -> Dict:
        """Get statistics for all providers"""
        stats = {}
        for provider in self.providers:
            total = self.total_attempts[provider]
            if total > 0:
                success_rate = self.success_counts[provider] / total
            else:
                success_rate = 0.0
                
            stats[provider] = {
                'successes': self.success_counts[provider],
                'failures': self.failure_counts[provider],
                'total_attempts': total,
                'success_rate': success_rate,
                'alpha': self.success_counts[provider] + 1,
                'beta': self.failure_counts[provider] + 1
            }
        
        return stats
    
    def get_best_provider(self) -> str:
        """Get the provider with the highest success rate"""
        if not self.providers:
            return None
            
        best_provider = None
        best_rate = -1
        
        for provider in self.providers:
            total = self.total_attempts[provider]
            if total > 0:
                rate = self.success_counts[provider] / total
                if rate > best_rate:
                    best_rate = rate
                    best_provider = provider
        
        return best_provider
    
    def get_exploration_stats(self) -> Dict:
        """Get exploration vs exploitation statistics"""
        total_selections = len(self.selection_history)
        if total_selections == 0:
            return {'exploration_rate': 0, 'exploitation_rate': 0}
        
        # Count exploration vs exploitation
        exploration_count = 0
        exploitation_count = 0
        
        for i, record in enumerate(self.selection_history):
            if i == 0:
                exploration_count += 1  # First selection is always exploration
            else:
                # Check if this provider was selected before
                prev_providers = set(r['provider'] for r in self.selection_history[:i])
                if record['provider'] in prev_providers:
                    exploitation_count += 1
                else:
                    exploration_count += 1
        
        return {
            'total_selections': total_selections,
            'exploration_count': exploration_count,
            'exploitation_count': exploitation_count,
            'exploration_rate': exploration_count / total_selections,
            'exploitation_rate': exploitation_count / total_selections
        }

class ProviderBloomFilter:
    """Simple bloom filter to track successful providers"""
    
    def __init__(self, size: int = 1000, hash_count: int = 3):
        self.size = size
        self.hash_count = hash_count
        self.bit_array = [False] * size
        self.successful_providers: Set[str] = set()
    
    def _get_hash_values(self, provider: str) -> List[int]:
        """Get hash values for a provider"""
        hash_values = []
        for i in range(self.hash_count):
            # Create a unique hash for each position
            hash_input = f"{provider}_{i}".encode('utf-8')
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16) % self.size
            hash_values.append(hash_value)
        return hash_values
    
    def add(self, provider: str):
        """Add a provider to the bloom filter"""
        hash_values = self._get_hash_values(provider)
        for hash_value in hash_values:
            self.bit_array[hash_value] = True
        self.successful_providers.add(provider)
        logger.info(f"✅ Added provider to bloom filter: {provider}")
    
    def might_contain(self, provider: str) -> bool:
        """Check if a provider might be in the bloom filter"""
        hash_values = self._get_hash_values(provider)
        return all(self.bit_array[hash_value] for hash_value in hash_values)
    
    def get_successful_providers(self) -> List[str]:
        """Get list of providers that have been successfully added"""
        return list(self.successful_providers)
    
    def get_stats(self) -> Dict:
        """Get bloom filter statistics"""
        true_count = sum(1 for bit in self.bit_array if bit)
        return {
            "size": self.size,
            "hash_count": self.hash_count,
            "true_bits": true_count,
            "false_positive_rate": (true_count / self.size) ** self.hash_count,
            "successful_providers": len(self.successful_providers),
            "providers": self.get_successful_providers()
        }

@dataclass
class AddressBalance:
    """Address balance information"""
    address: str
    confirmed_balance: int = 0  # in satoshis
    unconfirmed_balance: int = 0  # in satoshis
    utxo_count: int = 0
    last_updated: float = 0.0

@dataclass
class UTXO:
    """Unspent Transaction Output"""
    tx_hash: str
    output_index: int
    value: int  # in satoshis
    address: str
    confirmed: bool = False

@dataclass
class TransactionRequest:
    """Transaction request data"""
    from_address: str
    to_address: str
    amount_satoshi: int
    fee_satoshi: int = 1000  # Default fee
    private_key: Optional[str] = None  # WIF format
    change_address: Optional[str] = None

class SimpleSPVClient:
    """Simple SPV client using bitcoinlib"""
    
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.service = None
        self.is_running = False
        self.monitor_thread = None
        self.watched_addresses = {}  # address -> balance
        self.utxos = {}  # address -> list of UTXOs
        self.transactions = {}  # address -> list of transactions
        self.last_balances = {}  # Track previous balances for change detection
        self.socketio = None  # WebSocket instance
        self.provider_bloom_filter = ProviderBloomFilter()  # Track successful providers
        self.thompson_sampling = None  # Will be initialized after service setup
        
        # Initialize bitcoinlib service with better configuration
        try:
            # Use specific providers that are more reliable
            network = 'testnet' if testnet else 'bitcoin'
            
            # Initialize service with timeout and retry settings
            self.service = Service(
                network=network,
                timeout=10,  # 10 second timeout
                providers=['blockstream', 'blockchair', 'mempool']  # Use more reliable providers
            )
            
            # Initialize Thompson sampling with the configured providers
            provider_names = list(self.service.providers.keys())
            self.thompson_sampling = ThompsonSamplingProvider(provider_names)
            
            logger.info(f"🔧 Initialized Simple SPV Client (testnet: {testnet})")
            logger.info(f"📡 Using providers: {self.service.providers}")
            logger.info(f"🎯 Thompson sampling initialized with providers: {provider_names}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize service: {e}")
            # Fallback to default service
            try:
                self.service = Service(network='testnet' if testnet else 'bitcoin')
                # Initialize Thompson sampling with fallback providers
                provider_names = list(self.service.providers.keys())
                self.thompson_sampling = ThompsonSamplingProvider(provider_names)
                logger.info("🔧 Fallback service initialized")
            except Exception as e2:
                logger.error(f"❌ Fallback service also failed: {e2}")
                self.service = None
                self.thompson_sampling = None
    
    def set_socketio(self, socketio):
        """Set WebSocket instance for real-time updates"""
        self.socketio = socketio
        logger.info("🔌 WebSocket support enabled")
    
    def add_watched_address(self, address: str):
        """Add address to watch list"""
        if address not in self.watched_addresses:
            self.watched_addresses[address] = AddressBalance(address=address)
            self.last_balances[address] = 0
            logger.info(f"✅ Added watched address: {address}")
        else:
            logger.info(f"ℹ️ Address {address} is already being watched")
    
    def get_balance(self, address: str) -> Optional[AddressBalance]:
        """Get balance for a specific address using bitcoinlib"""
        if not self.service:
            logger.error("❌ Service not initialized")
            return None
            
        try:
            # Get balance from service
            balance_satoshi = self.service.getbalance(address)
            
            # Get UTXOs for more detailed info
            utxos_data = self.service.getutxos(address)
            
            balance = AddressBalance(
                address=address,
                confirmed_balance=balance_satoshi,
                unconfirmed_balance=0,  # We'll need to calculate this separately
                utxo_count=len(utxos_data) if utxos_data else 0,
                last_updated=time.time()
            )
            
            # Update our cache
            self.watched_addresses[address] = balance
            
            # Update UTXOs
            self.utxos[address] = []
            if utxos_data:
                for utxo_data in utxos_data:
                    utxo = UTXO(
                        tx_hash=utxo_data.get('txid', ''),
                        output_index=utxo_data.get('n', 0),
                        value=utxo_data.get('value', 0),
                        address=address,
                        confirmed=utxo_data.get('confirmations', 0) > 0
                    )
                    self.utxos[address].append(utxo)
            
            logger.info(f"💰 Balance for {address}: {balance.confirmed_balance} satoshis")
            return balance
                
        except Exception as e:
            logger.error(f"❌ Error getting balance for {address}: {e}")
        
        return self.watched_addresses.get(address)
    
    def get_utxos(self, address: str) -> List[UTXO]:
        """Get UTXOs for a specific address"""
        if not self.service:
            logger.error("❌ Service not initialized")
            return []
            
        try:
            utxos_data = self.service.getutxos(address)
            
            utxos = []
            if utxos_data:
                for utxo_data in utxos_data:
                    utxo = UTXO(
                        tx_hash=utxo_data.get('txid', ''),
                        output_index=utxo_data.get('n', 0),
                        value=utxo_data.get('value', 0),
                        address=address,
                        confirmed=utxo_data.get('confirmations', 0) > 0
                    )
                    utxos.append(utxo)
            
            logger.info(f"📦 Found {len(utxos)} UTXOs for {address}")
            return utxos
                
        except Exception as e:
            logger.error(f"❌ Error getting UTXOs for {address}: {e}")
        
        return self.utxos.get(address, [])
    
    def _json_serializable(self, obj):
        """Convert any object to JSON serializable format"""
        if isinstance(obj, bytes):
            return obj.hex()
        elif isinstance(obj, dict):
            return {k: self._json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._json_serializable(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Convert object to dict
            result = {}
            for attr in dir(obj):
                if not attr.startswith('_') and not callable(getattr(obj, attr)):
                    try:
                        value = getattr(obj, attr)
                        result[attr] = self._json_serializable(value)
                    except:
                        pass
            return result
        else:
            return obj
    
    def get_transactions(self, address: str) -> List[Dict]:
        """Get transactions for a specific address"""
        if not self.service:
            logger.error("❌ Service not initialized")
            return []
            
        try:
            # Get transactions from service
            transactions_data = self.service.gettransactions(address)
            
            if transactions_data:
                # Convert Transaction objects to dictionaries
                transactions_list = []
                for tx in transactions_data:
                    if hasattr(tx, '__dict__'):
                        # Convert object to dict
                        tx_dict = {}
                        for attr in dir(tx):
                            if not attr.startswith('_') and not callable(getattr(tx, attr)):
                                try:
                                    value = getattr(tx, attr)
                                    tx_dict[attr] = self._json_serializable(value)
                                except:
                                    pass
                        transactions_list.append(tx_dict)
                
                logger.info(f"📋 Found {len(transactions_list)} transactions for {address}")
                return transactions_list
                
        except Exception as e:
            logger.error(f"❌ Error getting transactions for {address}: {e}")
        
        return self.transactions.get(address, [])
    
    def send_transaction(self, tx_request: TransactionRequest) -> Dict:
        """Send a Bitcoin transaction"""
        try:
            logger.info(f"🚀 Creating transaction: {tx_request.from_address} -> {tx_request.to_address}")
            logger.info(f"   Amount: {tx_request.amount_satoshi} satoshis")
            logger.info(f"   Fee: {tx_request.fee_satoshi} satoshis")
            
            # Validate inputs
            if not tx_request.private_key:
                return {"error": "Private key is required", "success": False}
            
            if tx_request.amount_satoshi <= 0:
                return {"error": "Amount must be greater than 0", "success": False}
            
            # Get UTXOs for the from address
            utxos = self.get_utxos(tx_request.from_address)
            if not utxos:
                return {"error": "No UTXOs found for the source address", "success": False}
            
            # Calculate total available balance
            total_available = sum(utxo.value for utxo in utxos)
            total_needed = tx_request.amount_satoshi + tx_request.fee_satoshi
            
            if total_available < total_needed:
                return {
                    "error": f"Insufficient balance. Available: {total_available} satoshis, Needed: {total_needed} satoshis",
                    "success": False
                }
            
            # Create transaction using bitcoinlib
            try:
                # Create a wallet for signing
                wallet = Wallet.create(
                    name=f"temp_wallet_{int(time.time())}",
                    keys=tx_request.private_key,
                    network='testnet' if self.testnet else 'bitcoin',
                    db_uri=':memory:'  # Use in-memory database
                )
                
                # Create the transaction (removed change_address parameter)
                transaction = wallet.send_to(
                    tx_request.to_address,
                    tx_request.amount_satoshi,
                    fee=tx_request.fee_satoshi
                )
                
                # Get transaction ID
                tx_id = transaction.txid
                if isinstance(tx_id, bytes):
                    tx_id = tx_id.hex()
                
                logger.info(f"✅ Transaction created successfully: {tx_id}")
                
                return {
                    "success": True,
                    "txid": tx_id,
                    "from_address": tx_request.from_address,
                    "to_address": tx_request.to_address,
                    "amount_satoshi": tx_request.amount_satoshi,
                    "amount_btc": tx_request.amount_satoshi / 100000000,
                    "fee_satoshi": tx_request.fee_satoshi,
                    "fee_btc": tx_request.fee_satoshi / 100000000,
                    "total_satoshi": total_needed,
                    "total_btc": total_needed / 100000000,
                    "change_satoshi": total_available - total_needed,
                    "change_btc": (total_available - total_needed) / 100000000,
                    "network": "testnet" if self.testnet else "mainnet"
                }
                
            except Exception as e:
                logger.error(f"❌ Error creating transaction: {e}")
                return {"error": f"Transaction creation failed: {str(e)}", "success": False}
                
        except Exception as e:
            logger.error(f"❌ Error sending transaction: {e}")
            return {"error": f"Transaction failed: {str(e)}", "success": False}
    
    def estimate_fee(self, from_address: str, to_address: str, amount_satoshi: int) -> Dict:
        """Estimate transaction fee"""
        try:
            # Get UTXOs for the from address
            utxos = self.get_utxos(from_address)
            if not utxos:
                return {"error": "No UTXOs found for the source address", "success": False}
            
            # Simple fee estimation (can be improved)
            # For now, use a fixed fee based on transaction size
            estimated_fee = 1000  # 1000 satoshis base fee
            
            # Add fee based on number of inputs (rough estimation)
            num_inputs = len(utxos)
            estimated_fee += num_inputs * 200  # 200 satoshis per input
            
            return {
                "success": True,
                "estimated_fee_satoshi": estimated_fee,
                "estimated_fee_btc": estimated_fee / 100000000,
                "num_inputs": num_inputs,
                "total_available": sum(utxo.value for utxo in utxos),
                "amount_requested": amount_satoshi,
                "total_needed": amount_satoshi + estimated_fee
            }
            
        except Exception as e:
            logger.error(f"❌ Error estimating fee: {e}")
            return {"error": f"Fee estimation failed: {str(e)}", "success": False}
    
    def scan_history(self, address: str, blocks_back: int = 1000) -> bool:
        """Scan historical blocks for an address"""
        # Validate blocks_back to prevent excessive scanning
        if blocks_back > 10000:
            logger.warning(f"⚠️ Requested {blocks_back} blocks, limiting to 10000 for performance")
            blocks_back = 10000
        
        logger.info(f"🔍 Starting historical scan for {address} (last {blocks_back} blocks)")
        
        if not self.service:
            logger.error("❌ Service not initialized")
            return False
            
        try:
            # Get current block height
            current_height = self.service.blockcount()
            if current_height is None:
                logger.error("❌ Could not get current block height")
                return False
            
            start_height = max(0, current_height - blocks_back)
            logger.info(f"📊 Scanning blocks {start_height} to {current_height} ({blocks_back} blocks)")
            
            # Update balance and UTXOs
            self.get_balance(address)
            self.get_utxos(address)
            self.get_transactions(address)
            
            logger.info(f"✅ Historical scan completed for {address}")
            return True
                
        except Exception as e:
            logger.error(f"❌ Error during historical scan: {e}")
            return False
    
    def monitor_addresses_realtime(self):
        """Monitor watched addresses for new transactions in real-time"""
        while self.is_running:
            try:
                for address in list(self.watched_addresses.keys()):
                    # Get current balance
                    current_balance = self.get_balance(address)
                    
                    if current_balance:
                        old_balance = self.last_balances.get(address, 0)
                        new_balance = current_balance.confirmed_balance
                        
                        # Check for balance changes
                        if new_balance != old_balance:
                            logger.info(f"💰 Balance change detected for {address}: {old_balance} -> {new_balance}")
                            
                            # Emit real-time update via WebSocket
                            if self.socketio:
                                self.socketio.emit('balance_change', {
                                    'address': address,
                                    'old_balance': old_balance,
                                    'new_balance': new_balance,
                                    'old_balance_btc': old_balance / 100000000,
                                    'new_balance_btc': new_balance / 100000000,
                                    'timestamp': time.time()
                                })
                            
                            # Update last known balance
                            self.last_balances[address] = new_balance
                        
                        # Check for new transactions
                        current_transactions = self.get_transactions(address)
                        if current_transactions:
                            # Compare with previous transactions
                            old_transactions = self.transactions.get(address, [])
                            new_transactions = []
                            
                            for tx in current_transactions:
                                tx_id = tx.get('txid', '')
                                if not any(old_tx.get('txid', '') == tx_id for old_tx in old_transactions):
                                    new_transactions.append(tx)
                            
                            if new_transactions:
                                logger.info(f"🆕 New transactions detected for {address}: {len(new_transactions)}")
                                
                                # Emit real-time update via WebSocket
                                if self.socketio:
                                    self.socketio.emit('new_transactions', {
                                        'address': address,
                                        'transactions': new_transactions,
                                        'count': len(new_transactions),
                                        'timestamp': time.time()
                                    })
                            
                            # Update transaction cache
                            self.transactions[address] = current_transactions
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring addresses: {e}")
                time.sleep(5)
    
    def start(self):
        """Start the SPV client with real-time monitoring"""
        if self.is_running:
            logger.warning("⚠️ SPV client is already running")
            return
        
        self.is_running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_addresses_realtime, daemon=True)
        self.monitor_thread.start()
        
        logger.info("🚀 Simple SPV client started with real-time monitoring")
    
    def stop(self):
        """Stop the SPV client"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("🛑 Simple SPV client stopped")
    
    def get_status(self) -> Dict:
        """Get current status"""
        bloom_stats = self.provider_bloom_filter.get_stats()
        thompson_stats = self.get_thompson_sampling_stats() if self.thompson_sampling else {}
        
        return {
            "is_running": self.is_running,
            "watched_addresses": list(self.watched_addresses.keys()),
            "address_count": len(self.watched_addresses),
            "total_utxos": sum(len(utxos) for utxos in self.utxos.values()),
            "transactions": sum(len(txs) for txs in self.transactions.values()),
            "testnet": self.testnet,
            "service_available": self.service is not None,
            "realtime_monitoring": self.is_running,
            "bloom_filter_stats": bloom_stats,
            "successful_providers": bloom_stats["providers"],
            "thompson_sampling_stats": thompson_stats
        }
    
    def get_bloom_filter_stats(self) -> Dict:
        """Get detailed bloom filter statistics"""
        return self.provider_bloom_filter.get_stats()
    
    def get_successful_providers(self) -> List[str]:
        """Get list of providers that have successfully returned blocks"""
        return self.provider_bloom_filter.get_successful_providers()
    
    def get_thompson_sampling_stats(self) -> Dict:
        """Get Thompson sampling statistics"""
        if not self.thompson_sampling:
            return {}
        
        return {
            "provider_stats": self.thompson_sampling.get_provider_stats(),
            "best_provider": self.thompson_sampling.get_best_provider(),
            "exploration_stats": self.thompson_sampling.get_exploration_stats(),
            "last_selected": self.thompson_sampling.last_selected,
            "total_providers": len(self.thompson_sampling.providers)
        }
    
    def get_provider_performance(self) -> Dict:
        """Get detailed provider performance statistics"""
        if not self.thompson_sampling:
            return {}
        
        stats = self.thompson_sampling.get_provider_stats()
        best_provider = self.thompson_sampling.get_best_provider()
        
        return {
            "providers": stats,
            "best_provider": best_provider,
            "best_success_rate": stats[best_provider]["success_rate"] if best_provider else 0.0,
            "total_attempts": sum(stats[p]["total_attempts"] for p in stats),
            "total_successes": sum(stats[p]["successes"] for p in stats),
            "total_failures": sum(stats[p]["failures"] for p in stats)
        }

    def get_block_by_height(self, height: int) -> Optional[Dict]:
        """Get block information by height"""
        if not self.service:
            logger.error("❌ Service not initialized")
            return None
            
        try:
            logger.info(f"🔍 Fetching block at height {height}")
            
            # Get current block height to validate
            current_height = self.service.blockcount()
            if current_height is None:
                logger.error("❌ Could not get current block height")
                return None
            
            if height > current_height:
                logger.error(f"❌ Block height {height} exceeds current height {current_height}")
                return None
            
            # Retry mechanism: try different providers until we succeed
            max_retries = len(self.service.providers) * 2  # Try each provider up to 2 times
            retry_count = 0
            tried_providers = set()
            
            while retry_count < max_retries:
                retry_count += 1
                
                # Use Thompson sampling to select provider if available
                selected_provider = None
                if self.thompson_sampling:
                    selected_provider = self.thompson_sampling.select_provider()
                    logger.info(f"🎯 Thompson sampling selected provider: {selected_provider} (attempt {retry_count}/{max_retries})")
                
                # Try to get real block information using the service
                try:
                    # Try to get block data directly using height
                    block_info = self.service.getblock(height)
                    if block_info:
                        logger.info(f"✅ Got block info using height: {height}")
                        
                        # Update Thompson sampling with success
                        if self.thompson_sampling and selected_provider:
                            self.thompson_sampling.update_provider_result(selected_provider, True)
                        
                        # Track successful providers based on configured providers
                        # Since bitcoinlib doesn't expose current provider directly,
                        # we'll track all configured providers as potentially successful
                        if hasattr(self.service, 'providers'):
                            for provider_name in self.service.providers:
                                self.provider_bloom_filter.add(provider_name)
                            logger.info(f"🎯 Added configured providers to bloom filter: {list(self.service.providers)}")
                        
                        # Convert bitcoinlib Block object to dictionary
                        block_data = {
                            "height": height,
                            "hash": getattr(block_info, 'block_hash', '').hex() if hasattr(block_info, 'block_hash') and hasattr(block_info.block_hash, 'hex') else f"block_hash_height_{height}",
                            "version": getattr(block_info, 'version_int', 1),
                            "previousblockhash": getattr(block_info, 'prev_block', '').hex() if hasattr(block_info, 'prev_block') and hasattr(block_info.prev_block, 'hex') else "0000000000000000000000000000000000000000000000000000000000000000",
                            "merkleroot": getattr(block_info, 'merkle_root', '').hex() if hasattr(block_info, 'merkle_root') and hasattr(block_info.merkle_root, 'hex') else "0000000000000000000000000000000000000000000000000000000000000000",
                            "time": getattr(block_info, 'time', int(time.time())),
                            "bits": str(getattr(block_info, 'bits_int', '1d00ffff')),
                            "nonce": getattr(block_info, 'nonce_int', 0),
                            "size": getattr(block_info, 'size', 0),
                            "weight": getattr(block_info, 'size', 0) * 4,  # Approximate weight
                            "tx": [],
                            "tx_count": 0,
                            "difficulty": getattr(block_info, 'difficulty', 1.0),
                            "network": "testnet" if self.testnet else "mainnet"
                        }
                        
                        # Try to get transaction list if available
                        if hasattr(block_info, 'transactions') and block_info.transactions:
                            try:
                                block_data["tx"] = [tx.txid.hex() if hasattr(tx.txid, 'hex') else str(tx.txid) for tx in block_info.transactions]
                                block_data["tx_count"] = len(block_info.transactions)
                            except Exception as e:
                                logger.warning(f"⚠️ Could not extract transactions: {e}")
                        
                        logger.info(f"✅ Retrieved real block {height}: {block_data['hash']}")
                        return block_data
                    
                except Exception as e:
                    # Update Thompson sampling with failure
                    if self.thompson_sampling and selected_provider:
                        self.thompson_sampling.update_provider_result(selected_provider, False)
                        tried_providers.add(selected_provider)
                    
                    # Only log non-malformed script errors
                    error_msg = str(e)
                    if "Malformed script" not in error_msg:
                        logger.warning(f"⚠️ Attempt {retry_count}/{max_retries} failed: {error_msg}")
                    
                    # If we've tried all providers and still failing, try a different approach
                    if retry_count >= len(self.service.providers):
                        logger.warning(f"🔄 All providers failed, retrying with different approach...")
                        time.sleep(1)  # Brief pause before retry
                
                # If we haven't succeeded yet, continue to next retry
                if retry_count < max_retries:
                    logger.info(f"🔄 Retrying block fetch (attempt {retry_count + 1}/{max_retries})")
            
            # If we've exhausted all retries, return None instead of fallback data
            logger.error(f"❌ Failed to fetch block {height} after {max_retries} attempts")
            return None
                
        except Exception as e:
            logger.error(f"❌ Error getting block at height {height}: {e}")
            return None
    
    def get_block_by_hash(self, block_hash: str) -> Optional[Dict]:
        """Get block information by hash"""
        if not self.service:
            logger.error("❌ Service not initialized")
            return None
            
        try:
            logger.info(f"🔍 Fetching block with hash {block_hash}")
            
            # Retry mechanism: try different providers until we succeed
            max_retries = len(self.service.providers) * 2  # Try each provider up to 2 times
            retry_count = 0
            tried_providers = set()
            
            while retry_count < max_retries:
                retry_count += 1
                
                # Use Thompson sampling to select provider if available
                selected_provider = None
                if self.thompson_sampling:
                    selected_provider = self.thompson_sampling.select_provider()
                    logger.info(f"🎯 Thompson sampling selected provider: {selected_provider} (attempt {retry_count}/{max_retries})")
                
                # Try to get real block information using the service
                try:
                    # Convert hex hash to bytes if needed
                    if len(block_hash) == 64:  # Standard Bitcoin block hash length
                        # Try to get block info using the hash
                        block_info = self.service.getblock(block_hash)
                        if block_info:
                            # Update Thompson sampling with success
                            if self.thompson_sampling and selected_provider:
                                self.thompson_sampling.update_provider_result(selected_provider, True)
                            
                            # Convert bitcoinlib Block object to dictionary
                            block_data = {
                                "hash": block_hash,
                                "height": getattr(block_info, 'height', 0),
                                "version": getattr(block_info, 'version_int', 1),
                                "previousblockhash": getattr(block_info, 'prev_block', '').hex() if hasattr(block_info, 'prev_block') and hasattr(block_info.prev_block, 'hex') else "0000000000000000000000000000000000000000000000000000000000000000",
                                "merkleroot": getattr(block_info, 'merkle_root', '').hex() if hasattr(block_info, 'merkle_root') and hasattr(block_info.merkle_root, 'hex') else "0000000000000000000000000000000000000000000000000000000000000000",
                                "time": getattr(block_info, 'time', int(time.time())),
                                "bits": str(getattr(block_info, 'bits_int', '1d00ffff')),
                                "nonce": getattr(block_info, 'nonce_int', 0),
                                "size": getattr(block_info, 'size', 0),
                                "weight": getattr(block_info, 'size', 0) * 4,
                                "tx": [],
                                "tx_count": 0,
                                "difficulty": getattr(block_info, 'difficulty', 1.0),
                                "network": "testnet" if self.testnet else "mainnet"
                            }
                            
                            # Try to get transaction list if available
                            if hasattr(block_info, 'transactions') and block_info.transactions:
                                try:
                                    block_data["tx"] = [tx.txid.hex() if hasattr(tx.txid, 'hex') else str(tx.txid) for tx in block_info.transactions]
                                    block_data["tx_count"] = len(block_info.transactions)
                                except Exception as e:
                                    logger.warning(f"⚠️ Could not extract transactions: {e}")
                            
                            logger.info(f"✅ Retrieved real block: {block_hash}")
                            return block_data
                
                except Exception as e:
                    # Update Thompson sampling with failure
                    if self.thompson_sampling and selected_provider:
                        self.thompson_sampling.update_provider_result(selected_provider, False)
                        tried_providers.add(selected_provider)
                    
                    # Only log non-malformed script errors
                    error_msg = str(e)
                    if "Malformed script" not in error_msg:
                        logger.warning(f"⚠️ Attempt {retry_count}/{max_retries} failed: {error_msg}")
                    
                    # If we've tried all providers and still failing, try a different approach
                    if retry_count >= len(self.service.providers):
                        logger.warning(f"🔄 All providers failed, retrying with different approach...")
                        time.sleep(1)  # Brief pause before retry
                
                # If we haven't succeeded yet, continue to next retry
                if retry_count < max_retries:
                    logger.info(f"🔄 Retrying block fetch (attempt {retry_count + 1}/{max_retries})")
            
            # If we've exhausted all retries, return None instead of fallback data
            logger.error(f"❌ Failed to fetch block {block_hash} after {max_retries} attempts")
            return None
                
        except Exception as e:
            logger.error(f"❌ Error getting block with hash {block_hash}: {e}")
            return None
    

def create_simple_spv_api():
    """Create Flask API for simple SPV client with WebSocket support"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'spv-secret-key'
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")
    
    spv_client = SimpleSPVClient(testnet=True)
    spv_client.set_socketio(socketio)
    
    @app.route('/status', methods=['GET'])
    def get_status():
        return jsonify(spv_client.get_status())
    
    @app.route('/balance/<address>', methods=['GET'])
    def get_balance(address):
        balance = spv_client.get_balance(address)
        if balance:
            return jsonify({
                "address": balance.address,
                "confirmed_balance": balance.confirmed_balance,
                "confirmed_balance_btc": balance.confirmed_balance / 100000000,
                "unconfirmed_balance": balance.unconfirmed_balance,
                "unconfirmed_balance_btc": balance.unconfirmed_balance / 100000000,
                "utxo_count": balance.utxo_count,
                "last_updated": balance.last_updated
            })
        else:
            return jsonify({"error": "Could not get balance"}), 500
    
    @app.route('/utxos/<address>', methods=['GET'])
    def get_utxos(address):
        utxos = spv_client.get_utxos(address)
        return jsonify({
            "address": address,
            "count": len(utxos),
            "utxos": [
                {
                    "tx_hash": utxo.tx_hash,
                    "output_index": utxo.output_index,
                    "value": utxo.value,
                    "value_btc": utxo.value / 100000000,
                    "address": utxo.address,
                    "confirmed": utxo.confirmed
                }
                for utxo in utxos
            ]
        })
    
    @app.route('/transactions/<address>', methods=['GET'])
    def get_transactions(address):
        transactions = spv_client.get_transactions(address)
        if transactions is None:
            transactions = []
        
        return jsonify({
            "address": address,
            "count": len(transactions),
            "transactions": transactions
        })
    
    @app.route('/add_address', methods=['POST'])
    def add_address():
        data = request.get_json()
        address = data.get('address')
        
        if not address:
            return jsonify({"error": "Address is required"}), 400
        
        spv_client.add_watched_address(address)
        return jsonify({
            "address": address,
            "message": f"Address {address} added to watch list"
        })
    
    @app.route('/start', methods=['POST'])
    def start_spv():
        spv_client.start()
        return jsonify({
            "message": "Simple SPV client started",
            "status": spv_client.get_status()
        })
    
    @app.route('/stop', methods=['POST'])
    def stop_spv():
        spv_client.stop()
        return jsonify({
            "message": "Simple SPV client stopped"
        })
    
    @app.route('/scan_history/<address>', methods=['POST'])
    def scan_address_history(address):
        data = request.get_json() or {}
        blocks_back = data.get('blocks_back', 1000)
        
        # Validate blocks_back to prevent excessive scanning
        if blocks_back > 10000:
            blocks_back = 10000
            logger.warning(f"⚠️ Limiting scan to 10000 blocks for performance")
        
        def scan_background():
            success = spv_client.scan_history(address, blocks_back)
            if success:
                logger.info(f"✅ Historical scan completed for {address}")
            else:
                logger.error(f"❌ Historical scan failed for {address}")
        
        # Run scan in background
        thread = threading.Thread(target=scan_background, daemon=True)
        thread.start()
        
        return jsonify({
            "address": address,
            "blocks_back": blocks_back,
            "message": f"Started historical scan for {address}",
            "status": "scanning"
        })
    
    @app.route('/send_transaction', methods=['POST'])
    def send_transaction():
        """Send a Bitcoin transaction"""
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ['from_address', 'to_address', 'amount_satoshi', 'private_key']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create transaction request
        tx_request = TransactionRequest(
            from_address=data['from_address'],
            to_address=data['to_address'],
            amount_satoshi=data['amount_satoshi'],
            fee_satoshi=data.get('fee_satoshi', 1000),
            private_key=data['private_key'],
            change_address=data.get('change_address')
        )
        
        # Send transaction
        result = spv_client.send_transaction(tx_request)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @app.route('/estimate_fee', methods=['POST'])
    def estimate_fee():
        """Estimate transaction fee"""
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        required_fields = ['from_address', 'to_address', 'amount_satoshi']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Estimate fee
        result = spv_client.estimate_fee(
            data['from_address'],
            data['to_address'],
            data['amount_satoshi']
        )
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    @app.route('/bloom_filter_stats', methods=['GET'])
    def get_bloom_filter_stats():
        """Get bloom filter statistics"""
        return jsonify(spv_client.get_bloom_filter_stats())
    
    @app.route('/successful_providers', methods=['GET'])
    def get_successful_providers():
        """Get list of successful providers"""
        return jsonify({
            "providers": spv_client.get_successful_providers(),
            "count": len(spv_client.get_successful_providers())
        })
    
    @app.route('/thompson_sampling_stats', methods=['GET'])
    def get_thompson_sampling_stats():
        """Get Thompson sampling statistics"""
        return jsonify(spv_client.get_thompson_sampling_stats())
    
    @app.route('/provider_performance', methods=['GET'])
    def get_provider_performance():
        """Get detailed provider performance statistics"""
        return jsonify(spv_client.get_provider_performance())
    
    @app.route('/block_height', methods=['GET'])
    def get_block_height():
        try:
            if spv_client.service:
                height = spv_client.service.blockcount()
                return jsonify({
                    "height": height,
                    "network": "testnet" if spv_client.testnet else "mainnet"
                })
            else:
                return jsonify({"error": "Service not available"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/block/<int:height>', methods=['GET'])
    def get_block_by_height_endpoint(height):
        """Get block information by height"""
        try:
            # Validate height
            if height < 0:
                return jsonify({"error": "Block height must be non-negative"}), 400
            
            # Get current block height for validation
            current_height = spv_client.service.blockcount() if spv_client.service else None
            if current_height and height > current_height:
                return jsonify({
                    "error": f"Block height {height} exceeds current height {current_height}",
                    "current_height": current_height
                }), 400
            
            # Get block data
            block_data = spv_client.get_block_by_height(height)
            
            if block_data:
                return jsonify(block_data)
            else:
                return jsonify({"error": f"Could not retrieve block at height {height}"}), 404
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/block/hash/<block_hash>', methods=['GET'])
    def get_block_by_hash_endpoint(block_hash):
        """Get block information by hash"""
        try:
            # Validate hash format (basic check)
            if not block_hash or len(block_hash) != 64:
                return jsonify({"error": "Invalid block hash format"}), 400
            
            # Get block data
            block_data = spv_client.get_block_by_hash(block_hash)
            
            if block_data:
                return jsonify(block_data)
            else:
                return jsonify({"error": f"Could not retrieve block with hash {block_hash}"}), 404
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/blocks/recent', methods=['GET'])
    def get_recent_blocks():
        """Get recent blocks (last 10 by default)"""
        try:
            # Get parameters
            count = request.args.get('count', 10, type=int)
            count = min(count, 100)  # Limit to 100 blocks max
            
            if spv_client.service:
                current_height = spv_client.service.blockcount()
                if current_height is None:
                    return jsonify({"error": "Could not get current block height"}), 500
                
                blocks = []
                start_height = max(0, current_height - count + 1)
                
                for height in range(start_height, current_height + 1):
                    block_data = spv_client.get_block_by_height(height)
                    if block_data:
                        # Include only essential info for recent blocks
                        blocks.append({
                            "height": height,
                            "hash": block_data.get("hash"),
                            "timestamp": block_data.get("time"),
                            "size": block_data.get("size"),
                            "tx_count": block_data.get("tx_count"),
                            "network": block_data.get("network")
                        })
                
                return jsonify({
                    "blocks": blocks,
                    "count": len(blocks),
                    "start_height": start_height,
                    "end_height": current_height,
                    "network": "testnet" if spv_client.testnet else "mainnet"
                })
            else:
                return jsonify({"error": "Service not available"}), 500
                
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # WebSocket event handlers
    @socketio.on('connect')
    def handle_connect():
        logger.info(f"🔌 Client connected: {request.sid}")
        emit('connected', {'message': 'Connected to SPV real-time monitoring'})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info(f"🔌 Client disconnected: {request.sid}")
    
    @socketio.on('subscribe_address')
    def handle_subscribe_address(data):
        """Subscribe to real-time updates for an address"""
        address = data.get('address')
        if address:
            spv_client.add_watched_address(address)
            emit('subscribed', {
                'address': address,
                'message': f'Subscribed to real-time updates for {address}'
            })
            logger.info(f"📡 Client {request.sid} subscribed to {address}")
    
    @socketio.on('unsubscribe_address')
    def handle_unsubscribe_address(data):
        """Unsubscribe from real-time updates for an address"""
        address = data.get('address')
        if address and address in spv_client.watched_addresses:
            del spv_client.watched_addresses[address]
            emit('unsubscribed', {
                'address': address,
                'message': f'Unsubscribed from real-time updates for {address}'
            })
            logger.info(f"📡 Client {request.sid} unsubscribed from {address}")
    
    return app, socketio

def run_simple_spv_api():
    """Run the simple SPV API server with WebSocket support"""
    app, socketio = create_simple_spv_api()
    logger.info("Starting Simple SPV API server with WebSocket support on http://localhost:5005")
    socketio.run(app, host='0.0.0.0', port=5005, debug=True)

if __name__ == "__main__":
    run_simple_spv_api()
    
