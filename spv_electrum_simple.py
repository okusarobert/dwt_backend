#!/usr/bin/env python3
"""
Simplified SPV Implementation using bitcoinlib
This provides a much more robust and easier-to-maintain SPV client
"""

import logging
import threading
import time
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from flask import Flask, jsonify, request
import requests

# Bitcoin libraries
import bitcoinlib
from bitcoinlib.services.services import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class SimpleSPVClient:
    """Simplified SPV client using bitcoinlib"""
    
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        self.is_running = False
        self.watched_addresses: Dict[str, AddressBalance] = {}
        self.utxos: Dict[str, List[UTXO]] = {}
        self.transactions: Dict[str, List[Dict]] = {}
        self.lock = threading.Lock()
        
        # Initialize bitcoinlib service
        try:
            self.service = Service(network='testnet' if testnet else 'bitcoin')
            logger.info(f"🔧 Initialized Simple SPV Client (testnet: {testnet})")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Service: {e}")
            self.service = None
        
        # Thread for monitoring
        self.monitor_thread = None
    
    def add_watched_address(self, address: str):
        """Add address to watch list"""
        if address not in self.watched_addresses:
            self.watched_addresses[address] = AddressBalance(address=address)
            self.utxos[address] = []
            self.transactions[address] = []
            logger.info(f"✅ Added watched address: {address}")
        else:
            logger.info(f"ℹ️ Address {address} is already being watched")
    
    def get_balance(self, address: str) -> Optional[AddressBalance]:
        """Get balance for a specific address using bitcoinlib"""
        if not self.service:
            logger.error("❌ Service not initialized")
            return None
            
        try:
            # Get address info from service
            address_info = self.service.getaddressinfo(address)
            
            if address_info:
                balance = AddressBalance(
                    address=address,
                    confirmed_balance=address_info.get('balance', 0),
                    unconfirmed_balance=address_info.get('unconfirmed', 0),
                    utxo_count=len(address_info.get('utxos', [])),
                    last_updated=time.time()
                )
                
                # Update our cache
                self.watched_addresses[address] = balance
                
                # Update UTXOs
                self.utxos[address] = []
                for utxo_data in address_info.get('utxos', []):
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
            # Get address info from service
            address_info = self.service.getaddressinfo(address)
            
            if address_info:
                utxos = []
                for utxo_data in address_info.get('utxos', []):
                    utxo = UTXO(
                        tx_hash=utxo_data.get('txid', ''),
                        output_index=utxo_data.get('n', 0),
                        value=utxo_data.get('value', 0),
                        address=address,
                        confirmed=utxo_data.get('confirmations', 0) > 0
                    )
                    utxos.append(utxo)
                
                self.utxos[address] = utxos
                logger.info(f"📦 Found {len(utxos)} UTXOs for {address}")
                return utxos
                
        except Exception as e:
            logger.error(f"❌ Error getting UTXOs for {address}: {e}")
        
        return self.utxos.get(address, [])
    
    def get_transactions(self, address: str) -> List[Dict]:
        """Get transactions for a specific address"""
        if not self.service:
            logger.error("❌ Service not initialized")
            return []
            
        try:
            # Get address info from service
            address_info = self.service.getaddressinfo(address)
            
            if address_info:
                transactions = address_info.get('transactions', [])
                self.transactions[address] = transactions
                logger.info(f"📋 Found {len(transactions)} transactions for {address}")
                return transactions
                
        except Exception as e:
            logger.error(f"❌ Error getting transactions for {address}: {e}")
        
        return self.transactions.get(address, [])
    
    def scan_history(self, address: str, blocks_back: int = 100) -> bool:
        """Scan historical blocks for an address"""
        logger.info(f"🔍 Starting historical scan for {address} (last {blocks_back} blocks)")
        
        if not self.service:
            logger.error("❌ Service not initialized")
            return False
            
        try:
            # Get current block height
            current_height = self.service.getblockcount()
            if current_height is None:
                logger.error("❌ Could not get current block height")
                return False
            
            start_height = max(0, current_height - blocks_back)
            logger.info(f"📊 Scanning blocks {start_height} to {current_height}")
            
            # Get address info which includes historical data
            address_info = self.service.getaddressinfo(address)
            
            if address_info:
                # Update balance and UTXOs
                self.get_balance(address)
                self.get_utxos(address)
                self.get_transactions(address)
                
                logger.info(f"✅ Historical scan completed for {address}")
                return True
            else:
                logger.warning(f"⚠️ No data found for address {address}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error during historical scan: {e}")
            return False
    
    def monitor_addresses(self):
        """Monitor watched addresses for new transactions"""
        while self.is_running:
            try:
                for address in list(self.watched_addresses.keys()):
                    # Check for new transactions
                    old_balance = self.watched_addresses[address].confirmed_balance
                    new_balance = self.get_balance(address)
                    
                    if new_balance and new_balance.confirmed_balance != old_balance:
                        logger.info(f"💰 Balance change detected for {address}: {old_balance} -> {new_balance.confirmed_balance}")
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error monitoring addresses: {e}")
                time.sleep(10)
    
    def start(self):
        """Start the SPV client"""
        if self.is_running:
            logger.warning("⚠️ SPV client is already running")
            return
        
        self.is_running = True
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.monitor_addresses, daemon=True)
        self.monitor_thread.start()
        
        logger.info("🚀 Simple SPV client started")
    
    def stop(self):
        """Stop the SPV client"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("🛑 Simple SPV client stopped")
    
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "is_running": self.is_running,
            "watched_addresses": list(self.watched_addresses.keys()),
            "address_count": len(self.watched_addresses),
            "total_utxos": sum(len(utxos) for utxos in self.utxos.values()),
            "transactions": sum(len(txs) for txs in self.transactions.values()),
            "testnet": self.testnet,
            "service_available": self.service is not None
        }

def create_simple_spv_api():
    """Create Flask API for simple SPV client"""
    app = Flask(__name__)
    spv_client = SimpleSPVClient(testnet=True)
    
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
            return jsonify({"error": "Address not found"}), 404
    
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
        blocks_back = data.get('blocks_back', 100)
        
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
    
    @app.route('/block_height', methods=['GET'])
    def get_block_height():
        try:
            if spv_client.service:
                height = spv_client.service.getblockcount()
                return jsonify({
                    "height": height,
                    "network": "testnet" if spv_client.testnet else "mainnet"
                })
            else:
                return jsonify({"error": "Service not available"}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return app

def run_simple_spv_api():
    """Run the simple SPV API server"""
    app = create_simple_spv_api()
    logger.info("Starting Simple SPV API server on http://localhost:5004")
    app.run(host='0.0.0.0', port=5004, debug=True)

if __name__ == "__main__":
    run_simple_spv_api() 