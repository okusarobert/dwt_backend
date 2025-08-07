#!/usr/bin/env python3
"""
SPV Balance API - Simple API to get address balances from SPV client
"""

from flask import Flask, jsonify, request
import threading
import time
import logging
from spv_balance_tracker import SPVBalanceTracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global SPV tracker instance
spv_tracker = None
tracker_thread = None

def start_spv_tracker():
    """Start the SPV tracker in a background thread"""
    global spv_tracker, tracker_thread
    
    spv_tracker = SPVBalanceTracker()
    
    # Add some test addresses
    test_addresses = [
        "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
        "tb1qrp33g0q5c5txsp9arysrx4k6zdkfs4nce4xj0gdcccefvpysxf3q0sl5k7"
    ]
    
    for address in test_addresses:
        spv_tracker.add_watched_address(address)
    
    # Start tracker in background thread
    tracker_thread = threading.Thread(target=spv_tracker.start, daemon=True)
    tracker_thread.start()
    
    # Wait a bit for initialization
    time.sleep(3)
    logger.info("SPV tracker started in background")

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'spv_tracker_running': spv_tracker is not None and spv_tracker.is_running,
        'connected_peers': len(spv_tracker.peers) if spv_tracker else 0,
        'watched_addresses': len(spv_tracker.watched_addresses) if spv_tracker else 0
    })

@app.route('/balance/<address>', methods=['GET'])
def get_balance(address):
    """Get balance for a specific address"""
    if not spv_tracker:
        return jsonify({'error': 'SPV tracker not initialized'}), 500
    
    balance = spv_tracker.get_balance(address)
    if balance:
        return jsonify({
            'address': address,
            'confirmed_balance': balance.confirmed_balance,
            'unconfirmed_balance': balance.unconfirmed_balance,
            'confirmed_balance_btc': balance.confirmed_balance / 100000000,
            'unconfirmed_balance_btc': balance.unconfirmed_balance / 100000000,
            'utxo_count': balance.utxo_count,
            'last_updated': balance.last_updated
        })
    else:
        return jsonify({'error': 'Address not found or not being tracked'}), 404

@app.route('/balances', methods=['GET'])
def get_all_balances():
    """Get balances for all watched addresses"""
    if not spv_tracker:
        return jsonify({'error': 'SPV tracker not initialized'}), 500
    
    balances = {}
    for address, balance in spv_tracker.watched_addresses.items():
        balances[address] = {
            'confirmed_balance': balance.confirmed_balance,
            'unconfirmed_balance': balance.unconfirmed_balance,
            'confirmed_balance_btc': balance.confirmed_balance / 100000000,
            'unconfirmed_balance_btc': balance.unconfirmed_balance / 100000000,
            'utxo_count': balance.utxo_count,
            'last_updated': balance.last_updated
        }
    
    return jsonify({
        'balances': balances,
        'total_addresses': len(balances)
    })

@app.route('/add_address', methods=['POST'])
def add_address():
    """Add a new address to watch"""
    if not spv_tracker:
        return jsonify({'error': 'SPV tracker not initialized'}), 500
    
    data = request.get_json()
    if not data or 'address' not in data:
        return jsonify({'error': 'Address is required'}), 400
    
    address = data['address']
    spv_tracker.add_watched_address(address)
    
    return jsonify({
        'message': f'Address {address} added to watch list',
        'address': address
    })

@app.route('/utxos/<address>', methods=['GET'])
def get_utxos(address):
    """Get UTXOs for a specific address"""
    if not spv_tracker:
        return jsonify({'error': 'SPV tracker not initialized'}), 500
    
    if address not in spv_tracker.utxos:
        return jsonify({'error': 'Address not found or not being tracked'}), 404
    
    utxos = []
    for utxo in spv_tracker.utxos[address]:
        utxos.append({
            'tx_hash': utxo.tx_hash,
            'output_index': utxo.output_index,
            'value': utxo.value,
            'value_btc': utxo.value / 100000000,
            'confirmed': utxo.confirmed,
            'address': utxo.address
        })
    
    return jsonify({
        'address': address,
        'utxos': utxos,
        'count': len(utxos)
    })

@app.route('/spv_status', methods=['GET'])
def get_spv_status():
    """Get detailed SPV status information"""
    if not spv_tracker:
        return jsonify({'error': 'SPV tracker not initialized'}), 500
    
    return jsonify(spv_tracker.get_spv_status())

@app.route('/status', methods=['GET'])
def get_status():
    """Get detailed status of the SPV tracker"""
    if not spv_tracker:
        return jsonify({'error': 'SPV tracker not initialized'}), 500
    
    return jsonify({
        'is_running': spv_tracker.is_running,
        'connected_peers': spv_tracker.peers,
        'peer_count': len(spv_tracker.peers),
        'watched_addresses': list(spv_tracker.watched_addresses.keys()),
        'address_count': len(spv_tracker.watched_addresses),
        'cached_transactions': len(spv_tracker.transaction_cache),
        'total_utxos': sum(len(utxos) for utxos in spv_tracker.utxos.values())
    })

if __name__ == '__main__':
    # Start SPV tracker
    start_spv_tracker()
    
    # Start Flask app
    logger.info("Starting SPV Balance API on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True) 