#!/usr/bin/env python3
"""
Simple ZMQ connection test for Bitcoin
"""

import zmq
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_zmq_connection():
    """Test ZMQ connection to Bitcoin node"""
    print("🔍 Testing ZMQ connection to Bitcoin node...")
    
    # ZMQ ports
    zmq_ports = {
        'rawtx': 28332,
        'rawblock': 28333,
        'hashblock': 28334,
        'hashtx': 28335,
        'sequence': 28336
    }
    
    context = zmq.Context()
    sockets = {}
    
    # Test each ZMQ socket
    for topic, port in zmq_ports.items():
        try:
            socket = context.socket(zmq.SUB)
            socket.connect(f"tcp://localhost:{port}")
            socket.setsockopt_string(zmq.SUBSCRIBE, "")
            socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout
            
            sockets[topic] = socket
            logger.info(f"✅ Connected to ZMQ {topic} on port {port}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to ZMQ {topic}: {e}")
    
    if not sockets:
        logger.error("❌ No ZMQ connections established")
        return False
    
    # Test receiving data
    print("\n📡 Testing data reception (waiting 10 seconds)...")
    start_time = time.time()
    messages_received = 0
    
    try:
        while time.time() - start_time < 10:
            for topic, socket in sockets.items():
                try:
                    data = socket.recv()
                    if data:
                        logger.info(f"📦 Received {topic} data: {data.hex()[:32]}...")
                        messages_received += 1
                except zmq.Again:
                    # Timeout - continue
                    continue
                except Exception as e:
                    logger.error(f"❌ Error receiving {topic}: {e}")
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted")
    
    # Clean up
    for topic, socket in sockets.items():
        try:
            socket.close()
            logger.info(f"✅ Closed {topic} socket")
        except Exception as e:
            logger.error(f"❌ Error closing {topic} socket: {e}")
    
    context.term()
    
    print(f"\n📊 Test Results:")
    print(f"   Messages received: {messages_received}")
    
    if messages_received > 0:
        logger.info("✅ ZMQ is working! Bitcoin node is sending notifications")
        return True
    else:
        logger.warning("⚠️  No messages received. ZMQ might not be enabled or Bitcoin node is not synced")
        return False

if __name__ == "__main__":
    test_zmq_connection() 