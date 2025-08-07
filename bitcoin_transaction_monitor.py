#!/usr/bin/env python3
"""
Bitcoin Transaction Monitor
Comprehensive transaction monitoring with database integration
"""

import zmq
import json
import threading
import time
import logging
import requests
from typing import Dict, Any, List, Callable, Optional, Set
from datetime import datetime
from dataclasses import dataclass

# Import your existing database models
try:
    from db.connection import session
    from db.wallet import Transaction, TransactionType, TransactionStatus, CryptoAddress, PaymentProvider
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  Database not available - running in test mode")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TransactionNotification:
    """Transaction notification data"""
    tx_hash: str
    address: str
    amount: float
    tx_type: str
    block_height: Optional[int] = None
    confirmations: int = 0
    timestamp: datetime = None

class BitcoinTransactionMonitor:
    """Comprehensive Bitcoin transaction monitor"""
    
    def __init__(self, rpc_host: str = "localhost", rpc_port: int = 18332,
                 rpc_user: str = "bitcoin", rpc_password: str = "bitcoinpassword",
                 zmq_host: str = "localhost", zmq_ports: Dict[str, int] = None):
        """
        Initialize Bitcoin transaction monitor
        
        Args:
            rpc_host: Bitcoin RPC host
            rpc_port: Bitcoin RPC port
            rpc_user: Bitcoin RPC username
            rpc_password: Bitcoin RPC password
            zmq_host: ZMQ host
            zmq_ports: ZMQ port mappings
        """
        self.rpc_url = f"http://{rpc_host}:{rpc_port}"
        self.rpc_auth = (rpc_user, rpc_password)
        self.zmq_host = zmq_host
        self.zmq_ports = zmq_ports or {
            'rawtx': 28332,
            'hashblock': 28334,
            'hashtx': 28335
        }
        
        # Monitoring state
        self.is_running = False
        self.monitored_addresses: Set[str] = set()
        self.last_block_height = 0
        self.notification_callbacks: List[Callable] = []
        
        # Initialize ZMQ
        self._setup_zmq()
        
        # Initialize RPC session
        self.session = requests.Session()
        self.session.auth = self.rpc_auth
        
        logger.info("🔧 Bitcoin Transaction Monitor initialized")
    
    def _setup_zmq(self):
        """Setup ZMQ context and sockets"""
        try:
            self.zmq_context = zmq.Context()
            self.zmq_sockets = {}
            
            for topic, port in self.zmq_ports.items():
                try:
                    socket = self.zmq_context.socket(zmq.SUB)
                    socket.connect(f"tcp://{self.zmq_host}:{port}")
                    socket.setsockopt_string(zmq.SUBSCRIBE, "")
                    socket.setsockopt(zmq.RCVTIMEO, 1000)
                    self.zmq_sockets[topic] = socket
                    logger.info(f"✅ Connected to ZMQ {topic} on port {port}")
                except Exception as e:
                    logger.error(f"❌ Failed to connect to ZMQ {topic}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Failed to setup ZMQ: {e}")
    
    def add_monitored_address(self, address: str) -> bool:
        """Add an address to monitor"""
        try:
            # Validate Bitcoin address
            if not self._validate_address(address):
                logger.error(f"❌ Invalid Bitcoin address: {address}")
                return False
            
            self.monitored_addresses.add(address)
            logger.info(f"✅ Added address to monitor: {address}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding address {address}: {e}")
            return False
    
    def remove_monitored_address(self, address: str) -> bool:
        """Remove an address from monitoring"""
        try:
            self.monitored_addresses.discard(address)
            logger.info(f"✅ Removed address from monitoring: {address}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing address {address}: {e}")
            return False
    
    def add_notification_callback(self, callback: Callable[[TransactionNotification], None]):
        """Add a notification callback"""
        self.notification_callbacks.append(callback)
        logger.info("✅ Added notification callback")
    
    def _validate_address(self, address: str) -> bool:
        """Validate Bitcoin address format"""
        # Basic validation - you might want to use a proper Bitcoin library
        return address.startswith(('1', '3', 'bc1', 'tb1', 'm', 'n', '2'))
    
    def _make_rpc_request(self, method: str, params: list = None) -> Dict[str, Any]:
        """Make RPC request to Bitcoin node"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": "monitor"
        }
        
        try:
            response = self.session.post(self.rpc_url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ RPC request failed: {e}")
            return {}
    
    def _get_transaction_details(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get detailed transaction information"""
        try:
            response = self._make_rpc_request("getrawtransaction", [tx_hash, True])
            return response.get("result")
        except Exception as e:
            logger.error(f"❌ Error getting transaction details: {e}")
            return None
    
    def _get_block_info(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """Get block information"""
        try:
            response = self._make_rpc_request("getblock", [block_hash, 1])
            return response.get("result")
        except Exception as e:
            logger.error(f"❌ Error getting block info: {e}")
            return None
    
    def _process_transaction(self, tx_hash: str):
        """Process a new transaction"""
        try:
            # Get transaction details
            tx_info = self._get_transaction_details(tx_hash)
            if not tx_info:
                return
            
            # Check if transaction involves monitored addresses
            involved_addresses = set()
            
            # Check inputs
            for vin in tx_info.get("vin", []):
                if "prevout" in vin and "scriptpubkey_address" in vin["prevout"]:
                    address = vin["prevout"]["scriptpubkey_address"]
                    if address in self.monitored_addresses:
                        involved_addresses.add(address)
            
            # Check outputs
            for vout in tx_info.get("vout", []):
                if "scriptpubkey_address" in vout:
                    address = vout["scriptpubkey_address"]
                    if address in self.monitored_addresses:
                        involved_addresses.add(address)
            
            # If no monitored addresses involved, skip
            if not involved_addresses:
                return
            
            # Calculate amounts for each monitored address
            for address in involved_addresses:
                amount = self._calculate_address_amount(tx_info, address)
                if amount != 0:
                    notification = TransactionNotification(
                        tx_hash=tx_hash,
                        address=address,
                        amount=abs(amount),
                        tx_type="incoming" if amount > 0 else "outgoing",
                        confirmations=tx_info.get("confirmations", 0),
                        timestamp=datetime.fromtimestamp(tx_info.get("time", time.time()))
                    )
                    
                    # Send notification
                    self._send_notification(notification)
                    
                    # Save to database if available
                    if DB_AVAILABLE:
                        self._save_to_database(notification)
            
        except Exception as e:
            logger.error(f"❌ Error processing transaction {tx_hash}: {e}")
    
    def _calculate_address_amount(self, tx_info: Dict[str, Any], address: str) -> float:
        """Calculate the net amount for a specific address in a transaction"""
        try:
            total_in = 0.0
            total_out = 0.0
            
            # Calculate inputs (spending)
            for vin in tx_info.get("vin", []):
                if "prevout" in vin and "scriptpubkey_address" in vin["prevout"]:
                    if vin["prevout"]["scriptpubkey_address"] == address:
                        total_in += vin["prevout"]["value"] / 100000000  # Convert satoshis to BTC
            
            # Calculate outputs (receiving)
            for vout in tx_info.get("vout", []):
                if "scriptpubkey_address" in vout and vout["scriptpubkey_address"] == address:
                    total_out += vout["value"] / 100000000  # Convert satoshis to BTC
            
            # Net amount (positive = receiving, negative = sending)
            return total_out - total_in
            
        except Exception as e:
            logger.error(f"❌ Error calculating amount: {e}")
            return 0.0
    
    def _send_notification(self, notification: TransactionNotification):
        """Send notification to all registered callbacks"""
        logger.info(f"📦 Transaction notification: {notification.tx_hash[:16]}... "
                   f"| Address: {notification.address} | "
                   f"Amount: {notification.amount} BTC | "
                   f"Type: {notification.tx_type}")
        
        for callback in self.notification_callbacks:
            try:
                callback(notification)
            except Exception as e:
                logger.error(f"❌ Callback error: {e}")
    
    def _save_to_database(self, notification: TransactionNotification):
        """Save transaction to database"""
        try:
            # Check if transaction already exists
            existing_tx = session.query(Transaction).filter_by(
                tx_hash=notification.tx_hash,
                address=notification.address
            ).first()
            
            if existing_tx:
                logger.info(f"📝 Transaction already exists: {notification.tx_hash[:16]}...")
                return
            
            # Create new transaction record
            new_transaction = Transaction(
                address=notification.address,
                tx_hash=notification.tx_hash,
                amount=notification.amount,
                tx_type=TransactionType.INCOMING if notification.tx_type == "incoming" else TransactionType.OUTGOING,
                status=TransactionStatus.CONFIRMED if notification.confirmations > 0 else TransactionStatus.PENDING,
                timestamp=notification.timestamp,
                provider=PaymentProvider.BLOCKCYPHER,  # Or your preferred provider
                currency='BTC'
            )
            
            session.add(new_transaction)
            session.commit()
            
            logger.info(f"💾 Saved transaction to database: {notification.tx_hash[:16]}...")
            
        except Exception as e:
            logger.error(f"❌ Error saving to database: {e}")
            session.rollback()
    
    def _monitor_zmq_socket(self, topic: str, socket: zmq.Socket):
        """Monitor a ZMQ socket for notifications"""
        logger.info(f"🔍 Starting ZMQ monitor for {topic}")
        
        while self.is_running:
            try:
                data = socket.recv()
                if data:
                    if topic == 'hashtx':
                        tx_hash = data.hex()
                        logger.info(f"📦 New transaction hash: {tx_hash}")
                        self._process_transaction(tx_hash)
                    elif topic == 'hashblock':
                        block_hash = data.hex()
                        logger.info(f"📦 New block: {block_hash}")
                        # You could process the block here if needed
                        
            except zmq.Again:
                # Timeout - continue monitoring
                continue
            except Exception as e:
                logger.error(f"❌ Error monitoring {topic}: {e}")
                time.sleep(1)
    
    def _polling_monitor(self):
        """Fallback polling monitor for when ZMQ is not available"""
        logger.info("🔍 Starting polling monitor")
        
        while self.is_running:
            try:
                # Get current block height
                response = self._make_rpc_request("getblockcount")
                current_height = response.get("result", 0)
                
                if current_height > self.last_block_height:
                    logger.info(f"📦 New block detected: {current_height}")
                    self.last_block_height = current_height
                    
                    # Get recent transactions (this is a simplified approach)
                    # In practice, you'd want to track specific addresses more efficiently
                    
                time.sleep(10)  # Poll every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in polling monitor: {e}")
                time.sleep(30)
    
    def start_monitoring(self):
        """Start transaction monitoring"""
        if self.is_running:
            logger.warning("⚠️  Monitoring is already running")
            return
        
        self.is_running = True
        logger.info("🚀 Starting Bitcoin transaction monitoring...")
        
        # Start ZMQ monitoring threads
        self.monitor_threads = []
        for topic, socket in self.zmq_sockets.items():
            thread = threading.Thread(
                target=self._monitor_zmq_socket,
                args=(topic, socket),
                daemon=True
            )
            thread.start()
            self.monitor_threads.append(thread)
            logger.info(f"✅ Started ZMQ monitor for {topic}")
        
        # Start polling monitor as backup
        polling_thread = threading.Thread(
            target=self._polling_monitor,
            daemon=True
        )
        polling_thread.start()
        self.monitor_threads.append(polling_thread)
        logger.info("✅ Started polling monitor")
    
    def stop_monitoring(self):
        """Stop transaction monitoring"""
        if not self.is_running:
            logger.warning("⚠️  Monitoring is not running")
            return
        
        self.is_running = False
        logger.info("⏹️  Stopping Bitcoin transaction monitoring...")
        
        # Close ZMQ sockets
        for topic, socket in self.zmq_sockets.items():
            try:
                socket.close()
                logger.info(f"✅ Closed ZMQ socket for {topic}")
            except Exception as e:
                logger.error(f"❌ Error closing ZMQ socket {topic}: {e}")
        
        # Wait for threads to finish
        for thread in self.monitor_threads:
            thread.join(timeout=5)
        
        logger.info("✅ Transaction monitoring stopped")


def example_notification_callback(notification: TransactionNotification):
    """Example notification callback"""
    print(f"🎯 Transaction notification:")
    print(f"   Hash: {notification.tx_hash}")
    print(f"   Address: {notification.address}")
    print(f"   Amount: {notification.amount} BTC")
    print(f"   Type: {notification.tx_type}")
    print(f"   Confirmations: {notification.confirmations}")
    print(f"   Time: {notification.timestamp}")
    print()


def main():
    """Test the Bitcoin transaction monitor"""
    print("🔔 Bitcoin Transaction Monitor Test")
    print("=" * 50)
    
    # Create monitor
    monitor = BitcoinTransactionMonitor()
    
    # Add test addresses
    test_addresses = [
        "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",  # Testnet address
        "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh",           # Another testnet address
    ]
    
    for address in test_addresses:
        monitor.add_monitored_address(address)
    
    # Add notification callback
    monitor.add_notification_callback(example_notification_callback)
    
    try:
        # Start monitoring
        monitor.start_monitoring()
        
        # Run for 2 minutes
        print("⏳ Monitoring for 2 minutes...")
        time.sleep(120)
        
    except KeyboardInterrupt:
        print("\n⏹️  Stopping monitoring...")
    finally:
        monitor.stop_monitoring()
        print("✅ Monitoring stopped")


if __name__ == "__main__":
    main() 