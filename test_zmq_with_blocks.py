#!/usr/bin/env python3
"""
Test ZMQ with manual block generation on testnet
"""

import time
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_testnet_blocks():
    """Generate some testnet blocks to trigger ZMQ notifications"""
    print("🔧 Generating testnet blocks to test ZMQ...")
    
    try:
        # First, get a new address for mining
        result = subprocess.run([
            'docker', 'exec', 'bitcoin', 'bitcoin-cli', 
            '-conf=/home/bitcoin/.bitcoin/bitcoin.conf',
            '-rpcuser=bitcoin', '-rpcpassword=bitcoinpassword',
            'getnewaddress'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"❌ Failed to get new address: {result.stderr}")
            return False
        
        mining_address = result.stdout.strip()
        logger.info(f"✅ Got mining address: {mining_address}")
        
        # Generate 1 block to this address
        result = subprocess.run([
            'docker', 'exec', 'bitcoin', 'bitcoin-cli', 
            '-conf=/home/bitcoin/.bitcoin/bitcoin.conf',
            '-rpcuser=bitcoin', '-rpcpassword=bitcoinpassword',
            'generatetoaddress', '1', mining_address
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            logger.info("✅ Generated testnet block")
            print(f"📦 Block hash: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ Failed to generate block: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error generating block: {e}")
        return False

def check_bitcoin_status():
    """Check current Bitcoin node status"""
    try:
        result = subprocess.run([
            'docker', 'exec', 'bitcoin', 'bitcoin-cli',
            '-conf=/home/bitcoin/.bitcoin/bitcoin.conf',
            '-rpcuser=bitcoin', '-rpcpassword=bitcoinpassword',
            'getblockchaininfo'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("📊 Current Bitcoin status:")
            print(result.stdout)
        else:
            logger.error(f"❌ Failed to get blockchain info: {result.stderr}")
            
    except Exception as e:
        logger.error(f"❌ Error checking status: {e}")

def main():
    """Main test function"""
    print("🧪 Testing ZMQ with block generation")
    print("=" * 50)
    
    # Check current status
    check_bitcoin_status()
    
    print("\n🔧 Generating testnet blocks...")
    
    # Generate a few blocks
    for i in range(3):
        print(f"\n📦 Generating block {i+1}/3...")
        if generate_testnet_blocks():
            print("✅ Block generated successfully")
            time.sleep(2)  # Wait between blocks
        else:
            print("❌ Failed to generate block")
            break
    
    print("\n💡 Now run your ZMQ monitor to see notifications:")
    print("   python bitcoin_zmq_monitor.py")

if __name__ == "__main__":
    main() 