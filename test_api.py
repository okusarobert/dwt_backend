#!/usr/bin/env python3
"""
Test script to check which Bitcoin RPC methods are supported by GetBlock API
"""

import json
from btc_client import BitcoinClient, BitcoinConfig

def test_basic_methods():
    """Test basic methods that should work"""
    api_key = "7b0b202963324e9e8533c3b95a94c9cd"
    config = BitcoinConfig.testnet(api_key)
    client = BitcoinClient(config)
    
    print("Testing basic Bitcoin RPC methods...")
    print("=" * 50)
    
    # Test methods that should work
    basic_methods = [
        ("getblockchaininfo", []),
        ("getblockcount", []),
        ("getbestblockhash", []),
        ("getnetworkinfo", []),
        ("getdifficulty", []),
        ("getmininginfo", []),
        ("getmempoolinfo", []),
        ("estimatesmartfee", [6, "CONSERVATIVE"]),
    ]
    
    for method_name, params in basic_methods:
        try:
            print(f"Testing {method_name}...")
            response = client._make_request(method_name, params)
            if "result" in response:
                print(f"✅ {method_name} - SUCCESS")
                if method_name == "getblockchaininfo":
                    print(f"   Chain: {response['result'].get('chain', 'unknown')}")
                    print(f"   Blocks: {response['result'].get('blocks', 'unknown')}")
                elif method_name == "getblockcount":
                    print(f"   Block count: {response['result']}")
                elif method_name == "estimatesmartfee":
                    if response['result']:
                        print(f"   Fee rate: {response['result'].get('feerate', 'unknown')}")
                    else:
                        print("   No fee estimate available")
            else:
                print(f"❌ {method_name} - No result in response")
                print(f"   Response: {response}")
        except Exception as e:
            print(f"❌ {method_name} - ERROR: {e}")
        print()

def test_wallet_methods():
    """Test wallet-related methods"""
    api_key = "7b0b202963324e9e8533c3b95a94c9cd"
    config = BitcoinConfig.testnet(api_key)
    client = BitcoinClient(config)
    
    print("Testing wallet-related methods...")
    print("=" * 50)
    
    # Test wallet methods
    wallet_methods = [
        ("getbalance", ["*", 0, True]),
        ("getnewaddress", ["", "legacy"]),
        ("getaddressinfo", ["mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"]),
        ("validateaddress", ["mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"]),
        ("getreceivedbyaddress", ["mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh", 1]),
    ]
    
    for method_name, params in wallet_methods:
        try:
            print(f"Testing {method_name}...")
            response = client._make_request(method_name, params)
            if "result" in response:
                print(f"✅ {method_name} - SUCCESS")
                if method_name == "validateaddress":
                    is_valid = response['result'].get('isvalid', False)
                    print(f"   Is valid: {is_valid}")
                elif method_name == "getbalance":
                    print(f"   Balance: {response['result']}")
                elif method_name == "getnewaddress":
                    print(f"   Address: {response['result']}")
            else:
                print(f"❌ {method_name} - No result in response")
                print(f"   Response: {response}")
        except Exception as e:
            print(f"❌ {method_name} - ERROR: {e}")
        print()

def test_transaction_methods():
    """Test transaction-related methods"""
    api_key = "7b0b202963324e9e8533c3b95a94c9cd"
    config = BitcoinConfig.testnet(api_key)
    client = BitcoinClient(config)
    
    print("Testing transaction-related methods...")
    print("=" * 50)
    
    # Get a recent block to find a transaction
    try:
        best_hash = client.get_best_block_hash()
        if best_hash:
            block_info = client.get_block(best_hash, verbosity=2)
            if "result" in block_info and "tx" in block_info["result"]:
                txid = block_info["result"]["tx"][0] if block_info["result"]["tx"] else None
                
                if txid:
                    print(f"Testing with transaction: {txid}")
                    
                    # Test transaction methods
                    tx_methods = [
                        ("getrawtransaction", [txid, True]),
                        ("gettransaction", [txid, True]),
                    ]
                    
                    for method_name, params in tx_methods:
                        try:
                            print(f"Testing {method_name}...")
                            response = client._make_request(method_name, params)
                            if "result" in response:
                                print(f"✅ {method_name} - SUCCESS")
                                if method_name == "getrawtransaction":
                                    print(f"   Transaction ID: {response['result'].get('txid', 'unknown')}")
                            else:
                                print(f"❌ {method_name} - No result in response")
                                print(f"   Response: {response}")
                        except Exception as e:
                            print(f"❌ {method_name} - ERROR: {e}")
                        print()
                else:
                    print("No transaction found in latest block")
            else:
                print("Could not get block information")
        else:
            print("Could not get best block hash")
    except Exception as e:
        print(f"Error getting transaction for testing: {e}")

if __name__ == "__main__":
    test_basic_methods()
    test_wallet_methods()
    test_transaction_methods() 