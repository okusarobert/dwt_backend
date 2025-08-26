"""
Bitcoin RPC Client for DWT Backend
Connects to remote Bitcoin testnet node via RPC
"""
import json
import requests
import os
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BTCTransaction:
    """Bitcoin transaction data structure"""
    txid: str
    amount: Decimal
    confirmations: int
    address: str
    category: str  # 'send' or 'receive'
    fee: Optional[Decimal] = None
    blockhash: Optional[str] = None
    blocktime: Optional[int] = None

class BTCClient:
    """Bitcoin RPC Client for testnet operations"""
    
    def __init__(self, host: str, port: int, username: str, password: str, testnet: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.testnet = testnet
        self.base_url = f"http://{host}:{port}/"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({'content-type': 'text/plain'})
        
    def _rpc_call(self, method: str, params: List[Any] = None) -> Dict[str, Any]:
        """Make RPC call to Bitcoin node"""
        if params is None:
            params = []
            
        payload = {
            "jsonrpc": "1.0",
            "id": "dwt_backend",
            "method": method,
            "params": params
        }
        
        try:
            response = self.session.post(self.base_url, data=json.dumps(payload))
            response.raise_for_status()
            
            result = response.json()
            if result.get('error'):
                raise Exception(f"Bitcoin RPC error: {result['error']}")
                
            return result.get('result', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Bitcoin RPC connection error: {e}")
            raise Exception(f"Failed to connect to Bitcoin node: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from Bitcoin node: {e}")
            raise Exception(f"Invalid response from Bitcoin node: {e}")
    
    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return self._rpc_call("getblockchaininfo")
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        return self._rpc_call("getnetworkinfo")
    
    def get_balance(self, wallet_name: str = "", min_confirmations: int = 1) -> Decimal:
        """Get wallet balance"""
        try:
            balance = self._rpc_call("getbalance", ["*", min_confirmations])
            return Decimal(str(balance))
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return Decimal('0')
    
    def get_new_address(self, label: str = "", address_type: str = "bech32") -> str:
        """Generate new address"""
        return self._rpc_call("getnewaddress", [label, address_type])
    
    def validate_address(self, address: str) -> Dict[str, Any]:
        """Validate Bitcoin address"""
        return self._rpc_call("validateaddress", [address])
    
    def get_transaction(self, txid: str) -> Dict[str, Any]:
        """Get transaction details"""
        return self._rpc_call("gettransaction", [txid])
    
    def list_transactions(self, account: str = "*", count: int = 10, skip: int = 0) -> List[Dict[str, Any]]:
        """List recent transactions"""
        return self._rpc_call("listtransactions", [account, count, skip])
    
    def send_to_address(self, address: str, amount: Decimal, comment: str = "", 
                       comment_to: str = "", subtract_fee: bool = False) -> str:
        """Send Bitcoin to address"""
        params = [address, float(amount)]
        if comment:
            params.append(comment)
        if comment_to:
            params.append(comment_to)
        if subtract_fee:
            params.append(subtract_fee)
            
        return self._rpc_call("sendtoaddress", params)
    
    def send_many(self, amounts: Dict[str, Decimal], min_confirmations: int = 1, 
                  comment: str = "", subtract_fee_from: List[str] = None) -> str:
        """Send to multiple addresses"""
        amounts_dict = {addr: float(amount) for addr, amount in amounts.items()}
        params = [amounts_dict, min_confirmations]
        
        if comment:
            params.append(comment)
        if subtract_fee_from:
            params.append(subtract_fee_from)
            
        return self._rpc_call("sendmany", params)
    
    def estimate_smart_fee(self, conf_target: int = 6) -> Dict[str, Any]:
        """Estimate transaction fee"""
        return self._rpc_call("estimatesmartfee", [conf_target])
    
    def get_raw_transaction(self, txid: str, verbose: bool = True) -> Dict[str, Any]:
        """Get raw transaction data"""
        return self._rpc_call("getrawtransaction", [txid, verbose])
    
    def create_wallet(self, wallet_name: str, disable_private_keys: bool = False,
                     blank: bool = False, passphrase: str = "", 
                     avoid_reuse: bool = False) -> Dict[str, Any]:
        """Create new wallet"""
        return self._rpc_call("createwallet", [
            wallet_name, disable_private_keys, blank, passphrase, avoid_reuse
        ])
    
    def load_wallet(self, wallet_name: str) -> Dict[str, Any]:
        """Load existing wallet"""
        return self._rpc_call("loadwallet", [wallet_name])
    
    def list_wallets(self) -> List[str]:
        """List available wallets"""
        return self._rpc_call("listwallets")
    
    def get_wallet_info(self) -> Dict[str, Any]:
        """Get current wallet information"""
        return self._rpc_call("getwalletinfo")
    
    def import_address(self, address: str, label: str = "", rescan: bool = True, 
                      p2sh: bool = False) -> None:
        """Import address for watching"""
        self._rpc_call("importaddress", [address, label, rescan, p2sh])
    
    def get_received_by_address(self, address: str, min_confirmations: int = 1) -> Decimal:
        """Get amount received by specific address"""
        try:
            amount = self._rpc_call("getreceivedbyaddress", [address, min_confirmations])
            return Decimal(str(amount))
        except Exception as e:
            logger.error(f"Failed to get received amount for {address}: {e}")
            return Decimal('0')
    
    def list_received_by_address(self, min_confirmations: int = 1, 
                                include_empty: bool = False, 
                                include_watchonly: bool = True) -> List[Dict[str, Any]]:
        """List amounts received by address"""
        return self._rpc_call("listreceivedbyaddress", [
            min_confirmations, include_empty, include_watchonly
        ])
    
    def get_block_count(self) -> int:
        """Get current block height"""
        return self._rpc_call("getblockcount")
    
    def get_best_block_hash(self) -> str:
        """Get best block hash"""
        return self._rpc_call("getbestblockhash")
    
    def get_block(self, block_hash: str, verbosity: int = 1) -> Dict[str, Any]:
        """Get block information"""
        return self._rpc_call("getblock", [block_hash, verbosity])
    
    def is_synced(self) -> bool:
        """Check if node is fully synced"""
        try:
            info = self.get_blockchain_info()
            return not info.get('initialblockdownload', True)
        except Exception as e:
            logger.error(f"Failed to check sync status: {e}")
            return False
    
    def get_sync_progress(self) -> float:
        """Get sync progress percentage"""
        try:
            info = self.get_blockchain_info()
            return info.get('verificationprogress', 0.0) * 100
        except Exception as e:
            logger.error(f"Failed to get sync progress: {e}")
            return 0.0
    
    def satoshi_to_btc(self, satoshis: int) -> Decimal:
        """Convert satoshis to BTC"""
        return Decimal(satoshis) / Decimal('100000000')
    
    def btc_to_satoshi(self, btc: Decimal) -> int:
        """Convert BTC to satoshis"""
        return int(btc * Decimal('100000000'))

# Factory function for easy client creation
def create_btc_client(host: str = None, port: int = None, 
                     username: str = None, password: str = None) -> BTCClient:
    """Create Bitcoin client using environment variables"""
    host = host or os.getenv('BTC_TESTNET_RPC_HOST', 'localhost')
    port = port or int(os.getenv('BTC_TESTNET_RPC_PORT', '18332'))
    username = username or os.getenv('BTC_TESTNET_RPC_USER', 'user')
    password = password or os.getenv('BTC_TESTNET_RPC_PASSWORD', 'password')
    
    if not all([host, port, username, password]):
        raise ValueError("Missing required environment variables: BTC_TESTNET_RPC_HOST, BTC_TESTNET_RPC_PORT, BTC_TESTNET_RPC_USER, BTC_TESTNET_RPC_PASSWORD")
    
    return BTCClient(host, port, username, password, testnet=True)

# Example usage
if __name__ == "__main__":
    # Test the client
    client = create_btc_client()
    
    try:
        # Test connection
        info = client.get_blockchain_info()
        print(f"Connected to Bitcoin {info['chain']} network")
        print(f"Current block: {info['blocks']}")
        print(f"Sync progress: {client.get_sync_progress():.2f}%")
        
        # Test wallet operations
        wallets = client.list_wallets()
        print(f"Available wallets: {wallets}")
        
    except Exception as e:
        print(f"Error: {e}")
