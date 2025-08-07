#!/usr/bin/env python3
"""
Bitcoin RPC Client Test Script
Tests connection to local Bitcoin node running in Docker
"""

import requests
import json
import time
from typing import Dict, Any, Optional, List

class BitcoinRPCClient:
    """Bitcoin RPC Client for testing local node"""
    
    def __init__(self, host: str = "localhost", port: int = 18332, 
                 username: str = "bitcoin", password: str = "bitcoinpassword"):
        self.url = f"http://{host}:{port}"
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
    
    def _make_request(self, method: str, params: list = None, request_id: str = "test", wallet: str = None) -> Dict[str, Any]:
        """Make JSON-RPC request to Bitcoin node"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": request_id
        }
        
        # Add wallet path to URL if specified
        url = self.url
        if wallet:
            url = f"{self.url}/wallet/{wallet}"
        
        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")
    
    def test_connection(self) -> bool:
        """Test basic connection to Bitcoin node"""
        try:
            response = self._make_request("getblockchaininfo")
            return "result" in response
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return self._make_request("getblockchaininfo")
    
    def get_block_count(self) -> int:
        """Get current block count"""
        response = self._make_request("getblockcount")
        return response.get("result", 0)
    
    def get_best_block_hash(self) -> str:
        """Get the hash of the best (tip) block"""
        response = self._make_request("getbestblockhash")
        return response.get("result", "")
    
    def get_block(self, block_hash: str, verbosity: int = 1) -> Dict[str, Any]:
        """Get block information by hash"""
        return self._make_request("getblock", [block_hash, verbosity])
    
    def get_block_hash(self, height: int) -> str:
        """Get block hash by height"""
        response = self._make_request("getblockhash", [height])
        return response.get("result", "")
    
    def get_raw_transaction(self, txid: str, verbose: bool = True) -> Dict[str, Any]:
        """Get raw transaction data"""
        return self._make_request("getrawtransaction", [txid, verbose])
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return self._make_request("getnetworkinfo")
    
    def get_mempool_info(self) -> Dict[str, Any]:
        """Get mempool information"""
        return self._make_request("getmempoolinfo")
    
    def get_difficulty(self) -> float:
        """Get current difficulty"""
        response = self._make_request("getdifficulty")
        return response.get("result", 0.0)
    
    def get_mining_info(self) -> Dict[str, Any]:
        """Get mining information"""
        return self._make_request("getmininginfo")
    
    def estimate_smart_fee(self, conf_target: int, estimate_mode: str = "CONSERVATIVE") -> Dict[str, Any]:
        """Estimate smart fee"""
        return self._make_request("estimatesmartfee", [conf_target, estimate_mode])
    
    def validate_address(self, address: str) -> Dict[str, Any]:
        """Validate a Bitcoin address"""
        return self._make_request("validateaddress", [address])
    
    # Wallet and UTXO methods
    def list_wallets(self) -> List[str]:
        """List all available wallets"""
        response = self._make_request("listwallets")
        return response.get("result", [])
    
    def create_wallet(self, wallet_name: str, disable_private_keys: bool = True, 
                     blank: bool = True, passphrase: str = "", 
                     avoid_reuse: bool = False, descriptors: bool = False, 
                     load_on_startup: bool = True) -> Dict[str, Any]:
        """Create a new wallet"""
        params = [wallet_name, disable_private_keys, blank, passphrase, 
                 avoid_reuse, descriptors, load_on_startup]
        return self._make_request("createwallet", params)
    
    def load_wallet(self, wallet_name: str) -> Dict[str, Any]:
        """Load a wallet"""
        return self._make_request("loadwallet", [wallet_name])
    
    def import_address(self, address: str, label: str = "", rescan: bool = False, wallet: str = None) -> Dict[str, Any]:
        """Import an address to a wallet (legacy wallets only)"""
        return self._make_request("importaddress", [address, label, rescan], wallet=wallet)
    
    def import_descriptors(self, descriptors: List[Dict[str, Any]], wallet: str = None) -> Dict[str, Any]:
        """Import descriptors to a wallet (descriptor wallets)"""
        return self._make_request("importdescriptors", [descriptors], wallet=wallet)
    
    def list_unspent(self, min_conf: int = 0, max_conf: int = 9999999, 
                     addresses: List[str] = None, wallet: str = None) -> List[Dict[str, Any]]:
        """List unspent transaction outputs"""
        params = [min_conf, max_conf]
        if addresses:
            params.append(addresses)
        response = self._make_request("listunspent", params, wallet=wallet)
        return response.get("result", [])
    
    def get_utxos_for_address(self, address: str, wallet_name: str = "watchonly") -> List[Dict[str, Any]]:
        """Get UTXOs for a specific address"""
        try:
            # First, try to import the address if it's not already imported
            try:
                self.import_address(address, wallet=wallet_name)
                print(f"   ✅ Address {address} imported to wallet {wallet_name}")
            except Exception as e:
                if "already imported" not in str(e).lower():
                    print(f"   ⚠️  Address import warning: {e}")
            
            # Now get the UTXOs
            utxos = self.list_unspent(0, 9999999, [address], wallet=wallet_name)
            return utxos
        except Exception as e:
            print(f"   ❌ Error getting UTXOs: {e}")
            return []
    
    def setup_watch_only_wallet(self, wallet_name: str = "watchonly") -> bool:
        """Setup a watch-only wallet for monitoring addresses"""
        try:
            # Check if wallet already exists
            wallets = self.list_wallets()
            if wallet_name in wallets:
                print(f"   ✅ Wallet '{wallet_name}' already exists")
                return True
            
            # Create watch-only wallet
            print(f"   📝 Creating watch-only wallet '{wallet_name}'...")
            result = self.create_wallet(
                wallet_name=wallet_name,
                disable_private_keys=True,  # Watch-only
                blank=True,  # Empty wallet
                descriptors=False  # Legacy wallet for importaddress
            )
            
            if "result" in result:
                print(f"   ✅ Wallet '{wallet_name}' created successfully")
                return True
            else:
                print(f"   ❌ Failed to create wallet: {result}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error setting up wallet: {e}")
            return False

def test_bitcoin_node():
    """Test the Bitcoin node connection and basic functionality"""
    print("=== Bitcoin RPC Client Test ===\n")
    
    # Initialize client
    client = BitcoinRPCClient()
    
    # Test 1: Connection
    print("1. Testing connection...")
    if client.test_connection():
        print("   ✅ Connection successful!")
    else:
        print("❌ Connection failed!")
        print("Make sure the Bitcoin node is running:")
        print("docker-compose up -d bitcoin")
        return
    print()
    
    # Test 2: Blockchain info
    print("2. Getting blockchain information...")
    try:
        blockchain_info = client.get_blockchain_info()
        result = blockchain_info.get("result", {})
        print(f"   ✅ Chain: {result.get('chain', 'unknown')}")
        print(f"   ✅ Blocks: {result.get('blocks', 'unknown')}")
        print(f"   ✅ Headers: {result.get('headers', 'unknown')}")
        print(f"   ✅ Pruned: {result.get('pruned', 'unknown')}")
        if result.get('pruned'):
            print(f"   ✅ Prune height: {result.get('pruneheight', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 3: Block count
    print("3. Getting block count...")
    try:
        block_count = client.get_block_count()
        print(f"   ✅ Current block count: {block_count}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 4: Best block hash
    print("4. Getting best block hash...")
    try:
        best_hash = client.get_best_block_hash()
        print(f"   ✅ Best block hash: {best_hash}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 5: Network info
    print("5. Getting network information...")
    try:
        network_info = client.get_network_info()
        result = network_info.get("result", {})
        print(f"   ✅ Version: {result.get('version', 'unknown')}")
        print(f"   ✅ Subversion: {result.get('subversion', 'unknown')}")
        print(f"   ✅ Connections: {result.get('connections', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 6: Mempool info
    print("6. Getting mempool information...")
    try:
        mempool_info = client.get_mempool_info()
        result = mempool_info.get("result", {})
        print(f"   ✅ Mempool size: {result.get('size', 'unknown')}")
        print(f"   ✅ Mempool bytes: {result.get('bytes', 'unknown')}")
        print(f"   ✅ Mempool usage: {result.get('usage', 'unknown')} bytes")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 7: Difficulty
    print("7. Getting current difficulty...")
    try:
        difficulty = client.get_difficulty()
        print(f"   ✅ Current difficulty: {difficulty}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 8: Mining info
    print("8. Getting mining information...")
    try:
        mining_info = client.get_mining_info()
        result = mining_info.get("result", {})
        print(f"   ✅ Blocks: {result.get('blocks', 'unknown')}")
        print(f"   ✅ Current block weight: {result.get('currentblockweight', 'unknown')}")
        print(f"   ✅ Current block tx: {result.get('currentblocktx', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 9: Fee estimation
    print("9. Estimating transaction fee...")
    try:
        fee_estimate = client.estimate_smart_fee(6, "CONSERVATIVE")
        result = fee_estimate.get("result", {})
        if result:
            fee_rate = result.get('feerate', 'unknown')
            print(f"   ✅ Estimated fee rate: {fee_rate} BTC/kB")
        else:
            print("   ⚠️  No fee estimate available")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 10: Address validation
    print("10. Validating Bitcoin address...")
    test_address = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"  # Testnet address
    try:
        validation = client.validate_address(test_address)
        result = validation.get("result", {})
        print(f"   ✅ Address: {test_address}")
        print(f"   ✅ Is valid: {result.get('isvalid', 'unknown')}")
        if result.get('isvalid'):
            print(f"   ✅ Address type: {result.get('type', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    # Test 11: Get a recent block
    print("11. Getting recent block information...")
    try:
        best_hash = client.get_best_block_hash()
        if best_hash:
            block_info = client.get_block(best_hash, verbosity=1)
            result = block_info.get("result", {})
            print(f"   ✅ Block height: {result.get('height', 'unknown')}")
            print(f"   ✅ Block time: {result.get('time', 'unknown')}")
            print(f"   ✅ Block size: {result.get('size', 'unknown')} bytes")
            print(f"   ✅ Transaction count: {result.get('nTx', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print()
    
    print("=== Test Complete ===")

def test_litecoin_node():
    """Test the Litecoin node connection"""
    print("\n=== Litecoin RPC Client Test ===\n")
    
    # Initialize Litecoin client
    ltc_client = BitcoinRPCClient(port=19332, username="litecoin", password="litecoinpassword")
    
    # Test connection
    print("1. Testing Litecoin connection...")
    if ltc_client.test_connection():
        print("   ✅ Litecoin connection successful!")
        
        # Get basic info
        try:
            blockchain_info = ltc_client.get_blockchain_info()
            result = blockchain_info.get("result", {})
            print(f"   ✅ Chain: {result.get('chain', 'unknown')}")
            print(f"   ✅ Blocks: {result.get('blocks', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    else:
        print("   ❌ Litecoin connection failed!")
        print("   Make sure the Litecoin node is running:")
        print("   docker-compose up -d litecoin")
    
    print("\n=== Litecoin Test Complete ===")

def test_utxo_functionality():
    """Test UTXO checking functionality"""
    print("\n=== UTXO Functionality Test ===\n")
    
    # Initialize client
    client = BitcoinRPCClient()
    
    # Test 1: Setup watch-only wallet
    print("1. Setting up watch-only wallet...")
    wallet_name = "watchonly"
    if client.setup_watch_only_wallet(wallet_name):
        print("   ✅ Watch-only wallet ready")
    else:
        print("   ❌ Failed to setup wallet")
        return
    print()
    
    # Test 2: List wallets
    print("2. Listing available wallets...")
    try:
        wallets = client.list_wallets()
        print(f"   ✅ Available wallets: {wallets}")
    except Exception as e:
        print(f"   ❌ Error listing wallets: {e}")
    print()
    
    # Test 3: Check UTXOs for the test address
    test_address = "mt4Vd5HFw2C8BZDbEGDxdhAGYYdsJCazoh"
    print(f"3. Checking UTXOs for address: {test_address}")
    try:
        utxos = client.get_utxos_for_address(test_address, wallet_name)
        if utxos:
            print(f"   ✅ Found {len(utxos)} UTXO(s):")
            for i, utxo in enumerate(utxos, 1):
                print(f"      UTXO {i}:")
                print(f"        TXID: {utxo.get('txid', 'unknown')}")
                print(f"        Vout: {utxo.get('vout', 'unknown')}")
                print(f"        Amount: {utxo.get('amount', 'unknown')} BTC")
                print(f"        Confirmations: {utxo.get('confirmations', 'unknown')}")
                print(f"        Address: {utxo.get('address', 'unknown')}")
        else:
            print("   ℹ️  No UTXOs found for this address")
    except Exception as e:
        print(f"   ❌ Error checking UTXOs: {e}")
    print()
    
    # Test 4: Check UTXOs for another test address
    test_address2 = "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4"
    print(f"4. Checking UTXOs for address: {test_address2}")
    try:
        utxos2 = client.get_utxos_for_address(test_address2, wallet_name)
        if utxos2:
            print(f"   ✅ Found {len(utxos2)} UTXO(s):")
            for i, utxo in enumerate(utxos2, 1):
                print(f"      UTXO {i}:")
                print(f"        TXID: {utxo.get('txid', 'unknown')}")
                print(f"        Vout: {utxo.get('vout', 'unknown')}")
                print(f"        Amount: {utxo.get('amount', 'unknown')} BTC")
                print(f"        Confirmations: {utxo.get('confirmations', 'unknown')}")
                print(f"        Address: {utxo.get('address', 'unknown')}")
        else:
            print("   ℹ️  No UTXOs found for this address")
    except Exception as e:
        print(f"   ❌ Error checking UTXOs: {e}")
    print()
    
    # Test 5: Validate addresses
    print("5. Validating test addresses...")
    addresses_to_validate = [test_address, test_address2]
    for addr in addresses_to_validate:
        try:
            validation = client.validate_address(addr)
            result = validation.get("result", {})
            print(f"   Address: {addr}")
            print(f"   Is valid: {result.get('isvalid', 'unknown')}")
            if result.get('isvalid'):
                print(f"   Type: {result.get('type', 'unknown')}")
                print(f"   Is testnet: {result.get('is_testnet', 'unknown')}")
        except Exception as e:
            print(f"   ❌ Error validating {addr}: {e}")
        print()
    
    print("=== UTXO Test Complete ===")

if __name__ == "__main__":
    test_bitcoin_node()
    test_litecoin_node()
    test_utxo_functionality() 