#!/usr/bin/env python3
"""
TRON Address Polling System for efficient transaction monitoring
Uses TRONGrid API to poll for new transactions on monitored addresses
"""

import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from threading import Thread, Event
import requests

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PollingConfig:
    """Configuration for TRON address polling"""
    api_key: str
    network: str = "mainnet"
    poll_interval: int = 30  # seconds
    batch_size: int = 10  # addresses per batch
    max_retries: int = 3
    timeout: int = 10
    enable_logging: bool = True

class TronAddressPoller:
    """Efficient polling system for TRON addresses"""
    
    def __init__(self, config: PollingConfig):
        """Initialize the polling system"""
        self.config = config
        self.is_running = False
        self.stop_event = Event()
        self.monitored_addresses: Set[str] = set()
        self.last_transaction_hashes: Dict[str, str] = {}
        self.stats = {
            'total_polls': 0,
            'total_transactions': 0,
            'last_poll_time': None,
            'errors': 0
        }
        
        # Set up API URL based on network
        if config.network == "mainnet":
            self.base_url = "https://api.trongrid.io"
        elif config.network == "shasta":
            self.base_url = "https://api.shasta.trongrid.io"
        elif config.network == "nile":
            self.base_url = "https://api.nile.trongrid.io"
        else:
            raise ValueError(f"Unsupported network: {config.network}")
        
        logger.info(f"🔧 Initialized TRON poller for {config.network}")
        logger.info(f"📡 API URL: {self.base_url}")
        logger.info(f"⏱️  Poll interval: {config.poll_interval}s")
    
    def add_address(self, address: str) -> bool:
        """Add an address to monitor"""
        try:
            # Validate TRON address format
            if not self._is_valid_tron_address(address):
                logger.error(f"❌ Invalid TRON address format: {address}")
                return False
            
            self.monitored_addresses.add(address)
            logger.info(f"✅ Added address to monitor: {address}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding address {address}: {e}")
            return False
    
    def remove_address(self, address: str) -> bool:
        """Remove an address from monitoring"""
        try:
            self.monitored_addresses.discard(address)
            self.last_transaction_hashes.pop(address, None)
            logger.info(f"✅ Removed address from monitoring: {address}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing address {address}: {e}")
            return False
    
    def _is_valid_tron_address(self, address: str) -> bool:
        """Validate TRON address format"""
        # TRON addresses start with 'T' and are 34 characters long
        return address.startswith('T') and len(address) == 34
    
    def _get_address_transactions(self, address: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get recent transactions for an address"""
        try:
            url = f"{self.base_url}/v1/accounts/{address}/transactions"
            headers = {"TRON-PRO-API-KEY": self.config.api_key} if self.config.api_key else {}
            params = {"limit": limit, "only_confirmed": True}
            
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"❌ Failed to get transactions for {address}: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting transactions for {address}: {e}")
            return None
    
    def _get_trc20_transactions(self, address: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get TRC20 token transactions for an address"""
        try:
            url = f"{self.base_url}/v1/accounts/{address}/transactions/trc20"
            headers = {"TRON-PRO-API-KEY": self.config.api_key} if self.config.api_key else {}
            params = {"limit": limit, "only_confirmed": True}
            
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"❌ Failed to get TRC20 transactions for {address}: {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting TRC20 transactions for {address}: {e}")
            return None
    
    def _process_transactions(self, address: str, transactions: List[Dict[str, Any]]) -> int:
        """Process transactions and return count of new transactions"""
        new_transactions = 0
        last_hash = self.last_transaction_hashes.get(address)
        
        for tx in transactions:
            tx_hash = tx.get('txID', '')
            
            # Skip if we've already seen this transaction
            if last_hash and tx_hash == last_hash:
                break
            
            # Process new transaction
            if self._process_single_transaction(address, tx):
                new_transactions += 1
                
                # Update last seen hash
                if not last_hash:
                    self.last_transaction_hashes[address] = tx_hash
        
        return new_transactions
    
    def _process_single_transaction(self, address: str, tx: Dict[str, Any]) -> bool:
        """Process a single transaction"""
        try:
            tx_hash = tx.get('txID', '')
            tx_type = tx.get('type', '')
            timestamp = tx.get('block_timestamp', 0)
            
            # Convert timestamp to datetime
            tx_datetime = datetime.fromtimestamp(timestamp / 1000) if timestamp else datetime.now()
            
            logger.info(f"📦 New transaction: {tx_hash[:20]}... | Type: {tx_type} | Time: {tx_datetime}")
            
            # Here you would integrate with your database
            # For now, we'll just log the transaction
            self._save_transaction_to_database(address, tx, tx_datetime)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing transaction: {e}")
            return False
    
    def _save_transaction_to_database(self, address: str, tx: Dict[str, Any], tx_datetime: datetime):
        """Save transaction to database using the integration module"""
        try:
            # Import database integration
            from tron_database_integration import create_database_integration
            
            # Create database integration instance
            db_integration = create_database_integration()
            
            # Save transaction to database
            success = db_integration.save_transaction(address, tx, tx_datetime)
            
            if success:
                logger.info(f"💾 Transaction saved to database: {tx.get('txID', '')[:20]}...")
            else:
                logger.error(f"❌ Failed to save transaction to database: {tx.get('txID', '')[:20]}...")
                
        except Exception as e:
            logger.error(f"❌ Error saving transaction to database: {e}")
    
    def _save_trc20_transaction_to_database(self, address: str, tx: Dict[str, Any], tx_datetime: datetime):
        """Save TRC20 transaction to database using the integration module"""
        try:
            # Import database integration
            from tron_database_integration import create_database_integration
            
            # Create database integration instance
            db_integration = create_database_integration()
            
            # Save TRC20 transaction to database
            success = db_integration.save_trc20_transaction(address, tx, tx_datetime)
            
            if success:
                logger.info(f"💾 TRC20 transaction saved to database: {tx.get('transaction_id', '')[:20]}...")
            else:
                logger.error(f"❌ Failed to save TRC20 transaction to database: {tx.get('transaction_id', '')[:20]}...")
                
        except Exception as e:
            logger.error(f"❌ Error saving TRC20 transaction to database: {e}")
    
    def _poll_address_batch(self, addresses: List[str]) -> int:
        """Poll a batch of addresses for new transactions"""
        total_new_transactions = 0
        
        for address in addresses:
            try:
                # Get regular transactions
                tx_response = self._get_address_transactions(address)
                if tx_response:
                    transactions = tx_response.get('data', [])
                    new_txs = self._process_transactions(address, transactions)
                    total_new_transactions += new_txs
                
                # Get TRC20 token transactions
                trc20_response = self._get_trc20_transactions(address)
                if trc20_response:
                    trc20_transactions = trc20_response.get('data', [])
                    new_trc20_txs = self._process_trc20_transactions(address, trc20_transactions)
                    total_new_transactions += new_trc20_txs
                
                # Small delay between requests to avoid rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Error polling address {address}: {e}")
                self.stats['errors'] += 1
        
        return total_new_transactions
    
    def _process_trc20_transactions(self, address: str, transactions: List[Dict[str, Any]]) -> int:
        """Process TRC20 transactions and return count of new transactions"""
        new_transactions = 0
        last_hash = self.last_transaction_hashes.get(f"{address}_trc20")
        
        for tx in transactions:
            tx_hash = tx.get('transaction_id', '')
            
            # Skip if we've already seen this transaction
            if last_hash and tx_hash == last_hash:
                break
            
            # Process new transaction
            if self._process_single_trc20_transaction(address, tx):
                new_transactions += 1
                
                # Update last seen hash
                if not last_hash:
                    self.last_transaction_hashes[f"{address}_trc20"] = tx_hash
        
        return new_transactions
    
    def _process_single_trc20_transaction(self, address: str, tx: Dict[str, Any]) -> bool:
        """Process a single TRC20 transaction"""
        try:
            tx_hash = tx.get('transaction_id', '')
            token_symbol = tx.get('token_info', {}).get('token_abbr', 'Unknown')
            amount = tx.get('value', 0)
            timestamp = tx.get('block_timestamp', 0)
            
            # Convert timestamp to datetime
            tx_datetime = datetime.fromtimestamp(timestamp / 1000) if timestamp else datetime.now()
            
            logger.info(f"📦 New TRC20 transaction: {tx_hash[:20]}... | Token: {token_symbol} | Time: {tx_datetime}")
            
            # Save to database
            self._save_trc20_transaction_to_database(address, tx, tx_datetime)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing TRC20 transaction: {e}")
            return False
    
    def _polling_worker(self):
        """Main polling worker thread"""
        logger.info("🚀 Starting TRON address polling...")
        
        while not self.stop_event.is_set():
            try:
                if not self.monitored_addresses:
                    logger.info("⏳ No addresses to monitor, waiting...")
                    time.sleep(self.config.poll_interval)
                    continue
                
                # Convert set to list for batching
                addresses = list(self.monitored_addresses)
                
                # Process addresses in batches
                total_new_transactions = 0
                for i in range(0, len(addresses), self.config.batch_size):
                    batch = addresses[i:i + self.config.batch_size]
                    new_txs = self._poll_address_batch(batch)
                    total_new_transactions += new_txs
                
                # Update statistics
                self.stats['total_polls'] += 1
                self.stats['total_transactions'] += total_new_transactions
                self.stats['last_poll_time'] = datetime.now()
                
                if self.config.enable_logging:
                    logger.info(f"📊 Poll #{self.stats['total_polls']}: "
                              f"Found {total_new_transactions} new transactions "
                              f"from {len(addresses)} addresses")
                
                # Wait for next poll
                self.stop_event.wait(self.config.poll_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in polling worker: {e}")
                self.stats['errors'] += 1
                time.sleep(5)  # Wait before retrying
    
    def start_polling(self):
        """Start the polling system"""
        if self.is_running:
            logger.warning("⚠️  Polling is already running")
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start polling in a separate thread
        self.polling_thread = Thread(target=self._polling_worker, daemon=True)
        self.polling_thread.start()
        
        logger.info("✅ TRON polling started")
    
    def stop_polling(self):
        """Stop the polling system"""
        if not self.is_running:
            logger.warning("⚠️  Polling is not running")
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if hasattr(self, 'polling_thread'):
            self.polling_thread.join(timeout=5)
        
        logger.info("⏹️  TRON polling stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get polling statistics"""
        return {
            **self.stats,
            'monitored_addresses': len(self.monitored_addresses),
            'is_running': self.is_running,
            'network': self.config.network
        }
    
    def get_monitored_addresses(self) -> List[str]:
        """Get list of monitored addresses"""
        return list(self.monitored_addresses)


def main():
    """Test the TRON polling system"""
    print("🔧 TRON Address Polling System")
    print("=" * 50)
    
    # Get API key
    api_key = os.getenv('TRONGRID_API_KEY')
    if not api_key:
        print("⚠️  No TRONGRID_API_KEY environment variable found.")
        print("📝 Get your free API key at: https://www.trongrid.io/")
        api_key = "c6ea62f4-4f0b-4af2-9c6b-495ae84d1648"  # Test key
    
    # Create polling configuration
    config = PollingConfig(
        api_key=api_key,
        network="shasta",  # Use testnet for testing
        poll_interval=30,  # Poll every 30 seconds
        batch_size=5,      # Process 5 addresses at a time
        enable_logging=True
    )
    
    # Create poller
    poller = TronAddressPoller(config)
    
    # Add some test addresses
    test_addresses = [
        "TJRabPrwbZy45sbavfcjinPJC18kjpRTv8",  # Example TRON address
        "TJRabPrwbZy45sbavfcjinPJC18kjpRTv9",  # Another example
    ]
    
    for address in test_addresses:
        poller.add_address(address)
    
    try:
        # Start polling
        poller.start_polling()
        
        # Run for 2 minutes
        print("⏳ Running for 2 minutes...")
        time.sleep(120)
        
        # Show statistics
        stats = poller.get_statistics()
        print("\n📊 Polling Statistics:")
        print(f"   Total polls: {stats['total_polls']}")
        print(f"   Total transactions: {stats['total_transactions']}")
        print(f"   Errors: {stats['errors']}")
        print(f"   Monitored addresses: {stats['monitored_addresses']}")
        print(f"   Last poll: {stats['last_poll_time']}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Stopping polling...")
    finally:
        poller.stop_polling()
        print("✅ Polling stopped")


if __name__ == "__main__":
    main() 