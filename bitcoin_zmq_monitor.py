#!/usr/bin/env python3
"""
Bitcoin ZMQ Transaction Monitor
Real-time transaction notifications using ZeroMQ
"""

import zmq
import json
import threading
import time
import logging
import signal
import sys
from typing import Dict, Any, List, Callable
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BitcoinZMQMonitor:
    """Bitcoin ZMQ monitor for real-time transaction notifications"""
    
    def __init__(self, zmq_host: str = "localhost", zmq_ports: Dict[str, int] = None):
        """
        Initialize ZMQ monitor
        
        Args:
            zmq_host: ZMQ host (usually localhost)
            zmq_ports: Dictionary of ZMQ port mappings
        """
        self.zmq_host = zmq_host
        self.zmq_ports = zmq_ports or {
            'rawtx': 28332,
            'rawblock': 28333,
            'hashblock': 28334,
            'hashtx': 28335,
            'sequence': 28336
        }
        
        self.sockets: Dict[str, zmq.Socket] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.is_running = False
        self.monitor_threads = []
        
        # Set up ZMQ context
        self.context = zmq.Context()
        
        # Initialize sockets
        self._setup_sockets()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.stop_monitoring()
        sys.exit(0)
    
    def _setup_sockets(self):
        """Set up ZMQ sockets for each topic"""
        for topic, port in self.zmq_ports.items():
            try:
                socket = self.context.socket(zmq.SUB)
                socket.connect(f"tcp://{self.zmq_host}:{port}")
                socket.setsockopt_string(zmq.SUBSCRIBE, "")
                socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
                
                self.sockets[topic] = socket
                self.callbacks[topic] = []
                
                logger.info(f"✅ Connected to ZMQ {topic} on port {port}")
                
            except Exception as e:
                logger.error(f"❌ Failed to connect to ZMQ {topic}: {e}")
    
    def add_callback(self, topic: str, callback: Callable):
        """Add a callback function for a specific topic"""
        if topic in self.callbacks:
            self.callbacks[topic].append(callback)
            logger.info(f"✅ Added callback for {topic}")
        else:
            logger.error(f"❌ Unknown topic: {topic}")
    
    def _process_rawtx(self, data: bytes):
        """Process raw transaction data"""
        try:
            # Convert bytes to hex string
            tx_hex = data.hex()
            
            # Call all registered callbacks
            for callback in self.callbacks.get('rawtx', []):
                try:
                    callback(tx_hex)
                except Exception as e:
                    logger.error(f"❌ Error in rawtx callback: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error processing rawtx: {e}")
    
    def _process_hashblock(self, data: bytes):
        """Process block hash data"""
        try:
            # Convert bytes to hex string
            block_hash = data.hex()
            
            # Call all registered callbacks
            for callback in self.callbacks.get('hashblock', []):
                try:
                    callback(block_hash)
                except Exception as e:
                    logger.error(f"❌ Error in hashblock callback: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error processing hashblock: {e}")
    
    def _process_hashtx(self, data: bytes):
        """Process transaction hash data"""
        try:
            # Convert bytes to hex string
            tx_hash = data.hex()
            
            # Call all registered callbacks
            for callback in self.callbacks.get('hashtx', []):
                try:
                    callback(tx_hash)
                except Exception as e:
                    logger.error(f"❌ Error in hashtx callback: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error processing hashtx: {e}")
    
    def _monitor_socket(self, topic: str, socket: zmq.Socket):
        """Monitor a specific ZMQ socket"""
        logger.info(f"🔍 Starting monitor for {topic}")
        
        while self.is_running:
            try:
                # Receive data with timeout
                data = socket.recv()
                
                if data:
                    # Process based on topic
                    if topic == 'rawtx':
                        self._process_rawtx(data)
                    elif topic == 'hashblock':
                        self._process_hashblock(data)
                    elif topic == 'hashtx':
                        self._process_hashtx(data)
                    elif topic == 'rawblock':
                        # Process raw block data
                        logger.info(f"📦 New raw block received")
                    elif topic == 'sequence':
                        # Process sequence data
                        logger.info(f"📦 New sequence received")
                        
            except zmq.Again:
                # Timeout - continue monitoring
                continue
            except Exception as e:
                logger.error(f"❌ Error monitoring {topic}: {e}")
                time.sleep(1)
    
    def start_monitoring(self):
        """Start monitoring all ZMQ sockets"""
        if self.is_running:
            logger.warning("⚠️  Monitoring is already running")
            return
        
        self.is_running = True
        logger.info("🚀 Starting Bitcoin ZMQ monitoring...")
        
        # Start monitoring threads for each socket
        self.monitor_threads = []
        for topic, socket in self.sockets.items():
            thread = threading.Thread(
                target=self._monitor_socket,
                args=(topic, socket),
                daemon=True
            )
            thread.start()
            self.monitor_threads.append(thread)
            logger.info(f"✅ Started monitor thread for {topic}")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        if not self.is_running:
            logger.warning("⚠️  Monitoring is not running")
            return
        
        self.is_running = False
        logger.info("⏹️  Stopping Bitcoin ZMQ monitoring...")
        
        # Close sockets
        for topic, socket in self.sockets.items():
            try:
                socket.close()
                logger.info(f"✅ Closed socket for {topic}")
            except Exception as e:
                logger.error(f"❌ Error closing socket {topic}: {e}")
        
        # Wait for threads to finish
        for thread in self.monitor_threads:
            thread.join(timeout=5)
        
        logger.info("✅ ZMQ monitoring stopped")


def example_transaction_callback(tx_hex: str):
    """Example callback for transaction notifications"""
    print(f"🎯 Transaction received: {tx_hex[:64]}...")
    # Here you would:
    # 1. Decode the transaction
    # 2. Check if it involves addresses you're monitoring
    # 3. Update your database
    # 4. Send notifications

def example_block_callback(block_hash: str):
    """Example callback for block notifications"""
    print(f"🎯 New block: {block_hash}")
    # Here you would:
    # 1. Get block details from your Bitcoin node
    # 2. Check for transactions involving your addresses
    # 3. Update confirmations for pending transactions

def main():
    """Run the ZMQ monitor continuously"""
    print("🔔 Bitcoin ZMQ Transaction Monitor")
    print("=" * 50)
    print("📡 Starting continuous monitoring...")
    print("💡 Press Ctrl+C to stop")
    print()
    
    # Create monitor
    monitor = BitcoinZMQMonitor()
    
    # Add example callbacks
    monitor.add_callback('rawtx', example_transaction_callback)
    monitor.add_callback('hashblock', example_block_callback)
    
    try:
        # Start monitoring
        monitor.start_monitoring()
        
        # Run continuously until interrupted
        logger.info("🔄 Monitoring continuously - press Ctrl+C to stop")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️  Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        monitor.stop_monitoring()
        logger.info("✅ Monitoring stopped")


if __name__ == "__main__":
    main() 