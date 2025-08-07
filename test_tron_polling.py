#!/usr/bin/env python3
"""
Test script for TRON polling system with database integration
"""

import os
import time
import logging
from tron_polling import TronAddressPoller, PollingConfig

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_tron_polling():
    """Test the TRON polling system"""
    print("🔧 TRON Polling System Test")
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
        poll_interval=15,  # Poll every 15 seconds for testing
        batch_size=3,      # Process 3 addresses at a time
        enable_logging=True
    )
    
    # Create poller
    poller = TronAddressPoller(config)
    
    # Add test addresses
    test_addresses = [
        "TJRabPrwbZy45sbavfcjinPJC18kjpRTv8",  # Example TRON address
        "TJRabPrwbZy45sbavfcjinPJC18kjpRTv9",  # Another example
    ]
    
    print("📝 Adding test addresses...")
    for address in test_addresses:
        success = poller.add_address(address)
        if success:
            print(f"✅ Added: {address}")
        else:
            print(f"❌ Failed to add: {address}")
    
    try:
        # Start polling
        print("\n🚀 Starting polling system...")
        poller.start_polling()
        
        # Run for 1 minute
        print("⏳ Running for 1 minute...")
        time.sleep(60)
        
        # Show statistics
        stats = poller.get_statistics()
        print("\n📊 Polling Statistics:")
        print(f"   Total polls: {stats['total_polls']}")
        print(f"   Total transactions: {stats['total_transactions']}")
        print(f"   Errors: {stats['errors']}")
        print(f"   Monitored addresses: {stats['monitored_addresses']}")
        print(f"   Last poll: {stats['last_poll_time']}")
        print(f"   Network: {stats['network']}")
        
        # Show monitored addresses
        addresses = poller.get_monitored_addresses()
        print(f"\n📋 Monitored Addresses:")
        for addr in addresses:
            print(f"   {addr}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Stopping polling...")
    finally:
        poller.stop_polling()
        print("✅ Polling stopped")

def test_database_integration():
    """Test the database integration"""
    print("\n🔧 Database Integration Test")
    print("=" * 50)
    
    try:
        from tron_database_integration import create_database_integration
        
        # Create database integration
        db_integration = create_database_integration()
        
        # Test transaction saving
        test_tx_data = {
            'txID': 'test_polling_transaction_123456789',
            'amount': 500,
            'fee': 1,
            'block': 12345,
            'confirmed': True,
            'type': 'Transfer'
        }
        
        from datetime import datetime
        test_datetime = datetime.now()
        
        # Save test transaction
        success = db_integration.save_transaction(
            address="TJRabPrwbZy45sbavfcjinPJC18kjpRTv8",
            tx_data=test_tx_data,
            tx_datetime=test_datetime
        )
        
        if success:
            print("✅ Test transaction saved successfully")
            
            # Get statistics
            stats = db_integration.get_transaction_statistics()
            print(f"📊 Transaction statistics: {stats}")
        else:
            print("❌ Failed to save test transaction")
            
    except Exception as e:
        print(f"❌ Database integration test failed: {e}")

def main():
    """Main test function"""
    print("🧪 TRON Polling System Tests")
    print("=" * 60)
    
    # Test database integration first
    test_database_integration()
    
    # Test polling system
    test_tron_polling()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    main() 