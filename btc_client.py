import requests
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Testnet: https://go.getblock.io/7b0b202963324e9e8533c3b95a94c9cd
# Mainnet: https://go.getblock.io/f82fffbf14c94f96aef940b9f7de53a9
# Tron: https://go.getblock.io/33fb0f277e594b64a95bf21974c82a1b

@dataclass
class BitcoinConfig:
    """Configuration for Bitcoin client"""
    endpoint: str
    headers: Dict[str, str]
    
    @classmethod
    def testnet(cls, api_key: str) -> 'BitcoinConfig':
        return cls(
            endpoint=f'https://go.getblock.io/{api_key}',
            headers={
                'Content-Type': 'application/json'
            }
        )
    
    @classmethod
    def mainnet(cls, api_key: str) -> 'BitcoinConfig':
        return cls(
            endpoint=f'https://go.getblock.io/{api_key}',
            headers={
                'Content-Type': 'application/json'
            }
        )

class BitcoinClient:
    """Bitcoin client using GetBlock API (Read-only node)"""
    
    def __init__(self, config: BitcoinConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.headers)
    
    def _make_request(self, method: str, params: List = None, request_id: str = "getblock.io") -> Dict[str, Any]:
        """Make JSON-RPC request to Bitcoin node"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": request_id
        }
        
        try:
            response = self.session.post(self.config.endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")
    
    # ===== BLOCK METHODS (WORKING) =====
    
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
        """
        Get block information by hash
        
        Args:
            block_hash: Hash of the block
            verbosity: 0 = hex string, 1 = json object, 2 = json object with transaction data
        """
        return self._make_request("getblock", [block_hash, verbosity])
    
    def get_block_by_height(self, height: int, verbosity: int = 1) -> Dict[str, Any]:
        """
        Get block information by height
        
        Args:
            height: Block height
            verbosity: 0 = hex string, 1 = json object, 2 = json object with transaction data
        """
        return self._make_request("getblock", [height, verbosity])
    
    def get_block_hash(self, height: int) -> str:
        """Get block hash by height"""
        response = self._make_request("getblockhash", [height])
        return response.get("result", "")
    
    def get_block_header(self, block_hash: str, verbose: bool = True) -> Dict[str, Any]:
        """Get block header information"""
        return self._make_request("getblockheader", [block_hash, verbose])
    
    # ===== TRANSACTION METHODS (PARTIALLY WORKING) =====
    
    def get_raw_transaction(self, txid: str, verbose: bool = True, block_hash: str = None) -> Dict[str, Any]:
        """
        Get raw transaction data
        
        Args:
            txid: Transaction ID (string)
            verbose: If true, return a JSON object with transaction details
            block_hash: Optional block hash for faster lookup
        """
        params = [txid, verbose]
        if block_hash:
            params.append(block_hash)
        return self._make_request("getrawtransaction", params)
    
    def create_raw_transaction(self, inputs: List[Dict], outputs: List[Dict], locktime: int = 0, replaceable: bool = True) -> str:
        """
        Create a raw transaction (read-only node - for reference only)
        
        Args:
            inputs: List of input objects with txid and vout
            outputs: List of output objects with address and amount
            locktime: Lock time
            replaceable: Allow transaction to be replaced
        """
        response = self._make_request("createrawtransaction", [inputs, outputs, locktime, replaceable])
        return response.get("result", "")
    
    def sign_raw_transaction(self, hexstring: str, prevtxs: List = None, privkeys: List[str] = None, sighashtype: str = "ALL") -> Dict[str, Any]:
        """
        Sign a raw transaction (read-only node - for reference only)
        
        Args:
            hexstring: Raw transaction hex string
            prevtxs: Previous transaction outputs
            privkeys: Private keys for signing
            sighashtype: Signature hash type
        """
        params = [hexstring]
        if prevtxs:
            params.append(prevtxs)
        if privkeys:
            params.append(privkeys)
        params.append(sighashtype)
        
        return self._make_request("signrawtransactionwithkey", params)
    
    def send_raw_transaction(self, hexstring: str, allowhighfees: bool = False) -> str:
        """
        Submit a raw transaction to the network (read-only node - for reference only)
        
        Args:
            hexstring: Raw transaction hex string
            allowhighfees: Allow high fees
        """
        response = self._make_request("sendrawtransaction", [hexstring, allowhighfees])
        return response.get("result", "")
    
    # ===== NETWORK METHODS (WORKING) =====
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return self._make_request("getnetworkinfo")
    
    def get_connection_count(self) -> int:
        """Get number of connections"""
        response = self._make_request("getconnectioncount")
        return response.get("result", 0)
    
    def get_difficulty(self) -> float:
        """Get current difficulty"""
        response = self._make_request("getdifficulty")
        return response.get("result", 0.0)
    
    def get_mining_info(self) -> Dict[str, Any]:
        """Get mining information"""
        return self._make_request("getmininginfo")
    
    # ===== MEMPOOL METHODS (WORKING) =====
    
    def get_mempool_info(self) -> Dict[str, Any]:
        """Get mempool information"""
        return self._make_request("getmempoolinfo")
    
    def get_mempool_ancestors(self, txid: str, verbose: bool = False) -> List[str]:
        """Get mempool ancestors of a transaction"""
        response = self._make_request("getmempoolancestors", [txid, verbose])
        return response.get("result", [])
    
    def get_mempool_descendants(self, txid: str, verbose: bool = False) -> List[str]:
        """Get mempool descendants of a transaction"""
        response = self._make_request("getmempooldescendants", [txid, verbose])
        return response.get("result", [])
    
    # ===== FEE METHODS (WORKING) =====
    
    def estimate_smart_fee(self, conf_target: int, estimate_mode: str = "CONSERVATIVE") -> Dict[str, Any]:
        """
        Estimate smart fee
        
        Args:
            conf_target: Confirmation target
            estimate_mode: "ECONOMICAL" or "CONSERVATIVE"
        """
        return self._make_request("estimatesmartfee", [conf_target, estimate_mode])
    
    # ===== ADDRESS METHODS (LIMITED) =====
    
    def validate_address(self, address: str) -> Dict[str, Any]:
        """Validate a Bitcoin address"""
        return self._make_request("validateaddress", [address])
    
    # ===== UTILITY METHODS =====
    
    def get_transaction_from_block(self, block_hash: str, tx_index: int = 0) -> Dict[str, Any]:
        """
        Get a transaction from a block by index
        
        Args:
            block_hash: Hash of the block
            tx_index: Index of the transaction in the block (default: 0)
        """
        block_info = self.get_block(block_hash, verbosity=2)
        if "result" in block_info and "tx" in block_info["result"]:
            transactions = block_info["result"]["tx"]
            if tx_index < len(transactions):
                tx_data = transactions[tx_index]
                if isinstance(tx_data, dict) and "txid" in tx_data:
                    return self.get_raw_transaction(tx_data["txid"], verbose=True)
        return {"error": "Transaction not found"}
    
    def get_latest_transactions(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get the latest transactions from the most recent block
        
        Args:
            count: Number of transactions to return
        """
        try:
            best_hash = self.get_best_block_hash()
            if best_hash:
                block_info = self.get_block(best_hash, verbosity=2)
                if "result" in block_info and "tx" in block_info["result"]:
                    transactions = block_info["result"]["tx"]
                    result = []
                    for i, tx_data in enumerate(transactions[:count]):
                        if isinstance(tx_data, dict) and "txid" in tx_data:
                            tx_info = self.get_raw_transaction(tx_data["txid"], verbose=True)
                            if "result" in tx_info:
                                result.append(tx_info["result"])
                    return result
        except Exception as e:
            print(f"Error getting latest transactions: {e}")
        return []

# Example usage
if __name__ == "__main__":
    # Initialize client (you'll need to provide your API key)
    api_key = "your_api_key_here"
    config = BitcoinConfig.testnet(api_key)
    client = BitcoinClient(config)
    
    try:
        # Get blockchain info
        blockchain_info = client.get_blockchain_info()
        print("Blockchain Info:", json.dumps(blockchain_info, indent=2))
        
        # Get current block count
        block_count = client.get_block_count()
        print(f"Current Block Count: {block_count}")
        
        # Get best block hash
        best_hash = client.get_best_block_hash()
        print(f"Best Block Hash: {best_hash}")
        
        # Get block information
        if best_hash:
            block_info = client.get_block(best_hash, verbosity=1)
            print("Latest Block Info:", json.dumps(block_info, indent=2))
        
        # Get network info
        network_info = client.get_network_info()
        print("Network Info:", json.dumps(network_info, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
