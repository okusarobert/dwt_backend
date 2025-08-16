#!/usr/bin/env python3

from app import AlchemyWebSocketClient

def test_metrics():
    print("🔍 Testing ETH Polling Performance Metrics...")
    
    # Initialize client
    client = AlchemyWebSocketClient('test-key', 'sepolia')
    
    try:
        # Get performance metrics
        metrics = client.get_eth_polling_performance_metrics()
        print(f"Available keys: {list(metrics.keys())}")
        print(f"Metrics data: {metrics}")
        
        # Test individual metrics
        if 'efficiency_score' in metrics:
            print(f"Efficiency Score: {metrics['efficiency_score']}/100")
        
        if 'total_blocks_scanned' in metrics:
            print(f"Total Blocks Scanned: {metrics['total_blocks_scanned']}")
            
        if 'total_eth_transfers_found' in metrics:
            print(f"Total ETH Transfers Found: {metrics['total_eth_transfers_found']}")
            
    except Exception as e:
        print(f"Error getting metrics: {e}")
    
    print("✅ Metrics test completed")

if __name__ == "__main__":
    test_metrics()
