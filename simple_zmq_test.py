#!/usr/bin/env python3
"""
Simple ZMQ Test - Just check if we can receive notifications
"""

import zmq
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_zmq_reception():
    """Test if we can receive any ZMQ messages"""
    print("🔍 Testing ZMQ message reception...")
    
    # ZMQ ports to test
    zmq_ports = {
        'rawtx': 28332,
        'hashblock': 28334,
        'hashtx': 28335
    }
    
    context = zmq.Context()
    sockets = {}
    
    # Connect to ZMQ sockets
    for topic, port in zmq_ports.items():
        try:
            socket = context.socket(zmq.SUB)
            socket.connect(f"tcp://localhost:{port}")
            socket.setsockopt_string(zmq.SUBSCRIBE, "")
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            
            sockets[topic] = socket
            logger.info(f"✅ Connected to ZMQ {topic} on port {port}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to ZMQ {topic}: {e}")
    
    if not sockets:
        logger.error("❌ No ZMQ connections established")
        return False
    
    # Test receiving data for 30 seconds
    print("\n📡 Listening for ZMQ messages (30 seconds)...")
    start_time = time.time()
    messages_received = 0
    
    try:
        while time.time() - start_time < 30:
            for topic, socket in sockets.items():
                try:
                    data = socket.recv()
                    if data:
                        logger.info(f"📦 Received {topic} message: {data.hex()[:32]}...")
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
        logger.info("✅ ZMQ is working! Received notifications")
        return True
    else:
        logger.warning("⚠️  No messages received. This is expected during IBD")
        logger.info("💡 ZMQ will work once Bitcoin node finishes syncing")
        return False

def main():
    """Main test function"""
    print("🧪 Simple ZMQ Test")
    print("=" * 30)
    
    test_zmq_reception()

if __name__ == "__main__":
    main() 