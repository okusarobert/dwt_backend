#!/usr/bin/env python3
"""
Litecoin Light Client API
Connects to a Litecoin Core node and provides REST API endpoints
"""

import os
import time
import logging
import json
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from bitcoinrpc.authproxy import AuthServiceProxy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_attributedict(obj):
    """Convert AttributeDict objects to regular dictionaries for JSON serialization"""
    if hasattr(obj, '__dict__'):
        # Convert object to dict
        result = {}
        for attr in dir(obj):
            if not attr.startswith('_') and not callable(getattr(obj, attr)):
                try:
                    value = getattr(obj, attr)
                    result[attr] = convert_attributedict(value)
                except:
                    pass
        return result
    elif isinstance(obj, dict):
        return {k: convert_attributedict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_attributedict(item) for item in obj]
    elif hasattr(obj, 'hex'):  # Handle HexBytes
        return obj.hex()
    else:
        return obj

class LitecoinLightClient:
    """Light client that connects to a Litecoin Core node"""
    
    def __init__(self):
        # Get configuration from environment variables
        self.rpc_host = os.getenv('LITECOIN_RPC_HOST', 'localhost')
        self.rpc_port = int(os.getenv('LITECOIN_RPC_PORT', 9332))
        self.rpc_user = os.getenv('LITECOIN_RPC_USER', 'litecoin_rpc_user')
        self.rpc_password = os.getenv('LITECOIN_RPC_PASSWORD', 'your_secure_password_here_change_this')
        
        # Initialize RPC connection
        self.rpc_url = f"http://{self.rpc_user}:{self.rpc_password}@{self.rpc_host}:{self.rpc_port}"
        self.rpc_connection = None
        self.is_connected = False
        
        # Initialize connection
        self._connect_rpc()
    
    def _connect_rpc(self):
        """Connect to Litecoin Core RPC"""
        max_retries = 5
        retry_delay = 3  # seconds
        
        for attempt in range(max_retries):
            try:
                self.rpc_connection = AuthServiceProxy(self.rpc_url, timeout=30)
                # Test connection
                info = self.rpc_connection.getblockchaininfo()
                self.is_connected = True
                
                # Convert to dict for easier access
                info_dict = convert_attributedict(info)
                
                logger.info(f"✅ Connected to Litecoin Core node: {info_dict.get('chain', 'unknown')} chain")
                logger.info(f"📊 Current block height: {info_dict.get('blocks', 0)}")
                logger.info(f"📋 Headers: {info_dict.get('headers', 0)}")
                logger.info(f"💾 Pruned: {info_dict.get('pruned', False)}")
                logger.info(f"🔄 Sync progress: {info_dict.get('verificationprogress', 0):.6%}")
                
                # Check if still in initial block download
                if info_dict.get('initialblockdownload', False):
                    logger.warning(f"⚠️ Node is still in initial block download - some features may be limited")
                    logger.info(f"📈 Sync status: {info_dict.get('blocks', 0)}/{info_dict.get('headers', 0)} blocks downloaded")
                    logger.info(f"⏳ This is normal during initial sync. Node will be ready when blocks start downloading.")
                else:
                    logger.info(f"✅ Node is fully synced and ready")
                
                return  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Connection attempt {attempt + 1}/{max_retries} failed: {error_msg}")
                
                # If this is the last attempt, mark as failed
                if attempt == max_retries - 1:
                    logger.error(f"❌ Failed to connect to Litecoin Core after {max_retries} attempts: {error_msg}")
                    self.is_connected = False
                    return
                
                # Wait before retry
                time.sleep(retry_delay)
                retry_delay *= 1.2  # Slight exponential backoff
    
    def get_blockchain_info(self) -> Dict:
        """Get blockchain information"""
        if not self.is_connected:
            return {"error": "Not connected to Litecoin Core"}
        
        # Retry logic for unstable connections during initial sync
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                info = self.rpc_connection.getblockchaininfo()
                # Convert AttributeDict to regular dict
                info_dict = convert_attributedict(info)
                
                # Check if node is still in initial block download
                if info_dict.get('initialblockdownload', False):
                    logger.info(f"📊 Node sync status: {info_dict.get('blocks', 0)}/{info_dict.get('headers', 0)} blocks")
                    return {
                        "status": "syncing",
                        "message": "Litecoin node is still in initial block download",
                        "blocks": info_dict.get('blocks', 0),
                        "headers": info_dict.get('headers', 0),
                        "verification_progress": info_dict.get('verificationprogress', 0),
                        "chain": info_dict.get('chain', 'unknown'),
                        "pruned": info_dict.get('pruned', False),
                        "sync_percentage": f"{info_dict.get('verificationprogress', 0) * 100:.6f}%",
                        "initial_block_download": True
                    }
                
                return info_dict
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {error_msg}")
                
                # If this is the last attempt, return error
                if attempt == max_retries - 1:
                    logger.error(f"❌ All attempts failed to get blockchain info: {error_msg}")
                    return {"error": error_msg}
                
                # Wait before retry
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
    
    def get_block_by_height(self, height: int) -> Dict:
        """Get block information by height"""
        if not self.is_connected:
            return {"error": "Not connected to Litecoin Core"}
        
        try:
            block_hash = self.rpc_connection.getblockhash(height)
            block_info = self.rpc_connection.getblock(block_hash)
            
            # Convert AttributeDict to regular dict
            return convert_attributedict(block_info)
        except Exception as e:
            logger.error(f"❌ Error getting block {height}: {e}")
            return {"error": str(e)}
    
    def get_block_by_hash(self, block_hash: str) -> Dict:
        """Get block information by hash"""
        if not self.is_connected:
            return {"error": "Not connected to Litecoin Core"}
        
        try:
            block_info = self.rpc_connection.getblock(block_hash)
            
            # Convert AttributeDict to regular dict
            return convert_attributedict(block_info)
        except Exception as e:
            logger.error(f"❌ Error getting block {block_hash}: {e}")
            return {"error": str(e)}
    
    def get_transaction(self, txid: str) -> Dict:
        """Get transaction information"""
        if not self.is_connected:
            return {"error": "Not connected to Litecoin Core"}
        
        try:
            tx_info = self.rpc_connection.getrawtransaction(txid, True)
            
            # Convert AttributeDict to regular dict
            return convert_attributedict(tx_info)
        except Exception as e:
            logger.error(f"❌ Error getting transaction {txid}: {e}")
            return {"error": str(e)}
    
    def get_utxos(self, address: str) -> List[Dict]:
        """Get UTXOs for an address"""
        if not self.is_connected:
            return {"error": "Not connected to Litecoin Core"}
        
        try:
            utxos = self.rpc_connection.gettxoutsetinfo()
            # For now, return basic UTXO info
            # In a real implementation, you'd need to scan for address-specific UTXOs
            return {
                "address": address,
                "total_utxos": utxos.get('txouts', 0),
                "total_amount": utxos.get('total_amount', 0),
                "note": "This endpoint returns general UTXO info. Address-specific UTXOs require full node scanning."
            }
        except Exception as e:
            logger.error(f"❌ Error getting UTXOs for {address}: {e}")
            return {"error": str(e)}
    
    def get_balance(self, address: str) -> Dict:
        """Get balance for an address"""
        if not self.is_connected:
            return {"error": "Not connected to Litecoin Core"}
        
        try:
            # Note: This requires the address to be imported or watched
            # For a light client, you'd typically need to scan the blockchain
            balance = self.rpc_connection.getreceivedbyaddress(address)
            
            return {
                "address": address,
                "balance": balance,
                "note": "This is the received amount. For full balance, address must be imported/watched."
            }
        except Exception as e:
            logger.error(f"❌ Error getting balance for {address}: {e}")
            return {"error": str(e)}

# Initialize light client
light_client = LitecoinLightClient()

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'litecoin-light-client-secret'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/status', methods=['GET'])
def get_status():
    """Get light client status"""
    blockchain_info = light_client.get_blockchain_info()
    
    return jsonify({
        "connected": light_client.is_connected,
        "rpc_host": light_client.rpc_host,
        "rpc_port": light_client.rpc_port,
        "blockchain_info": blockchain_info
    })

@app.route('/blockchain_info', methods=['GET'])
def get_blockchain_info():
    """Get blockchain information"""
    return jsonify(light_client.get_blockchain_info())

@app.route('/block/<int:height>', methods=['GET'])
def get_block_by_height(height):
    """Get block by height"""
    return jsonify(light_client.get_block_by_height(height))

@app.route('/block/hash/<block_hash>', methods=['GET'])
def get_block_by_hash(block_hash):
    """Get block by hash"""
    return jsonify(light_client.get_block_by_hash(block_hash))

@app.route('/transaction/<txid>', methods=['GET'])
def get_transaction(txid):
    """Get transaction by ID"""
    return jsonify(light_client.get_transaction(txid))

@app.route('/utxos/<address>', methods=['GET'])
def get_utxos(address):
    """Get UTXOs for an address"""
    return jsonify(light_client.get_utxos(address))

@app.route('/balance/<address>', methods=['GET'])
def get_balance(address):
    """Get balance for an address"""
    return jsonify(light_client.get_balance(address))

@app.route('/recent_blocks', methods=['GET'])
def get_recent_blocks():
    """Get recent blocks"""
    try:
        blockchain_info = light_client.get_blockchain_info()
        if "error" in blockchain_info:
            return jsonify({"error": blockchain_info["error"]})
        
        current_height = blockchain_info.get("blocks", 0)
        count = min(int(request.args.get('count', 10)), 100)  # Limit to 100 blocks
        
        blocks = []
        for height in range(max(0, current_height - count + 1), current_height + 1):
            block_info = light_client.get_block_by_height(height)
            if "error" not in block_info:
                blocks.append({
                    "height": height,
                    "hash": block_info.get("hash"),
                    "time": block_info.get("time"),
                    "size": block_info.get("size"),
                    "tx_count": block_info.get("tx_count")
                })
        
        return jsonify({
            "blocks": blocks,
            "count": len(blocks),
            "current_height": current_height
        })
    except Exception as e:
        return jsonify({"error": str(e)})

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    logger.info(f"🔌 Client connected: {request.sid}")
    emit('connected', {
        'message': 'Connected to Litecoin Light Client',
        'status': 'connected'
    })

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"🔌 Client disconnected: {request.sid}")

@socketio.on('get_blockchain_info')
def handle_get_blockchain_info():
    """Handle WebSocket request for blockchain info"""
    info = light_client.get_blockchain_info()
    emit('blockchain_info', info)

if __name__ == '__main__':
    logger.info("🚀 Starting Litecoin Light Client API on port 5007")
    socketio.run(app, host='0.0.0.0', port=5007, debug=True, allow_unsafe_werkzeug=True) 