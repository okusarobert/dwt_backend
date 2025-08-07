#!/usr/bin/env python3
"""
Bitcoin Client Example
Demonstrates how to use the BitcoinClient for common operations
"""

import json
from btc_client import BitcoinClient, BitcoinConfig

def main():
    # Initialize client with your API key
    api_key = "7b0b202963324e9e8533c3b95a94c9cd"  # Replace with your actual API key
    config = BitcoinConfig.testnet(api_key)  # Use mainnet for production
    client = BitcoinClient(config)
    
    print("=== Bitcoin Client Example ===\n")
    
    try:
        # 1. Get blockchain information
        print("1. Getting blockchain information...")
        blockchain_info = client.get_blockchain_info()
        print(f"   Chain: {blockchain_info['result']['chain']}")
        print(f"   Blocks: {blockchain_info['result']['blocks']}")
        print(f"   Headers: {blockchain_info['result']['headers']}")
        print()
        
        # 2. Get current block count
        print("2. Getting current block count...")
        block_count = client.get_block_count()
        print(f"   Current block count: {block_count}")
        print()
        
        # 3. Get best block hash
        print("3. Getting best block hash...")
        best_hash = client.get_best_block_hash()
        print(f"   Best block hash: {best_hash}")
        print()
        
        # 4. Get block information
        print("4. Getting latest block information...")
        if best_hash:
            block_info = client.get_block(best_hash, verbosity=1)
            result = block_info['result']
            print(f"   Block height: {result['height']}")
            print(f"   Block time: {result['time']}")
            print(f"   Block size: {result['size']} bytes")
            print(f"   Transaction count: {result['nTx']}")
        print()
        
        # 5. Get network information
        print("5. Getting network information...")
        network_info = client.get_network_info()
        result = network_info['result']
        print(f"   Version: {result['version']}")
        print(f"   Subversion: {result['subversion']}")
        print(f"   Connections: {result['connections']}")
        print()
        
        # 6. Get mempool information
        print("6. Getting mempool information...")
        mempool_info = client.get_mempool_info()
        result = mempool_info['result']
        print(f"   Mempool size: {result['size']}")
        print(f"   Mempool bytes: {result['bytes']}")
        print(f"   Mempool usage: {result['usage']} bytes")
        print()
        
        # 7. Estimate transaction fee
        print("7. Estimating transaction fee...")
        fee_estimate = client.estimate_smart_fee(6, "CONSERVATIVE")
        if 'result' in fee_estimate and fee_estimate['result']:
            fee_rate = fee_estimate['result'].get('feerate', 'unknown')
            print(f"   Estimated fee rate: {fee_rate} BTC/kB")
        else:
            print("   Could not estimate fee")
        print()
        
        # 8. Validate a Bitcoin address
        print("8. Validating Bitcoin address...")
        test_address = "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"  # Testnet address
        validation = client.validate_address(test_address)
        result = validation['result']
        print(f"   Address: {test_address}")
        print(f"   Is valid: {result['isvalid']}")
        if result['isvalid']:
            print(f"   Address type: {result.get('type', 'unknown')}")
        print()
        
        # 9. Get difficulty
        print("9. Getting current difficulty...")
        difficulty = client.get_difficulty()
        print(f"   Current difficulty: {difficulty}")
        print()
        
        # 10. Get mining information
        print("10. Getting mining information...")
        mining_info = client.get_mining_info()
        result = mining_info['result']
        print(f"   Blocks: {result['blocks']}")
        print(f"   Current block weight: {result['currentblockweight']}")
        print(f"   Current block tx: {result['currentblocktx']}")
        print()
        
        # 11. Get latest transactions
        print("11. Getting latest transactions...")
        latest_txs = client.get_latest_transactions(3)
        print(f"   Found {len(latest_txs)} transactions in latest block")
        for i, tx in enumerate(latest_txs):
            print(f"   Transaction {i+1}: {tx.get('txid', 'unknown')}")
            print(f"     Size: {tx.get('size', 'unknown')} bytes")
            print(f"     Value: {tx.get('vout', [{}])[0].get('value', 'unknown')} BTC")
        print()
        
        # 12. Get a specific transaction from the latest block
        print("12. Getting first transaction from latest block...")
        if best_hash:
            tx_info = client.get_transaction_from_block(best_hash, 0)
            if "result" in tx_info:
                tx = tx_info["result"]
                print(f"   Transaction ID: {tx.get('txid', 'unknown')}")
                print(f"   Size: {tx.get('size', 'unknown')} bytes")
                print(f"   Inputs: {len(tx.get('vin', []))}")
                print(f"   Outputs: {len(tx.get('vout', []))}")
            else:
                print("   Could not get transaction")
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("1. A valid GetBlock API key")
        print("2. The 'requests' library installed (pip install requests)")
        print("3. Proper network connectivity")

def working_methods_example():
    """Example of working methods"""
    print("\n=== Working Methods Example ===")
    print("These methods are supported by GetBlock's read-only Bitcoin node:")
    print()
    print("Block Methods:")
    print("- client.get_blockchain_info()")
    print("- client.get_block_count()")
    print("- client.get_best_block_hash()")
    print("- client.get_block(block_hash)")
    print("- client.get_block_by_height(height)")
    print("- client.get_block_hash(height)")
    print("- client.get_block_header(block_hash)")
    print()
    print("Transaction Methods:")
    print("- client.get_raw_transaction(txid)")
    print("- client.get_transaction_from_block(block_hash, index)")
    print("- client.get_latest_transactions(count)")
    print()
    print("Network Methods:")
    print("- client.get_network_info()")
    print("- client.get_connection_count()")
    print("- client.get_difficulty()")
    print("- client.get_mining_info()")
    print()
    print("Mempool Methods:")
    print("- client.get_mempool_info()")
    print("- client.get_mempool_ancestors(txid)")
    print("- client.get_mempool_descendants(txid)")
    print()
    print("Fee Methods:")
    print("- client.estimate_smart_fee(conf_target, mode)")
    print()
    print("Address Methods:")
    print("- client.validate_address(address)")

def unsupported_methods_note():
    """Note about unsupported methods"""
    print("\n=== Unsupported Methods ===")
    print("GetBlock's Bitcoin node is read-only, so these wallet methods are NOT supported:")
    print()
    print("Wallet Methods (NOT SUPPORTED):")
    print("- client.get_balance()")
    print("- client.get_new_address()")
    print("- client.get_address_info()")
    print("- client.send_to_address()")
    print("- client.get_transaction()")
    print("- client.get_received_by_address()")
    print()
    print("For wallet operations, you would need:")
    print("1. A full Bitcoin node with wallet enabled")
    print("2. Or a different service that supports wallet operations")

if __name__ == "__main__":
    main()
    working_methods_example()
    unsupported_methods_note() 